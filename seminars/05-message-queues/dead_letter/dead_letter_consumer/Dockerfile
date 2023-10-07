FROM python:3.8

RUN mkdir /root/app/
WORKDIR /root/app/

RUN pip install pika

COPY . .

ENV PYTHONPATH "${PYTHONPATH}:/root/app/"
EXPOSE 5000

CMD ["bash", "-c", "while ! curl -s rabbitmq:15672 > /dev/null; do echo waiting for rabbitmq; sleep 3; done; python -u dead_letter_consumer.py"]
