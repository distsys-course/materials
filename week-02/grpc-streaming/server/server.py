import grpc
import os
import queue_pb2
import queue_pb2_grpc

from collections import deque
from concurrent import futures
from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp
from threading import Lock


class Queue:
    data = deque()
    lock = Lock()

    @classmethod
    def push(cls, value):
        with cls.lock:
            cls.data.append(value)

    @classmethod
    def pop(cls):
        with cls.lock:
            if len(cls.data) > 0:
                return cls.data.popleft()
            else:
                return None

    @classmethod
    def drain(cls):
        with cls.lock:
            data = list(cls.data)
            cls.data = deque()
            return data


class QueueService(queue_pb2_grpc.QueueServicer):
    def Push(self, request, context):
        request.value.updated_at.GetCurrentTime()
        Queue.push(request.value)
        return queue_pb2.PushResponse()

    def PushMany(self, request_iterator, context):
        for request in request_iterator:
            request.value.updated_at.GetCurrentTime()
            Queue.push(request.value)
        return queue_pb2.PushResponse()

    def Pop(self, request, context):
        return queue_pb2.PopResponse(value=Queue.pop())

    def Drain(self, request, context):
        for item in Queue.drain():
            yield queue_pb2.PopResponse(value=item)


if __name__ == '__main__':
    server_addr = os.getenv('SERVER_ADDR', 'localhost:51000')
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    queue_pb2_grpc.add_QueueServicer_to_server(QueueService(), server)
    server.add_insecure_port(server_addr)
    server.start()
    server.wait_for_termination(timeout=None)
