import os
import random
import time

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

import storage_pb2
import storage_pb2_grpc


SERVER_ADDR = os.getenv('SERVER_ADDR', 'localhost:51000')
VALUE_TO_PUT = int(os.getenv('VALUE_TO_PUT', '100'))


channel = grpc.insecure_channel(SERVER_ADDR)
stub = storage_pb2_grpc.StorageStub(channel)


while True:
    current = stub.GetValue(storage_pb2.GetRequest())
    payload = current.value.payload
    updated_at = current.value.updated_at.ToDatetime()

    if payload != VALUE_TO_PUT:
        print(f'Current value: {payload} (updated at {updated_at})')

    print(f'Putting {VALUE_TO_PUT}', flush=True)

    stub.PutValue(storage_pb2.PutRequest( 
        value=storage_pb2.Value(payload=VALUE_TO_PUT)
    ))

    delay = random.uniform(1.0, 2.0)
    time.sleep(delay)
