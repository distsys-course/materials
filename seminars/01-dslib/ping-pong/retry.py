from dslib import Context, Message, Node


class PingClient(Node):
    def __init__(self, node_id: str, server_id: str):
        self._id = node_id
        self._server_id = server_id
        self._ping = None

    def on_local_message(self, msg: Message, ctx: Context):
        if msg.type == 'PING':
            self._ping = msg
            ctx.send(msg, self._server_id)
            ctx.set_timer('check_pong', 3)

    def on_message(self, msg: Message, sender: str, ctx: Context):
        # process messages from server
        if msg.type == 'PONG' and self._ping is not None:
            self._ping = None
            ctx.cancel_timer('check_pong')
            ctx.send_local(msg)

    def on_timer(self, timer_name: str, ctx: Context):
        # process fired timers here
        if timer_name == 'check_pong':
            ctx.send(self._ping, self._server_id)
            ctx.set_timer('check_pong', 3)


class PingServer(Node):
    def __init__(self, node_id: str):
        self._id = node_id

    def on_local_message(self, msg: Message, ctx: Context):
        # not used
        pass

    def on_message(self, msg: Message, sender: str, ctx: Context):
        # process messages from client
        pong = Message('PONG', {'value': msg['value']})
        ctx.send(pong, sender)

    def on_timer(self, timer_name: str, ctx: Context):
        # process fired timers here
        pass
