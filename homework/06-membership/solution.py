from dslabmp import Context, Message, Process


class GroupMember(Process):
    def __init__(self, proc_id: str):
        self._id = proc_id

    def on_local_message(self, msg: Message, ctx: Context):
        if msg.type == 'JOIN':
            # Add process to the group
            seed = msg['seed']
            if seed == self._id:
                # create new empty group and add process to it
                pass
            else:
                # join existing group
                pass
        elif msg.type == 'LEAVE':
            # Remove process from the group
            pass
        elif msg.type == 'GET_MEMBERS':
            # Get a list of group members
            # - return the list of all known alive processes in MEMBERS message
            ctx.send_local(Message('MEMBERS', {'members': [self._id]}))

    def on_message(self, msg: Message, sender: str, ctx: Context):
        # Implement communication between processes using any message types
        pass

    def on_timer(self, timer_name: str, ctx: Context):
        pass
