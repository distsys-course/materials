#!/usr/bin/env python3

import argparse
import logging
import json

from dslib import Communicator, Message

from common import Store


class StoreProxy(Store):
    """This is client-side proxy for Store service"""

    def __init__(self, server_addr):
        self._client = RpcClient(server_addr)

    def put(self, key, value, overwrite):
        return self._client.call('put', key, value, overwrite)

    def get(self, key):
        return self._client.call('get', key)

    def append(self, key, value):
        return self._client.call('append', key, value)

    def remove(self, key):
        return self._client.call('remove', key)


class RpcClient:
    """This is client-side RPC implementation"""

    def __init__(self, server_addr):
        self._comm = Communicator('client')
        self._server_addr = server_addr
        self._message_id = 0

    def call(self, func, *args):
        """Call function on RPC server and return result"""

        def is_idempotent(func_name):
            return func_name in ['get', 'put', 'remove']

        msg_body = json.dumps(args)
        self._message_id += 1
        msg = Message(message_type=func, body=msg_body, headers={'id': self._message_id})
        while True:
            self._comm.send(msg, self._server_addr)
            response = self._comm.recv(1)
            if response is not None and response.headers['id'] == msg.headers['id']:
                if response.type == 'ERROR':
                    raise Exception(response.body)
                if response.type != 'RESULT':
                    raise Exception('Unknown message type')
                return json.loads(response.body)
            if not is_idempotent(func):
                raise Exception('Response timeout')


class User:
    """This class mocks a user during tests by invoking proxy functions"""

    def __init__(self, proxy):
        self._proxy = proxy
        # reuse communicator from proxy
        self._comm = proxy._client._comm

    def run(self):
        while True:
            msg = self._comm.recv()

            # Calls are passed as "CALL func arg1 arg2 ..."
            if msg.type == 'CALL' and msg.is_local():
                params = msg.body.split(' ')
                func = params[0]
                args = map(self._parse_arg, params[1:])

                try:
                    if func == 'get':
                        result = self._proxy.get(*args)
                    elif func == 'put':
                        result = self._proxy.put(*args)
                    elif func == 'append':
                        result = self._proxy.append(*args)
                    elif func == 'remove':
                        result = self._proxy.remove(*args)
                    resp = Message('RESULT', result)
                    self._comm.send_local(resp)
                except Exception as err:
                    resp = Message('ERROR', str(err))
                    self._comm.send_local(resp)

    def _parse_arg(self, arg):
        if arg == 'True':
            return True
        elif arg == 'False':
            return False
        else:
            return arg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', dest='server_addr', metavar='host:port',
                        help='server address', default='127.0.0.1:9701')
    parser.add_argument('-d', dest='log_level', action='store_const', const=logging.DEBUG,
                        help='print debugging info', default=logging.WARNING)
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s - %(message)s", level=args.log_level)

    store = StoreProxy(args.server_addr)
    user = User(store)
    user.run()


if __name__ == "__main__":
    main()
