#!/usr/bin/env bash

docker build . -t jupyter/datascience-notebook-rust

docker run -p 8888:8888 -v `pwd`:/home/jovyan/load-balancing-lab jupyter/datascience-notebook-rust
