from flask import Flask, render_template

import os
import random
import requests

app = Flask(__name__)

APP_VERSION = os.getenv('APP_VERSION')
BIND_HOST = os.getenv('BIND_HOST') or '0.0.0.0'
BIND_PORT = os.getenv('BIND_PORT') or '8000'

FAILURE_PROBABILITY = float(os.getenv('FAILURE_PROBABILITY') or '0.0')


@app.route('/')
def home():
    if random.random() <= FAILURE_PROBABILITY:
        return f'[{APP_VERSION}] You are unlucky :( Server failed [x]', 500

    return f'Hello from app {APP_VERSION}'


@app.route('/kittens')
def kittens():
    # Get a URL to a random kitten photo.
    response = requests.get('https://api.thecatapi.com/v1/images/search?api_')

    try:
        # Response structure is as follows:
        # [{"id":"bL3lrUi1A","url":"ex.com/bL3lrUi1A.jpg","width":1280,"height":720}]
        data = response.json()
        kitten_url = data[0]['url']

        return render_template('index.html', kitten_url=kitten_url)
    except Exception as e:
        return f'Failed to fetch a kitten image :(\n {e}'


if __name__ == '__main__':
    app.run(host=BIND_HOST, port=BIND_PORT)
