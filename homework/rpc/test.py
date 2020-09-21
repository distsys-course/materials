
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


def run_client(impl_dir, serv_addr, ts_addr, debug):
    env = os.environ.copy()
    env["TEST_SERVER"] = ts_addr
    cmd = ['/usr/bin/env', 'python3', os.path.join(impl_dir, 'client.py'), '-s', serv_addr]
    if debug:
        cmd.append("-d")
        out = None
    else:
        out = subprocess.DEVNULL
    process = subprocess.Popen(cmd, env=env, stdout=out, stderr=out)
    threading.Thread(target=process.communicate).start()
    return process


def run_server(impl_dir, serv_addr, ts_addr, debug):
    env = os.environ.copy()
    env["TEST_SERVER"] = ts_addr
    cmd = ['/usr/bin/env', 'python3', os.path.join(impl_dir, 'server.py'), '-l', serv_addr]
    if debug:
        cmd.append("-d")
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
        self.user = run_client(self.impl_dir, SERVER_ADDR, TEST_SERVER_ADDR, self.debug)
        

    def tearDown(self):
        self.server.terminate()
        self.user.terminate()
        self.ts.stop()
        self.server.kill()
        self.user.kill()


class BasicPutTestCase(BaseTestCase):
    
    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")
        self.ts.step(1)

        client_req = Message("CALL", "put field 2 False")
        self.ts.send_local_message('client', client_req)
        self.ts.step_until_no_events(1)
        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(client_resp)
        self.assertEqual(client_resp.type, "RESULT")
        self.assertEqual(client_resp.body, True)

        client_req = Message("CALL", "put field 3 True")
        self.ts.send_local_message('client', client_req, 1)
        self.ts.step_until_no_events(1)
        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(client_resp)
        self.assertEqual(client_resp.type, "RESULT")
        self.assertEqual(client_resp.body, True)

        client_req = Message("CALL", "put field 2 False")
        self.ts.send_local_message('client', client_req, 1)
        self.ts.step_until_no_events(1)
        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(client_resp)
        self.assertEqual(client_resp.type, "RESULT")
        self.assertEqual(client_resp.body, False)

        self.ts.step_until_no_events(1)

        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNone(client_resp)


class BasicGetTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")
        self.ts.set_real_time_mode(True)
        self.ts.step(1)

        client_req = Message("CALL", "get field")
        self.ts.send_local_message('client', client_req, 1)
        self.ts.step_until_no_events(1)
        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(client_resp)
        self.assertEqual(client_resp.type, "ERROR")
        self.assertEqual(client_resp.body, "Key field not found")

        client_req = Message("CALL", "put field 2 True")
        self.ts.send_local_message('client', client_req, 1)
        self.ts.step_until_no_events(2)
        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(client_resp)
        self.assertEqual(client_resp.type, "RESULT")
        self.assertEqual(client_resp.body, True)

        client_req = Message("CALL", "get field")
        self.ts.send_local_message('client', client_req, 1)
        self.ts.step_until_no_events(2)
        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(client_resp)
        self.assertEqual(client_resp.type, "RESULT")
        self.assertEqual(client_resp.body, "2")

        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNone(client_resp)


class BasicAppendTestCase(BaseTestCase):
    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")
        
        client_req = Message("CALL", "put field 2 False")
        self.ts.send_local_message('client', client_req, 1)
        self.ts.step_until_no_events(1)
        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(client_resp)
        self.assertEqual(client_resp.type, "RESULT")
        self.assertEqual(client_resp.body, True)

        client_req = Message("CALL", "get field")
        self.ts.send_local_message('client', client_req, 1)
        self.ts.step_until_no_events(1)
        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(client_resp)
        self.assertEqual(client_resp.type, "RESULT")
        self.assertEqual(client_resp.body, "2")

        client_req = Message("CALL", "append field 2")
        self.ts.send_local_message('client', client_req, 1)
        self.ts.step_until_no_events(1)
        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(client_resp)
        self.assertEqual(client_resp.type, "RESULT")
        self.assertEqual(client_resp.body, "22")

        client_req = Message("CALL", "append unknown_field 2")
        self.ts.send_local_message('client', client_req, 1)
        self.ts.step_until_no_events(1)
        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(client_resp)
        self.assertEqual(client_resp.type, "ERROR")
        self.assertEqual(client_resp.body, "Key unknown_field not found")

        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNone(client_resp)


