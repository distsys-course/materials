import os
import time

import pytest
import requests

def wait_for_http(url):
    retries = 10
    exception = None
    while retries > 0:
        try:
            requests.get(url)
            return
        except requests.exceptions.ConnectionError as e:
            exception = e
            print(f'Got ConnectionError for url {url}: {e} , retrying')
            retries -= 1
            time.sleep(2)
    raise exception

@pytest.fixture
def client1_url():
    url = 'http://' + os.environ.get('MESSENGER_TEST_CLIENT1_ADDR', '127.0.0.1:8080')
    wait_for_http(url)
    get_messages(url)  # we need to flush pending messages before and after each tests
    yield url
    get_messages(url)


@pytest.fixture
def client2_url():
    url = 'http://' + os.environ.get('MESSENGER_TEST_CLIENT2_ADDR', '127.0.0.1:8081')
    wait_for_http(url)
    get_messages(url)
    yield url
    get_messages(url)


def send_message(url, mes):
    resp = requests.post(url + '/sendMessage', json=mes)
    assert resp.status_code == 200, resp.text
    return resp.json()


def get_messages(url):
    resp = requests.post(url + '/getAndFlushMessages')
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_single_client_single_message(client1_url):
    mes = {
        'author': 'TestSingleClient',
        'text': 'This is test text'
    }
    resp = send_message(client1_url, mes)
    mes['sendTime'] = resp['sendTime']
    time.sleep(0.1)  # just in case of network delays
    messages = get_messages(client1_url)
    assert len(messages) == 1
    assert messages[0] == mes


def test_single_client_multiple_messages(client1_url):
    mes = [{
        'author': 'TestSingleClient1',
        'text': 'This is test text'
    }, {
        'author': 'TestSingleClient2',
        'text': 'This is test text'
    }]
    for m in mes:
        resp = send_message(client1_url, m)
        m['sendTime'] = resp['sendTime']
    sorted(mes, key=lambda x: x['sendTime'])
    time.sleep(0.1)  # just in case of network delays
    messages = get_messages(client1_url)
    assert len(messages) == len(mes)
    for i in range(len(mes)):
        assert messages[i] == mes[i]


def test_two_clients_multiple_messages(client1_url, client2_url):
    client1_name = 'TestMultiClient1'
    client2_name = 'TestMultiClient2'
    mes = [{
        'author': client1_name,
        'text': 'This is test text #1'
    }, {
        'author': client1_name,
        'text': 'This is test text #2'
    }, {
        'author': client2_name,
        'text': 'This is test text #3'
    }, {
        'author': client2_name,
        'text': 'This is test text #4'
    }]
    times = set()
    for m in mes:
        resp = send_message(client1_url if m['author'] == client1_name else client2_url, m)
        m['sendTime'] = resp['sendTime']
        times.add(m['sendTime'])
    assert len(times) == len(mes)
    mes = sorted(mes, key=lambda x: x['sendTime'])
    time.sleep(0.1)  # just in case of network delays
    messages = get_messages(client1_url)
    assert len(messages) == len(mes)
    for i in range(len(mes)):
        assert messages[i] == mes[i]
    messages = get_messages(client2_url)
    assert len(messages) == len(mes)
    for i in range(len(mes)):
        assert messages[i] == mes[i]
