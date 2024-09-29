import socket
import struct


if __name__ == '__main__':
    in_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    in_socket.bind(('', 9999))
    out_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    out_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))
    while True:
        data, addr = in_socket.recvfrom(1024)
        if not data:
            break
        out_socket.sendto(data, ('224.0.2.0', 10000))
