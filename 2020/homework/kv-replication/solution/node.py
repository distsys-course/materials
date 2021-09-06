#!/usr/bin/env python3

import argparse
import logging

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
            # - request body: 
            #   - key: key (string)
            #   - quorum: quorum size for reading (int)
            # - reponse: GET_RESP message, body contains 
            #   - values: list of value versions (empty list if record is not found)
            #   - metadata: list of metadata (for each values[i] its metadata is provided in metadata[i])
            elif msg.type == 'GET':
                pass

            # Store value for the key
            # - request body: 
            #   - key: key (string)
            #   - value: value (string)
            #   - metadata: metadata of previously read or written value version (optional)
            #   - quorum: quorum size for writing (int)
            # - response: PUT_RESP message, body contains metadata of written version
            elif msg.type == 'PUT':
                pass

            # Get nodes responsible for the key
            # - request body: key (string)
            # - response: LOOKUP_RESP message, body contains list with [node_name, node_address] elements
            elif msg.type == 'LOOKUP':
                pass

            # Get number of records stored on the node
            # - request body: none
            # - response: COUNT_RECORDS_RESP message, body contains the number of stored records
            elif msg.type == 'COUNT_RECORDS':
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
