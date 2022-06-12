import socket
import sys

inSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
inSocket.bind((sys.argv[1],int(sys.argv[2])))
fst = True
last = 0
lost = 0
while True:
    data,addr = inSocket.recvfrom(1024)
    data = int(data.decode('utf-8'))
    if fst:
        fst = False
        last = data
    else:
        if data-last > 1:
            print("Packet Lost!")
            lost += data-last
        last = data
    print(data, f" loss {round(100*lost/data,2)}%")