import pika
import time


if __name__ == '__main__':
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', port=5672))
    channel = connection.channel()

    channel.exchange_declare(exchange='topic_logs', exchange_type='topic')

    time.sleep(2)
    channel.basic_publish(exchange='topic_logs', routing_key='kernel.critical', body='critical error')
    channel.basic_publish(exchange='topic_logs', routing_key='monitoring.warning', body='warning')
    channel.basic_publish(exchange='topic_logs', routing_key='production.kernel.critical', body='another critical error')
    connection.close()
