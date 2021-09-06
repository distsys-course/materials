#!/usr/bin/env python3

import argparse
import logging

from dslib import Message, Process, Runtime


class PingClient(Process):
    def __init__(self, name, server_addr):
        super().__init__(name)
        self._server_addr = server_addr

    def receive(self, ctx, msg):
        # send PING to server
        if msg.type == 'PING' and msg.is_local():
            ctx.send(msg, self._server_addr)
            ctx.set_timer('timeout', 1)

        # process server response
        elif msg.type == 'PONG':
            ctx.cancel_timer('timeout')
            ctx.send_local(msg)

        # unknown message
        else:
            err = Message('ERROR', 'unknown message: %s' % msg.type)
            ctx.send(err, msg.sender)

    def on_timer(self, ctx, timer):
        err = Message('ERROR', 'No reply from the server')
        ctx.send_local(err)        


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', dest='server_addr', metavar='host:port', 
                        help='server address', default='127.0.0.1:9701')
    parser.add_argument('-d', dest='log_level', action='store_const', const=logging.DEBUG,
                        help='print debugging info', default=logging.WARNING)
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s - %(message)s", level=args.log_level)

    client = PingClient('client', args.server_addr)
    Runtime(client).start()


if __name__ == "__main__":
    main()
