FROM golang:1.20-alpine

WORKDIR /pracrice-security/auth
COPY go.* .

RUN go mod download -x

COPY * .

RUN go build .

ENTRYPOINT ["./auth"]

