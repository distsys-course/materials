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

            # Add new node to the system
            # - request body: address of some existing node
            # - response: none
            if msg.type == 'JOIN':
                pass

            # Remove node from the system
            # - request body: none
            # - response: none
            elif msg.type == 'LEAVE':
                pass

            # Get a list of nodes in the system
            # - request body: none
            # - response: MEMBERS message, body contains the list of all known alive nodes
            elif msg.type == 'GET_MEMBERS':
                pass

            # Get key value
            # - request body: key
            # - reponse: GET_RESP message, body contains value or empty string if record is not found
            elif msg.type == 'GET':
                pass

            # Store value for the key
            # - request body: string "key=value"
            # - response: PUT_RESP message, body is empty
            elif msg.type == 'PUT':
                pass

            # Delete value for the key
            # - request body: key
            # - response: DELETE_RESP message, body is empty
            elif msg.type == 'DELETE':
                pass

            # Get node responsible for the key
            # - request body: key
            # - response: LOOKUP_RESP message, body contains the node name
            elif msg.type == 'LOOKUP':
                pass

            # Get number of records stored on the node
            # - request body: none
            # - response: COUNT_RECRODS_RESP message, body contains the number of stored records
            elif msg.type == 'COUNT_RECORDS':
                pass

            # Get keys of records stored on the node
            # - request body: none
            # - response: DUMP_KEYS_RESP message, body contains the list of stored keys
            elif msg.type == 'DUMP_KEYS':
                pass

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
