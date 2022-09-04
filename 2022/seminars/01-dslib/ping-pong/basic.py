from dslib import Context, Message, Node


class PingClient(Node):
    def __init__(self, node_id: str, server_id: str):
        self._id = node_id
        self._server_id = server_id

    def on_local_message(self, msg: Message, ctx: Context):
        if msg.type == 'PING':
            ctx.send(msg, self._server_id)

    def on_message(self, msg: Message, sender: str, ctx: Context):
        # process messages from server
        if msg.type == 'PONG':
            ctx.send_local(msg)

    def on_timer(self, timer_name: str, ctx: Context):
        # process fired timers here
        pass


class PingServer(Node):
    def __init__(self, node_id: str):
        self._id = node_id

    def on_local_message(self, msg: Message, ctx: Context):
        # not used
        pass

    def on_message(self, msg: Message, sender: str, ctx: Context):
        # process messages from client
        if msg.type == 'PING':
            pong = Message('PONG', {'value': msg['value']})
            ctx.send(pong, sender)

    def on_timer(self, timer_name: str, ctx: Context):
        # process fired timers here
        pass
