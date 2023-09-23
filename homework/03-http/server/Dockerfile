FROM python:3.11.5-slim-bullseye

WORKDIR /http/server

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

ENTRYPOINT ["python", "server.py"]
