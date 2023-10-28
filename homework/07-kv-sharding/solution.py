from dslabmp import Context, Message, Process
from typing import List


class StorageNode(Process):
    def __init__(self, node_id: str, nodes: List[str]):
        self._id = node_id
        self._nodes = set(nodes)
        self._data = {}

    def on_local_message(self, msg: Message, ctx: Context):
        # Get value for the key.
        # Request:
        #   GET {"key": "some key"}
        # Response:
        #   GET_RESP {"key": "some key", "value": "value for this key"}
        #   GET_RESP {"key": "some key", "value": null} - if record for this key is not found
        if msg.type == 'GET':
            key = msg['key']
            value = self._data.get(key)
            resp = Message('GET_RESP', {
                'key': key,
                'value': value
            })
            ctx.send_local(resp)

        # Store (key, value) record.
        # Request:
        #   PUT {"key": "some key", "value: "some value"}
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

        # Delete value for the key.
        # Request:
        #   DELETE {"key": "some key"}
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

        # Notification that a new node is added to the system.
        # Request:
        #   NODE_ADDED {"id": "node id"}
        # Response:
        #   N/A
        elif msg.type == 'NODE_ADDED':
            self._nodes.add(msg['id'])

        # Notification that a node is removed from the system.
        # Request:
        #   NODE_REMOVED {"id": "node id"}
        # Response:
        #   N/A
        elif msg.type == 'NODE_REMOVED':
            self._nodes.remove(msg['id'])

        # Get number of records stored on the node.
        # Request:
        #   COUNT_RECORDS {}
        # Response:
        #   COUNT_RECORDS_RESP {"count": 100}
        elif msg.type == 'COUNT_RECORDS':
            resp = Message('COUNT_RECORDS_RESP', {
                'count': len(self._data)
            })
            ctx.send_local(resp)

        # Get keys of records stored on the node.
        # Request:
        #   DUMP_KEYS {}
        # Response:
        #   DUMP_KEYS_RESP {"keys": ["key1", "key2", ...]}
        elif msg.type == 'DUMP_KEYS':
            resp = Message('DUMP_KEYS_RESP', {
                'keys': list(self._data.keys())
            })
            ctx.send_local(resp)

    def on_message(self, msg: Message, sender: str, ctx: Context):
        # Implement node-to-node communication using any message types
        pass

    def on_timer(self, timer_name: str, ctx: Context):
        pass
