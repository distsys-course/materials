import socket
import struct


if __name__ == '__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', 10000))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, struct.pack('4sL', socket.inet_aton('224.0.2.0'), socket.INADDR_ANY))
    while True:
        data, addr = sock.recvfrom(1024)
        if not data:
            break
        print(f'got message "{data}" from {addr}')
