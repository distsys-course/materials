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

        for node in group:
            self.send_join(node, group[0])

        self.step_until_stabilized(group=group, expect_keys=0)

    def step_until_stabilized(self, steps=10, timeout=10, group=None, expect_keys=None):
        if group is None:
            group = self.nodes
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
            if expect_keys is not None:
                counts_changed = False
                for i, node in enumerate(group):
                    self.ts.send_local_message(node, Message('COUNT_RECORDS'))
                    msg = self.ts.step_until_local_message(node, 1)
                    self.assertEqual(msg.type, 'COUNT_RECORDS_RESP')
                    count = int(msg.body)
                    if count != counts[i]:
                        counts_changed = True
                    counts[i] = count
            if len(synced_nodes) == len(group) and (expect_keys is None or (sum(counts) == expect_keys and not counts_changed)):
                break
            if not step_status:
                break

        self.assertEqual(synced_nodes, set(group), "Members lists are not stabilized")
        if expect_keys is not None:
            self.assertEqual(sum(counts), expect_keys, "Keys are not stabilized")

    def random_str(self):
        return ''.join(random.choices(string.ascii_lowercase, k=8))

    def send_join(self, node, seed):
        seed_addr = self.ts.get_process_addr(seed)
        self.ts.send_local_message(node, Message('JOIN', seed_addr))

    def send_leave(self, node):
        self.ts.send_local_message(node, Message('LEAVE'))

    def send_get(self, node, key, quorum=2, timeout=1):
        self.ts.send_local_message(node, Message('GET', {'key': key, 'quorum': quorum}))
        msg = self.ts.step_until_local_message(node, timeout)
        self.assertIsNotNone(msg, "GET response is not received")
        self.assertEqual(msg.type, 'GET_RESP')
        self.assertIsNotNone(msg.body)
        self.assertTrue(isinstance(msg.body, dict), "GET response is not dict")
        self.assertTrue('values' in msg.body)
        self.assertTrue('metadata' in msg.body)
        self.assertEqual(len(msg.body['values']), len(msg.body['metadata']))
        return (msg.body['values'], msg.body['metadata'])

    def send_put(self, node, key, value, metadata=None, quorum=2, wait=True, timeout=1):
        body = {'key': key, 'value': value, 'quorum': quorum}
        if metadata is not None:
            body['metadata'] = metadata
        self.ts.send_local_message(node, Message('PUT', body))
        if wait:
            msg = self.ts.step_until_local_message(node, timeout)
            self.assertIsNotNone(msg, "PUT response is not received")
            self.assertEqual(msg.type, 'PUT_RESP')
            self.assertIsNotNone(msg.body)
            return msg.body

    def lookup_key(self, node, key, timeout=1):
        self.ts.send_local_message(node, Message('LOOKUP', key))
        msg = self.ts.step_until_local_message(node, timeout)
        self.assertIsNotNone(msg, "LOOKUP response is not received")
        self.assertEqual(msg.type, 'LOOKUP_RESP')
        self.assertIsNotNone(msg.body)
        self.assertTrue(isinstance(msg.body, list), "LOOKUP response is not list")
        return msg.body


class BasicTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, 5), "Startup timeout")

        self.init_cluster()

        key = self.random_str()        
        replicas = self.lookup_key(self.nodes[0], key)
        self.assertEqual(len(replicas), 3)
        replicas = [x[0] for x in replicas]

        values, metadata = self.send_get(self.nodes[0], key, quorum=2)
        self.assertEqual(values, [])
        self.assertEqual(metadata, [])

        value1 = self.random_str()
        put_metadata = self.send_put(replicas[0], key, value1, quorum=2)
        
        values, metadata = self.send_get(replicas[2], key, quorum=2)
        self.assertEqual(values, [value1])
        self.assertEqual(metadata[0], put_metadata)

        non_replicas = [x for x in self.nodes if x not in replicas]
        values, metadata = self.send_get(non_replicas[0], key, quorum=2)
        self.assertEqual(values, [value1])
        self.assertEqual(metadata[0], put_metadata)

        value2 = self.random_str()
        put_metadata = self.send_put(non_replicas[-1], key, value2, metadata=put_metadata, quorum=2)

        values, metadata = self.send_get(self.nodes[0], key, quorum=2)
        self.assertEqual(values, [value2])
        self.assertEqual(metadata[0], put_metadata)


class ReplicasCheckTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, 5), "Startup timeout")

        self.init_cluster()

        key = self.random_str()
        value = self.random_str()

        replicas = self.lookup_key(self.nodes[0], key)
        self.assertEqual(len(replicas), 3)
        replicas = [x[0] for x in replicas]

        self.send_put(replicas[0], key, value, quorum=3)

        for node in replicas:
            self.ts.disconnect_process(node)
            values, _ = self.send_get(node, key, quorum=1)
            self.assertEqual(values, [value])


class StaleReplicaTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, 5), "Startup timeout")

        self.init_cluster()

        key = self.random_str()
        value1 = self.random_str()
        value2 = self.random_str()

        replicas = self.lookup_key(self.nodes[0], key)
        self.assertEqual(len(replicas), 3)
        replicas = [x[0] for x in replicas]

        metadata = self.send_put(replicas[0], key, value1, quorum=3)

        self.ts.disconnect_process(replicas[2])

        self.send_put(replicas[0], key, value2, metadata=metadata, quorum=2)

        self.ts.disconnect_process(replicas[0])
        self.ts.connect_process(replicas[2])

        values, metadata = self.send_get(replicas[2], key, quorum=2)
        self.assertEqual(values, [value2])

        self.ts.steps(50, 30)
        self.ts.disconnect_process(replicas[2])
        values, metadata = self.send_get(replicas[2], key, quorum=1)
        self.assertEqual(values, [value2])


class ReplicasDivergenceTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, 5), "Startup timeout")

        self.init_cluster()

        key = self.random_str()
        value = self.random_str()

        replicas = self.lookup_key(self.nodes[0], key)
        self.assertEqual(len(replicas), 3)
        replicas = [x[0] for x in replicas]

        metadata = self.send_put(replicas[0], key, value, quorum=3)

        new_values = []
        for node in replicas:
            value = self.random_str()
            new_values.append(value)
            self.ts.disconnect_process(node)
            self.send_put(node, key, value, metadata=metadata, quorum=1)

        self.ts.reset_network()
        self.ts.steps(100, 30)

        values, metadata = self.send_get(replicas[0], key, quorum=3)
        self.assertEqual(set(values), set(new_values))


class SloppyQuorumTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, 5), "Startup timeout")

        self.init_cluster()

        key = self.random_str()
        value1 = self.random_str()
        value2 = self.random_str()

        replicas = self.lookup_key(self.nodes[0], key)
        self.assertEqual(len(replicas), 3)
        replicas = [x[0] for x in replicas]

        metadata = self.send_put(self.nodes[0], key, value1, quorum=3)
        
        # temporary fail one replica
        self.ts.disconnect_process(replicas[0])

        metadata = self.send_put(replicas[1], key, value2, metadata=metadata, quorum=3, timeout=10)

        values, metadata = self.send_get(replicas[1], key, quorum=3)
        self.assertEqual(values, [value2])

        # recover failed replica and let it receive the update
        self.ts.connect_process(replicas[0])
        self.ts.steps(30, 10)

        # now check it
        self.ts.disconnect_process(replicas[0])
        values, metadata = self.send_get(replicas[0], key, quorum=1)
        self.assertEqual(values, [value2])


class PartitionedClientTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, 5), "Startup timeout")

        self.init_cluster()

        key = self.random_str()
        value = self.random_str()

        replicas = self.lookup_key(self.nodes[0], key)
        self.assertEqual(len(replicas), 3)
        replicas = [x[0] for x in replicas]
        non_replicas = [x for x in self.nodes if x not in replicas]

        # partition client from all replicas
        client = non_replicas[0]
        self.ts.partition_network(non_replicas, replicas)

        put_metadata = self.send_put(client, key, value, quorum=2, timeout=60)
        values, metadata = self.send_get(client, key, quorum=2)
        self.assertEqual(values, [value])
        self.assertEqual(metadata, [put_metadata])


class PartitionedClientsTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, 5), "Startup timeout")

        self.init_cluster()

        key = self.random_str()
        value = self.random_str()

        replicas = self.lookup_key(self.nodes[0], key)
        self.assertEqual(len(replicas), 3)
        replicas = [x[0] for x in replicas]
        non_replicas = [x for x in self.nodes if x not in replicas]
        client1 = non_replicas[0]
        client2 = non_replicas[1]
        client3 = non_replicas[2]

        metadata = self.send_put(self.nodes[0], key, value, quorum=2)

        # partition clients and replicas
        part1 = [client1, client2, replicas[0]]
        part2 = [client3, replicas[1], replicas[2]]
        self.ts.partition_network(part1, part2)

        # partition 1
        values, metadata = self.send_get(client1, key, quorum=2, timeout=30)
        value1 = values[0] + '1'
        metadata = self.send_put(client1, key, value1, metadata=metadata[0], quorum=2)
        values, metadata = self.send_get(client2, key, quorum=2, timeout=30)
        value1 = values[0] + '2'
        metadata = self.send_put(client2, key, value1, metadata=metadata[0], quorum=2)
        values, metadata = self.send_get(client2, key, quorum=2)
        self.assertEqual(values, [value + '12'])

        # partition 2
        values, metadata = self.send_get(client3, key, quorum=2, timeout=30)
        value2 = values[0] + '3'
        metadata = self.send_put(client3, key, value2, metadata=metadata[0], quorum=2)
        values, metadata = self.send_get(client3, key, quorum=2)
        self.assertEqual(values, [value + '3'])

        # heal partition
        self.ts.reset_network()
        self.ts.steps(100, 30)

        values1, metadata1 = self.send_get(client1, key, quorum=2)
        values2, metadata2 = self.send_get(client2, key, quorum=2)
        values3, metadata3 = self.send_get(client2, key, quorum=2)
        self.assertEqual(set(values1), set([value1, value2]))
        self.assertEqual(set(values1), set(values2))
        self.assertEqual(set(values2), set(values3))
        self.assertEqual(set(metadata1), set(metadata2))
        self.assertEqual(set(metadata2), set(metadata3))
        self.assertEqual(set(values1), set(values2))

        for node in replicas:
            self.ts.disconnect_process(node)
            values, _ = self.send_get(node, key, quorum=1)
            self.assertEqual(set(values), set([value1, value2]))


class ShoppingCartTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, 5), "Startup timeout")

        self.init_cluster()

        key = 'cart-' + self.random_str()

        replicas = self.lookup_key(self.nodes[0], key)
        self.assertEqual(len(replicas), 3)
        replicas = [x[0] for x in replicas]
        non_replicas = [x for x in self.nodes if x not in replicas]
        client1 = non_replicas[0]
        client2 = non_replicas[1]
        client3 = non_replicas[2]

        metadata = self.send_put(client1, key, 'cheese,wine', quorum=2)

        # partition clients and replicas
        part1 = [client1, client2, replicas[0]]
        part2 = [client3, replicas[1], replicas[2]]
        self.ts.partition_network(part1, part2)

        # partition 1
        values, metadata = self.send_get(client1, key, quorum=2, timeout=30)
        value1 = values[0] + ',milk'
        metadata = self.send_put(client1, key, value1, metadata=metadata[0], quorum=2)
        values, metadata = self.send_get(client2, key, quorum=2, timeout=30)
        value1 = values[0] + ',eggs'
        metadata = self.send_put(client2, key, value1, metadata=metadata[0], quorum=2)
        values, metadata = self.send_get(client2, key, quorum=2)
        self.assertEqual(values, ['cheese,wine,milk,eggs'])

        # partition 2
        values, metadata = self.send_get(client3, key, quorum=2, timeout=30)
        value2 = 'snacks,beer'
        metadata = self.send_put(client3, key, value2, metadata=metadata[0], quorum=2)
        values, metadata = self.send_get(client3, key, quorum=2)
        self.assertEqual(values, ['snacks,beer'])

        # heal partition
        self.ts.reset_network()
        self.ts.steps(100, 30)

        values1, metadata1 = self.send_get(client1, key, quorum=2)
        values2, metadata2 = self.send_get(client2, key, quorum=2)
        values3, metadata3 = self.send_get(client2, key, quorum=2)
        correct = set('cheese,beer,milk,wine,snacks,eggs'.split(','))
        self.assertEqual(set(values1[0].split(',')), correct)
        self.assertEqual(set(values1), set(values2))
        self.assertEqual(set(values2), set(values3))
        self.assertEqual(set(metadata1), set(metadata2))
        self.assertEqual(set(metadata2), set(metadata3))
        self.assertEqual(set(values1), set(values2))

        for node in replicas:
            self.ts.disconnect_process(node)
            values, _ = self.send_get(node, key, quorum=1)
            self.assertEqual(len(values), 1)
            self.assertEqual(set(values[0].split(',')), correct)


class NodeJoinTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, 5), "Startup timeout")

        self.init_cluster(group=self.nodes[1:])

        for _ in range(30):
            key = self.random_str()
            replicas = self.lookup_key(self.nodes[1], key)
            replicas = [x[0] for x in replicas]
            self.assertFalse(self.nodes[0] in replicas, 'Absent node is responsible for some key')

        value = self.random_str()
        self.send_put(self.nodes[1], key, value, quorum=3)

        self.send_join(self.nodes[0], self.nodes[1])
        self.step_until_stabilized()

        values, _ = self.send_get(self.nodes[0], key, quorum=3)
        self.assertEqual(values, [value])

        found = False
        for _ in range(100):
            key = self.random_str()
            replicas = self.lookup_key(self.nodes[1], key)
            replicas = [x[0] for x in replicas]
            if self.nodes[0] in replicas:
                found = True
                break
        self.assertTrue(found, 'Joined node is not reponsible for any of 1000 random keys')


class NodeLeaveTestCase(BaseTestCase):

    def runTest(self):
        self.assertTrue(self.ts.wait_processes(self.node_count, 5), "Startup timeout")

        self.init_cluster()

        key = self.random_str()
        value = self.random_str()

        replicas = self.lookup_key(self.nodes[0], key)
        replicas = [x[0] for x in replicas]

        self.send_put(self.nodes[0], key, value, quorum=2)

        leaved = replicas[0]
        left = [x for x in self.nodes if x != leaved]
        self.send_leave(leaved)
        self.step_until_stabilized(group=left)

        new_replicas = self.lookup_key(left[0], key)
        new_replicas = [x[0] for x in new_replicas]
        self.assertFalse(leaved in new_replicas, 'Leaved node is still responsible for the key')

        for _ in range(100):
            key = self.random_str()
            replicas = self.lookup_key(left[0], key)
            replicas = [x[0] for x in replicas]
            self.assertFalse(leaved in replicas, 'Absent node is responsible for some key')


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
            args.impl_dir, 6, debug=args.debug),
        ReplicasCheckTestCase(
            args.impl_dir, 6, debug=args.debug),
        StaleReplicaTestCase(
            args.impl_dir, 3, debug=args.debug),
        ReplicasDivergenceTestCase(
            args.impl_dir, 6, debug=args.debug),
        SloppyQuorumTestCase(
            args.impl_dir, 6, debug=args.debug),
        PartitionedClientTestCase(
            args.impl_dir, 6, debug=args.debug),
        PartitionedClientsTestCase(
            args.impl_dir, 6, debug=args.debug),
        ShoppingCartTestCase(
            args.impl_dir, 6, debug=args.debug),
        NodeJoinTestCase(
            args.impl_dir, 6, debug=args.debug),
        NodeLeaveTestCase(
            args.impl_dir, 6, debug=args.debug)
        ]
    suite = unittest.TestSuite()
    suite.addTests(tests)

    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    if not result.wasSuccessful():
        return 1


if __name__ == "__main__":
    sys.exit(main())
