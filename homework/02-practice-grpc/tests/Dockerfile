FROM python:3.8-alpine

COPY tests/requirements.txt .
RUN pip install -r requirements.txt

RUN apk add curl
RUN curl -sSL "https://github.com/fullstorydev/grpcurl/releases/download/v1.8.7/grpcurl_1.8.7_linux_x86_64.tar.gz" | tar -xz -C /usr/local/bin

COPY messenger/proto/messenger.proto messenger/proto/messenger.proto
COPY tests/*.py tests/

ENTRYPOINT ["pytest", "-vs", "tests/"]
