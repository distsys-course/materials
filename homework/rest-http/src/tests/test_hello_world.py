import os

import requests

SERVER_HOST = os.environ.get('HSE_HTTP_TESTS_SERVER_HOST', 'server')
SERVER_PORT = int(os.environ.get('HSE_HTTP_FLASK_PORT', 80))
URL = 'http://' + SERVER_HOST
if SERVER_PORT != 80:
    URL += ':{}'.format(SERVER_PORT)


def test_hello_world():
    response = requests.get(URL + '/')
    assert response.text == 'Hello, World!'
    assert response.status_code == 200
