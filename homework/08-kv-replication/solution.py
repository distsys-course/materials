import hashlib
from dslabmp import Context, Message, Process
from typing import List


class StorageNode(Process):
    def __init__(self, node_id: str, nodes: List[str]):
        self._id = node_id
        self._nodes = nodes
        self._data = {}

    def on_local_message(self, msg: Message, ctx: Context):
        # Get key value.
        # Request:
        #   GET {"key": "some key", "quorum": 1-3}
        # Response:
        #   GET_RESP {"key": "some key", "value": "value for this key"}
        #   GET_RESP {"key": "some key", "value": null} - if record for this key is not found
        if msg.type == 'GET':
            key = msg['key']
            print("[py] Key", key, "replicas:", get_key_replicas(key, len(self._nodes)))
            value = self._data.get(key)
            resp = Message('GET_RESP', {
                'key': key,
                'value': value
            })
            ctx.send_local(resp)

        # Store (key, value) record
        # Request:
        #   PUT {"key": "some key", "value: "some value", "quorum": 1-3}
        # Response:
        #   PUT_RESP {"key": "some key", "value: "some value"}
        elif msg.type == 'PUT':
            key = msg['key']
            value = msg['value']
            self._data[key] = value
            resp = Message('PUT_RESP', {
                'key': key,
                'value': value
            })
            ctx.send_local(resp)

        # Delete value for the key
        # Request:
        #   DELETE {"key": "some key", "quorum": 1-3}
        # Response:
        #   DELETE_RESP {"key": "some key", "value": "some value"}
        elif msg.type == 'DELETE':
            key = msg['key']
            value = self._data.pop(key, None)
            resp = Message('DELETE_RESP', {
                'key': key,
                'value': value
            })
            ctx.send_local(resp)

    def on_message(self, msg: Message, sender: str, ctx: Context):
        # Implement node-to-node communication using any message types
        pass

    def on_timer(self, timer_name: str, ctx: Context):
        pass


def get_key_replicas(key: str, node_count: int):
    replicas = []
    key_hash = int.from_bytes(hashlib.md5(key.encode('utf8')).digest(), 'little', signed=False)
    cur = key_hash % node_count
    for _ in range(3):
        replicas.append(str(cur))
        cur = get_next_replica(cur, node_count)
    return replicas


def get_next_replica(i, node_count: int):
    return (i + 1) % node_count
