import sys
import time
import socket

sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

i=0
while True:
    sock.sendto(f"{i}".encode('utf-8'),(sys.argv[1],int(sys.argv[2])))
    print(f"Sent {i}")
    i+=1
    time.sleep(1)
