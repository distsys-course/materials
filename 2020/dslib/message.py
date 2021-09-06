import json


class Message:

    def __init__(self, message_type, body=None, headers=None, sender=None, message_id=None):
        self._type = message_type
        self._headers = headers
        self._body = body
        self._sender = sender
        self._id = message_id

    @property
    def type(self):
        return self._type

    @property
    def body(self):
        return self._body

    @property
    def headers(self):
        return self._headers

    @property
    def sender(self):
        return self._sender

    def is_local(self):
        return self._sender is not None and self._sender == 'local'

    def marshall(self, sender=None, message_id=None):
        message = {}
        message['type'] = self._type
        if self._body is not None:
            message['body'] = self._body
        if self._headers is not None:
            message['headers'] = self._headers
        if sender is not None:
            message['sender'] = sender
        elif self._sender is not None:
            message['sender'] = self._sender
        if message_id is not None:
            message['id'] = message_id
        elif self._id is not None:
            message['id'] = self._id
        return json.dumps(message).encode('utf-8')

    @staticmethod
    def unmarshall(raw_bytes):
        message = json.loads(raw_bytes.decode('utf-8'))
        message_type = message['type']
        body = message.get('body', None)
        headers = message.get('headers', None)
        sender = message.get('sender', None)
        message_id = message.get('id', None)
        return Message(message_type, body, headers, sender, message_id)

    def __str__(self):
        out = self._type
        if self._headers is not None:
            out += " " + json.dumps(self._headers)
        if self._body is not None:
            out += " " + str(self._body)
        return out

    def __eq__(self, other):
        return self._type == other._type and \
               self._headers == other._headers and \
               self._body == other._body and \
               self._sender == other._sender

    def __neq__(self, other):
        return not __eq__(self, other)

    def __hash__(self):
        return hash(self._type) ^ hash(self._headers) ^ hash(self._body) ^ \
               hash(self._sender)