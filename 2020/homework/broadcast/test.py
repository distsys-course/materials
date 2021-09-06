#!/usr/bin/env python3

import argparse
import logging
import os
import random
import subprocess
import sys
import threading
import unittest

from dslib.message import Message
from dslib.test_server import TestMode, TestServer


PEER_NAMES = ['Alice', 'Bob', 'Carl', 'Dan', 'Eve']
TEST_SERVER_ADDR = '127.0.0.1:9746'


def run_peer(impl_dir, name, addr, peer_list, ts_addr, debug):
    env = os.environ.copy()
    env['TEST_SERVER'] = ts_addr
    cmd = ['python3', os.path.join(impl_dir, 'peer.py'), '-n', name, '-l', addr, '-p', ','.join(peer_list)]
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
        self.peers = []
        self.peer_processes = []
        peer_list = []
        for i in range(5):
            peer_addr = '127.0.0.1:970%d' % (i+1)
            peer_list.append(peer_addr)
        for i in range(5):
            peer_name = PEER_NAMES[i]
            self.peers.append(peer_name)
            proc = run_peer(self.impl_dir, peer_name, peer_list[i], peer_list, TEST_SERVER_ADDR, self.debug)
            self.peer_processes.append(proc)

    def tearDown(self):
        for i in range(5):
            self.peer_processes[i].terminate()
        self.ts.stop()
        for i in range(5):
            self.peer_processes[i].kill()


class BasicTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(5, 1), "Startup timeout")
        self.ts.set_real_time_mode(False)

        # send message from Alice
        self.ts.send_local_message(self.peers[0], Message('SEND', 'hello'))

        # deliver the message
        self.ts.step_until_no_events(1)

        # make sure all peers delivered the message
        for peer in self.peers[1:]:
            msg = self.ts.wait_local_message(peer, 0)
            self.assertIsNotNone(msg, "Peer not delivered the message")
            self.assertEqual(msg.type, 'DELIVER')
            self.assertEqual(msg.body, 'Alice: hello')


class ReliableTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(5, 1), "Startup timeout")
        self.ts.set_real_time_mode(False)

        # send message from Alice
        self.ts.send_local_message(self.peers[0], Message('SEND', 'Hello'))

        # deliver 2 messages
        self.ts.step(1)
        self.ts.step(1)

        # crash Alice
        self.ts.crash_process(self.peers[0])

        # deliver the message
        self.ts.step_until_no_events(1)

        # make sure all alive peers delivered the message
        for peer in self.peers[2:]:
            msg = self.ts.wait_local_message(peer, 0)
            self.assertIsNotNone(msg, "Peer not delivered the message")
            self.assertEqual(msg.type, 'DELIVER')
            self.assertEqual(msg.body, 'Alice: Hello')


class UniformReliableTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(5, 1), "Startup timeout")
        self.ts.set_real_time_mode(False)

        # send message from Bob
        self.ts.send_local_message(self.peers[1], Message('SEND', 'Hello'))

        # if Bob has not delivered the message yet, make a step
        # (so he will receive his own message and possibly deliver it)
        delivered = 0
        if self.ts.wait_local_message(self.peers[1], 0) is None:
            self.ts.step(1)
            if self.ts.wait_local_message(self.peers[1], 0) is not None:
                delivered = 1
        else:
            delivered = 1

        # crash Bob
        self.ts.crash_process(self.peers[1])

        # complete execution
        self.ts.step_until_no_events(3)

        # check agreement property
        crashed = ['Bob']
        correct = ['Alice', 'Carl', 'Dan', 'Eve']
        crashed_delivered = delivered
        correct_delivered = 0
        for peer in self.peers:
            if peer not in crashed:
                msg = self.ts.wait_local_message(peer, 0)
                if msg is not None:
                    correct_delivered += 1
        passed = False
        if crashed_delivered == 0 and correct_delivered == 0:
            passed = True
        if crashed_delivered == 0 and correct_delivered == len(correct):
            passed = True
        if crashed_delivered > 0 and correct_delivered == len(correct):
            passed = True
        self.assertTrue(passed, 
            "Agreement property is not satisfied: correct - " + str(correct_delivered) + "/4, crashed - " + str(crashed_delivered) + "/1")


class OrderedTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(5, 1), "Startup timeout")
        self.ts.set_real_time_mode(False)

        # send two messages from Carl
        self.ts.send_local_message(self.peers[2], Message('SEND', 'Hello'))
        self.ts.send_local_message(self.peers[2], Message('SEND', 'How are you?'))

        # deliver the message
        self.ts.set_message_delay(0, 1)
        self.ts.step_until_no_events(1)

        # make sure all peers received the first message from Carl first
        for peer in self.peers:
            msg = self.ts.wait_local_message(peer, 0)
            self.assertIsNotNone(msg, "Peer " + peer + " not received the first message")
            self.assertEqual(msg.type, 'DELIVER')
            self.assertEqual(msg.body, 'Carl: Hello')


class TwoCrashesTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(5, 1), "Startup timeout")
        self.ts.set_real_time_mode(False)

        # send message from Eve
        self.ts.send_local_message(self.peers[4], Message('SEND', 'Hello'))

        for _ in range(4):
            self.ts.step(1)

        # crash Alice
        self.ts.crash_process(self.peers[0])

        for _ in range(4):
            self.ts.step(1)

        # crash Bob
        self.ts.crash_process(self.peers[1])

        # deliver the message
        self.ts.step_until_no_events(1)

        # make sure all alive peers delivered the message
        for peer in self.peers[2:]:
            msg = self.ts.wait_local_message(peer, 0)
            self.assertIsNotNone(msg, "Peer not delivered the message")
            self.assertEqual(msg.type, 'DELIVER')
            self.assertEqual(msg.body, 'Eve: Hello')


class TwoCrashesRandomTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(5, 1), "Startup timeout")
        self.ts.set_real_time_mode(False)

        # send message from Eve
        self.ts.send_local_message(self.peers[4], Message('SEND', 'Hello'))

        for _ in range(random.randint(0,10)):
            self.ts.step(1)

        # crash Alice
        self.ts.crash_process(self.peers[0])

        for _ in range(random.randint(0,10)):
            self.ts.step(1)

        # crash Bob
        self.ts.crash_process(self.peers[1])

        for _ in range(random.randint(0,10)):
            self.ts.step(1)
        
        # deliver the message
        self.ts.step_until_no_events(1)

        # check agreement property
        crashed = ['Alice', 'Bob']
        correct = ['Carl', 'Dan', 'Eve']
        crashed_delivered = 0
        correct_delivered = 0
        for peer in self.peers:
            msg = self.ts.wait_local_message(peer, 0)
            if msg is not None:
                if peer in crashed:
                    crashed_delivered += 1
                else:
                    correct_delivered += 1
        passed = False
        if crashed_delivered == 0 and correct_delivered == 0:
            passed = True
        if crashed_delivered == 0 and correct_delivered == len(correct):
            passed = True
        if crashed_delivered > 0 and correct_delivered == len(correct):
            passed = True
        self.assertTrue(passed, 
            "Agreement property is not satisfied: correct - " + str(correct_delivered) + "/3, crashed - " + str(crashed_delivered) + "/2")


class ThreeCrashesRandomTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(5, 1), "Startup timeout")
        self.ts.set_real_time_mode(False)

        # send message from Eve
        self.ts.send_local_message(self.peers[4], Message('SEND', 'Hello'))

        for _ in range(random.randint(0,10)):
            self.ts.step(1)

        # crash Alice
        self.ts.crash_process(self.peers[0])

        for _ in range(random.randint(0,10)):
            self.ts.step(1)

        # crash Bob
        self.ts.crash_process(self.peers[1])

        for _ in range(random.randint(0,10)):
            self.ts.step(1)
        
        # crash Carl
        self.ts.crash_process(self.peers[2])

        # deliver the message
        self.ts.step_until_no_events(1)

        # check agreement property
        crashed = ['Alice', 'Bob', 'Carl']
        correct = ['Dan', 'Eve']
        crashed_delivered = 0
        correct_delivered = 0
        for peer in self.peers:
            msg = self.ts.wait_local_message(peer, 0)
            if msg is not None:
                if peer in crashed:
                    crashed_delivered += 1
                else:
                    correct_delivered += 1
        passed = False
        if crashed_delivered == 0 and correct_delivered == 0:
            passed = True
        if crashed_delivered == 0 and correct_delivered == len(correct):
            passed = True
        if crashed_delivered > 0 and correct_delivered == len(correct):
            passed = True
        self.assertTrue(passed, 
            "Agreement property is not satisfied: correct - " + str(correct_delivered) + "/2, crashed - " + str(crashed_delivered) + "/3")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(dest='impl_dir', metavar='DIRECTORY',
                        help="directory with implementation to test")
    parser.add_argument('-d', dest='debug', action='store_true',
                        help="include debugging output from implementation")
    args = parser.parse_args()

    logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.DEBUG)

    tests = [
        BasicTestCase(
            args.impl_dir, args.debug),
        ReliableTestCase(
            args.impl_dir, args.debug),
        UniformReliableTestCase(
            args.impl_dir, args.debug),
        OrderedTestCase(
            args.impl_dir, args.debug),
        TwoCrashesTestCase(
            args.impl_dir, args.debug),
        TwoCrashesRandomTestCase(
            args.impl_dir, args.debug),
        # uncomment to see what happens when 3 of 5 processes fail
        # ThreeCrashesRandomTestCase(
        #     args.impl_dir, args.debug),
    ]
    suite = unittest.TestSuite()
    suite.addTests(tests)

    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    if not result.wasSuccessful():
        return 1


if __name__ == "__main__":
    sys.exit(main())
