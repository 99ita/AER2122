import socket
import sys

inSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
inSocket.bind(sys.argv[1],int(sys.argv[2]))

while True:
    data,addr = inSocket.recvfrom(1024)
    print(data)
    print(addr)