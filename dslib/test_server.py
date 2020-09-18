import argparse
import grpc
import logging
import os
import queue
import random
import signal
import sys
import threading
import time
from collections import defaultdict
from concurrent import futures
from google.protobuf.any_pb2 import Any

from .message import Message
from .proto import test_server_pb2 as pb
from .proto import test_server_pb2_grpc as rpc


class TestMode:
    WATCH = 'WATCH'
    CONTROL = 'CONTROL'


class Event:
    MESSAGE = 'message'
    TIMER = 'timer'

    def __init__(self, event_id, event_type):
        self._id = event_id
        self._type = event_type
        self._create_time = time.time()
        self._time = None

    @property
    def id(self):
        return self._id

    @property
    def type(self):
        return self._type

    @property
    def create_time(self):
        return self._create_time

    @property
    def time(self):
        return self._time

    @time.setter
    def time(self, time):
        self._time = time


class MessageEvent(Event):
    def __init__(self, message_id, sender, recepient, raw_message):
        super().__init__(message_id, Event.MESSAGE)
        self._sender = sender
        self._recepient = recepient
        self._raw_message = raw_message
        self._is_repeatable = True

    @property
    def sender(self):
        return self._sender

    @property
    def recepient(self):
        return self._recepient

    @property
    def raw_message(self):
        return self._raw_message


class TimerEvent(Event):
    def __init__(self, process_id, timer_id, name, interval):
        super().__init__(timer_id, Event.TIMER)
        self._process_id = process_id
        self._name = name
        self._interval = interval
        self._time = self._create_time + interval

    @property
    def process_id(self):
        return self._process_id

    @property
    def name(self):
        return self._name

    @property
    def interval(self):
        return self._interval


