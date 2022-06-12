import socket
import struct
import threading
import time
import util
import traceback

neighbour_mcast = ("ff02::abcd:1",8080)
beacon_period = 0.25
print_period = 5


class Neighbours():
    def __init__(self,gw,ip,fwd,beacon_period = beacon_period):
        self.fstTime = time.time()
        self.gw = gw
        self.ip = ip
        self.beacon_period = beacon_period
        self.fwd = fwd

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
        while True:
            if not self.gw:
                self.score = round((self.gateway_count*100 + self.gwon_count*10)/(time.time()-self.fstTime))
            data = struct.pack("h",self.gwOn)
            data += struct.pack("h",self.score)
            data += struct.pack("h%ds" % (len(s),), len(s), s)
            self.sock.sendto(data, neighbour_mcast)
            self.fwd.clearingQueue = True

            newBest = self.best_neighbour_addr()

            self.fwd.clear_queue(newBest)

            if self.curr_best_neighbour != newBest:
                self.curr_best_neighbour = newBest
                '''if self.curr_best_neighbour != None:
                    print(f"\n[Neighbours] Current best neighbour {self.curr_best_neighbour} ({self.neighbours[self.curr_best_neighbour]['score']}/{self.neighbours[self.curr_best_neighbour]['gw_on']})!\n")
                else:
                    print(f"\n[Neighbours] No better neighbours ({self.score}/{self.gwOn})!\n") '''         
                
            time.sleep(self.beacon_period)

            

    def beacon_receiver(self):
        print("[Neighbours] Beacon receiver thread started!")
        while True:
            data, addr = self.sock.recvfrom(1024)

            gwon,c = struct.unpack("hh",data[:4])
            data = data[4:]
            (i,), data = struct.unpack("h", data[:2]), data[2:]
            neighbour_ip = data[:i].decode('utf-8')
            if not neighbour_ip in self.neighbours:
                self.neighbours[neighbour_ip] = {}
                if c != -1:
                    if gwon >= 1:
                        self.gwon_count += 1
                    #print(f"[Neighbours] Neighbour at {neighbour_ip} connected ({c}/{gwon})!\n")
                else:
                    self.gwOn += 1
                    #print(f"[Neighbours] Gateway router at {neighbour_ip} connected!\n")

            if c == -1 and not self.gw:
                self.gateway_count += 1

            self.neighbours[neighbour_ip]["gw_on"] = gwon
            self.neighbours[neighbour_ip]["score"] = c
            self.neighbours[neighbour_ip]["time"] = time.time()


            
    def check_neighbours_timeout(self):
        to = []
        for addr in self.neighbours.keys():
            if time.time() - self.neighbours[addr]["time"] >= 1.5*self.beacon_period:
                if self.neighbours[addr]["score"] != -1:
                    pass
                    #print(f"[Neighbours] Neighbour at {addr} timed out!\n")
                else:
                    #print(f"[Neighbours] Gateway router at {addr} timed out!\n")
                    self.gwOn -= 1

                to.append(addr)
        for addr in to:
            del self.neighbours[addr]


    def best_neighbour_addr(self):
        self.check_neighbours_timeout()
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
        
        if self.score == -1:
            best_addr = None
        elif self.gwOn > 0: 
            if self.neighbours[best_addr]["gw_on"] < 1:
                best_addr = None
            elif self.score > self.neighbours[best_addr]["score"]:
                best_addr = None
        elif self.neighbours[best_addr]["gw_on"] < 1 and self.score > self.neighbours[best_addr]["score"]:
            best_addr = None

        
        return best_addr


