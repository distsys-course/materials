#!/usr/bin/env python3

import argparse
import logging
import os
import random
import subprocess
import sys
import time
import threading
import unittest

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
        for i in range(self.node_count):
            self.node_processes[i].terminate()
        self.ts.stop()
        for i in range(self.node_count):
            try:
                self.node_processes[i].kill()
            except OSError:
                pass

    def step_until_stabilized(self, steps=10, timeout=10, group=None):
        if group is None:
            group = self.nodes
        synced_nodes = set()
        start = time.time()
        while time.time() - start < timeout and len(synced_nodes) < len(group):
            step_status = self.ts.steps(steps, 1)
            for node in group:
                if node not in synced_nodes:
                    self.ts.send_local_message(node, Message('GET_MEMBERS'))
                    msg = self.ts.step_until_local_message(node, 1)
                    self.assertIsNotNone(msg, "Members list is not returned")
                    self.assertEqual(msg.type, 'MEMBERS')
                    if len(msg.body) == len(group) and set(msg.body) == set(group):
                        synced_nodes.add(node)
            if not step_status:
                break
            # print(len(synced_nodes))
        self.assertEqual(synced_nodes, set(group), "Members lists are not stabilized")

    def restart_node(self, node):
        node_idx = node.replace('node', '')
        addr = '127.0.0.1:97%s' % node_idx
        self.node_processes[int(node_idx) - 1] = run_node(self.impl_dir, node, addr, TEST_SERVER_ADDR, self.debug)


class BasicTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, self.node_count), "Startup timeout")

        # add nodes to the group (seed is fisrt node)
        seed_addr = self.ts.get_process_addr(self.nodes[0])
        for node in self.nodes:
            self.ts.send_local_message(node, Message('JOIN', seed_addr))

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)

        # number of used messages
        logging.debug("MESSAGE COUNT: %d" % self.ts._message_count)


class RandomSeedTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, self.node_count), "Startup timeout")

        # add nodes to the group (seed is random)
        members = set()
        for node in self.nodes:
            if len(members) == 0:
                seed_addr = self.ts.get_process_addr(self.nodes[0])
            else:
                seed_addr = self.ts.get_process_addr(random.choice(tuple(members)))
            self.ts.send_local_message(node, Message('JOIN', seed_addr))
            members.add(node)

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)

        # number of used messages
        logging.debug("MESSAGE COUNT: %d" % self.ts._message_count)


class NodeJoinTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, self.node_count), "Startup timeout")

        # select node which will join the group later
        new_node = random.choice(self.nodes)
        self.nodes.remove(new_node)

        # add nodes to the group (seed is first node)
        seed_addr = self.ts.get_process_addr(self.nodes[0])
        for node in self.nodes:
            self.ts.send_local_message(node, Message('JOIN', seed_addr))

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)
        init_message_count = self.ts._message_count

        # new node joins the group
        self.ts.send_local_message(new_node, Message('JOIN', seed_addr))
        self.nodes.append(new_node)

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)

        # number of used messages
        logging.debug("MESSAGE COUNT: %d" % (self.ts._message_count - init_message_count))
        

class NodeLeaveTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, self.node_count), "Startup timeout")

        # add nodes to the group (seed is first node)
        seed_addr = self.ts.get_process_addr(self.nodes[0])
        for node in self.nodes:
            self.ts.send_local_message(node, Message('JOIN', seed_addr))

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)
        init_message_count = self.ts._message_count

        # node leaves the group
        left_node = random.choice(self.nodes)
        self.ts.send_local_message(left_node, Message('LEAVE'))
        self.nodes.remove(left_node)

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)

        # number of used messages
        logging.debug("MESSAGE COUNT: %d" % (self.ts._message_count - init_message_count))


class NodeCrashTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, self.node_count), "Startup timeout")

        # add nodes to the group (seed is first node)
        seed_addr = self.ts.get_process_addr(self.nodes[0])
        for node in self.nodes:
            self.ts.send_local_message(node, Message('JOIN', seed_addr))

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)
        init_message_count = self.ts._message_count

        # node crashes
        crashed_node = random.choice(self.nodes)
        self.ts.crash_process(crashed_node)
        self.nodes.remove(crashed_node)

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=30)

        # number of used messages
        logging.debug("MESSAGE COUNT: %d" % (self.ts._message_count - init_message_count))


class NodeCrashRecoverTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, self.node_count), "Startup timeout")

        # add nodes to the group (seed is first node)
        seed_addr = self.ts.get_process_addr(self.nodes[0])
        for node in self.nodes:
            self.ts.send_local_message(node, Message('JOIN', seed_addr))

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)

        # node crashes
        crashed_node = random.choice(self.nodes)
        self.ts.crash_process(crashed_node)
        self.nodes.remove(crashed_node)

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=30)
        init_message_count = self.ts._message_count

        # crashed node recovers
        self.restart_node(crashed_node)
        time.sleep(1)
        seed_addr = seed_addr = self.ts.get_process_addr(random.choice(tuple(self.nodes)))
        self.ts.send_local_message(crashed_node, Message('JOIN', seed_addr))
        self.nodes.append(crashed_node)

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)

        # number of used messages
        logging.debug("MESSAGE COUNT: %d" % (self.ts._message_count - init_message_count))


class NodeOfflineTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, self.node_count), "Startup timeout")

        # add nodes to the group (seed is first node)
        seed_addr = self.ts.get_process_addr(self.nodes[0])
        for node in self.nodes:
            self.ts.send_local_message(node, Message('JOIN', seed_addr))

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)
        init_message_count = self.ts._message_count

        # node disconnects
        offline_node = random.choice(self.nodes)
        self.ts.disconnect_process(offline_node)
        self.nodes.remove(offline_node)

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=30)

        # number of used messages
        logging.debug("MESSAGE COUNT: %d" % (self.ts._message_count - init_message_count))


class NodeOfflineRecoverTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, self.node_count), "Startup timeout")

        # add nodes to the group (seed is first node)
        seed_addr = self.ts.get_process_addr(self.nodes[0])
        for node in self.nodes:
            self.ts.send_local_message(node, Message('JOIN', seed_addr))

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)
        init_message_count = self.ts._message_count

        # node disconnects
        offline_node = random.choice(self.nodes)
        self.ts.disconnect_process(offline_node)
        self.nodes.remove(offline_node)

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=30)
        init_message_count = self.ts._message_count

        # node reconnects
        self.ts.connect_process(offline_node)
        self.nodes.append(offline_node)

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)

        # number of used messages
        logging.debug("MESSAGE COUNT: %d" % (self.ts._message_count - init_message_count))
        print(offline_node)


class NetworkPartitionTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, self.node_count), "Startup timeout")

        # add nodes to the group (seed is first node)
        seed_addr = self.ts.get_process_addr(self.nodes[0])
        for node in self.nodes:
            self.ts.send_local_message(node, Message('JOIN', seed_addr))

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)
        init_message_count = self.ts._message_count

        # network partition (odd and even nodes are isolated from each other)
        group1 = self.nodes[::2]
        group2 = self.nodes[1::2]
        self.ts.partition_network(group1, group2)

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=30, group=group1)
        self.step_until_stabilized(steps=10, timeout=30, group=group2)

        # number of used messages
        logging.debug("MESSAGE COUNT: %d" % (self.ts._message_count - init_message_count))


class NetworkPartitionRecoverTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, self.node_count), "Startup timeout")

        # add nodes to the group (seed is first node)
        seed_addr = self.ts.get_process_addr(self.nodes[0])
        for node in self.nodes:
            self.ts.send_local_message(node, Message('JOIN', seed_addr))

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)
        init_message_count = self.ts._message_count

        # network partition (odd and even nodes are isolated from each other)
        group1 = self.nodes[::2]
        group2 = self.nodes[1::2]
        self.ts.partition_network(group1, group2)

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=30, group=group1)
        self.step_until_stabilized(steps=10, timeout=30, group=group2)

        # network partition is healed
        self.ts.reset_network()

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=30)

        # number of used messages
        logging.debug("MESSAGE COUNT: %d" % (self.ts._message_count - init_message_count))


class NodeCannotReceiveTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, self.node_count), "Startup timeout")

        # add nodes to the group (seed is first node)
        seed_addr = self.ts.get_process_addr(self.nodes[0])
        for node in self.nodes:
            self.ts.send_local_message(node, Message('JOIN', seed_addr))

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)
        init_message_count = self.ts._message_count

        # node cannot receive messages
        blocked_node = random.choice(self.nodes)
        self.ts.drop_incoming(blocked_node)
        self.nodes.remove(blocked_node)

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=20)

        # number of used messages
        logging.debug("MESSAGE COUNT: %d" % (self.ts._message_count - init_message_count))


class NodesDisconnectedTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, self.node_count), "Startup timeout")

        # add nodes to the group (seed is first node)
        seed_addr = self.ts.get_process_addr(self.nodes[0])
        for node in self.nodes:
            self.ts.send_local_message(node, Message('JOIN', seed_addr))

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)
        init_message_count = self.ts._message_count

        # disconnect two nodes from each other
        node1 = random.choice(self.nodes)
        node2 = random.choice(self.nodes)
        self.ts.disable_link(node1, node2)
        self.ts.disable_link(node2, node1)

        # run for a while
        self.ts.step_until_no_events(10)

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=20)

        # number of used messages
        logging.debug("MESSAGE COUNT: %d" % (self.ts._message_count - init_message_count))


class FlakyNetworkTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, self.node_count), "Startup timeout")

        # add nodes to the group (seed is first node)
        seed_addr = self.ts.get_process_addr(self.nodes[0])
        for node in self.nodes:
            self.ts.send_local_message(node, Message('JOIN', seed_addr))

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)
        init_message_count = self.ts._message_count

        # make network unreliable
        self.ts.set_message_drop_rate(0.5)

        # run for a while
        self.ts.step_until_no_events(15)

        # make network reliable
        self.ts.set_message_drop_rate(0)

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)

        # number of used messages
        logging.debug("MESSAGE COUNT: %d" % (self.ts._message_count - init_message_count))


class FlakyNetworkStartTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, self.node_count), "Startup timeout")

        # make network unreliable from the start
        self.ts.set_message_drop_rate(0.2)

        # add nodes to the group (seed is first node)
        seed_addr = self.ts.get_process_addr(self.nodes[0])
        for node in self.nodes:
            self.ts.send_local_message(node, Message('JOIN', seed_addr))

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)
        init_message_count = self.ts._message_count

        # run for a while
        self.ts.step_until_no_events(15)

        # make network reliable
        self.ts.set_message_drop_rate(0)

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)

        # number of used messages
        logging.debug("MESSAGE COUNT: %d" % (self.ts._message_count - init_message_count))


class FlakyNetworkCrashTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, self.node_count), "Startup timeout")

        # add nodes to the group (seed is first node)
        seed_addr = self.ts.get_process_addr(self.nodes[0])
        for node in self.nodes:
            self.ts.send_local_message(node, Message('JOIN', seed_addr))

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)
        init_message_count = self.ts._message_count

        # make network unreliable and crash one node
        self.ts.set_message_drop_rate(0.5)
        crashed_node = random.choice(self.nodes)
        self.ts.crash_process(crashed_node)
        self.nodes.remove(crashed_node)

        # run for a while
        self.ts.step_until_no_events(15)

        # make network reliable
        self.ts.set_message_drop_rate(0)

        # step until all nodes know each other
        self.step_until_stabilized(steps=10, timeout=10)

        # number of used messages
        logging.debug("MESSAGE COUNT: %d" % (self.ts._message_count - init_message_count))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', dest='node_count', type=int, default=10,
                        help="number of nodes")
    parser.add_argument('-d', dest='debug', action='store_true',
                        help="include debugging output from implementation")
    parser.add_argument(dest='impl_dir', metavar='DIRECTORY',
                        help="directory with implementation to test")
    args = parser.parse_args()

    logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.DEBUG)

    tests = [
        BasicTestCase(
            args.impl_dir, args.node_count, debug=args.debug),
        RandomSeedTestCase(
            args.impl_dir, args.node_count, debug=args.debug),
        NodeJoinTestCase(
            args.impl_dir, args.node_count, debug=args.debug),
        NodeLeaveTestCase(
            args.impl_dir, args.node_count, debug=args.debug),
        NodeCrashTestCase(
            args.impl_dir, args.node_count, debug=args.debug),
        NodeCrashRecoverTestCase(
            args.impl_dir, args.node_count, debug=args.debug),
        NodeOfflineTestCase(
            args.impl_dir, args.node_count, debug=args.debug),
        NodeOfflineRecoverTestCase(
            args.impl_dir, args.node_count, debug=args.debug),
        NetworkPartitionTestCase(
            args.impl_dir, args.node_count, debug=args.debug),
        NetworkPartitionRecoverTestCase(
            args.impl_dir, args.node_count, debug=args.debug),
        NodeCannotReceiveTestCase(
            args.impl_dir, args.node_count, debug=args.debug),
        FlakyNetworkTestCase(
            args.impl_dir, args.node_count, debug=args.debug),
        FlakyNetworkStartTestCase(
            args.impl_dir, args.node_count, debug=args.debug),
        FlakyNetworkCrashTestCase(
            args.impl_dir, args.node_count, debug=args.debug),
        ]
    suite = unittest.TestSuite()
    suite.addTests(tests)

    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    if not result.wasSuccessful():
        return 1


if __name__ == "__main__":
    sys.exit(main())
