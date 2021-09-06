import abc


class Context(object):
    @abc.abstractmethod
    def addr(self):
        # type: None -> str
        pass

    @abc.abstractmethod
    def send(self, message, recepient):
        # type: (Message, str) -> None
        pass

    @abc.abstractmethod
    def send_local(self, message):
        # type: Message -> None
        pass

    @abc.abstractmethod
    def set_timer(self, timer, interval):
        # type: (str, int) -> None
        pass

    @abc.abstractmethod
    def cancel_timer(self, timer):
        # type: (str) -> None
        pass

class Process:
    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        # type: () -> str
        return self._name

    @abc.abstractmethod
    def receive(self, ctx, message):
        # type: (Context, Message) -> None
        pass

    def on_timer(self, ctx, timer):
        # type: (Context, str) -> None
        pass
