#!/usr/bin/env python3

import argparse
import logging
import os
import random
import string
import subprocess
import sys
import time
import threading
import unittest
from functools import reduce

from dslib.message import Message
from dslib.test_server import TestMode, TestServer


TEST_SERVER_ADDR = '127.0.0.1:9746'


def run_node(impl_dir, name, addr, ts_addr, debug):
    env = os.environ.copy()
    env['TEST_SERVER'] = ts_addr
    cmd = ['python3', os.path.join(impl_dir, 'node.py'), '-n', name, '-l', addr]
    if debug:
        cmd.append('-d')
        out = None
    else:
        out = subprocess.DEVNULL
    process = subprocess.Popen(cmd, env=env, stdout=out, stderr=out)
    threading.Thread(target=process.communicate).start()
    return process


class BaseTestCase(unittest.TestCase):

    def __init__(self, impl_dir, node_count, debug=False):
        super(BaseTestCase, self).__init__()
        self.impl_dir = impl_dir
        self.node_count = node_count
        self.keys_count = None
        self.debug = debug

    def setUp(self):
        super(BaseTestCase, self).setUp()
        sys.stderr.write("\n\n" + self.__class__.__name__ + " " + "-" * 60 + "\n\n")

        self.ts = TestServer(TEST_SERVER_ADDR)
        self.ts.start()
        self.nodes = []
        self.node_processes = []
        for i in range(self.node_count):
            name = 'node%02d' % (i+1)
            addr = '127.0.0.1:97%02d' % (i+1)
            self.nodes.append(name)
            proc = run_node(self.impl_dir, name, addr, TEST_SERVER_ADDR, self.debug)
            self.node_processes.append(proc)

    def tearDown(self):
        for i in range(len(self.node_processes)):
            self.node_processes[i].terminate()
        self.ts.stop()
        for i in range(len(self.node_processes)):
            try:
                self.node_processes[i].kill()
            except OSError:
                pass

    def init_cluster(self, group=None):
        if group is None:
            group = self.nodes

        weights = []
        for i in range(len(string.ascii_lowercase)):
            weights.append(random.randint(0, i^2))
        random.shuffle(weights)
        while True:
            self.keys = list(''.join(random.choices(string.ascii_lowercase, weights=weights, k=8)) for i in range(self.keys_count))
            if len(self.keys) == len(set(self.keys)):
                break
        self.values = {
            self.keys[i] : ''.join(random.choices(string.ascii_lowercase, k=8)) for i in range(self.keys_count)
        }
        random.shuffle(self.keys)

        seed_addr = self.ts.get_process_addr(group[0])
        for node in group:
            self.ts.send_local_message(node, Message('JOIN', seed_addr))

        self.step_until_stabilized(group=group, expect_keys=0)

        for i in range(self.keys_count):
            node = random.choice(group)
            self.ts.send_local_message(node, Message('PUT', f"{str(self.keys[i])}={self.values[self.keys[i]]}"))
            msg = self.ts.step_until_local_message(node, 1)
            self.assertIsNotNone(msg, "PUT response is not received")
            self.assertEqual(msg.type, 'PUT_RESP')

    def snapshot(self):
        dumped_keys = []
        for node in self.nodes:
            self.ts.send_local_message(node, Message('DUMP_KEYS'))
            msg = self.ts.step_until_local_message(node, 2)
            self.assertEqual(msg.type, 'DUMP_KEYS_RESP')
            dumped_keys.append(msg.body)
        return dumped_keys

    def check_distribution(self):
        snapshot = self.snapshot()
        stored_keys = reduce(lambda a, b: set(a) | set(b), snapshot)
        all_keys_are_stored = (set(self.keys) == stored_keys)
        total_records = sum(map(len, snapshot))
        max_keys_per_node = max(map(len, snapshot))
        min_keys_per_node = min(map(len, snapshot))
        if len(self.keys) > 0:
            target_keys_per_node = len(self.keys) / len(self.nodes)
            average_deviation = sum(map(lambda x: abs(len(x) - target_keys_per_node) / target_keys_per_node, snapshot)) / len(self.nodes)
            max_deviation = max(map(lambda x: abs(len(x) - target_keys_per_node) / target_keys_per_node, snapshot))

        logging.info(
            "FINAL SNAPSHOT STATS:\n" +
            f" - keys are unique: " + ("OK" if total_records == len(stored_keys) else "FAIL") + '\n' +
            f" - all keys are stored: " + ("OK" if all_keys_are_stored else "FAIL") + '\n' +
            f" - max keys per node: {max_keys_per_node}\n" +
            f" - min keys per node: {min_keys_per_node}\n" + 
            ("" if len(self.keys) == 0 else "" +
                f" - target per node: {target_keys_per_node:.2f}\n" +
                f" - average deviation from target: {average_deviation*100:.2f}%\n" +
                f" - max deviation from target: {max_deviation*100:.2f}%\n"
            ) +
            ("" if len(stored_keys) > 100 else ''.join(
                f" - - {self.nodes[i]}: {sorted(snapshot[i])}\n" for i in range(len(self.nodes))
            ))
        )
        self.assertTrue(total_records == len(stored_keys), "Keys are not unique!")
        self.assertTrue(all_keys_are_stored, "Some keys are missing!")
        if len(stored_keys) > 100:
            self.assertTrue(max_deviation <= 0.2, "Key distribution is not balanced")

    def step_until_stabilized(self, steps=10, timeout=10, group=None, expect_keys=None):
        if group is None:
            group = self.nodes
        if expect_keys is None:
            expect_keys = len(self.keys)
        synced_nodes = set()
        counts = [0] * len(group)

        start = time.time()
        while time.time() - start < timeout:
            step_status = self.ts.steps(steps, 1)
            for node in group:
                if node not in synced_nodes:
                    self.ts.send_local_message(node, Message('GET_MEMBERS'))
                    msg = self.ts.step_until_local_message(node, 1)
                    self.assertIsNotNone(msg, "Members list is not returned")
                    self.assertEqual(msg.type, 'MEMBERS')
                    if len(msg.body) == len(group) and set(msg.body) == set(group):
                        synced_nodes.add(node)
            counts_changed = False
            for i, node in enumerate(group):
                self.ts.send_local_message(node, Message('COUNT_RECORDS'))
                msg = self.ts.step_until_local_message(node, 1)
                self.assertEqual(msg.type, 'COUNT_RECORDS_RESP')
                count = int(msg.body)
                if count != counts[i]:
                    counts_changed = True
                counts[i] = count
            if len(synced_nodes) == len(group) and sum(counts) == expect_keys and not counts_changed:
                break
            if not step_status:
                break

        self.assertEqual(synced_nodes, set(group), "Members lists are not stabilized")
        self.assertEqual(sum(counts), expect_keys, "Keys are not stabilized")


class BasicTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, 5), "Startup timeout")

        seed_addr = self.ts.get_process_addr(self.nodes[0])
        for i in range(self.node_count):
            self.ts.send_local_message(self.nodes[i], Message('JOIN', seed_addr))

        self.step_until_stabilized(expect_keys=0)

        self.keys_count = self.node_count
        self.keys = list(''.join(random.choices(string.ascii_lowercase, k=8)) for i in range(self.keys_count))
        self.values = {
            self.keys[i] : ''.join(random.choices(string.ascii_lowercase, k=8)) for i in range(self.keys_count)
        }
        random.shuffle(self.keys)

        for i in range(self.node_count):
            self.ts.send_local_message(self.nodes[i], Message('PUT', f"{str(self.keys[i])}={self.values[self.keys[i]]}"))
            msg = self.ts.step_until_local_message(self.nodes[i], 2)
            self.assertIsNotNone(msg, "PUT response is not received")
            self.assertEqual(msg.type, 'PUT_RESP')

        tests = []
        for i in range(0, self.node_count):
            for k, v in self.values.items():
                tests.append([i, k, v])
        random.shuffle(tests)

        for nodeid, key, value in tests:
            self.ts.send_local_message(self.nodes[nodeid], Message('GET', key))
            msg = self.ts.step_until_local_message(self.nodes[nodeid], 1)
            self.assertIsNotNone(msg, "GET response is not received")
            self.assertEqual(msg.type, 'GET_RESP')
            self.assertEqual(msg.body, value)

        self.check_distribution()


class DeleteTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, 5), "Startup timeout")

        self.keys_count = 10
        self.init_cluster()

        random.shuffle(self.keys)
        for k in self.keys:
            request_node = random.choice(self.nodes)
            delete_node = random.choice(self.nodes)

            self.ts.send_local_message(request_node, Message('GET', k))
            msg = self.ts.step_until_local_message(request_node, 1)
            self.assertIsNotNone(msg, "GET response is not received")
            self.assertEqual(msg.type, "GET_RESP")
            self.assertEqual(msg.body, self.values[k])

            self.ts.send_local_message(delete_node, Message('DELETE', k))
            msg = self.ts.step_until_local_message(delete_node, 1)
            self.assertIsNotNone(msg, "DELETE response is not received")
            self.assertEqual(msg.type, "DELETE_RESP")
            self.assertIsNone(msg.body) 
            
            self.ts.send_local_message(request_node, Message('GET', k))
            msg = self.ts.step_until_local_message(request_node, 1)
            self.assertIsNotNone(msg, "GET response is not received")
            self.assertEqual(msg.type, "GET_RESP")
            self.assertEqual(msg.body, '')
        
        self.keys = []
        self.keys_count = 0
        self.step_until_stabilized()
        self.check_distribution()


class LeaveTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, 5), "Startup timeout")

        self.keys_count = 100
        self.init_cluster()

        leave_node = random.choice(self.nodes)
        self.ts.send_local_message(leave_node, Message('COUNT_RECORDS'))
        msg = self.ts.step_until_local_message(leave_node, 1)

        self.assertIsNotNone(msg, "COUNT_RECORDS is not responced")
        self.assertEqual(msg.type, 'COUNT_RECORDS_RESP')
        self.assertNotEqual(msg.body, 0, "Node stores no records, bad distribution")

        self.ts.send_local_message(leave_node, Message('LEAVE'))
        self.nodes.remove(leave_node)
        
        self.step_until_stabilized()
        self.check_distribution()


class SwingTestCase(BaseTestCase):

    def runTest(self):
        self.ts.set_real_time_mode(False)
        self.assertTrue(self.ts.wait_processes(self.node_count, 5), "Startup timeout")

        self.keys_count = 100
        group = self.nodes[:5]
        self.init_cluster(group=group)

        seed_addr = self.ts.get_process_addr(random.choice(self.nodes[:5]))
        for node in self.nodes[5:]:
            self.ts.send_local_message(node, Message('JOIN', seed_addr))
            group.append(node)
            self.step_until_stabilized(group=group)
        
        self.check_distribution()

        for node in self.nodes[5:]:
            self.ts.send_local_message(node, Message('LEAVE'))
            group.remove(node)
            self.step_until_stabilized(group=group)

        self.nodes = self.nodes[:5]
        self.check_distribution()


class CrashTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, 5), "Startup timeout")

        self.keys_count = 100
        self.init_cluster()

        victim = random.choice(self.nodes)
        self.ts.send_local_message(victim, Message('DUMP_KEYS'))
        msg = self.ts.step_until_local_message(victim, 1)
        self.assertIsNotNone(msg, "DUMP_KEYS response is not received")
        self.assertEqual(msg.type, 'DUMP_KEYS_RESP')
        victim_keys = set(msg.body)
        self.assertTrue(len(victim_keys) > 0, "Node stores no records, bad distribution")

        self.ts.crash_process(victim)
        self.nodes.remove(victim)

        self.keys = [x for x in self.keys if x not in victim_keys]
        self.keys_count -= len(victim_keys)
        self.step_until_stabilized()

        query_node = random.choice(self.nodes)
        self.ts.send_local_message(query_node, Message('GET', list(victim_keys)[0]))
        msg = self.ts.step_until_local_message(query_node, 10)
        self.assertIsNotNone(msg, "GET response is not received")
        self.assertEqual(msg.type, 'GET_RESP')
        self.assertEqual(msg.body, '')

        self.check_distribution()


