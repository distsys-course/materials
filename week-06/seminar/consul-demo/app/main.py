import os
from flask import Flask
from consul import Consul, Check

app = Flask(__name__)

consul_host = os.environ.get('CONSUL_HOST', 'localhost')
consul_port = os.environ.get('CONSUL_PORT', 8500)
my_host = os.environ.get('MY_HOST', 'localhost')
my_port = os.environ.get('MY_PORT', 5000)

# Initialize Consul client
consul = Consul(host=consul_host, port=consul_port)

# Register the Flask app in Consul
service_name = 'flask-hello-world'
consul.agent.service.register(
    name=service_name,
    service_id=f'{service_name}-{my_host}',
    port=my_port,
    check=Check.http(f'http://{my_host}:{my_port}/health', interval='10s', deregister='30s')
)

@app.route('/')
def hello():
    return 'Hello, World!'

@app.route('/health')
def health():
    return 'OK'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=my_port)