FROM python:3.9-slim

RUN pip install Flask==2.3.3

WORKDIR /app
COPY . .

ENTRYPOINT ["python3", "main.py"]