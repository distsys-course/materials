import random

from dslabmp import Context, Message, Process


class Peer(Process):
    def __init__(self, proc_id: int, proc_count: int, fanout: int):
        self._id = proc_id
        self._proc_count = proc_count
        self._peers = [id for id in range(0, self._proc_count) if id != self._id]
        self._fanout = fanout
        self._info = None
        self._stop_prob = 0.8
        self._stopped = False

    def on_local_message(self, msg: Message, ctx: Context):
        if msg.type == 'START':
            ctx.set_timer("gossip", 1)
        elif msg.type == 'BROADCAST':
            self.got_info(msg['info'], ctx)

    def on_message(self, msg: Message, sender: str, ctx: Context):
        if msg.type == 'GOSSIP_REQ':
            if self._info is not None:
                ctx.send(Message('GOSSIP_RESP', {'info': self._info}), sender)
            elif msg['info'] is not None:
                self.got_info(msg['info'], ctx)
        elif msg.type == 'GOSSIP_RESP':
            self.got_info(msg['info'], ctx)

    def on_timer(self, timer_name: str, ctx: Context):
        self.gossip(ctx)
        ctx.set_timer("gossip", 1)

    def got_info(self, info, ctx):
        if self._info is None:
            self._info = info
            ctx.send_local(Message('DELIVER', {'info': self._info}))
        else:
            self.try_stop(ctx)

    def gossip(self, ctx):
        for peer in random.sample(self._peers, self._fanout):
            ctx.send(Message('GOSSIP_REQ', {'info': self._info}), str(peer))

    def try_stop(self, ctx):
        if not self._stopped and random.uniform(0, 1) < self._stop_prob:
            self._stopped = True
            ctx.cancel_timer("gossip")
            ctx.send_local(Message('STOPPED', {}))
