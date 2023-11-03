FROM jupyter/datascience-notebook

ENV JUPYTER_USER=jovyan

USER root
# Update default packages
RUN apt-get update

# Get Ubuntu packages
RUN apt-get install -y \
    build-essential \
    curl

# Update new packages
RUN apt-get update

USER ${JUPYTER_USER}

# Get Rust
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y

ENV PATH="/home/${JUPYTER_USER}/.cargo/bin:${PATH}"
