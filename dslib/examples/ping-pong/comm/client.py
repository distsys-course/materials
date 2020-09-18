#!/usr/bin/env python3

import argparse
import logging

from dslib import Communicator, Message


class PingClient:
    def __init__(self, name, server_addr):
        self._comm = Communicator(name)
        self._server_addr = server_addr

    def run(self):
        while True:
            command = self._comm.recv_local()

            # send PING to server
            if command.type == 'PING':
                self._comm.send(command, self._server_addr)
                resp = self._comm.recv(timeout=1)
                if resp is not None and resp.type == 'PONG':
                    self._comm.send_local(resp)
                else:
                    err = Message('ERROR', 'No reply from the server')
                    self._comm.send_local(err)

            # unknown command
            else:
                err = Message('ERROR', 'unknown command: %s' % command.type)
                self._comm.send_local(err)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', dest='server_addr', metavar='host:port', 
                        help='server address', default='127.0.0.1:9701')
    parser.add_argument('-d', dest='log_level', action='store_const', const=logging.DEBUG,
                        help='print debugging info', default=logging.WARNING)
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s - %(message)s", level=args.log_level)

    client = PingClient('client', args.server_addr)
    client.run()


if __name__ == "__main__":
    main()
