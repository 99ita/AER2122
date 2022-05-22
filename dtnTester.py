from re import S
import dtn
import sys
import time
import socket

fwd = dtn.Forwarder(sys.argv[1])

message = "message"
i = 0   
while True:
    message += f'{i}'
    print(f"sending: '{message}'")
    fwd.send_packet(message)
    time.sleep(1)
    i+=1