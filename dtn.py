import socket
import struct
import threading
import time
from tkinter import N
import util

neighbour_mcast = ("ff02::abcd:1",8080)
game_mcast = ("ff02::dcba:1",6666)


class Neighbours():
    def __init__(self,gw,ip,beacon_period = 1):
        self.gw = gw
        self.ip = ip
        self.beacon_period = beacon_period

        self.gateway_count = 0
        if self.gw:
            self.gateway_count = -1

        self.neighbours = {}
        self.gwOn = 0

        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', neighbour_mcast[1]))
        self.sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_LOOP, False)
        mreq = struct.pack("16s15s".encode('utf-8'), socket.inet_pton(socket.AF_INET6, neighbour_mcast[0]), (chr(0) * 16).encode('utf-8'))
        self.sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)
        
        t1 = threading.Thread(target=self.beacon_receiver)
        t2 = threading.Thread(target=self.beacon_sender)
        t1.daemon = True
        t2.daemon = True
        t1.start()
        t2.start()

        
    def beacon_sender(self):
        print("Beacon sender thread started!")
        s = bytes(self.ip, 'utf-8')
        while True:
            data = struct.pack("i",self.gwOn)
            data += struct.pack("i",self.gateway_count)
            data += struct.pack("I%ds" % (len(s),), len(s), s)
            self.sock.sendto(data, neighbour_mcast)
            self.check_neighbour_timeout()
            time.sleep(self.beacon_period)

    def beacon_receiver(self):
        print("Beacon receiver thread started!")
        while True:
            data, addr = self.sock.recvfrom(1024)

            gwon,c = struct.unpack("ii",data[:8])
            data = data[8:]
            (i,), data = struct.unpack("I", data[:4]), data[4:]
            neighbour_ip = data[:i].decode('utf-8')
            if not neighbour_ip in self.neighbours:
                self.neighbours[neighbour_ip] = {}
                if c != -1:
                    if gwon == 1:
                        gateway = 'gateway'
                    else:
                        gateway = 'gateways'
                    print(f"Neighbour at {neighbour_ip} connected with a score of {c} and connected to {gwon} {gateway}!")
                else:
                    self.gwOn += 1
                    print(f"Gateway router at {neighbour_ip} connected!")



            if c == -1 and not self.gw:
                self.gateway_count += 1

            self.neighbours[neighbour_ip]["gw_on"] = gwon
            self.neighbours[neighbour_ip]["gw_count"] = c
            self.neighbours[neighbour_ip]["time"] = time.time()


            
    def check_neighbour_timeout(self):
        to = []
        for addr in self.neighbours.keys():
            if time.time() - self.neighbours[addr]["time"] > self.beacon_period:
                if self.neighbours[addr]["gw_count"] != -1:
                    print(f"Neighbour at {addr} timed out!")
                else:
                    print(f"Gateway router at {addr} timed out!")
                    self.gwOn -= 1

                to.append(addr)
        for addr in to:
            del self.neighbours[addr]

    def best_neighbour_addr(self):
        best_addr = None
        fst = True
        if len(self.neighbours.keys()) < 1:
            return None
        for addr in self.neighbours.keys():
            if self.neighbours[addr]["gw_count"] == -1 or self.neighbours[addr]["gw_on"] > 0:
                return addr
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
    def __init__(self, nodeIP, gw = False, server_pair = None, main = False):
        self.server_pair = server_pair
        
        self.neighbour_in_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.neighbour_in_socket.bind((nodeIP,util.mobilePort))

        self.outSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        
        self.neighbours = Neighbours(gw,nodeIP)

        self.gw = gw
        if gw:
            self.server_in_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            self.server_in_socket.bind((nodeIP,util.gwServerPort))
            server_listener_thread = threading.Thread(target=self.server_listener)
            server_listener_thread.daemon = True
            server_listener_thread.start()
        
        if main:
            self.wait_message()
        else:
            neighbour_listener_thread = threading.Thread(target=self.wait_message)
            neighbour_listener_thread.daemon = True
            neighbour_listener_thread.start()
        


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
            print(f"Sending packet to server at {self.server_pair}")
            self.outSocket.sendto(data,self.server_pair)
        else:
            nextHop = self.neighbours.best_neighbour_addr()
            if nextHop:
                self.outSocket.sendto(data,(nextHop,util.mobilePort))
            else:
                print("Packet dropped")



if __name__ == "__main__":
    nodeIP,gw,serverIP = util.dtnParsing()
    if gw:
        f = Forwarder(nodeIP,gw,(serverIP,util.gamePort),main = True)
    else:
        f = Forwarder(nodeIP,main = True)