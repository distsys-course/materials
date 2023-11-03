from flask import Flask
import sys

app = Flask(__name__)

if len(sys.argv) < 3:
    print('please call with arguments <port> <hostname>')
    exit()

@app.route('/')
def index():
    return f'Hello from {app.name}\n'

app.name = sys.argv[2]
app.run(host='0.0.0.0', port=int(sys.argv[1]))