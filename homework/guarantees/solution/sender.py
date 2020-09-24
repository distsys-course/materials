#!/usr/bin/env python

import argparse
import logging

from dslib import Communicator, Message


class Sender:
    def __init__(self, name, recv_addr):
        self._comm = Communicator(name)
        self._recv_addr = recv_addr
        self.msg_queue = []

    def run(self):
        while True:
            if len(self.msg_queue) > 0:
                msg = self.msg_queue[0]
                self.msg_queue = self.msg_queue[1:]
            else:
                msg = self._comm.recv_local()

            # deliver INFO-1 message to receiver user
            # underlying transport: unreliable with possible repetitions
            # goal: receiver knows all that were recieved but at most once
            if msg.type == 'INFO-1':
                self._comm.send(msg, self._recv_addr)

            # deliver INFO-2 message to receiver user
            # underlying transport: unreliable with possible repetitions
            # goal: receiver knows all at least once
            elif msg.type == 'INFO-2':
                while True:
                    self._comm.send(msg, self._recv_addr)
                    ans = self._comm.recv(1)
                    if ans is not None:
                        if not ans.is_local():
                            ans._sender = msg._sender
                            if msg == ans:
                                break
                        else:
                            self.msg_queue.append(ans)

            # deliver INFO-3 message to receiver user
            # underlying transport: unreliable with possible repetitions
            # goal: receiver knows all exactly once
            elif msg.type == 'INFO-3':
                while True:
                    self._comm.send(msg, self._recv_addr)
                    ans = self._comm.recv(1)
                    if ans is not None:
                        if not ans.is_local():
                            ans._sender = msg._sender
                            if msg == ans:
                                break
                        else:
                            # add to beginning of msg_queue, to fail INFO-4 invariant
                            self.msg_queue = [ans] + self.msg_queue

            # deliver INFO-4 message to receiver user
            # underlying transport: unreliable with possible repetitions
            # goal: receiver knows all exactly once in the order
            elif msg.type == 'INFO-4':
                # Same as INFO-3, but we add msg to the end of self.msg_queue
                while True:
                    self._comm.send(msg, self._recv_addr)
                    ans = self._comm.recv(1)
                    if ans is not None:
                        if not ans.is_local():
                            ans._sender = msg._sender
                            if msg == ans:
                                break
                        else:
                            self.msg_queue.append(ans)

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
