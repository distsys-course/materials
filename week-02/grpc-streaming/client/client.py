import grpc
import os
import time

import queue_pb2
import queue_pb2_grpc


def request_generator():
    for i in range(5):
        yield queue_pb2.PushRequest(value=queue_pb2.Value(payload=i))


if __name__ == '__main__':
    server_addr = os.getenv('SERVER_ADDR', 'localhost:51000')
    with grpc.insecure_channel(server_addr) as channel:
        stub = queue_pb2_grpc.QueueStub(channel)
        stub.Push(queue_pb2.PushRequest(value=queue_pb2.Value(payload=100)))
        response = stub.Pop(queue_pb2.PopRequest())
        print(f'Pop returned payload={response.value.payload}, updated_at={response.value.updated_at.ToDatetime()}')
        time.sleep(1)
        stub.PushMany(request_generator())
        for response in stub.Drain(queue_pb2.DrainRequest()):
            print(f'Drain returned payload={response.value.payload}, updated_at={response.value.updated_at.ToDatetime()}')
