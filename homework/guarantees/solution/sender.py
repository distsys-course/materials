#!/usr/bin/env python

import argparse
import logging

from dslib import Communicator, Message


class Sender:
    def __init__(self, name, recv_addr):
        self._comm = Communicator(name)
        self._recv_addr = recv_addr

        self._msg_counter = 0
        self._id_to_msg = dict()
        self._msgs = set()
        self._msg_queue = []

    def run(self):
        # deliver INFO-1 message to receiver user
        # underlying transport: unreliable with possible repetitions
        # goal: receiver knows all that were received but at most once
        def msg_handler_1(msg):
            if msg is None:
                pass
            elif msg.is_local():
                self._comm.send(msg, self._recv_addr)
            else:
                pass

        # deliver INFO-2 message to receiver user
        # underlying transport: unreliable with possible repetitions
        # goal: receiver knows all at least once
        def msg_handler_2(msg):
            if msg is None:
                pass
            elif msg.is_local():
                msg = Message(msg.type, msg.body, self._msg_counter)
                self._msg_counter += 1
                self._id_to_msg[msg.headers] = msg
            else:  # receiving an ACK
                self._id_to_msg.pop(msg.headers, None)

            for msg in self._id_to_msg.values():
                self._comm.send(msg, self._recv_addr)

        # deliver INFO-3 message to receiver user
        # underlying transport: unreliable with possible repetitions
        # goal: receiver knows all exactly once
        def msg_handler_3(msg):
            if msg is None:
                pass
            elif msg.is_local():
                if msg not in self._msgs:
                    self._msgs.add(msg)
                    msg = Message(msg.type, msg.body, self._msg_counter)
                    self._msg_counter += 1
                    self._id_to_msg[msg.headers] = msg
            else:  # receiving an ACK
                self._id_to_msg.pop(msg.headers, None)

            for msg in self._id_to_msg.values():
                self._comm.send(msg, self._recv_addr)

        # deliver INFO-4 message to receiver user
        # underlying transport: unreliable with possible repetitions
        # goal: receiver knows all exactly once in the order
        def msg_handler_4(msg):
            msg_handler_3(msg)

        def msg_error_handler(msg):
            err = Message('ERROR', 'unknown command: %s' % msg.type)
            self._comm.send_local(err)

        msg = self._comm.recv_local()

        msg_handlers = [msg_handler_1, msg_handler_2, msg_handler_3, msg_handler_4]
        type = int(msg.type[len('INFO-')]) - 1
        handler = msg_handlers[type]

        handler(msg)
        while True:
            msg = self._comm.recv(1)
            handler(msg)


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