class TestServer(rpc.TestServerServicer):

    class ProcessHandler:
        def __init__(self, server, event_stream, context):
            self._server = server
            self._event_stream = event_stream
            self._context = context
            self._command_queue = queue.Queue()
            self._process_id = None
            threading.Thread(target=self._process_events, args=(event_stream,)).start()

        def get_command_stream(self):
            return iter(self._command_queue.get, None)

        def receive_local_message(self, raw_message):
            self._send_command(
                pb.ReceiveLocalMessageCommand(
                    message=raw_message))

        def receive_message(self, message_id, sender, raw_message):
            self._send_command(
                pb.ReceiveMessageCommand(
                    message_id=message_id,
                    sender=sender,
                    message=raw_message))

        def fire_timer(self, timer_id):
            self._send_command(
                pb.FireTimerCommand(
                    timer_id=timer_id))

        def stop(self):
            self._command_queue.put(None)
            self._context.cancel()

        def _process_events(self, stream):
            try:
                for e in self._event_stream:
                    if e.Is(pb.ProcessStartedEvent.DESCRIPTOR):
                        event = pb.ProcessStartedEvent()
                        e.Unpack(event)
                        self._process_id = event.process_id
                        self._server._on_process_started(self._process_id, event.address, self)

                    if e.Is(pb.NewMessageEvent.DESCRIPTOR):
                        event = pb.NewMessageEvent()
                        e.Unpack(event)
                        self._server._on_new_message(
                            self._process_id, event.message_id, event.recepient, event.message)

                    if e.Is(pb.MessageReceivedEvent.DESCRIPTOR):
                        event = pb.MessageReceivedEvent()
                        e.Unpack(event)
                        self._server._on_message_received(self._process_id, event.message_id)

                    if e.Is(pb.MessageDataReceivedEvent.DESCRIPTOR):
                        event = pb.MessageDataReceivedEvent()
                        e.Unpack(event)
                        self._server._on_message_received(self._process_id, event.message_id, event.message)

                    if e.Is(pb.MessageProcessedEvent.DESCRIPTOR):
                        event = pb.MessageProcessedEvent()
                        e.Unpack(event)
                        self._server._on_message_processed(self._process_id, event.message_id)

                    if e.Is(pb.NewTimerEvent.DESCRIPTOR):
                        event = pb.NewTimerEvent()
                        e.Unpack(event)
                        self._server._on_new_timer(self._process_id, event.timer_id, event.name, event.interval)

                    if e.Is(pb.TimerFiredEvent.DESCRIPTOR):
                        event = pb.TimerFiredEvent()
                        e.Unpack(event)
                        self._server._on_timer_fired(self._process_id, event.timer_id)

                    if e.Is(pb.TimerProcessedEvent.DESCRIPTOR):
                        event = pb.TimerProcessedEvent()
                        e.Unpack(event)
                        self._server._on_timer_processed(self._process_id, event.timer_id)

                    if e.Is(pb.TimerCanceledEvent.DESCRIPTOR):
                        event = pb.TimerCanceledEvent()
                        e.Unpack(event)
                        self._server._on_timer_canceled(self._process_id, event.timer_id)

                    if e.Is(pb.ProcessStoppedEvent.DESCRIPTOR):
                        self._server._on_process_stopped(self._process_id)
                        self._command_queue.put(None)
                        return
            except grpc.RpcError:
                pass

        def _send_command(self, command):
            c = Any()
            c.Pack(command)
            self._command_queue.put(c)


    def __init__(self, addr):
        self._addr = addr
        self._test_mode = os.getenv('TEST_MODE', TestMode.CONTROL)
        self._processes = {}
        self._crashed_processes = set()
        self._lookup = {}
        self._rev_lookup = {}

        self._events = []
        self._messages = {}
        self._processed_events = queue.Queue()
        self._local_messages = defaultdict(queue.Queue)

        self._real_time_mode = True
        self._event_reordering = False
        self._min_message_delay = 0
        self._max_message_delay = 0
        self._message_drop_rate = 0
        self._repeat_rate = 0
        self._repeat_event_times = 0

        self._message_count = 0

        signal.signal(signal.SIGINT, self._stop_signal)
        signal.signal(signal.SIGTERM, self._stop_signal)

    # RPC

    def AttachProcess(self, request_iterator, context):
        handler = TestServer.ProcessHandler(self, request_iterator, context)
        return handler.get_command_stream()

    # Public

    def start(self, block=False):
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=64))
        rpc.add_TestServerServicer_to_server(
            self, self._server)
        self._server.add_insecure_port(self._addr)
        self._server.start()
        if block:
            self._server.wait_for_termination()

    def wait_processes(self, proc_count, timeout):
        start = time.time()
        while len(self._processes) != proc_count and time.time() - start < timeout:
            time.sleep(.01)
        return len(self._processes) == proc_count

    def set_real_time_mode(self, enabled):
        self._real_time_mode = enabled

    def set_event_reordering(self, enabled):
        self._event_reordering = enabled
        if enabled:
            self._real_time_mode = False

    def set_message_delay(self, min_delay, max_delay=None):
        self._min_message_delay = min_delay
        if max_delay is None:
            self._max_message_delay = min_delay
        else:
            self._max_message_delay = max_delay

    def set_message_drop_rate(self, rate):
        self._message_drop_rate = rate

    def set_repeat_rate(self, rate, times):
        self._repeat_rate = rate
        self._repeat_event_times = times

    def get_process_addr(self, proc_name):
        return self._lookup[proc_name]

    def step(self, timeout):
        # stop if no pending events
        if len(self._events) == 0:
            logging.debug("no pending events")
            return False

        # compute delays for new messages
        for event in self._events:
            if event.type == Event.MESSAGE and event.time is None:
                if self._min_message_delay == 0 and self._max_message_delay == 0:
                    if event.sender == event.recepient:
                        delay = 0
                    else:
                        delay = .1
                else:
                    delay = self._min_message_delay + random.uniform(0, 1) * (self._max_message_delay - self._min_message_delay)
                event.time = event.create_time + delay

        # select next event
        if not self._event_reordering:
            # sort events by event time then select the earliest event
            sorted_events = sorted(self._events, key=lambda e: e.time)
            event = sorted_events[0]
            self._events = sorted_events[1:]
        else:
            event = random.choice(self._events)
            self._events.remove(event)

        # process next event
        if self._real_time_mode:
            time_left = event.time - time.time()
            if time_left > 0:
                time.sleep(time_left)
        logging.debug("next event %s", event.id)

        if event.type == Event.MESSAGE:
            message = event
            if message.recepient in self._crashed_processes:
                logging.debug("discarded message %s to crashed process %s", message.id, message.recepient)
                return True
            if random.uniform(0, 1) > self._message_drop_rate:
                if event._is_repeatable and random.uniform(0, 1) < self._repeat_rate:
                    for i in range(self._repeat_event_times):
                        logging.debug("repeating message %s", message.id)
                        event._is_repeatable = False
                        self._events.append(event)
                self._processes[message.recepient].receive_message(
                        message.id, self._lookup[message.sender], message.raw_message)
                try:
                    while True:
                        processed_id = self._processed_events.get(timeout=timeout)
                        if processed_id == message.id:
                            break
                    return True
                except queue.Empty:
                    return False
            else:
                logging.debug("dropped message %s", message.id)
                return True

        elif event.type == Event.TIMER:
            timer = event
            self._processes[timer.process_id].fire_timer(timer.id)
            try:
                while True:
                    processed_id = self._processed_events.get(timeout=timeout)
                    if processed_id == timer.id:
                        break
                return True
            except queue.Empty:
                return False
            return True

    def steps(self, count, timeout):
        for _ in range(0, count):
            if not self.step(timeout):
                break

    def step_until_local_message(self, process_id, timeout):
        deadline = time.time() + timeout
        time_left = timeout
        while self._local_messages[process_id].qsize() == 0 and time_left > 0:
            if not self.step(time_left):
                return None
            time_left = deadline - time.time()
        if time_left > 0:
            return self._local_messages[process_id].get()
        else:
            return None

    def step_until_no_events(self, timeout):
        deadline = time.time() + timeout
        time_left = timeout
        while time_left > 0:
            if not self.step(time_left):
                return
            time_left = deadline - time.time()

    def send_local_message(self, recepient, message, timeout=1):
        logging.debug("sent local message to %s: %s", recepient, message)
        raw_message = message.marshall(sender='local', message_id='local')
        self._processes[recepient].receive_local_message(raw_message)
        if self._test_mode == TestMode.CONTROL:
            try:
                while True:
                    processed_id = self._processed_events.get(timeout=timeout)
                    if processed_id == 'local':
                        break
            except queue.Empty:
                return False
        return True

    def wait_local_message(self, process_id, timeout):
        try:
            return self._local_messages[process_id].get(timeout=timeout)
        except queue.Empty:
            return None

    def crash_process(self, process_id):
        logging.debug("[%s] crashed", process_id)
        self._crashed_processes.add(process_id)
        new_events = []
        for e in self._events:
            if e.type == Event.MESSAGE and (e.sender == process_id or e.recepient == process_id):
                logging.debug("discarded message %s", e.id)
            elif e.type == Event.TIMER and e.process_id == process_id:
                logging.debug("discarded timer %s", e.id)
            else:
                new_events.append(e)
        self._events = new_events

    def stop(self, wait_processes=True):
        if wait_processes:
            while len(self._processes) > 0:
                time.sleep(.005)
        else:
            for handler in list(self._processes.values()):
                handler.stop()
        self._server.stop(None)

    # Process Event Handlers

    def _on_process_started(self, process_id, address, handler):
        logging.debug("[%s] started on %s", process_id, address)
        self._processes[process_id] = handler
        self._lookup[process_id] = address
        self._rev_lookup[address] = process_id

    def _on_process_stopped(self, process_id):
        if process_id not in self._crashed_processes:
            logging.debug("[%s] stopped", process_id)
        del self._processes[process_id]

    def _on_new_message(self, process_id, message_id, recepient, raw_message):
        message = Message.unmarshall(raw_message)
        if message.is_local():
            logging.debug("[%s] sent local message: %s", process_id, message)
            self._local_messages[process_id].put(message)
        else:
            recepient_id = self._rev_lookup[recepient]
            logging.debug("[%s] sent message %s to %s: %s", process_id, message_id, recepient_id, message)
            if self._test_mode == TestMode.CONTROL:
                event = MessageEvent(message_id, process_id, recepient_id, raw_message)
                self._events.append(event)
                self._messages[message_id] = message
            self._message_count += 1

    def _on_message_received(self, process_id, message_id, raw_message=None):
        if raw_message is not None:
            message = Message.unmarshall(raw_message)
        else:
            message = self._messages.pop(message_id, None)
        if message is not None:
            if message.is_local():
                logging.debug("[%s] received local message: %s", process_id, message)
            else:
                logging.debug("[%s] received message %s: %s", process_id, message_id, message)
        else:
            if message_id == 'local':
                logging.debug("[%s] received local message", process_id)
            else:
                logging.debug("[%s] received message %s", process_id, message_id)

    def _on_message_processed(self, process_id, message_id):
        if message_id == 'local':
            logging.debug("[%s] processed local message", process_id)
        else:
            logging.debug("[%s] processed message %s", process_id, message_id)
        self._processed_events.put(message_id)

    def _on_new_timer(self, process_id, timer_id, name, interval):
        if self._test_mode == TestMode.CONTROL:
            # set timer intervals to 1 during testing
            interval = 1
            event = TimerEvent(process_id, timer_id, name, interval)
            self._events.append(event)
        logging.debug("[%s] set timer %s: %s, %.1fs", process_id, timer_id, name, interval)

    def _on_timer_fired(self, process_id, timer_id):
        logging.debug("[%s] fired timer %s", process_id, timer_id)

    def _on_timer_processed(self, process_id, timer_id):
        logging.debug("[%s] processed timer %s", process_id, timer_id)
        self._processed_events.put(timer_id)

    def _on_timer_canceled(self, process_id, timer_id):
        logging.debug("[%s] canceled timer %s", process_id, timer_id)
        self._events = [e for e in self._events if e.id != timer_id]

    # Misc

    def _stop_signal(self, signum, frame):
        self.stop(wait_processes=False)


def read_input(ts):
    while True:
        line = sys.stdin.readline().strip()
        parts = line.split(" ", 2)
        recepient = parts[0]
        message_type = parts[1]
        if len(parts) == 3:
            body = parts[2]
        else:
            body = None
        message = Message(message_type, body)
        ts.send_local_message(recepient, message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', dest='server_addr', metavar='host:port',
                        help='server address', default='localhost:9746')
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.DEBUG)

    ts = TestServer(args.server_addr)
    threading.Thread(target=read_input, args=(ts,), daemon=True).start()
    ts.start(block=True)


if __name__ == "__main__":
    main()
