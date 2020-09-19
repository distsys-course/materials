#!/usr/bin/env python

import argparse
import logging

from dslib import Communicator, Message


class Sender:
    def __init__(self, name, recv_addr):
        self._comm = Communicator(name)
        self._recv_addr = recv_addr

    def run(self):
        while True:
            msg = self._comm.recv_local()

            # deliver INFO-1 message to receiver user
            # underlying transport: unreliable with possible repetitions
            # goal: receiver knows all that were recieved but at most once
            if msg.type == 'INFO-1':
                pass

            # deliver INFO-2 message to receiver user
            # underlying transport: unreliable with possible repetitions
            # goal: receiver knows all at least once
            elif msg.type == 'INFO-2':
                pass

            # deliver INFO-3 message to receiver user
            # underlying transport: unreliable with possible repetitions
            # goal: receiver knows all exactly once
            elif msg.type == 'INFO-3':
                pass

            # deliver INFO-4 message to receiver user
            # underlying transport: unreliable with possible repetitions
            # goal: receiver knows all exactly once in the order
            elif msg.type == 'INFO-4':
                pass

            else:
                err = Message('ERROR', 'unknown command: %s' % msg.type)
                self._comm.send_local(err)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', dest='recv_addr', metavar='host:port',
                        help='receiver address', default='127.0.0.1:9701')
    parser.add_argument('-d', dest='log_level', action='store_const', const=logging.DEBUG,
                        help='print debugging info', default=logging.WARNING)
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s - %(message)s", level=args.log_level)

    sender = Sender('sender', args.recv_addr)
    sender.run()


if __name__ == "__main__":
    main()
