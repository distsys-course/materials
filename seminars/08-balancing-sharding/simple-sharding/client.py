import requests

# put your shards for experiments here
shards = {
        'server1': 'http://localhost:8001/',
        'server2': 'http://localhost:8002/'
}

keys = [
    'aasdjkahsdl',
    'clkjhlkajhsd',
    'basdjahlkj',
    'dakjshd',
]

MAX_HASH = 1000000

def hashf(x: str):
    # sum of ascii codes
    return sum([ord(c) for c in x]) % MAX_HASH

def get_shard(k, shards):
    i = hashf(k) % len(shards)
    return list(shards)[i]


def call_by_key(key):
    shard = get_shard(key, shards.keys())
    resp = requests.get(shards[shard])
    return resp.text


if __name__=='__main__':
    for k in keys:
        print(call_by_key(k))