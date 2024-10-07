#!/usr/bin/env python
import pika
import sys
import time


if __name__ == '__main__':
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', port=5672))
    channel = connection.channel()

    channel.queue_declare(queue='task_queue', durable=True)
    channel.confirm_delivery()

    for message in ['first message.', 'second message..', 'third message...']:
        while True:
            try:
                channel.basic_publish(
                    exchange='',
                    routing_key='task_queue',
                    body=message,
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # make message persistent. Marking messages as persistent doesn't fully guarantee that a message won't be lost. Although it tells RabbitMQ to save the message to disk, there is still a short time window when RabbitMQ has accepted a message and hasn't saved it yet. Also, RabbitMQ doesn't do fsync(2) for every message
                ))
            except Exception as e:
                print("retransmit")
                time.sleep(1)
            else:
                break
        print(" [x] Sent %r" % message)
    connection.close()
