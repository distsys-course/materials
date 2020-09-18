#!/usr/bin/env python3

import argparse
import logging

from dslib import Communicator, Message


class PingServer:
    def __init__(self, name, addr):
        self._comm = Communicator(name, addr)

    def run(self):
        while True:
            req = self._comm.recv()

            # process PING request
            if req.type == 'PING':
                resp = Message('PONG', req.body)
                self._comm.send(resp, req.sender)

            # unknown request
            else:
                err = Message('ERROR', 'unknown request type: %s' % req.type)
                self._comm.send(err, req.sender)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', dest='addr', metavar='host:port', 
                        help='listen on specified address', default='127.0.0.1:9701')
    parser.add_argument('-d', dest='log_level', action='store_const', const=logging.DEBUG,
                        help='print debugging info', default=logging.WARNING)
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s - %(message)s", level=args.log_level)
    args = parser.parse_args()

    server = PingServer('server', args.addr)
    server.run()


if __name__ == "__main__":
    main()
