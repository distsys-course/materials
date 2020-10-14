import pika
import click
import sys
import os
import time

def callback(ch, method, properties, body):
    command = body.decode().split()
    print(f"[worker] Received command `{command}` from channel {method.routing_key}, method {type(method)}")
    print(f"[worker] Executing command")
    if command[0] == "print":
        print("[worker] print:", *command[1:])
    elif command[0] == "sleep":
        print(f"[worker] sleep {command[1]}")
        time.sleep(int(command[1]))
        print(f"[worker] sleep done")

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

    print("[worker] Waiting for messages.")

    channel.start_consuming()


if __name__ == "__main__":
    print("started simple worker")
    
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
