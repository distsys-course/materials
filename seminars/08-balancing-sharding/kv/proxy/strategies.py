from dataclasses import dataclass
import json
from collections import defaultdict
import math
from typing import Union
from flask import jsonify
import requests
from abc import ABC, abstractmethod
import base64

from requests.exceptions import ConnectionError

import hashlib


class Proxy(ABC):
    def __init__(self, nodes):
        self.nodes = nodes
    
    @abstractmethod
    def put(self, key, value):
        pass

    @abstractmethod
    def get(self, key):
        pass


class ShardingProxy(Proxy):
    def __init__(self, nodes):
        super().__init__(nodes)

    def put(self, key, value):
        node = self.get_node(key)
        if node is None:
            return {'error': 'No nodes available.'}, 500

        url = f'{node["url"]}/put?key={key}'
        response = requests.post(url, json={'value': value})

        return response.content, response.status_code

    def get(self, key):
        node = self.get_node(key)
        if node is None:
            return {'error': 'No nodes available.'}, 500

        url = f'{node["url"]}/get?key={key}'
        response = requests.get(url)

        return response.content, response.status_code

    def get_node(self, key):
        if len(self.nodes) == 0:
            return None

        hash_val = hashlib.sha256(key.encode()).hexdigest()
        node_index = int(hash_val, 16) % len(self.nodes)
        return self.nodes[list(self.nodes.keys())[node_index]]


class ReplicatingProxy(Proxy):
    def __init__(self, nodes):
        super().__init__(nodes)

    def put(self, key, value):
        responses = []
        for _, node in self.nodes.items():
            url = f'{node["url"]}/put?key={key}'
            response = requests.post(url, json={'value': value})
            if response.status_code == 200:
                responses.append(response.content)

        if len(responses) == 0:
            return {'error': 'No nodes available.'}, 500

        return responses[0], 200

    def get(self, key):
        non_ok_responses = dict()
        for node_name, node in self.nodes.items():
            url = f'{node["url"]}/get?key={key}'
            response = requests.get(url)
            if response.status_code == 200:
                return response.content, 200
            else:
                non_ok_responses[node_name] = response.json()

        return jsonify({'error': 'None of the nodes responded with 200.', 'responses': non_ok_responses}), 500


class ReplicatingQuorumProxy(Proxy):
    def __init__(self, nodes):
        super().__init__(nodes)

    def put(self, key, value):
        responses = []
        for _, node in self.nodes.items():
            url = f'{node["url"]}/put?key={key}'
            response = requests.post(url, json={'value': value})
            if response.status_code == 200:
                responses.append(response.content)

        if len(responses) == 0:
            return {'error': 'No nodes available.'}, 500

        if len(responses) > len(self.nodes) / 2:
            return responses[0], 200

        return jsonify({'error': 'Not enough responses for quorum write.', 'responses': responses}), 300

    def get(self, key):
        non_ok_responses = dict()
        values = defaultdict(lambda: 0)
        for node_name, node in self.nodes.items():
            url = f'{node["url"]}/get?key={key}'
            response = requests.get(url)
            if response.status_code == 200:
                values[response.content] += 1
            else:
                non_ok_responses[node_name] = response.json()

        for value, cnt in values.items():
            if cnt > len(self.nodes) / 2:
                return value, 200

        if len(values) > 0:
            values_for_response = []
            for value, cnt in values.items():
                values_for_response.append({'value': json.loads(value)['value'], 'count': cnt})
            return jsonify({'error': 'Got multiple values, none of them has enough responses for quorum', 'values': values_for_response}), 300

        return jsonify({'error': 'None of the nodes responded with 200.', 'responses': non_ok_responses}), 500


@dataclass
class DataBlock:
    index: Union[int, None]
    data: bytes


def raid3_split(data_blocks: int, value: str) -> list[DataBlock]:
    bytes_value = value.encode()
    L = int(math.ceil(len(bytes_value) / data_blocks))
    split: list[bytes] = [
        bytes_value[i:i + L]
        for i in range(0, len(bytes_value), L)
    ]
    res = []
    for i, block in enumerate(split):
        data_bytes: bytes = block + (L - len(block)) * b'\x00'
        res.append(DataBlock(i, data_bytes))

    return res


def raid3_parity(blocks: list[DataBlock]) -> DataBlock:
    parity = len(blocks[0].data) * b'\x00'
    for block in blocks:
        if len(block.data) != len(parity):
            raise ValueError('All blocks must have the same length.')
        parity = bytes(a ^ b for a, b in zip(parity, block.data))
    return DataBlock(None, parity)


def raid3_join(blocks: list[DataBlock]) -> str:
    return (b''.join(block.data for block in blocks[:-1])).rstrip(b'\x00').decode()


def raid3_recover(blocks: list[Union[DataBlock, None]], error_index: int) -> str:
    if error_index == len(blocks) - 1:
        return raid3_join(blocks)

    recovered = None
    for block in blocks:
        if recovered is None and block is not None:
            recovered = len(block.data) * b'\x00'
        if block is None:
            continue
        recovered = bytes(a ^ b for a, b in zip(recovered, block.data))

    blocks[error_index] = DataBlock(error_index, recovered)
    return raid3_join(blocks)


class RAID3Proxy(Proxy):
    def __init__(self, nodes):
        if len(nodes) < 3:
            raise ValueError('RAID3 requires at least 3 nodes.')
        if len(nodes) > 255:
            raise ValueError('This implementation does not support more than 255 nodes.')
        super().__init__(nodes)
        self._divisor = len(self.nodes) - 1
    
    def put(self, key, value):
        if len(value) < self._divisor:
            return {'error': f'Too small body for RAID3 algorithm with {self._divisor} blocks.'}, 500
        
        blocks = raid3_split(self._divisor, value)
        parity = raid3_parity(blocks)

        for node, block in zip(self.nodes.values(), blocks + [parity]):
            value_dict = {
                'index': block.index,
                'value': base64.b64encode(block.data).decode('utf-8'),
            }

            url = f'{node["url"]}/put?key={key}'
            response = requests.post(url, json={'value': json.dumps(value_dict)})
            if response.status_code != 200:
                return {'error': f'Error while writing to node {node["url"]}.'}, 500

        return jsonify({'message': 'Key-value pair stored successfully on all nodes.'}), 200

    def get(self, key):
        blocks = []
        errors = []
        error_index = None
        for node in self.nodes.values():
            url = f'{node["url"]}/get?key={key}'
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    value_dict = json.loads(response.json()['value'])
                    blocks.append(DataBlock(value_dict['index'], base64.b64decode(value_dict['value'])))
                else:
                    error_index = len(blocks)
                    blocks.append(None)
                    errors.append(response)
                    if len(errors) > 1:
                        return {'error': f'Got too many errors while reading key \'{key}\''}, 500
            except ConnectionError as e:
                error_index = len(blocks)
                blocks.append(None)
                errors.append(e)
                if len(errors) > 1:
                    return {'error': f'Got too many errors while reading key \'{key}\''}, 500
    
        if error_index is None:
            value = raid3_join(blocks)
        else:
            value = raid3_recover(blocks, error_index)

        return jsonify({'value': value}), 200
