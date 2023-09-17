FROM golang:1.16-buster

WORKDIR /practice-grpc/solutions
RUN mkdir client proto server
COPY client/go.* client/
COPY proto/go.* proto/
COPY server/go.* server/

RUN for d in  client proto server; do (cd $d && go mod tidy && go mod download -x); done || exit 1

COPY client client
COPY proto proto
COPY server server
RUN for d in client proto server; do (cd $d && go build .); done || exit 1

CMD ./client/client
