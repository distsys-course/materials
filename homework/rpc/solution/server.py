#!/usr/bin/env python3

import argparse
import logging
import json

from dslib import Communicator, Message

from common import Store


class StoreImpl(Store):
    """This is Store service implementation"""

    def __init__(self):
        self._data = {}

    def put(self, key, value, overwrite):
        if key not in self._data or overwrite:
            self._data[key] = value
            return True
        else:
            return False

    def get(self, key):
        if key not in self._data:
            raise Exception('Key %s not found' % key)
        else:
            return self._data[key]

    def append(self, key, value):
        if key not in self._data:
            raise Exception('Key %s not found' % key)
        else:
            self._data[key] += value
            return self._data[key]

    def remove(self, key):
        if key not in self._data:
            raise Exception('Key %s not found' % key)
        else:
            return self._data.pop(key)


class RpcServer:
    """This is server-side RPC implementation"""

    def __init__(self, addr, service):
        self._comm = Communicator('server', addr)
        self._service = service

    def run(self):
        """Main server loop where it handles incoming RPC requests"""
        while True:
            msg = self._comm.recv()
            args = json.loads(msg.body)
            try:
                res = getattr(self._service, msg._type)(*args)
                response = Message(message_type='RESULT', body=json.dumps(res), headers=msg._headers)
            except Exception as e:
                response = Message(message_type='ERROR', body=str(e), headers=msg._headers)
            self._comm.send(response, msg._sender)



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', dest='addr', metavar='host:port', 
                        help='listen on specified address', default='127.0.0.1:9701')
    parser.add_argument('-d', dest='log_level', action='store_const', const=logging.DEBUG,
                        help='print debugging info', default=logging.WARNING)
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s - %(message)s", level=args.log_level)
    args = parser.parse_args()

    store = StoreImpl()
    server = RpcServer(args.addr, store)
    server.run()


if __name__ == "__main__":
    main()
