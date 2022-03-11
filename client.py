import socket

UDP_IP = "::1"  # localhost
UDP_PORT = 5554
MESSAGE = "Hello, World!"
 
inSock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
inSock.bind((UDP_IP, UDP_PORT))

print("Listening...")

while True:
	try: 
		string = inSock.recvfrom(1024)
	except:
		exit()
	print(string.decode("utf-8")) 