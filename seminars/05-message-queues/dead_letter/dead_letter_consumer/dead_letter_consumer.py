import pika
import time

connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', port=5672))
channel = connection.channel()


def callback(ch, method, properties, body):
    print('got new unprocessed message (body = "{}")'.format(body))
    ch.basic_ack(delivery_tag=method.delivery_tag)


time.sleep(1)
channel.basic_consume(queue='unprocessed_logs', on_message_callback=callback)
channel.start_consuming()
