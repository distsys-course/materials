#!/usr/bin/env python3

import argparse
import logging
import random

from dslib import Message, Process, Runtime


class Node(Process):
    def __init__(self, name):
        super().__init__(name)

    def receive(self, ctx, msg):

        if msg.is_local():

            # Client commands (API) ***************************************************************

            # Join the group
            # - message body contains the address of some existing group member
            if msg.type == 'JOIN':
                seed = msg.body
                if seed == ctx.addr():
                    # create new empty group and add local node to it
                    pass
                else:
                    # join existing group
                    pass

            # Leave the group
            elif msg.type == 'LEAVE':
                pass

            # Get a list of group members
            # - return the list of all known alive nodes in MEMBERS message
            elif msg.type == 'GET_MEMBERS':
                ctx.send_local(Message('MEMBERS', [self._name]))

            else:
                err = Message('ERROR', 'unknown command: %s' % msg.type)
                ctx.send_local(err)

        else:

            # Node-to-Node messages ***************************************************************

            # You can introduce any messages for node-to-node communcation
            if msg.type == 'SOME_MESSAGE':
                pass

            else:
                err = Message('ERROR', 'unknown message: %s' % msg.type)
                ctx.send(err, msg.sender)

    def on_timer(self, ctx, timer):
        # type: (Context, str) -> None
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', dest='name', 
                        help='node name (should be unique)', default='1')
    parser.add_argument('-l', dest='addr', metavar='host:port', 
                        help='listen on specified address', default='127.0.0.1:9701')
    parser.add_argument('-d', dest='log_level', action='store_const', const=logging.DEBUG,
                        help='print debugging info', default=logging.WARNING)
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s - %(message)s", level=args.log_level)

    node = Node(args.name)
    Runtime(node, args.addr).start()


if __name__ == "__main__":
    main()
