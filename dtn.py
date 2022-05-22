import socket
import struct
import threading
import time
import util

neighbour_mcast = ("ff02::abcd:1",8080)
game_mcast = ("ff02::dcba:1",8182)
beacon_period = 0.5


class Neighbours():
    def __init__(self,gw,ip,beacon_period = beacon_period):
        self.fstTime = time.time()
        self.gw = gw
        self.ip = ip
        self.beacon_period = beacon_period

        self.gateway_count = 0
        if self.gw:
            self.gateway_count = -1
        
        self.gwon_count = 0

        self.score = self.gateway_count

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
            if not self.gw:
                self.score = (self.gateway_count*10 + self.gwon_count)/(time.time()-self.fstTime)
            data = struct.pack("i",self.gwOn)
            data += struct.pack("i",self.score)
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
                    if gwon >= 1:
                        self.gwon_count += 1
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
            self.neighbours[neighbour_ip]["score"] = c
            self.neighbours[neighbour_ip]["time"] = time.time()


            
    def check_neighbour_timeout(self):
        to = []
        for addr in self.neighbours.keys():
            if time.time() - self.neighbours[addr]["time"] >= 2*self.beacon_period:
                if self.neighbours[addr]["score"] != -1:
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
            if fst:
                best_addr = addr
                fst = False
                pass
            if self.neighbours[addr]["score"] == -1:
                return addr
            elif self.neighbours[addr]["gw_on"] > 0:
                if self.neighbours[best_addr]["gw_on"] < 1:
                    best_addr = addr
                else:
                    if self.neighbours[addr]["score"] > self.neighbours[best_addr]["score"]:
                        best_addr = addr
            elif self.neighbours[addr]["score"] > self.neighbours[best_addr]["score"]:
                best_addr = addr
        
        if best_addr != None:
            if self.gwOn > 0 and self.neighbours[best_addr]["gw_on"] < 1:
                return None
            if self.neighbours[best_addr]["gw_on"] > 0 and self.gwOn > 0:
                if self.gateway_count >= self.neighbours[best_addr]["score"]:
                    return None
            if self.neighbours[best_addr]["gw_on"] == 0 and self.gwOn == 0:
                if self.gateway_count >= self.neighbours[best_addr]["score"]:
                    return None
            
        return best_addr

class Forwarder():
    def __init__(self, nodeIP, gw = False, listeningIP = None, main = False):
        self.nodeIP = nodeIP
        
        self.neighbour_in_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.neighbour_in_socket.bind((nodeIP,util.mobilePort))

        self.outSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        
        self.neighbours = Neighbours(gw,nodeIP)

        self.main = main

        self.gw = gw

        if gw:
            self.wireless_clients = {}
            server_listener_thread = threading.Thread(target=self.server_listener)
            server_listener_thread.daemon = True
            server_listener_thread.start()

        if self.main:
            self.wait_message()
        else:
            neighbour_listener_thread = threading.Thread(target=self.wait_message)
            neighbour_listener_thread.daemon = True
            neighbour_listener_thread.start()
        


    def wait_message(self):
        serverPair = None
        while True:
            try:
                data,addr = self.neighbour_in_socket.recvfrom(1024)
            except:
                self.neighbour_in_socket.close()
                self.outSocket.close()
                exit()

            if self.gw:
                sizeC, = struct.unpack("I", data[:4])

                clientIp = data[4:sizeC+4].decode('utf-8')
                
                sizeS, = struct.unpack("I", data[sizeC+4:sizeC+8])
        
                serverIp = data[sizeC+8:sizeC+sizeS+8].decode('utf-8')
                serverPort, = struct.unpack("I", data[sizeC+sizeS+8:sizeC+sizeS+12])
                data = data[sizeC+sizeS+12:]

                serverPair = (serverIp,serverPort)

                self.wireless_clients.setdefault(serverPair[0],[])
                    
                if clientIp not in self.wireless_clients[serverPair[0]]:
                    self.wireless_clients[serverPair[0]].append(clientIp)

            print(f"Packet received from {addr[0]}")
            self.send_packet(data, server_pair=serverPair)



    def server_listener(self):
        print("Server listener thread started!")

        server_in_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        server_in_socket.bind((listeningIP,util.gamePort))
        socketToWan = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        
        
        while True:
            try:
                data,adr = server_in_socket.recvfrom(1024)
            except:
                print("Server listener died!")
                server_in_socket.close()
                exit()

            for addr in self.wireless_clients[adr[0]]:
                print(f"Sending packet to {addr}!")
                socketToWan.sendto(data,(addr,util.gamePort))

            print(f"Packet received from server and forwarded to all wireless clients!")
    
    
    def send_packet(self, data, fst = False, server_pair = None):
        if self.gw:
            print(f"Sending packet to server at {server_pair}")
            self.outSocket.sendto(data,server_pair)
        else:
            nextHop = self.neighbours.best_neighbour_addr()
            if nextHop:
                if fst: #DTN Header: I src_ip I dst_ip dst_port
                    s1 = self.nodeIP.encode('utf-8')
                    s2 = server_pair[0].encode('utf-8')
                    header = struct.pack(f"I{len(s1)}s",len(s1),s1)
                    header += struct.pack(f"I{len(s2)}s",len(s2),s2)
                    header += struct.pack("I",server_pair[1])
                    data = header + data
                try:
                    self.outSocket.sendto(data,(nextHop,util.mobilePort))
                    print(f"Sending packet to best neighbour ({nextHop})")
                except:
                    print("Packet dropped")

            else:
                print("Packet dropped")



if __name__ == "__main__":
    nodeIP,gw,listeningIP = util.dtnParsing()
    if gw:
        f = Forwarder(nodeIP,True,listeningIP,main = True)
    else:
        f = Forwarder(nodeIP,main = True)