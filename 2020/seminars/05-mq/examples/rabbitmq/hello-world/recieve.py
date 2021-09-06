import pika
import click
import sys
import os

def callback(ch, method, properties, body):
    print(f"[reciever] Received {body.decode()} from channel {ch}, method {method}")

@click.command()
@click.option(
    "--host",
    default="localhost",
    type=str
)
@click.option(
    "-q", "--queue",
    default="default",
    type=str
)
def main(host: str, queue: str):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
    channel = connection.channel()

    channel.queue_declare(queue=queue)

    channel.basic_consume(
        queue=queue, 
        on_message_callback=callback, 
        auto_ack=True
    )

    print("[producer] Waiting for messages.")

    channel.start_consuming()


if __name__ == "__main__":
    print("started simple reciever")
    
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