class BalancedStaticCase(BaseTestCase):

    def runTest(self):
        self.ts.set_real_time_mode(False)
        self.assertTrue(self.ts.wait_processes(self.node_count, 5), "Startup timeout")
        self.keys_count = 1000
        self.init_cluster()
        self.check_distribution()


class BalancedJoinCase(BaseTestCase):

    def runTest(self):
        self.ts.set_real_time_mode(False)
        self.assertTrue(self.ts.wait_processes(self.node_count, 5), "Startup timeout")
        self.keys_count = 1000
        group = self.nodes[:-1]
        self.init_cluster(group=group)
        s1 = self.snapshot()

        seed_addr = self.ts.get_process_addr(random.choice(self.nodes[:-1]))
        node = self.nodes[-1]
        self.ts.send_local_message(node, Message('JOIN', seed_addr))
        self.step_until_stabilized()
        s2 = self.snapshot()

        target = self.keys_count / self.node_count
        moved_keys_count = self.keys_count - sum(map(lambda a, b: len(set(a) & set(b)), s1, s2))
        deviation = ((moved_keys_count - target) / target) * 100

        self.check_distribution()
        logging.info(f" - moved keys: {moved_keys_count} | target: {target:.2f} | deviation: {deviation:.2f}%")
        self.assertTrue(deviation <= 20, "Deviation from target is more than 20%")


class BalancedLeaveCase(BaseTestCase):

    def runTest(self):
        self.ts.set_real_time_mode(False)
        self.assertTrue(self.ts.wait_processes(self.node_count, 5), "Startup timeout")
        self.keys_count = 1000
        self.init_cluster()
        s1 = self.snapshot()

        node = random.choice(self.nodes)
        s1.pop(self.nodes.index(node))
        self.ts.send_local_message(node, Message('LEAVE'))
        self.nodes.remove(node)
        self.step_until_stabilized()
        s2 = self.snapshot()

        target = self.keys_count / self.node_count
        moved_keys_count = self.keys_count - sum(map(lambda a, b: len(set(a) & set(b)), s1, s2))
        deviation = ((moved_keys_count - target) / target) * 100

        self.check_distribution()
        logging.info(f" - moved keys: {moved_keys_count} | target: {target:.2f} | deviation: {deviation:.2f}%")
        self.assertTrue(deviation <= 20, "Deviation from target is more than 20%")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', dest='verbose', action='store_true',
                        help="print messages and other info from tests")
    parser.add_argument('-d', dest='debug', action='store_true',
                        help="include debugging output from simplementation")
    parser.add_argument(dest='impl_dir', metavar='DIRECTORY',
                        help="directory with implementation to test")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.DEBUG)
    else:
        logging.basicConfig(format="%(message)s", level=logging.INFO)

    tests = [
        BasicTestCase(
            args.impl_dir, 5, debug=args.debug),
        DeleteTestCase(
            args.impl_dir, 5, debug=args.debug),
        LeaveTestCase(
            args.impl_dir, 5, debug=args.debug),
        SwingTestCase(
            args.impl_dir, 10, debug=args.debug),
        CrashTestCase(
            args.impl_dir, 5, debug=args.debug),
        BalancedStaticCase(
            args.impl_dir, 5, debug=args.debug),
        BalancedJoinCase(
            args.impl_dir, 6, debug=args.debug),
        BalancedLeaveCase(
            args.impl_dir, 5, debug=args.debug),
        ]
    suite = unittest.TestSuite()
    suite.addTests(tests)

    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    if not result.wasSuccessful():
        return 1


if __name__ == "__main__":
    sys.exit(main())
