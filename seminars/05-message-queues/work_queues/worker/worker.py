#!/usr/bin/env python
import pika
import time


if __name__ == '__main__':
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', port=5672))
    channel = connection.channel()

    channel.queue_declare(queue='task_queue', durable=True)  # to make sure that the queue will survive a RabbitMQ node restart
    print(' [*] Waiting for messages.')


    def callback(ch, method, properties, body):
        print(" [x] Received %r" % body.decode())
        time.sleep(body.count(b'.'))
        print(" [x] Done")
        ch.basic_ack(delivery_tag=method.delivery_tag)  # Send ack


    channel.basic_qos(prefetch_count=1)  # This uses the basic.qos protocol method to tell RabbitMQ not to give more than one message to a worker at a time
    channel.basic_consume(queue='task_queue', on_message_callback=callback)

    channel.start_consuming()
