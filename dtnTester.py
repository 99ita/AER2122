import dtn
import sys
import time

fwd = dtn.Forwarder(sys.argv[1])

message = "message"
i = 0   
while True:
    message = "message"
    message += f'{i}'
    #print(f"sending: '{message}'")
    fwd.send_packet(bytes(message,'utf-8'),fst = True, server_pair = (sys.argv[2],int(sys.argv[3])))
    time.sleep(1)
    i+=1