class Forwarder():
    def __init__(self, nodeIP, gw = False, listeningIP = None, main = False):
        self.nodeIP = nodeIP
        self.listeningIP = listeningIP
        
        self.neighbour_in_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.neighbour_in_socket.bind((nodeIP,util.mobilePort))

        self.outSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        
        self.packetQueue = []

        self.neighbours = Neighbours(gw,nodeIP,self)

        self.main = main

        self.gw = gw

        if self.gw:
            self.printStr = "[Forwarder]"
        else:
            self.printStr = "[Gateway]"

        self.clearingQueue = False

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


            sizeC, = struct.unpack("h", data[:2])
            clientIp = data[2:sizeC+2].decode('utf-8')
                
            if self.gw:
                sizeS, = struct.unpack("h", data[sizeC+2:sizeC+4])
        
                serverIp = data[sizeC+4:sizeC+sizeS+4].decode('utf-8')
                serverPort, = struct.unpack("H", data[sizeC+sizeS+4:sizeC+sizeS+6])
                data = data[sizeC+sizeS+6:]

                serverPair = (serverIp,serverPort)

                self.wireless_clients.setdefault(serverPair[0],[])
                    
                if clientIp not in self.wireless_clients[serverPair[0]]:
                    self.wireless_clients[serverPair[0]].append(clientIp)

            #print(f"{self.printStr} Packet received from {addr[0]}")
            self.send_packet(data, pktFrom=addr[0], pktOrigin=clientIp, server_pair=serverPair)



    def server_listener(self):
        print(f"{self.printStr} Server listener thread started!")

        server_in_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        server_in_socket.bind((self.listeningIP,util.gamePort))
        socketToWan = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        
        while True:
            try:
                data,adr = server_in_socket.recvfrom(1024)
            except:
                print(f"{self.printStr} Server listener died!")
                server_in_socket.close()
                exit()


            #print(f"{self.printStr} Packet received from server at {adr[0]}, forwarding to {self.wireless_clients[adr[0]]}\n")
            for addr in self.wireless_clients[adr[0]]:
                socketToWan.sendto(data,(addr,util.gamePort))

    
    
    def send_packet(self, data, pktFrom = '', pktOrigin = '', fst = False, server_pair = None):
        if self.gw:
            print(f"{self.printStr} Sending packet to server at {server_pair}\n")
            self.outSocket.sendto(data,server_pair)
        else:
            if fst: #DTN Header: I src_ip I dst_ip dst_port
                s1 = self.nodeIP.encode('utf-8')
                s2 = server_pair[0].encode('utf-8')
                header = struct.pack(f"h{len(s1)}s",len(s1),s1)
                header += struct.pack(f"h{len(s2)}s",len(s2),s2)
                header += struct.pack("H",server_pair[1])
                data = header + data

            nextHop = self.neighbours.best_neighbour_addr()
            if nextHop == pktFrom:
                print(f"{self.printStr} Best neighbour is the one who sent the packet!\n")
                nextHop = None
            elif nextHop == pktOrigin:
                print(f"{self.printStr} Best neighbour is the one who created the packet!\n")
                nextHop = None
            if nextHop:
                try:
                    self.clear_queue(nextHop)
                        
                    self.outSocket.sendto(data,(nextHop,util.mobilePort))
                    #print(f"{self.printStr} Sending packet to best neighbour ({nextHop})\n")
                except:
                    print(traceback.format_exc())
                    print(f"{self.printStr} Sending error, packet added to queue!\n")
                    pktEntry = []
                    pktEntry.append(pktFrom)
                    pktEntry.append(pktOrigin)
                    pktEntry.append(data)
                    self.packetQueue.append(pktEntry)
            else:
                print(f"{self.printStr} Packet added to queue!")
                pktEntry = []
                pktEntry.append(pktFrom)
                pktEntry.append(pktOrigin)
                pktEntry.append(data)
                self.packetQueue.append(pktEntry)
                return

    def clear_queue(self,nextHop):
        if len(self.packetQueue) < 1 or nextHop == None:
            return
        rem = []
        print(f"\n{self.printStr} Atempting to clear packet queue ({len(self.packetQueue)} packets)...")
        for entry in self.packetQueue:
            success = False
            if nextHop != entry[0] and nextHop != entry[1]: 
                try:
                    self.outSocket.sendto(entry[2],(nextHop,util.mobilePort))
                    success = True
                    print(f"{self.printStr} Sending queued packet to best neighbour ({nextHop})")
                except:
                    print(traceback.format_exc())
            if success:
                rem.append(entry)
        for entry in rem:
            self.packetQueue.remove(entry)
        if len(self.packetQueue) < 1:
            print(f"{self.printStr} Queue empty!\n")



if __name__ == "__main__":
    nodeIP,gw,listeningIP = util.dtnParsing()
    if gw:
        f = Forwarder(nodeIP,True,listeningIP,main = True)
    else:
        f = Forwarder(nodeIP,main = True)