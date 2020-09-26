import abc
import grpc
import json
import logging
import os
import queue
import signal
import sys
import time
import threading
from google.protobuf.any_pb2 import Any

from .message import Message
from .transport import UDPTransport

from .proto import test_server_pb2 as pb
from .proto import test_server_pb2_grpc as rpc


class TestMode:
    WATCH = 'WATCH'
    CONTROL = 'CONTROL'


class Communicator:

    class TestServerClient:
        def __init__(self, server_addr, runtime):
            self._server_addr = server_addr
            self._events = queue.Queue()
            self._command_stream = None
            self._runtime = runtime

        def start(self):
            tserver = rpc.TestServerStub(grpc.insecure_channel(self._server_addr))
            self._command_stream = tserver.AttachProcess(iter(self._events.get, None))
            threading.Thread(target=self._process_commands).start()

        def on_process_started(self, process_id, address):
            self._send_event(pb.ProcessStartedEvent(process_id=process_id, address=address))

        def on_process_stopped(self):
            self._send_event(pb.ProcessStoppedEvent())

        def on_new_message(self, message_id, recepient, raw_message):
            self._send_event(pb.NewMessageEvent(message_id=message_id, recepient=recepient, message=raw_message))

        def on_message_received(self, message_id, raw_message=None):
            if raw_message is None:
                self._send_event(pb.MessageReceivedEvent(message_id=message_id))
            else:
                self._send_event(pb.MessageDataReceivedEvent(message_id=message_id, message=raw_message))

        def on_message_processed(self, message_id):
            self._send_event(pb.MessageProcessedEvent(message_id=message_id))

        def on_new_timer(self, timer_id, name, interval):
            self._send_event(pb.NewTimerEvent(timer_id=timer_id, name=name, interval=interval))

        def on_timer_fired(self, timer_id):
            self._send_event(pb.TimerFiredEvent(timer_id=timer_id))

        def on_timer_processed(self, timer_id):
            self._send_event(pb.TimerProcessedEvent(timer_id=timer_id))

        def on_timer_canceled(self, timer_id):
            self._send_event(pb.TimerCanceledEvent(timer_id=timer_id))

        def _process_commands(self):
            try:
                for c in self._command_stream:
                    if c.Is(pb.ReceiveLocalMessageCommand.DESCRIPTOR):
                        command = pb.ReceiveLocalMessageCommand()
                        c.Unpack(command)
                        self._runtime._handle_receive_local_message(command.message)

                    if c.Is(pb.ReceiveMessageCommand.DESCRIPTOR):
                        command = pb.ReceiveMessageCommand()
                        c.Unpack(command)
                        self._runtime._handle_receive_message(command.message_id, command.sender, command.message)

                    if c.Is(pb.FireTimerCommand.DESCRIPTOR):
                        command = pb.FireTimerCommand()
                        c.Unpack(command)
                        self._runtime._handle_fire_timer(command.timer_id)
            except grpc.RpcError as e:
                logging.debug("grpc error %s", e)
                self._events.put(None)

        def _send_event(self, event):
            e = Any()
            e.Pack(event)
            self._events.put(e)


    def __init__(self, name, addr=None, read_stdin=True):
        self._name = name
        self._addr = addr
        self._trans = UDPTransport(addr)
        self._addr = self._trans.addr
        self._read_stdin = read_stdin

        self._inbox = queue.Queue()

        signal.signal(signal.SIGINT, self._stop_signal)
        signal.signal(signal.SIGTERM, self._stop_signal)

        if os.environ.get('TEST_SERVER') is None:
            self._testing = False
        else:
            self._testing = True
            self._tserver_addr = os.environ['TEST_SERVER']
            self._tserver_client = Communicator.TestServerClient(self._tserver_addr, self)
            self._test_mode = os.getenv('TEST_MODE', TestMode.CONTROL)
            self._message_count = 0
            self._timer_count = 0
            self._prev_message = None
            self._prev_timer = None

        self._start()

    # Public

    @property
    def addr(self):
        return self._addr

    def send(self, message, recepient):
        if recepient == 'local':
            self.send_local(message)
            return
        logging.debug("%s send to %s: %s", self._name, recepient, message)

        if self._testing:
            self._message_count += 1
            message_id = "%s-m%d" % (self._name, self._message_count)
            raw = message.marshall(self._addr, message_id)
            self._tserver_client.on_new_message(message_id, recepient, raw)
        else:
            raw = message.marshall(self._addr)

        if not self._testing or self._test_mode == TestMode.WATCH:
            self._trans.send(raw, recepient)

    def send_local(self, message):
        print('>>', message)
        if self._testing:
            message_id = sender = 'local'
            raw = message.marshall(sender, message_id)
            self._tserver_client.on_new_message(message_id, sender, raw)

    def recv(self, timeout=None):
        if self._testing:
            if timeout is not None:
                self._timer_count += 1
                timer_id = "%s-t%d" % (self._name, self._timer_count)
                self._tserver_client.on_new_timer(timer_id, 'recv', timeout)

            if self._prev_message is not None:
                self._tserver_client.on_message_processed(self._prev_message)
                self._prev_message = None

            if self._prev_timer is not None:
                self._tserver_client.on_timer_processed(self._prev_timer)
                self._prev_timer = None

        if not self._testing or self._test_mode == TestMode.WATCH:
            try:
                message = self._inbox.get(timeout=timeout)
            except queue.Empty:
                message = None
        else:
            message = self._inbox.get()

        if self._testing and timeout is not None:
            if ((self._test_mode == TestMode.WATCH and message is None) or
                    (self._test_mode == TestMode.CONTROL and message.type == 'TIMER' and message.body == timer_id)):
                self._tserver_client.on_timer_fired(timer_id)
                self._prev_timer = timer_id
                message = None
            else:
                self._tserver_client.on_timer_canceled(timer_id)

        if message is not None:
            logging.debug("%s receive from %s: %s", self._name, message.sender, message)

            if self._testing:
                if self._test_mode == TestMode.WATCH or message.is_local():
                    self._tserver_client.on_message_received(message._id, message.marshall())
                else:
                    self._tserver_client.on_message_received(message._id)
                self._prev_message = message._id

        return message

    def recv_local(self):
        while True:
            message = self.recv()
            if message.is_local():
                return message
            else:
                logging.debug("%s dropped message from %s: %s %s", self._name, message.sender, message.type, message.body)
                if self._testing:
                    self._tserver_client.on_message_processed(self._prev_message)
                    self._prev_message = None

    # Private

    def _start(self):
        if not self._testing or self._test_mode == TestMode.WATCH:
            threading.Thread(target=self._receive_messages, daemon=True).start()
            if self._read_stdin:
                threading.Thread(target=self._receive_local_messages, daemon=True).start()

        if self._testing:
            self._tserver_client.start()
            self._tserver_client.on_process_started(self._name, self._addr)

    def _receive_messages(self):
        while True:
            raw = self._trans.recv()
            if raw is None:
                continue
            message = Message.unmarshall(raw)
            self._inbox.put(message)

    def _receive_local_messages(self):
        while True:
            line = sys.stdin.readline().strip()
            parts = line.split(" ", 1)
            message_type = parts[0]
            if len(parts) == 2:
                body = parts[1]
            else:
                body = None
            message = Message(message_type, body, sender='local')
            self._inbox.put(message)

    def _stop_signal(self, signum, frame):
        self._stop()
        # this is rather brutal but safe against misbehaving programs
        # (TODO: consider raising InterruptedError)
        sys.exit(0)

    def _stop(self):
        if self._testing:
            self._tserver_client.on_process_stopped()
            # make sure test server received our goodbye
            time.sleep(0.01)
        self._trans.destroy()

    # Test Server Command Handlers

    def _handle_receive_local_message(self, raw_message):
        message = Message.unmarshall(raw_message)
        self._inbox.put(message)

    def _handle_receive_message(self, message_id, sender, raw_message):
        message = Message.unmarshall(raw_message)
        self._inbox.put(message)

    def _handle_fire_timer(self, timer_id):
        self._inbox.put(Message('TIMER', timer_id))
