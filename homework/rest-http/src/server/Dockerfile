FROM python:3.8

RUN mkdir /app/
WORKDIR /app/
COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .
EXPOSE 80
CMD ["python", "server.py"]