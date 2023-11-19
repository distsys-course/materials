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
        #   GET {
        #       "key": "some key",
        #       "quorum": 1-3
        #   }
        # Response:
        #   GET_RESP {
        #       "key": "some key",
        #       "values": list of key values (multiple values if there are conflicts, empty list if record is not found)
        #       "context": "opaque string encoding values version (version vector)" (null if record is not found)
        #   }
        if msg.type == 'GET':
            key = msg['key']
            print("[py] Key", key, "replicas:", get_key_replicas(key, len(self._nodes)))
            if key in self._data:
                values = [self._data.get(key)]
                context = 'todo'
            else:
                values = []
                context = None
            resp = Message('GET_RESP', {
                'key': key,
                'values': values,
                'context': context
            })
            ctx.send_local(resp)

        # Store (key, value) record
        # Request:
        #   PUT {
        #       "key": "some key",
        #       "value: "some value",
        #       "context": context from previous read or write operation (can be null if key is written first time),
        #       "quorum": 1-3
        #   }
        # Response:
        #   PUT_RESP {
        #       "key": "some key",
        #       "values: list of key values (multiple values if conflict is detected on write)
        #       "context": "opaque string encoding values version (version vector)"
        #   }
        elif msg.type == 'PUT':
            key = msg['key']
            value = msg['value']
            context = msg['context']
            self._data[key] = value
            resp = Message('PUT_RESP', {
                'key': key,
                'values': [value],
                'context': 'todo'
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
        replicas.append(cur)
        cur = get_next_replica(cur, node_count)
    return replicas


def get_next_replica(i, node_count: int):
    return (i + 1) % node_count