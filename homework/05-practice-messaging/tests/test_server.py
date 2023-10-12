import pytest
import signal
import socket
import time

import requests
import requests_unixsocket
from loguru import logger
from pathlib import Path


def get_containers():
    session = requests_unixsocket.Session()
    response = session.get('http+unix://%2Ftmp%2Fdocker.sock/containers/json')
    assert response.status_code == 200
    server = None
    mq = None
    workers = []
    for item in response.json():
        if 'worker' in item['Image']:
            workers.append(item['Id'])
        elif 'web' in item['Image']:
            server = item['Id']
        elif 'rabbitmq' in item['Image']:
            mq = item['Id']
    return server, mq, workers


SERVER_HOST = 'web'
SERVER_PORT = 5000
URL = 'http://' + SERVER_HOST
if SERVER_PORT != 80:
    URL += ':{}'.format(SERVER_PORT)
IMAGES_ENDPOINT = URL + '/api/v1.0/images'
SERVER_ID, MQ_ID, WORKER_IDS = get_containers()


def test_post_image():
    input_data = {"image_url": "https://jrnlst.ru/sites/default/files/covers/cover_6.jpg"}
    response = requests.post(IMAGES_ENDPOINT, json=input_data)
    logger.info(response.json())
    assert response.status_code == 200
    assert 'image_id' in response.json()


def test_get_image():
    time.sleep(5)
    response = requests.get(IMAGES_ENDPOINT)
    image_ids = response.json()['image_ids']
    response = requests.get(f'{IMAGES_ENDPOINT}/{image_ids[0]}')
    logger.info(response.json())
    assert response.status_code == 200
    assert 'description' in response.json()
    assert isinstance(response.json()['description'], str)


def test_get_image_error():
    response = requests.get(f'{IMAGES_ENDPOINT}')
    image_ids = response.json()['image_ids']
    not_existing_image_id = max(image_ids) + 1
    response = requests.get(f'{IMAGES_ENDPOINT}/{not_existing_image_id}')
    assert response.status_code == 404


def test_unique_ids():
    returned_ids = set(requests.get(f'{IMAGES_ENDPOINT}').json()['image_ids'])
    for i in range(100):
        input_data = {"image_url": "https://jrnlst.ru/sites/default/files/covers/cover_6.jpg"}
        response = requests.post(IMAGES_ENDPOINT, json=input_data)
        assert response.status_code == 200
        idx = response.json()['image_id']
        assert idx not in returned_ids
        returned_ids.add(idx)
    time.sleep(30)
    response = requests.get(f'{IMAGES_ENDPOINT}')
    image_ids = response.json()['image_ids']
    assert set(image_ids) == returned_ids


def test_captions_generated_on_worker():
    for worker in WORKER_IDS:
        session = requests_unixsocket.Session()
        session.post('http+unix://%2Ftmp%2Fdocker.sock/containers/{}/pause'.format(worker))
    time.sleep(2)
    ids = set()
    for i in range(10):
        input_data = {"image_url": "https://jrnlst.ru/sites/default/files/covers/cover_6.jpg"}
        response = requests.post(IMAGES_ENDPOINT, json=input_data)
        assert response.status_code == 200
        idx = response.json()['image_id']
        ids.add(idx)
    response = requests.get(f'{IMAGES_ENDPOINT}')
    image_ids = set(response.json()['image_ids'])
    assert image_ids.isdisjoint(ids)
    for worker in WORKER_IDS:
        session = requests_unixsocket.Session()
        session.post('http+unix://%2Ftmp%2Fdocker.sock/containers/{}/unpause'.format(worker))
    time.sleep(2)
    response = requests.get(f'{IMAGES_ENDPOINT}')
    image_ids = set(response.json()['image_ids'])
    assert image_ids.issuperset(ids)


@pytest.mark.order("last")
def test_no_listdir():
    response = requests.get(f'{IMAGES_ENDPOINT}')
    image_ids = set(response.json()['image_ids'])
    for item in Path('/data').glob('*.txt'):
        item.unlink()
    response = requests.get(f'{IMAGES_ENDPOINT}')
    image_ids_new = set(response.json()['image_ids'])
    assert image_ids == image_ids_new


def test_fault_tolerance():
    session = requests_unixsocket.Session()
    session.post('http+unix://%2Ftmp%2Fdocker.sock/containers/{}/pause'.format(MQ_ID))
    time.sleep(2)
    ids = set()
    for i in range(20):
        input_data = {"image_url": "https://jrnlst.ru/sites/default/files/covers/cover_6.jpg"}
        response = requests.post(IMAGES_ENDPOINT, json=input_data)
        assert response.status_code == 200
        idx = response.json()['image_id']
        ids.add(idx)
    time.sleep(5)
    new_ids = set(requests.get(f'{IMAGES_ENDPOINT}').json()['image_ids'])
    assert new_ids.isdisjoint(ids)  # New images can't be processed if rabbitmq is down.
    session = requests_unixsocket.Session()
    session.post('http+unix://%2Ftmp%2Fdocker.sock/containers/{}/unpause'.format(MQ_ID))
    time.sleep(15)
    new_ids = set(requests.get(f'{IMAGES_ENDPOINT}').json()['image_ids'])
    assert new_ids.issuperset(ids)
