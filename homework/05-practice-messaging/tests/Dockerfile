FROM python:3.8

RUN mkdir /app/
WORKDIR /app/
COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .
ENTRYPOINT ["bash", "-c", "while ! curl -s web:5000 > /dev/null; do echo waiting for server; sleep 3; done; pytest -vs"]
