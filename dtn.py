import socket
import struct
import threading
import time
import util

neighbour_mcast = ("ff02::abcd:1",8080)
game_mcast = ("ff02::dcba:1",8182)
beacon_period = 0.5
print_period = 5


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
        self.curr_best_neighbour = None

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
        print("[Neighbours] Beacon sender thread started!")
        s = bytes(self.ip, 'utf-8')
        last = time.time()
        while True:
            if not self.gw:
                self.score = round((self.gateway_count*10 + self.gwon_count)/(time.time()-self.fstTime))
            data = struct.pack("i",self.gwOn)
            data += struct.pack("i",self.score)
            data += struct.pack("I%ds" % (len(s),), len(s), s)
            self.sock.sendto(data, neighbour_mcast)
            self.check_neighbour_timeout()


            newBest = self.best_neighbour_addr()
            if self.curr_best_neighbour != newBest:
                self.curr_best_neighbour = newBest
                if self.curr_best_neighbour != None:
                    print(f"\nCurrent best neighbour {self.curr_best_neighbour} ({self.neighbours[self.curr_best_neighbour]['score']})!\n")
                else:
                    print(f"\nNo better neighbours ({self.score})!\n")          
                

            time.sleep(self.beacon_period)

            

    def beacon_receiver(self):
        print("[Neighbours] Beacon receiver thread started!")
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
                    print(f"[Neighbours] Neighbour at {neighbour_ip} connected with a score of {c} and connected to {gwon} {gateway}!\n")
                else:
                    self.gwOn += 1
                    print(f"[Neighbours] Gateway router at {neighbour_ip} connected!\n")

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
                    print(f"[Neighbours] Neighbour at {addr} timed out!\n")
                else:
                    print(f"[Neighbours] Gateway router at {addr} timed out!\n")
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
            elif self.neighbours[addr]["score"] > self.neighbours[best_addr]["score"] and self.neighbours[best_addr]["gw_on"] == 0:
                best_addr = addr
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


            sizeC, = struct.unpack("I", data[:4])
            clientIp = data[4:sizeC+4].decode('utf-8')
                
            if self.gw:
                sizeS, = struct.unpack("I", data[sizeC+4:sizeC+8])
        
                serverIp = data[sizeC+8:sizeC+sizeS+8].decode('utf-8')
                serverPort, = struct.unpack("I", data[sizeC+sizeS+8:sizeC+sizeS+12])
                data = data[sizeC+sizeS+12:]

                serverPair = (serverIp,serverPort)

                self.wireless_clients.setdefault(serverPair[0],[])
                    
                if clientIp not in self.wireless_clients[serverPair[0]]:
                    self.wireless_clients[serverPair[0]].append(clientIp)

            #print(f"[Node {self.nodeIP}] Packet received from {addr[0]}")
            self.send_packet(data, pktFrom=addr[0], pktOrigin=clientIp, server_pair=serverPair)



    def server_listener(self):
        print(f"[Node {self.nodeIP}] Server listener thread started!")

        server_in_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        server_in_socket.bind((listeningIP,util.gamePort))
        socketToWan = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        
        while True:
            try:
                data,adr = server_in_socket.recvfrom(1024)
            except:
                print("[Node {self.nodeIP}] Server listener died!")
                server_in_socket.close()
                exit()


            #print(f"[Node {self.nodeIP}] Packet received from server at {adr[0]}, forwarding to {self.wireless_clients[adr[0]]}\n")
            for addr in self.wireless_clients[adr[0]]:
                socketToWan.sendto(data,(addr,util.gamePort))

    
    
    def send_packet(self, data, pktFrom = '', pktOrigin = '', fst = False, server_pair = None):
        if self.gw:
            #print(f"[Node {self.nodeIP}] Sending packet to server at {server_pair}\n")
            self.outSocket.sendto(data,server_pair)
        else:
            nextHop = self.neighbours.best_neighbour_addr()
            if nextHop == pktFrom:
                print(f"[Node {self.nodeIP}] Best neighbour is the one who sent the packet, packet dropped!\n")
                nextHop = None
            elif nextHop == pktOrigin:
                print(f"[Node {self.nodeIP}] Best neighbour is the one who created the packet, packet droped!\n")
                nextHop = None
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
                    #print(f"[Node {self.nodeIP}] Sending packet to best neighbour ({nextHop})\n")
                except:
                    print(f"[Node {self.nodeIP}] Sending error, packet dropped!\n")
            else:
                #save the packet
                return



if __name__ == "__main__":
    nodeIP,gw,listeningIP = util.dtnParsing()
    if gw:
        f = Forwarder(nodeIP,True,listeningIP,main = True)
    else:
        f = Forwarder(nodeIP,main = True)