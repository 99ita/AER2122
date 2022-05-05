import socket
import struct
import threading
import time

beacon_period = 1 #s
gateway_routers = []


class Beacon():

    def __init__(self):
        self.gateway_count = 18313

        self.neighbours = {}

        self.ip = "2001:55:66:77"
        self.port = 5555

        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', 8080))
        self.sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_LOOP, True)
        mreq = struct.pack("16s15s".encode('utf-8'), socket.inet_pton(socket.AF_INET6, "ff02::abcd:1"), (chr(0) * 16).encode('utf-8'))
        self.sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)
        t1 = threading.Thread(target=self.beacon_receiver)
        t2 = threading.Thread(target=self.beacon_sender)
        t1.daemon = True
        t2.daemon = True
        print("Starting beacon receiver and sender threads!")
        t1.start()
        t2.start()
        return
        

        
    def beacon_sender(self):
        while True:
            data = struct.pack("i",self.gateway_count)
            self.sock.sendto(data, ("ff02::abcd:1", 8080))
            time.sleep(2)

    def beacon_receiver(self):
        while True:
            data, addr = self.sock.recvfrom(1024)

            if addr[0] in gateway_routers:
                self.gateway_count += 1

            if not addr[0] in self.neighbours:
                self.neighbours[addr[0]] = {}
                print(f"Neighbour at {addr[0]} connected!")

            c = struct.unpack("i",data)
            
            self.neighbours[addr[0]]["gw_count"] = c
            self.neighbours[addr[0]]["time"] = time.time()

            self.check_neighbour_timeout()

            print(data)
            print(addr)
            print(self.neighbours)
            
    def check_neighbour_timeout(self):
        for addr in self.neighbours.keys():
            if time.time() - self.neighbours[addr]["time"] > 1:
                print(f"Neighbour at {addr} timed out!")
                del self.neighbours[addr]

    def best_neighbour_addr(self):
        best_addr = None
        fst = True
        for addr in self.neighbours.keys():
            if fst:
                best = self.neighbours[addr]["gw_count"]
                best_addr = addr
                fst = False
            else:   
                if self.neighbours[addr]["gw_count"] > best:
                    best = self.neighbours[addr]["gw_count"]
                    best_addr = addr
        return best_addr
                    
class Forwarder():
    def send_packet(self):
        return


Beacon()
time.sleep(5)