class BasicRemoveTestCase(BaseTestCase):
    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")
        
        client_req = Message("CALL", "remove field")
        self.ts.send_local_message('client', client_req, 1)
        self.ts.step_until_no_events(1)
        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(client_resp)
        self.assertEqual(client_resp.type, "ERROR")
        self.assertEqual(client_resp.body, "Key field not found")

        client_req = Message("CALL", "put field 2 False")
        self.ts.send_local_message('client', client_req, 1)
        self.ts.step_until_no_events(1)
        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(client_resp)
        self.assertEqual(client_resp.type, "RESULT")
        self.assertEqual(client_resp.body, True)

        client_req = Message("CALL", "get field")
        self.ts.send_local_message('client', client_req, 1)
        self.ts.step_until_no_events(1)
        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(client_resp)
        self.assertEqual(client_resp.type, "RESULT")
        self.assertEqual(client_resp.body, "2")

        client_req = Message("CALL", "remove field")
        self.ts.send_local_message('client', client_req, 1)
        self.ts.step_until_no_events(1)
        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(client_resp)
        self.assertEqual(client_resp.type, "RESULT")
        self.assertEqual(client_resp.body, "2")

        client_req = Message("CALL", "get field")
        self.ts.send_local_message('client', client_req, 1)
        self.ts.step_until_no_events(1)
        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(client_resp)
        self.assertEqual(client_resp.type, "ERROR")
        self.assertEqual(client_resp.body, "Key field not found")

        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNone(client_resp)


class BasicTimeoutTestCase(BaseTestCase):
    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")

        self.ts.set_message_delay(5)
        self.ts.set_real_time_mode(True)

        client_req = Message("CALL", "append field 2")
        self.ts.send_local_message('client', client_req, 1)
        self.ts.steps(20,1)
        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(client_resp)
        self.assertEqual(client_resp.type, "ERROR")
        self.assertEqual(client_resp.body, "Response timeout")

        self.ts.set_message_delay(1)
        self.ts.step(1)

        client_req = Message("CALL", "put field 2 False")
        self.ts.send_local_message('client', client_req, 1)
        self.ts.steps(20,1)
        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(client_resp)
        self.assertEqual(client_resp.type, "RESULT")
        self.assertEqual(client_resp.body, True)

        client_req = Message("CALL", "put field 2 False")
        self.ts.send_local_message('client', client_req, 1)
        self.ts.steps(20,1)
        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(client_resp)
        self.assertEqual(client_resp.type, "RESULT")
        self.assertEqual(client_resp.body, False)

        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNone(client_resp)


class CheckRepeatedCallsTestCase(BaseTestCase):
    def runTest(self):
        self.assertTrue(self.ts.wait_processes(2, 1), "Startup timeout")

        self.ts.set_message_drop_rate(0.4)

        client_req = Message("CALL", "get field")
        self.ts.send_local_message('client', client_req, 1)
        self.ts.steps(150,2)
        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(client_resp)
        self.assertEqual(client_resp.type, "ERROR")
        self.assertEqual(client_resp.body, "Key field not found")

        self.ts.set_message_drop_rate(0)
        client_req = Message("CALL", "put field 2 False")
        self.ts.send_local_message('client', client_req, 1)
        self.ts.step_until_no_events(1)
        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(client_resp)
        self.assertEqual(client_resp.type, "RESULT")
        self.assertEqual(client_resp.body, True)

        self.ts.set_message_drop_rate(0.4)
        client_req = Message("CALL", "get field")
        self.ts.send_local_message('client', client_req, 1)
        self.ts.steps(150,2)
        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNotNone(client_resp)
        self.assertEqual(client_resp.type, "RESULT")
        self.assertEqual(client_resp.body, "2")


        client_resp = self.ts.step_until_local_message('client', 1)
        self.assertIsNone(client_resp)


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
        BasicPutTestCase(
            args.impl_dir, args.debug),
        BasicGetTestCase(
            args.impl_dir, args.debug),
        BasicAppendTestCase(
            args.impl_dir, args.debug),
        BasicRemoveTestCase(
            args.impl_dir, args.debug),
        BasicTimeoutTestCase(
            args.impl_dir, args.debug),
        CheckRepeatedCallsTestCase(
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
