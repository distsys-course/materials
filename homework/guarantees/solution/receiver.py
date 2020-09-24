#!/usr/bin/env python

import argparse
import copy
import logging

from dslib import Communicator, Message


class Receiver:
    def __init__(self, name, addr):
        self._comm = Communicator(name, addr)
        self.received_messages = set()

    def run(self):
        while True:
            msg = self._comm.recv()

            # deliver INFO-1 message to receiver user
            # underlying transport: unreliable with possible repetitions
            # goal: receiver knows all that were recieved but at most once
            if msg.type == 'INFO-1':
                if msg not in self.received_messages:
                    self._comm.send_local(msg)
                    self.received_messages.add(msg)

            # deliver INFO-2 message to receiver user
            # underlying transport: unreliable with possible repetitions
            # goal: receiver knows all at least once
            elif msg.type == 'INFO-2':
                self._comm.send_local(msg)
                self._comm.send(msg, msg._sender)

            # deliver INFO-3 message to receiver user
            # underlying transport: unreliable with possible repetitions
            # goal: receiver knows all exactly once
            elif msg.type == 'INFO-3':
                if msg not in self.received_messages:
                    self._comm.send_local(msg)
                    self.received_messages.add(msg)
                self._comm.send(msg, msg._sender)

            # deliver INFO-4 message to receiver user
            # underlying transport: unreliable with possible repetitions
            # goal: receiver knows all exactly once in the order
            elif msg.type == 'INFO-4':
                # Same as INFO-3
                if msg not in self.received_messages:
                    self._comm.send_local(msg)
                    self.received_messages.add(msg)
                self._comm.send(msg, msg._sender)

            # unknown message
            else:
                err = Message('ERROR', 'unknown message type: %s' % msg.type)
                self._comm.send(err, msg.sender)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', dest='addr', metavar='host:port',
                        help='listen on specified address', default='127.0.0.1:9701')
    parser.add_argument('-d', dest='log_level', action='store_const', const=logging.DEBUG,
                        help='print debugging info', default=logging.WARNING)
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s - %(message)s", level=args.log_level)
    args = parser.parse_args()

    receiver = Receiver('receiver', args.addr)
    receiver.run()


if __name__ == "__main__":
    main()
