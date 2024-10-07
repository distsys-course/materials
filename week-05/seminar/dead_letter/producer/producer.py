import pika
import sys

connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', port=5672))
channel = connection.channel()

channel.queue_declare(queue='unprocessed_logs')
channel.queue_declare(queue='logs', arguments={
    'x-max-priority': 5,
    'x-dead-letter-exchange' : '',
    'x-dead-letter-routing-key' : 'unprocessed_logs'})

channel.basic_publish(exchange='', routing_key='logs', body='warning', properties=pika.BasicProperties(priority=1))
channel.basic_publish(exchange='', routing_key='logs', body='error', properties=pika.BasicProperties(priority=5))
channel.basic_publish(exchange='', routing_key='logs', body='info', properties=pika.BasicProperties(priority=1))
connection.close()
