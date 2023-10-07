FROM python:3.8

RUN mkdir /root/app/
WORKDIR /root/app/

COPY requirements.txt .
RUN pip install -r requirements.txt && rm -rf /root/.cache/pip

COPY . .

ENV PYTHONPATH "${PYTHONPATH}:/root/app/"
EXPOSE 5000

CMD ["bash", "-c", "rm -f /data/*.txt && while ! curl -s rabbitmq:15672 > /dev/null; do echo waiting for rabbitmq; sleep 3; done; python -u worker.py"]
