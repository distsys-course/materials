FROM python:3.9-alpine

RUN apk add --no-cache gcc libressl-dev musl-dev libffi-dev && \
    pip install --no-cache-dir cryptography==38.0.4 && \
    apk del libressl-dev musl-dev libffi-dev

WORKDIR /practice-security/tests

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY *.py .

ENTRYPOINT pytest -vs --log-level=INFO
