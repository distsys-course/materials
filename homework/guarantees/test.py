#!/usr/bin/env python

import argparse
import logging
import os
import subprocess
import sys
import threading
import unittest

from dslib.message import Message
from dslib.test_server import TestMode, TestServer


SERVER_ADDR = '127.0.0.1:9701'
TEST_SERVER_ADDR = '127.0.0.1:9746'


def run_receiver(impl_dir, receiver_addr, ts_addr, debug):
    env = os.environ.copy()
    env['TEST_SERVER'] = ts_addr
    cmd = ['/usr/bin/env', 'python3', os.path.join(impl_dir, 'receiver.py'), '-l', receiver_addr]
    if debug:
        cmd.append('-d')
        out = None
    else:
        out = subprocess.DEVNULL
    process = subprocess.Popen(cmd, env=env, stdout=out, stderr=out)
    threading.Thread(target=process.communicate).start()
    return process


def run_sender(impl_dir, receiver_addr, ts_addr, debug):
    env = os.environ.copy()
    env['TEST_SERVER'] = ts_addr
    cmd = ['/usr/bin/env', 'python3', os.path.join(impl_dir, 'sender.py')]
    if debug:
        cmd.append('-d')
        out = None
    else:
        out = subprocess.DEVNULL
    process = subprocess.Popen(cmd, env=env, stdout=out, stderr=out)
    threading.Thread(target=process.communicate).start()
    return process


class BaseTestCase(unittest.TestCase):
    def __init__(self, impl_dir, debug=False):
        super(BaseTestCase, self).__init__()
        self.impl_dir = impl_dir
        self.debug = debug

    def setUp(self):
        super(BaseTestCase, self).setUp()
        sys.stderr.write("\n\n" + self.__class__.__name__ + " " + "-" * 60 + "\n\n")

        self.ts = TestServer(TEST_SERVER_ADDR)
        self.ts.start()
        self.receiver = run_receiver(self.impl_dir, SERVER_ADDR, TEST_SERVER_ADDR, self.debug)
        self.sender = run_sender(self.impl_dir, SERVER_ADDR, TEST_SERVER_ADDR, self.debug)

    def tearDown(self):
        self.sender.terminate()
        self.receiver.terminate()
        self.ts.stop()
        self.sender.kill()
        self.receiver.kill()


class BasicTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")

        # Reliable network, should get the result.
        sender_req = Message('INFO-1', 'message1')
        self.ts.send_local_message('sender', sender_req, 1)
        sender_resp = self.ts.step_until_local_message('receiver', 1)
        self.assertIsNotNone(sender_resp, "Receiver response timeout")
        self.assertEqual(sender_resp.type, 'INFO-1')
        self.assertEqual(sender_resp.body, 'message1')
        # Should be no other messages
        sender_resp = self.ts.step_until_local_message('receiver', 1)
        self.assertIsNone(sender_resp)


class BasicRepeatedTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")
        # With probability 1 repeat 5 times
        self.ts.set_repeat_rate(1, 5)
        sender_req = Message('INFO-1', 'message1')
        self.ts.send_local_message('sender', sender_req, 1)
        sender_resp = self.ts.step_until_local_message('receiver', 1)
        self.assertIsNotNone(sender_resp, "Receiver response timeout")
        self.assertEqual(sender_resp.type, 'INFO-1')
        self.assertEqual(sender_resp.body, 'message1')
        # Should be no other messages
        sender_resp = self.ts.step_until_local_message('receiver', 1)
        self.assertIsNone(sender_resp)


class BasicBiggerRepeatedTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")
        num_messages = 5
        self.ts.set_repeat_rate(1, 5)
        self.ts.set_event_reordering(True)
        # Send the same messages
        for i in range(2 * num_messages):
            sender_req = Message('INFO-1', str(i % num_messages))
            self.ts.send_local_message('sender', sender_req, 1)
        messages = []
        while True:
            sender_resp = self.ts.step_until_local_message('receiver', 1)
            if sender_resp is None:
                break
            messages.append(sender_resp)
        # We should get all them
        self.assertEqual(len(messages), num_messages)
        all_present = [0 for i in range(num_messages)]
        # Only once
        for i in range(num_messages):
            self.assertEqual(messages[i].type, 'INFO-1')
            all_present[int(messages[i].body)] += 1
        self.assertListEqual(all_present, [1 for i in range(num_messages)])


class BasicDroppedTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")
        # Drop with probability 1
        self.ts.set_message_drop_rate(1)
        sender_req = Message('INFO-1', 'message1')
        self.ts.send_local_message('sender', sender_req, 1)
        # Wait for receiver to respond
        sender_resp = self.ts.step_until_local_message('receiver', 1)
        # Nothing to respond
        self.assertIsNone(sender_resp)


class MoreThanOnceTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")
        num_messages = 3
        rate = 3
        self.ts.set_repeat_rate(1, rate)
        self.ts.set_event_reordering(True)
        for i in range(num_messages):
            sender_req = Message('INFO-2', str(i))
            self.ts.send_local_message('sender', sender_req, 1)
        messages = []
        while True:
            sender_resp = self.ts.step_until_local_message('receiver', 1)
            if sender_resp is None:
                break
            messages.append(sender_resp)
        self.assertGreaterEqual(len(messages), num_messages)
        all_present = [0 for i in range(num_messages)]
        for i in range(len(messages)):
            self.assertEqual(messages[i].type, 'INFO-2')
            all_present[int(messages[i].body)] += 1
        for el in all_present:
            self.assertGreaterEqual(el, rate + 1)

class MoreThanOnceMessageDropTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")
        num_messages = 10
        rate = 1
        self.ts.set_repeat_rate(1, rate)
        self.ts.set_event_reordering(True)
        self.ts.set_message_drop_rate(0.5)
        for i in range(num_messages):
            sender_req = Message('INFO-2', str(i))
            self.ts.send_local_message('sender', sender_req, 1)
        messages = []
        while True:
            sender_resp = self.ts.step_until_local_message('receiver', 1)
            if sender_resp is None:
                break
            messages.append(sender_resp)
        self.assertGreaterEqual(len(messages), num_messages)
        all_present = [0 for i in range(num_messages)]
        for i in range(len(messages)):
            self.assertEqual(messages[i].type, 'INFO-2')
            all_present[int(messages[i].body)] += 1
        for el in all_present:
            self.assertGreaterEqual(el, 1)


class ExactlyOnceTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")
        num_messages = 10
        rate = 1
        self.ts.set_repeat_rate(1, rate)
        self.ts.set_event_reordering(True)
        self.ts.set_message_drop_rate(0.5)
        for i in range(num_messages):
            sender_req = Message('INFO-3', str(i))
            self.ts.send_local_message('sender', sender_req, 1)
        messages = []
        while True:
            sender_resp = self.ts.step_until_local_message('receiver', 1)
            if sender_resp is None:
                break
            messages.append(sender_resp)
        self.assertGreaterEqual(len(messages), num_messages)
        all_present = [0 for i in range(num_messages)]
        for i in range(len(messages)):
            self.assertEqual(messages[i].type, 'INFO-3')
            all_present[int(messages[i].body)] += 1
        for el in all_present:
            self.assertEqual(el, 1)


class RandomDropsTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")
        self.ts.set_real_time_mode(False)

        client_req = Message('INFO-3', 'some message')
        # Send 5 identical messages
        self.ts.send_local_message('sender', client_req)
        self.ts.send_local_message('sender', client_req)
        self.ts.send_local_message('sender', client_req)
        self.ts.send_local_message('sender', client_req)
        self.ts.send_local_message('sender', client_req)
        # Drop them and force the retry
        self.ts.set_message_drop_rate(0.5)
        # Try to get something from 100 steps, very high probability of success
        self.ts.steps(100, 1)
        self.ts.set_message_drop_rate(0)
        sender_resp = self.ts.step_until_local_message('receiver', 1)
        self.assertIsNotNone(sender_resp, "Receiver response timeout")
        self.assertEqual(sender_resp.type, 'INFO-3')
        self.assertEqual(sender_resp.body, 'some message')
        # Should be no other messages
        sender_resp = self.ts.step_until_local_message('receiver', 1)
        self.assertIsNone(sender_resp)


class ExactlyOnceWithOrderTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")
        num_messages = 10
        rate = 1
        self.ts.set_repeat_rate(1, rate)
        self.ts.set_event_reordering(True)
        self.ts.set_message_drop_rate(0.5)
        for i in range(num_messages):
            sender_req = Message('INFO-4', str(i))
            self.ts.send_local_message('sender', sender_req, 1)
        messages = []
        # New logic
        current_message = 0
        while True:
            sender_resp = self.ts.step_until_local_message('receiver', 1)
            if sender_resp is None:
                break
            messages.append(sender_resp)
            # New logic
            self.assertEqual(int(sender_resp.body), current_message)
            current_message += 1
        self.assertGreaterEqual(len(messages), num_messages)
        all_present = [0 for i in range(num_messages)]
        for i in range(len(messages)):
            self.assertEqual(messages[i].type, 'INFO-4')
            all_present[int(messages[i].body)] += 1
        for el in all_present:
            self.assertEqual(el, 1)


class RandomDropsWithOrderTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")
        self.ts.set_real_time_mode(False)

        messages =  [(Message('INFO-4', 'some message1'), 'some message1'),
                     (Message('INFO-4', 'some message2'), 'some message2'),
                     (Message('INFO-4', 'some message3'), 'some message3'),
                     (Message('INFO-4', 'some message4'), 'some message4'),
                     (Message('INFO-4', 'some message5'), 'some message5')]

        # New Logic. send 5 messages
        for client_req, message_body in messages:
            # Send 5 identical messages
            self.ts.send_local_message('sender', client_req)
            self.ts.send_local_message('sender', client_req)
            self.ts.send_local_message('sender', client_req)
            self.ts.send_local_message('sender', client_req)
            self.ts.send_local_message('sender', client_req)
            # Drop them and force the retry
            self.ts.set_message_drop_rate(0.5)
            # Try to get something from 100 steps, very high probability of success
            self.ts.steps(100, 1)
            self.ts.set_message_drop_rate(0)

        for client_req, message_body in messages:
            sender_resp = self.ts.step_until_local_message('receiver', 1)
            self.assertIsNotNone(sender_resp, "Receiver response timeout")
            self.assertEqual(sender_resp.type, 'INFO-4')
            self.assertEqual(sender_resp.body, message_body)
        # Should be no other messages
        sender_resp = self.ts.step_until_local_message('receiver', 1)
        self.assertIsNone(sender_resp)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(dest='impl_dir', metavar='DIRECTORY',
                        help="directory with implementation to test")
    parser.add_argument('-d', dest='debug', action='store_true',
                        help="include debugging output from implementation")
    parser.add_argument('-n', default='1', type=int)
    args = parser.parse_args()

    logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.DEBUG)

    tests = [
        BasicTestCase(
            args.impl_dir, args.debug),
        BasicBiggerRepeatedTestCase(
            args.impl_dir, args.debug),
        BasicRepeatedTestCase(
            args.impl_dir, args.debug),
        BasicDroppedTestCase(
            args.impl_dir, args.debug),
        MoreThanOnceTestCase(
            args.impl_dir, args.debug),
        MoreThanOnceMessageDropTestCase(
            args.impl_dir, args.debug),
        ExactlyOnceTestCase(
            args.impl_dir, args.debug),
        RandomDropsTestCase(
            args.impl_dir, args.debug),
        ExactlyOnceWithOrderTestCase(
            args.impl_dir, args.debug),
        RandomDropsWithOrderTestCase(
            args.impl_dir, args.debug)
    ]

    for i in range(args.n):
        suite = unittest.TestSuite()
        suite.addTests(tests)
        runner = unittest.TextTestRunner(verbosity=1)
        result = runner.run(suite)
        if not result.wasSuccessful():
            return 1


if __name__ == "__main__":
    sys.exit(main())
