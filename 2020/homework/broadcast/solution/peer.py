#!/usr/bin/env python3

import argparse
import logging

from dslib import Communicator, Message


class Peer:
    def __init__(self, name, addr, peers):
        self._name = name
        self._peers = peers
        self._comm = Communicator(name, addr)
    
    def run(self):
        while True:
            msg = self._comm.recv()

            # local user wants to send a message to the chat
            if msg.type == 'SEND' and msg.is_local():
                # basic broadcast
                bcast_msg = Message('BCAST', msg.body, {'from': self._name})
                for peer in self._peers:
                    self._comm.send(bcast_msg, peer)

            # received broadcasted message
            elif msg.type == 'BCAST':
                # deliver message to the local user
                deliver_msg = Message('DELIVER', msg.headers['from'] + ': ' + msg.body)
                self._comm.send_local(deliver_msg)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', dest='name', 
                        help='peer name (should be unique)', default='peer1')
    parser.add_argument('-l', dest='addr', metavar='host:port', 
                        help='listen on specified address', default='127.0.0.1:9701')
    parser.add_argument('-p', dest='peers', 
                        help='comma separated list of peers', default='127.0.0.1:9701,127.0.0.1:9702')
    parser.add_argument('-d', dest='log_level', action='store_const', const=logging.DEBUG,
                        help='print debugging info', default=logging.WARNING)
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s - %(message)s", level=args.log_level)

    peer = Peer(args.name, args.addr, args.peers.split(','))
    peer.run()


if __name__ == "__main__":
    main()
