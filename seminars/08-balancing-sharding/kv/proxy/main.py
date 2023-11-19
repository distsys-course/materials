import argparse
import requests
from strategies import (
    Proxy, ShardingProxy, 
    ReplicatingProxy, ReplicatingQuorumProxy,
    RAID3Proxy
)
import yaml
from flask import Flask, jsonify, request

app = Flask(__name__)

proxy: Proxy = None


@app.route('/put', methods=['POST'])
def put_handler():
    key = request.args.get('key')
    value = request.get_json().get('value')

    if key is None or value is None:
        return jsonify({'error': 'Please provide key and value.'}), 400

    return proxy.put(key, value)

@app.route('/get', methods=['GET'])
def get_handler():
    key = request.args.get('key')

    if key is None:
        return jsonify({'error': 'Please provide key.'}), 400

    return proxy.get(key)


@app.route('/state', methods=['GET'])
def state_handler():
    results = ""
    for _, node in proxy.nodes.items():
        url = f'{node["url"]}/state'
        response = requests.get(url)
        results += f'<h1 style="font-family: monospace;">Response from {url}</h1>{response.content.decode("utf-8")}<hr>'

    return f"<html><body>{results}</body></html>", 200


def load_proxy_from_config(config_path):
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)

    mode = config.get('mode', '')
    nodes = {}
    for node in config['nodes']:
        name = node['name']
        url = node['url']
        nodes[name] = {'url': url}
    if mode == 'sharding':
        return ShardingProxy(nodes)
    elif mode == 'replication':
        return ReplicatingProxy(nodes)
    elif mode == 'replication-quorum':
        return ReplicatingQuorumProxy(nodes)
    elif mode == 'replication-raid3':
        return RAID3Proxy(nodes)
    raise ValueError('Invalid mode, allowed values: sharding, replication, replication-quorum')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Flask app acting as a proxy for key-value nodes')
    parser.add_argument('-c', '--config', type=str, required=True, help='Path to the YAML config file')
    parser.add_argument('-p', '--port', type=int, help='Port of the server')
    args = parser.parse_args()

    proxy = load_proxy_from_config(args.config)

    app.run('0.0.0.0', args.port)