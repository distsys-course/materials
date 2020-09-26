import grpc
import json
import logging
import os
import queue
import signal
import sys
import threading
import time
import uuid
from google.protobuf.any_pb2 import Any

from .message import Message
from .process import Context
from .transport import UDPTransport

from .proto import test_server_pb2 as pb
from .proto import test_server_pb2_grpc as rpc


class TestMode:
    WATCH = 'WATCH'
    CONTROL = 'CONTROL'


class Runtime:

    class ProcessContext(Context):
        def __init__(self, runtime):
            self._runtime = runtime

        def addr(self):
            return self._runtime._addr

        def send(self, message, recepient):
            assert self._runtime is not None, "context was destroyed"
            self._runtime._send(message, recepient)

        def send_local(self, message):
            assert self._runtime is not None, "context was destroyed"
            self._runtime._send_local(message)

        def set_timer(self, timer, interval):
            assert self._runtime is not None, "context was destroyed"
            self._runtime._set_timer(timer, interval)

        def cancel_timer(self, timer):
            assert self._runtime is not None, "context was destroyed"
            self._runtime._cancel_timer(timer)

        def destroy(self):
            self._runtime = None

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
            except grpc.RpcError:
                self._events.put(None)

        def _send_event(self, event):
            e = Any()
            e.Pack(event)
            self._events.put(e)


    def __init__(self, proc, addr=None):
        self._proc = proc
        self._trans = UDPTransport(addr)
        self._addr = self._trans.addr

        self._inbox = queue.Queue()
        self._local_outbox = queue.Queue()
        self._timers = {}
        self._timer_ids = {}

        self._stop_event = threading.Event()
        signal.signal(signal.SIGINT, self._stop_signal)
        signal.signal(signal.SIGTERM, self._stop_signal)

        if os.environ.get('TEST_SERVER') is None:
            self._testing = False
        else:
            self._testing = True
            self._tserver_addr = os.environ['TEST_SERVER']
            self._tserver_client = Runtime.TestServerClient(self._tserver_addr, self)
            self._test_mode = os.getenv('TEST_MODE', TestMode.CONTROL)
            self._pending_timers = {}
            self._message_count = 0
            self._timer_count = 0

    # Public

    def start(self):
        threading.Thread(target=self._receive_messages).start()
        threading.Thread(target=self._receive_local_messages, daemon=True).start()
        threading.Thread(target=self._process_messages, daemon=True).start()
        if self._testing:
            self._tserver_client.start()
            self._tserver_client.on_process_started(self._proc.name, self._addr)

    def stop(self):
        if self._testing:
            self._tserver_client.on_process_stopped()
            # make sure test server received our goodbye
            time.sleep(0.01)
        for t in self._timers.values():
            t.cancel()
        self._stop_event.set()
        self._trans.destroy()

    def send_local(self, message):
        if self._testing:
            self._tserver_client.on_message_received('local', message.marshall())

        ctx = Runtime.ProcessContext(self)
        self._proc.receive(ctx, message)
        ctx.destroy()

        if self._testing:
            self._tserver_client.on_message_processed('local')

    def receive_local(self):
        return self._local_outbox.get()

    # Messaging

    def _send(self, message, recepient):
        if recepient == 'local':
            self._send_local(message)
            return

        logging.debug("%s send to %s: %s", self._proc.name, recepient, message)
        if self._testing:
            self._message_count += 1
            message_id = "%s-m%d" % (self._proc.name, self._message_count)
            raw = message.marshall(self._addr, message_id)
            self._tserver_client.on_new_message(message_id, recepient, raw)
        else:
            raw = message.marshall(self._addr)

        if not self._testing or self._test_mode == TestMode.WATCH:
            self._trans.send(raw, recepient)

    def _send_local(self, message):
        logging.debug("%s send to local: %s", self._proc.name, message)
        print('>>', message)
        self._local_outbox.put(message)
        if self._testing:
            message_id = sender = 'local'
            raw = message.marshall(sender, message_id)
            self._tserver_client.on_new_message(message_id, sender, raw)

    def _receive_messages(self):
        while not self._stop_event.is_set():
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

    def _process_messages(self):
        while True:
            message = self._inbox.get()
            logging.debug("%s receive from %s: %s", self._proc.name, message.sender, message)

            if self._testing:
                if self._test_mode == TestMode.WATCH:
                    self._tserver_client.on_message_received(message._id, message.marshall())
                else:
                    self._tserver_client.on_message_received(message._id)

            ctx = Runtime.ProcessContext(self)
            self._proc.receive(ctx, message)
            ctx.destroy()

            if self._testing:
                self._tserver_client.on_message_processed(message._id)

    # Timers

    def _set_timer(self, name, interval):
        if not self._testing:
            timer_id = uuid.uuid1()
        else:
            self._timer_count += 1
            timer_id = "%s-t%d" % (self._proc.name, self._timer_count)
        self._timer_ids[name] = timer_id

        if not self._testing or self._test_mode == TestMode.WATCH:
            t = threading.Timer(interval, self._on_timer, args=(timer_id, name,))
            t.start()
            self._timers[timer_id] = t

        if self._testing:
            if self._test_mode == TestMode.CONTROL:
                self._pending_timers[timer_id] = name
            self._tserver_client.on_new_timer(timer_id, name, interval)

    def _cancel_timer(self, name):
        timer_id = self._timer_ids.pop(name)

        if not self._testing or self._test_mode == TestMode.WATCH:
            t = self._timers.pop(timer_id)
            t.cancel()

        if self._testing:
            if self._test_mode == TestMode.CONTROL:
                self._pending_timers.pop(timer_id)
            self._tserver_client.on_timer_canceled(timer_id)

    def _on_timer(self, timer_id, name):
        logging.debug("%s firing timer %s", self._proc.name, name)
        if self._testing:
            self._tserver_client.on_timer_fired(timer_id)

        ctx = Runtime.ProcessContext(self)
        self._proc.on_timer(ctx, name)
        ctx.destroy()

        if self._testing:
            self._tserver_client.on_timer_processed(timer_id)
        if not self._testing or self._test_mode == TestMode.WATCH:
            self._timers.pop(timer_id)

    # Test Server Command Handlers

    def _handle_receive_local_message(self, raw_message):
        message = Message.unmarshall(raw_message)
        self.send_local(message)

    def _handle_receive_message(self, message_id, sender, raw_message):
        message = Message.unmarshall(raw_message)
        self._inbox.put(message)

    def _handle_fire_timer(self, timer_id):
        timer_name = self._pending_timers.pop(timer_id)
        if timer_name is not None:
            self._on_timer(timer_id, timer_name)

    # Misc

    def _stop_signal(self, signum, frame):
        self.stop()
