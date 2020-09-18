#!/usr/bin/env python3

import argparse
import logging
import os
import subprocess
import sys
import threading
import unittest

from dslib.message import Message
from dslib.test_server import TestMode, TestServer


SERVER_ADDR = 'localhost:9701'
TEST_SERVER_ADDR = 'localhost:9746'


def run_server(impl_dir, server_addr, ts_addr, debug):
    env = os.environ.copy()
    env['TEST_SERVER'] = ts_addr
    cmd = ['python3', os.path.join(impl_dir, 'server.py'), '-l', server_addr]
    if debug:
        cmd.append('-d')
        out = None
    else:
        out = subprocess.DEVNULL
    process = subprocess.Popen(cmd, env=env, stdout=out, stderr=out)
    threading.Thread(target=process.communicate).start()
    return process


def run_client(impl_dir, server_addr, ts_addr, debug):
    env = os.environ.copy()
    env['TEST_SERVER'] = ts_addr
    cmd = ['python3', os.path.join(impl_dir, 'client.py'), '-s', server_addr]
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
        self.server = run_server(self.impl_dir, SERVER_ADDR, TEST_SERVER_ADDR, self.debug)
        self.client = run_client(self.impl_dir, SERVER_ADDR, TEST_SERVER_ADDR, self.debug)

    def tearDown(self):
        self.client.terminate()
        self.server.terminate()
        self.ts.stop()
        self.client.kill()
        self.server.kill()


class BasicTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")

        req = Message('PING', 'Hello!')
        self.ts.send_local_message('client', req)        
        resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(resp, "Client response timeout")
        self.assertEqual(resp.type, 'PONG')
        self.assertEqual(resp.body, req.body)


class PingLostTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")
        
        req = Message('PING', 'Hello!')
        self.ts.send_local_message('client', req)        
        self.ts.set_message_drop_rate(1)
        self.ts.step(1)
        self.ts.set_message_drop_rate(0)
        resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(resp, "Client response timeout")
        self.assertEqual(resp.type, 'PONG')
        self.assertEqual(resp.body, req.body)


class PongLostTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")
        
        req = Message('PING', 'Hello!')
        self.ts.send_local_message('client', req)
        self.ts.step(1)        
        self.ts.set_message_drop_rate(1)
        self.ts.step(1)
        self.ts.set_message_drop_rate(0)
        resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(resp, "Client response timeout")
        self.assertEqual(resp.type, 'PONG')
        self.assertEqual(resp.body, req.body)


class PingDelayedTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")
        
        req = Message('PING', 'Hello!')
        self.ts.send_local_message('client', req)        
        self.ts.set_message_delay(1)
        self.ts.step(1)
        self.ts.set_message_delay(0)
        resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(resp, "Client response timeout")
        self.assertEqual(resp.type, 'PONG')
        self.assertEqual(resp.body, req.body)


class PongDelayedTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")
        
        req = Message('PING', 'Hello!')
        self.ts.send_local_message('client', req)
        self.ts.step(1)
        self.ts.set_message_delay(1)
        self.ts.step(1)
        self.ts.set_message_delay(0)
        resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(resp, "Client response timeout")
        self.assertEqual(resp.type, 'PONG')
        self.assertEqual(resp.body, req.body)


class ServerCrashTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")
        
        req = Message('PING', 'Hello!')
        self.ts.send_local_message('client', req)
        self.ts.crash_process('server')
        resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(resp, "Client response timeout")
        self.assertEqual(resp.type, 'PONG')
        self.assertEqual(resp.body, req.body)


class RandomDropsTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")
        self.ts.set_real_time_mode(False)
        
        req = Message('PING', 'Hello!')
        self.ts.send_local_message('client', req)
        self.ts.set_message_drop_rate(0.5)
        self.ts.steps(100, 1)
        self.ts.set_message_drop_rate(0)
        resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(resp, "Client response timeout")
        self.assertEqual(resp.type, 'PONG')
        self.assertEqual(resp.body, req.body)


class RandomDelaysTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")
        self.ts.set_real_time_mode(False)
        
        req = Message('PING', 'Hello!')
        self.ts.send_local_message('client', req)
        self.ts.set_message_delay(0.5, 1.5)
        self.ts.steps(100, 1)
        self.ts.set_message_delay(0)
        resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(resp, "Client response timeout")
        self.assertEqual(resp.type, 'PONG')
        self.assertEqual(resp.body, req.body)


class RandomReorderingTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")
        self.ts.set_real_time_mode(False)
        
        req = Message('PING', 'Hello!')
        self.ts.send_local_message('client', req)
        self.ts.set_event_reordering(True)
        self.ts.steps(100, 1)
        self.ts.set_event_reordering(False)
        resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(resp, "Client response timeout")
        self.assertEqual(resp.type, 'PONG')
        self.assertEqual(resp.body, req.body)


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
        PingLostTestCase(
            args.impl_dir, args.debug),
        PongLostTestCase(
            args.impl_dir, args.debug),
        PingDelayedTestCase(
            args.impl_dir, args.debug),
        PongDelayedTestCase(
            args.impl_dir, args.debug),
        ServerCrashTestCase(
            args.impl_dir, args.debug),
        RandomDropsTestCase(
            args.impl_dir, args.debug),
        RandomDelaysTestCase(
            args.impl_dir, args.debug),
        RandomReorderingTestCase(
            args.impl_dir, args.debug),
    ]
    suite = unittest.TestSuite()
    suite.addTests(tests)

    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    if not result.wasSuccessful():
        return 1


if __name__ == "__main__":
    sys.exit(main())
