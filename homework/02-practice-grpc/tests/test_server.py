import copy
import json
import os
import subprocess
import threading
import time
from typing import Dict, List
import socket

import pytest

test_message = {'author': 'alice', 'text': 'hello'}

SLEEP_S = 0.1

def wait_for_socket(host, port):
    retries = 10
    exception = None
    while retries > 0:
        try:
            socket.socket().connect((host, port))
            return
        except ConnectionRefusedError as e:
            exception = e
            print(f'Got ConnectionError for url {host}:{port}: {e} , retrying')
            retries -= 1
            time.sleep(2)
    raise exception


@pytest.fixture
def server_addr():
    addr = os.environ.get('MESSENGER_TEST_SERVER_ADDR', '127.0.0.1:51075')
    host = addr.split(':')[0]
    port = int(addr.split(':')[1])
    wait_for_socket(host, port)
    yield addr


def send_message(server_address, message: Dict[str, str]) -> Dict[str, str]:
    grpcurl_cmd = ['grpcurl',
                   '-proto', '../messenger/proto/messenger.proto',
                   '-d',
                   json.dumps(message),
                   '-plaintext',
                   server_address,
                   'mes_grpc.MessengerServer/SendMessage']
    completed = subprocess.run(grpcurl_cmd, capture_output=True, check=False)
    assert len(completed.stderr) == 0, completed.stderr
    output_str = completed.stdout.decode('ascii')
    output = json.loads(output_str)

    message_with_timestamp = copy.deepcopy(message)
    message_with_timestamp['sendTime'] = output['sendTime']
    return message_with_timestamp


class Waiter:
    def __init__(self):
        self.lock = threading.Lock()
        self.cv = threading.Condition(self.lock)
        self.breaking = False

    def wait(self):
        while True:
            with self.lock:
                self.cv.wait()
                if self.breaking:  # double check to prevent spurious wakeups
                    self.breaking = False
                    return

    def notify(self):
        with self.lock:
            self.breaking = True
            self.cv.notify()


def get_messages(server_address, waiter: Waiter) -> List[Dict]:
    grpcurl_cmd = ['grpcurl',
                   '-proto', '../messenger/proto/messenger.proto',
                   '-plaintext',
                   server_address,
                   'mes_grpc.MessengerServer/ReadMessages']
    completed = subprocess.Popen(grpcurl_cmd, stdout=subprocess.PIPE)

    waiter.wait()
    completed.terminate()

    stdout, _ = completed.communicate()

    if stdout is not None:
        output_str = stdout.decode('ascii')
    else:
        output_str = ''

    msg_list = grpcurl_output_str_to_dict_list(output_str)
    return msg_list


def grpcurl_output_str_to_dict_list(output_str: str) -> List[Dict]:
    output_str_list = output_str.split('}\n')[:-1]
    output_dict_list = [json.loads(output + '}') for output in output_str_list]
    return output_dict_list


def test_send_smoke(server_addr):
    send_message(server_addr, test_message)


def test_send_returns_ascending_time(server_addr):
    outputs = []
    for _ in range(10):
        outputs.append(send_message(server_addr, test_message))

    for output1, output2 in zip(outputs, outputs[1:]):
        assert output1['sendTime'] < output2['sendTime']


def test_get_messages_smoke(server_addr):
    waiter = Waiter()
    messages = []
    thread = threading.Thread(target=lambda: messages.extend(get_messages(server_addr, waiter)))
    thread.start()
    time.sleep(SLEEP_S)  # make sure get is running before sending anything

    test_message_with_timestamp = send_message(server_addr, test_message)

    time.sleep(SLEEP_S)
    waiter.notify()
    thread.join()

    assert len(messages) == 1
    assert messages[0] == test_message_with_timestamp


def test_get_only_sends_new(server_addr):
    messages1 = []
    messages3 = []
    n1, n2, n3 = 2, 3, 4

    waiter = Waiter()
    messages = []
    thread = threading.Thread(target=lambda: messages.extend(get_messages(server_addr, waiter)))
    thread.start()
    time.sleep(SLEEP_S)

    for _ in range(n1):
        message = send_message(server_addr, test_message)
        messages1.append(message)

    time.sleep(SLEEP_S)
    waiter.notify()
    thread.join()

    assert len(messages1) == len(messages)
    for m1, m2 in zip(messages1, messages):
        assert m1 == m2

    for _ in range(n2):
        send_message(server_addr, test_message)

    waiter = Waiter()
    messages = []
    thread = threading.Thread(target=lambda: messages.extend(get_messages(server_addr, waiter)))
    thread.start()
    time.sleep(SLEEP_S)

    for _ in range(n3):
        message = send_message(server_addr, test_message)
        messages3.append(message)

    time.sleep(SLEEP_S)
    waiter.notify()
    thread.join()

    assert len(messages3) == len(messages)
    for m1, m2 in zip(messages3, messages):
        assert m1 == m2

