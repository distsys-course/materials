import pika
import time

connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', port=5672))
channel = connection.channel()


def callback(ch, method, properties, body):
    if body.startswith(b'warning'):
        print('got new warning (body = "{}")'.format(body))
        ch.basic_ack(delivery_tag=method.delivery_tag)
    elif body.startswith(b'error'):
        print('got new error (body = "{}")'.format(body))
        ch.basic_ack(delivery_tag=method.delivery_tag)
    else:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


time.sleep(1)
channel.basic_consume(queue='logs', on_message_callback=callback)
channel.start_consuming()
