import asyncio
import copy
import json
import os
from typing import List

from aiohttp import web


# TODO: implement grpc client for messenger service

class MessengerHandler:
    _pendingMessages: List[dict]  # list of messages, that have not been requested yet via get_messages
    _pendingMessagesLock: asyncio.Lock
    _grpcClient = None  # grpc client of the messenger service

    def __init__(self):
        self._pendingMessages = []
        self._pendingMessagesLock = asyncio.Lock()

    async def send_message(self, request):
        """
        Body should be of the form:
        {"author": "Ivan", "text": "hey guys"}
        :return web.json_response of the form {"sendTime": ... }
        """
        j = await request.json()  # TODO: use google.protobuf.json_format.ParseDict and raise BadRequest on error
        if 'author' not in j or 'text' not in j:
            raise web.HTTPBadRequest
        print('Got message to send:', json.dumps(j))

        # TODO: your rpc call of the messenger here

        raise NotImplementedError
        return web.json_response({'sendTime': ""})  # TODO: use google.protobuf.json_format.MessageToDict here

    async def get_messages(self, _):
        async with self._pendingMessagesLock:
            res: List[dict] = copy.deepcopy(self._pendingMessages)
            self._pendingMessages = []
        return web.json_response(res)

    # TODO: implement message stream consumer in async method, that fills self._pendingMessages
    #       btw, consumption can be lazy and happen on get_messages, implement in any suitable way


if __name__ == '__main__':
    app = web.Application()
    grpcServerAddr = os.environ.get('MESSENGER_SERVER_ADDR', 'localhost:51075')

    # TODO: create your grpc client with given address and pass it to MessengerHandler constructor

    handler = MessengerHandler()
    app.add_routes([web.post('/getAndFlushMessages', handler.get_messages)])
    app.add_routes([web.post('/sendMessage', handler.send_message)])

    # TODO: run message stream consumer in a background coroutine

    httpPort = os.environ.get('MESSENGER_HTTP_PORT', '8080')
    web.run_app(app, host='0.0.0.0', port=httpPort)
