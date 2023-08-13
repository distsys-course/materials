import pika
import sys

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

# direct, topic, headers and fanout
channel.exchange_declare(exchange='logs', exchange_type='fanout')  # it just broadcasts all the messages it receives to all the queues it knows
channel.exchange_declare(exchange='logs1', exchange_type='fanout')

message = ' '.join(sys.argv[1:]) or "info: Hello World!"
channel.basic_publish(exchange='logs', routing_key='', body=message)  # The exchange parameter is the name of the exchange. The empty string denotes the default or nameless exchange: messages are routed to the queue with the name specified by routing_key, if it exists.
channel.basic_publish(exchange='logs1', routing_key='', body=message)  # The exchange parameter is the name of the exchange. The empty string denotes the default or nameless exchange: messages are routed to the queue with the name specified by routing_key, if it exists.
print(" [x] Sent %r" % message)
connection.close()
