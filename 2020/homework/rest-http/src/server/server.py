import os

from flask import Flask

app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'Hello, World!'


app.run(host='0.0.0.0', port=int(os.environ.get('HSE_HTTP_FLASK_PORT', 80)))
