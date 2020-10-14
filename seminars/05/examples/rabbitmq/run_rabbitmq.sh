#!/usr/bin/env bash

docker run --rm \
    --hostname rabbitmq \
    --name distsys-rabbitmq \
    --network host \
    rabbitmq:3;
