import copy
import json
import os
import random
import threading
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import List, Dict

import grpc
import google.protobuf.json_format  # ParseDict, MessageToDict
import google.protobuf.empty_pb2  # Empty
from messenger.proto import messenger_pb2
from messenger.proto import messenger_pb2_grpc


class PostBox:
    def __init__(self):
        self._messages: List[Dict] = []
        self._lock = threading.Lock()

    def collect_messages(self) -> List[Dict]:
        with self._lock:
            messages = copy.deepcopy(self._messages)
            self._messages = []
        return messages

    def put_message(self, message: Dict):
        with self._lock:
            self._messages.append(message)


class MessageHandler(BaseHTTPRequestHandler):
    _stub = None
    _postbox: PostBox

    def _read_content(self):
        content_length = int(self.headers['Content-Length'])
        bytes_content = self.rfile.read(content_length)
        return bytes_content.decode('ascii')

    # noinspection PyPep8Naming
    def do_POST(self):
        if self.path == '/sendMessage':
            response = self._send_message(self._read_content())
        elif self.path == '/getAndFlushMessages':
            response = self._get_messages()
        else:
            self.send_error(HTTPStatus.NOT_IMPLEMENTED)
            self.end_headers()
            return

        response_bytes = json.dumps(response).encode('ascii')
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Length', str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def _send_message(self, content: str) -> dict:
        json_request = json.loads(content)

        # TODO: use google.protobuf.json_format.ParseDict

        # TODO: your rpc call of the messenger here

        # TODO: use google.protobuf.json_format.MessageToDict here
        return {'sendTime': ''}

    def _get_messages(self) -> List[dict]:
        return self._postbox.collect_messages()


def main():
    grpc_server_address = os.environ.get('MESSENGER_SERVER_ADDR', 'localhost:51075')

    # TODO: create your grpc client with given address
    stub = None

    # A list of messages obtained from the server-py but not yet requested by the user to be shown
    # (via the http's /getAndFlushMessages).
    postbox = PostBox()

    # TODO: Implement and run a messages stream consumer in a background thread here.
    # It should fetch messages via the grpc client and store them in the postbox.

    # Pass the stub and the postbox to the HTTP server.
    # Dirty, but this simple http server doesn't provide interface
    # for passing arguments to the handler c-tor.
    MessageHandler._stub = stub
    MessageHandler._postbox = postbox

    http_port = os.environ.get('MESSENGER_HTTP_PORT', '8080')
    http_server_address = ('0.0.0.0', int(http_port))

    # NB: handler_class is instantiated for every http request. Do not store any inter-request state in it.
    httpd = HTTPServer(http_server_address, MessageHandler)
    httpd.serve_forever()


if __name__ == '__main__':
    main()
