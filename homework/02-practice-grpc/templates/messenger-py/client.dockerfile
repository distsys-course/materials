FROM python:3.8-slim

WORKDIR /practice-grpc/messenger/
COPY client/requirements.txt .
RUN pip install -r requirements.txt

RUN mkdir messenger
COPY __init__.py messenger/__init__.py
COPY client/ messenger/client-py/
COPY proto messenger/proto/

ENTRYPOINT ["python", "-m", "messenger.client.client"]
