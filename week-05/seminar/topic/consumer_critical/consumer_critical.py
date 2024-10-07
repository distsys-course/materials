import os
import pika


if __name__ == '__main__':
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', port=5672))
    channel = connection.channel()

    channel.exchange_declare(exchange='topic_logs', exchange_type='topic')

    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue

    channel.queue_bind(exchange='topic_logs', queue=queue_name, routing_key='*.critical')

    print(' [*] Waiting for logs.')

    def callback(ch, method, properties, body):
        print(f" [x] {method.routing_key}:{body.decode()}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue=queue_name, on_message_callback=callback)

    channel.start_consuming()
