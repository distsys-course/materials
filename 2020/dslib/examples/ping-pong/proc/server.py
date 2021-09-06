#!/usr/bin/env python3

import argparse
import logging

from dslib import Message, Process, Runtime


class PingServer(Process):
    def __init__(self, name):
        super().__init__(name)
        self._token = None
        self._last_request_id = 0

    def receive(self, ctx, msg):
        # process PING request
        if msg.type == 'PING':
            resp = Message('PONG', msg.body)
            ctx.send(resp, msg.sender)

        # unknown request
        else:
            err = Message('ERROR', 'unknown message: %s' % msg.type)
            ctx.send(err, msg.sender)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', dest='addr', metavar='host:port', 
                        help='listen on specified address', default='127.0.0.1:9701')
    parser.add_argument('-d', dest='log_level', action='store_const', const=logging.DEBUG,
                        help='print debugging info', default=logging.WARNING)
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s - %(message)s", level=args.log_level)
    args = parser.parse_args()

    server = PingServer('server')
    Runtime(server, args.addr).start()


if __name__ == "__main__":
    main()
