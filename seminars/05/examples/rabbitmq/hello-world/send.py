import pika
import click

def _do_send(host, queue, message):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host))
    channel = connection.channel()

    channel.queue_declare(queue=queue)

    channel.basic_publish(exchange="", routing_key=queue, body=message)
    print(f"[sender] Sent {message} to queue {queue} on host {host}")
    connection.close()

def run_send(host, queue, message):
    if message:
        _do_send(host, queue, message)
    else:
        while True:
            message = input("enter message >>> ")
            _do_send(host, queue, message)


@click.command()
@click.option(
    '--host', 
    default='localhost',
    type=str
)
@click.option(
    '--queue',
    default='default',
    type=str
)
@click.option(
    '--message',
    type=str,
    default=None
)
def main(host, queue, message):
    try:
        run_send(host, queue, message)
    except KeyboardInterrupt:
        print("[sender] Ok, exiting")
        exit(0)
        
if __name__ == "__main__":
    main()


