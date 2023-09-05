from dslabmp import Context, Message, Process


class PingClient(Process):
    def __init__(self, proc_id: str, server_id: str):
        self._id = proc_id
        self._server_id = server_id

    def on_local_message(self, msg: Message, ctx: Context):
        # process messages from the local user
        if msg.type == 'PING':
            ctx.send(msg, self._server_id)

    def on_message(self, msg: Message, sender: str, ctx: Context):
        # process messages from the server
        if msg.type == 'PONG':
            ctx.send_local(msg)

    def on_timer(self, timer_name: str, ctx: Context):
        # process fired timers
        pass


class PingServer(Process):
    def __init__(self, proc_id: str):
        self._id = proc_id

    def on_local_message(self, msg: Message, ctx: Context):
        # process messages from the local user (not used in this example)
        pass

    def on_message(self, msg: Message, sender: str, ctx: Context):
        # process messages from the client
        if msg.type == 'PING':
            pong = Message('PONG', {'value': msg['value']})
            ctx.send(pong, sender)

    def on_timer(self, timer_name: str, ctx: Context):
        # process fired timers
        pass
