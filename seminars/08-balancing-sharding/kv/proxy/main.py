import argparse
import hashlib
import requests
import yaml
from flask import Flask, jsonify, request
from abc import ABC, abstractmethod

app = Flask(__name__)

class Proxy(ABC):
    def __init__(self, nodes):
        self.nodes = nodes

    @abstractmethod
    def put(self, key, value):
        pass

    @abstractmethod
    def get(self, key):
        pass

proxy: Proxy = None


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


@app.route('/put', methods=['POST'])
def put_handler():
    key = request.args.get('key')
    value = request.get_json().get('value')

    if key is None or value is None:
        return jsonify({'error': 'Please provide key and value.'}), 400

    return proxy.put(key, value)

@app.route('/get', methods=['GET'])
def get_handler():
    key = request.args.get('key')

    if key is None:
        return jsonify({'error': 'Please provide key.'}), 400

    return proxy.get(key)


@app.route('/state', methods=['GET'])
def state_handler():
    results = ""
    for node_name, node in proxy.nodes.items():
        url = f'{node["url"]}/state'
        response = requests.get(url)
        results += f'<h1 style="font-family: monospace;">Response from {url}</h1>{response.content.decode("utf-8")}<hr>'

    return f"<html><body>{results}</body></html>", 200


def load_proxy_from_config(config_path):
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)

    mode = config.get('mode', '')
    nodes = {}
    for node in config['nodes']:
        name = node['name']
        url = node['url']
        nodes[name] = {'url': url}
    if mode == 'sharding':
        return ShardingProxy(nodes)
    elif mode == 'replication':
        return ReplicatingProxy(nodes)
    raise ValueError('Invalid mode, allowed values: sharding, replication')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Flask app acting as a proxy for key-value nodes')
    parser.add_argument('-c', '--config', type=str, required=True, help='Path to the YAML config file')
    parser.add_argument('-p', '--port', type=int, help='Port of the server')
    args = parser.parse_args()

    proxy = load_proxy_from_config(args.config)

    app.run('0.0.0.0', args.port)