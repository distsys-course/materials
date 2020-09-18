import abc
import select
import socket
import time


class Transport:

    def __init__(self, addr):
        self._addr = addr

    @property
    def addr(self):
        # type: () -> str
        return self._addr

    @abc.abstractmethod
    def send(self, data, to):
        # type: (bytes, str) -> None
        pass

    @abc.abstractmethod
    def recv(self, timeout=None):
        # type: (None, float) -> bytes
        pass

    @abc.abstractmethod
    def destroy(self):
        # type: None -> None
        pass


class UDPTransport(Transport):

    def __init__(self, addr=None):
        super().__init__(addr)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setblocking(0)
        if addr is not None:
            self._sock.bind(self._host_port(addr))
        else:
            self._sock.bind(('', 0))
            self._host, self._port = self._sock.getsockname()
            self._addr = "%s:%d" % (self._host, self._port)
        self._stopped = False

    def send(self, data, to):
        self._sock.sendto(data, self._host_port(to))

    def recv(self, timeout=None):
        if timeout is not None:
            deadline = time.time() + timeout
        while not self._stopped and (timeout is None or time.time() <= deadline):
            ready = select.select([self._sock], [], [], 0.1)
            if ready[0]:
                data, _ = self._sock.recvfrom(4096)
                return data
        return None

    def destroy(self):
        self._stopped = True
        self._sock.close()

    def _host_port(self, addr):
        host_port = addr.split(':')
        return (host_port[0], int(host_port[1]))