#!/usr/bin/env python
import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.exchange_declare(exchange='logs', exchange_type='fanout') 
channel.exchange_declare(exchange='logs1', exchange_type='fanout') 

result = channel.queue_declare(queue='', exclusive=True)  # random name + exclusive - delete queue while connection is closed
queue_name = result.method.queue
print(queue_name)

channel.queue_bind(exchange='logs', queue=queue_name)
channel.queue_bind(exchange='logs1', queue=queue_name)

print(' [*] Waiting for logs. To exit press CTRL+C')

def callback(ch, method, properties, body):
    print(" [x] %r" % body)

channel.basic_consume(
    queue=queue_name, on_message_callback=callback, auto_ack=True)

channel.start_consuming()
