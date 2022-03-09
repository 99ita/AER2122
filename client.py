import socket

UDP_IP = "::1"  # localhost
UDP_PORT = 5555
MESSAGE = "Hello, World!"

sock = socket.socket(socket.AF_INET6, # Internet
					socket.SOCK_DGRAM) # UDP
sock.sendto(MESSAGE.encode("utf-8"), (UDP_IP, UDP_PORT))