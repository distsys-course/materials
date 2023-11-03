import argparse
from flask import Flask, jsonify, request

app = Flask(__name__)
data = {}


@app.route('/put', methods=['POST'])
def put_handler():
    key = request.args.get('key')
    value = request.get_json().get('value')
    
    if key is None or value is None:
        return jsonify({'error': 'Please provide key and value.'}), 400
    
    data[key] = value
    return jsonify({'message': 'Key-value pair stored successfully.'}), 200


@app.route('/get', methods=['GET'])
def get_handler():
    key = request.args.get('key')
    
    if key is None:
        return jsonify({'error': 'Please provide key.'}), 400
    
    value = data.get(key)
    
    if value is None:
        return jsonify({'error': 'Key not found.', 'key': key}), 404
    
    return jsonify({'value': value}), 200


@app.route('/state', methods=['GET'])
def state_handler():
    table = '<table>'
    table += f'<tr><th colspan="2" style="font-size: 24px; font-weight: bold; font-family: monospace; padding-bottom: 10px;">Data on {app.name}</th></tr>'
    table += '<tr><th style="font-weight: bold; text-align: left; font-family: monospace; padding-bottom: 15px;">Key</th><th style="font-family: monospace; text-align: left; padding-bottom: 15px; padding-left: 20px;">Value</th></tr>'
    
    for key, value in data.items():
        value = value[:64] + f'...[total of {len(value)} bytes]' if len(value) > 100 else value
        table += f'<tr><td style="font-weight: bold; font-family: monospace;">{key}</td><td style="font-family: monospace; text-align: left; padding-left: 20px;">{value}</td></tr>'
    
    table += '</table>'
    return table


@app.route('/health', methods=['GET'])
def health_handler():
    return f'Hi from {app.name}'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Flask app with hostname as app name')
    parser.add_argument('-n', '--hostname', type=str, help='Hostname of the server')
    parser.add_argument('-p', '--port', type=int, help='Port of the server')
    args = parser.parse_args()
    
    if args.hostname:
        app.name = args.hostname

    
    app.run('0.0.0.0', args.port)