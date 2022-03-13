import socket

UDP_IP = "::1"  # localhost
UDP_PORT = 5554
MESSAGE = "Hello, World!"
 
inSock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
inSock.bind((UDP_IP, UDP_PORT))

print("Listening...")

while True:
	try: 
		data,addr = inSock.recvfrom(1024)
	except:
		exit()
	print(data.decode("utf-8")) 