import socket
import struct
import threading
import time
from tkinter import N
import util

neighbour_mcast = ("ff02::abcd:1",8080)
game_mcast = ("ff02::dcba:1",6666)


class Neighbours():
    def __init__(self,gw,beacon_period = 1):
        self.gw = gw
        self.beacon_period = beacon_period

        self.gateway_count = 0
        if self.gw:
            self.gateway_count = -1

        self.neighbours = {}

        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', 8080))
        self.sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_LOOP, False)
        mreq = struct.pack("16s15s".encode('utf-8'), socket.inet_pton(socket.AF_INET6, neighbour_mcast[0]), (chr(0) * 16).encode('utf-8'))
        self.sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)
        
        self.lock = threading.Lock()
        t1 = threading.Thread(target=self.beacon_receiver)
        t2 = threading.Thread(target=self.beacon_sender)
        t1.daemon = True
        t2.daemon = True
        t1.start()
        t2.start()

        
    def beacon_sender(self):
        print("Beacon sender thread started!")
        while True:
            data = struct.pack("i",self.gateway_count)
            self.sock.sendto(data, neighbour_mcast)
            self.check_neighbour_timeout()
            time.sleep(self.beacon_period)

    def beacon_receiver(self):
        print("Beacon sender thread started!")
        while True:
            data, addr = self.sock.recvfrom(1024)

            self.lock.acquire()
            if not addr[0] in self.neighbours:
                self.neighbours[addr[0]] = {}
                print(f"Neighbour at {addr[0]} connected!")

            c = struct.unpack("i",data)
            if c == -1 and not self.gw:
                self.gateway_count += 1

            self.neighbours[addr[0]]["gw_count"] = c
            self.neighbours[addr[0]]["time"] = time.time()

            print(data)
            print(addr)
            print(self.neighbours)

            self.lock.release()
            
    def check_neighbour_timeout(self):
        to = []
        for addr in self.neighbours.keys():
            if time.time() - self.neighbours[addr]["time"] > self.beacon_period:
                print(f"Neighbour at {addr} timed out!")
                to.append(addr)
        for addr in to:
            del self.neighbours[addr]

    def best_neighbour_addr(self):
        self.lock.acquire()
        best_addr = None
        fst = True
        for addr in self.neighbours.keys():
            if self.neighbours[addr]["gw_count"] == -1:
                return addr
            if fst:
                best = self.neighbours[addr]["gw_count"]
                best_addr = addr
                fst = False
            else:   
                if self.neighbours[addr]["gw_count"] > best:
                    best = self.neighbours[addr]["gw_count"]
                    best_addr = addr
        if self.gateway_count >= best_addr:
            return None
        self.lock.release()
        return best_addr
                    
class Forwarder():
    def __init__(self, dtn_pair, gw = False, server_pair = None, server_listen_port = 0):
        self.dtn_port = dtn_pair[1]
        self.server_pair = server_pair
        self.server_listen_port = server_listen_port
        
        self.neighbour_in_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.neighbour_in_socket.bind(dtn_pair)

        self.outSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

        self.neighbours = Neighbours(gw)
        self.gw = gw
        if gw:
            self.server_in_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            self.server_in_socket.bind((dtn_pair[0],server_listen_port))
            server_listen_thread = threading.Thread(target = self.server_listener)
            server_listen_thread.daemon = True
            server_listen_thread.start()
        
        neighbour_listen_thread = threading.Thread(target = self.wait_message)
        neighbour_listen_thread.daemon = True
        neighbour_listen_thread.start()


    def wait_message(self):
        while True:
            try:
                data,addr = self.neighbour_in_socket.recvfrom(1024)
            except:
                self.neighbour_in_socket.close()
                self.outSocket.close()
                exit()

            print(f"Packet received from {addr[0]}")
            self.send_packet(data)



    def server_listener(self):
        print("Server listener thread started!")
        mcast_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        mcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        mcast_socket.bind(('', 8080))
        mcast_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_LOOP, False)
        mreq = struct.pack("16s15s".encode('utf-8'), socket.inet_pton(socket.AF_INET6, game_mcast[0]), (chr(0) * 16).encode('utf-8'))
        mcast_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)
        
        while True:
            try:
                data,addr = self.server_in_socket.recvfrom(1024)
            except:
                self.server_in_socket.close()
                exit()

            mcast_socket.sendto(data,game_mcast)

            print(f"Packet received from server and forwarded to multicast group!")

    
    def send_packet(self, data):
        if self.gw:
            print(f"Sending packet to server")
            self.outSocket.sendto(data,self.server_pair)
        else:
            nextHop = self.neighbours.best_neighbour_addr()
            if nextHop:
                self.outSocket.sendto(data,(nextHop,self.dtn_port))
            else:
                print("Packet dropped")



if __name__ == "__main__":
    dtn_pair,gw,server_pair,server_listen_port = util.dtnParsing()
    if gw:
        f = Forwarder(dtn_pair,gw,server_pair,server_listen_port)
    else:
        f = Forwarder(dtn_pair)