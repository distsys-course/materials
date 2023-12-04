FROM golang:1.20-alpine

WORKDIR /pracrice-security/kv
COPY go.* .

RUN go mod download -x

COPY * .

RUN go build .

ENTRYPOINT ["./kv"]

