import struct
import traceback
import socket
from datetime import datetime
import threading
import util
import pygame as pg
import time
import dtn


printInterval = 3*(util.framerate/util.netrate)

#Network class for the client communications
class NetworkClient():
    def __init__(self, game):
        self.outSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

        self.serverPair = game.serverPair
        self.clientPair = game.clientPair

        self.mobile = game.mobile

        self.game = game

        if self.mobile:
            self.inSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.inSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.inSocket.bind(('', dtn.game_mcast[1]))
            self.inSocket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_LOOP, False)
            mreq = struct.pack("16s15s".encode('utf-8'), socket.inet_pton(socket.AF_INET6, dtn.game_mcast[0]), (chr(0) * 16).encode('utf-8'))
            self.inSocket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)
            fwd = threading.Thread(target=dtn.Forwarder,args=(self.clientPair[0],))
            fwd.daemon = True
            fwd.start()
        else:   
            self.inSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            print(self.clientPair)
            self.inSocket.bind(self.clientPair)
            self.dtn = None

        self.packetID = 0

        self.metrics = {}
            

    def send(self,player,shots):
        message = bytearray(struct.pack('!Hi',self.clientPair[1],self.packetID)) + player.toBytes()
        for s in shots:
            message += s.toBytes()
        
        if self.mobile:
            self.dtn.send_packet(message)
        else:
            self.outSocket.sendto(message, self.serverPair)
    
        self.packetID += 1


    def sessionControl(self,fst,packetID):
        self.metrics['now'] = time.time()
        if fst:
            self.metrics['lastPrinted'] = -10000
            self.metrics['first'] = int(packetID)
            self.metrics['curr'] = int(packetID)
            self.metrics['lost'] = 0
            self.metrics['nPackets'] = 0
            self.metrics['lastTime'] = time.time()
        else:
            self.metrics['nPackets'] += 1
            self.metrics['last'] = self.metrics['curr']
            self.metrics['curr'] = int(packetID)
            self.metrics['lost'] += self.metrics['curr'] - self.metrics['last'] - 1

        if self.metrics['curr'] - self.metrics['lastPrinted'] >= printInterval:
            dif = 0
            if not fst: 
                dif = self.metrics['nPackets']/(self.metrics['now']-self.metrics['lastTime'])
            self.metrics['lastPrinted'] = self.metrics['curr']
            lossPerc = self.metrics['lost']/(self.metrics['curr'] - self.metrics['first'] + 1)
            print(f"Current packetID: {packetID}")
            print(f"        lost {self.metrics['lost']} packets so far ({lossPerc}%)") 
            print(f"        {dif}packets/s")
            self.metrics['nPackets'] = 0
            self.metrics['lastTime'] = self.metrics['now']


        return False

    def resolvePlayers(self,data):
        self.game.sPlayers = {}
        fst = 0
        snd = 17
        while True:
            try:
                p = util.sPlayer(data[fst:snd],0,0)
                fst += 17
                snd += 17
                if p != None:
                    self.game.sPlayers[p.color] = p
            except:
                break

    def resolveShots(self,data):
        self.game.sShots = []
        fst = 0
        snd = 17
        while snd <= len(data):
            try:
                sh = util.sShot(data[fst:snd])
                fst += 17
                snd += 17
                if sh != None:
                    self.game.sShots.append(sh)
            except:
                break
    

    def serverListener(self):
        print("Server listener thread started...\n")
        fst = True
        try:
            while True:
                data,addr = self.inSocket.recvfrom(1024)
                packetID,nJogs = struct.unpack("!hh",data[:4])
                playersBArr = data[4:4+(17*nJogs)]
                shotsBArr = data[4+(17*nJogs):]
                
                fst = self.sessionControl(fst,packetID)

                self.resolvePlayers(playersBArr)
                self.resolveShots(shotsBArr)
        except:
            print(traceback.format_exc())
            print("Server listener thread exiting!")


        

        
#Network class for the server communications
class NetworkServer():
    def __init__(self, serverPair, timeout):
        self.inSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.inSocket.bind(serverPair)
        self.timeout = timeout
        self.inSocket.settimeout(10)
        
        self.metrics = {}
        self.shots = {}
        self.players = {}

        self.killSessions = {}
        self.outIps = []

            
    #Server loop, listens and parses new messages on a port shared by all clients, and populates the data structures
    def run(self):
        print("Server started!\nWaiting for messages...\n")
        while True:
            try:
                data,addr = self.inSocket.recvfrom(1024)
            except:
                for k in self.killSessions.keys():
                    self.killSessions[k] = True
                
                self.inSocket.close()
                print("Server timed out!")
                exit()
            clientPort,packetID = struct.unpack('!Hi',data[:6])
            playerArr = data[6:23]
            p = util.sPlayer(playerArr,addr,clientPort)
            self.players[p.color] = p

            self.shots[p.color] = []

            fst = 23
            snd = 40
            while snd <= len(data):
                try:
                    self.shots[p.color].append(util.sShot(data[fst:snd]))
                    fst += 17
                    snd += 17
                except:
                    break
            currTime = datetime.utcnow()
            self.sessionControl(p.color, packetID, currTime, addr, clientPort)
            self.resolveHits()

    def resolveHits(self):
        for p in self.players.values():
            for sl in self.shots.keys():
                for s in self.shots[sl]:
                    if p.color != s.color:
                        s,p = util.resolve_colision(s,p)
                        
                        


    #Launches a client thread when a session is new or updates the session metrics
    def sessionControl(self, color, packetID, time, addr, clientPort):
        if not color in self.metrics:
            self.killSessions[color] = False
            self.metrics[color] = {}
            self.metrics[color]['lastPrinted'] = -10000
            self.metrics[color]['first'] = int(packetID)
            self.metrics[color]['lastTime'] = time
            self.metrics[color]['curr'] = int(packetID)
            self.metrics[color]['lost'] = 0

            if not addr[0] in self.outIps:
                t = threading.Thread(target=self.clientHandler, args=(color,(addr[0],clientPort),))
                t.start()
                self.outIps.append(addr[0])
        else:
            self.metrics[color]['lastTime'] = time
            self.metrics[color]['last'] = self.metrics[color]['curr']
            self.metrics[color]['curr'] = int(packetID)
            self.metrics[color]['lost'] += self.metrics[color]['curr'] - self.metrics[color]['last'] - 1

        if self.metrics[color]['curr'] - self.metrics[color]['lastPrinted'] >= printInterval:
            self.metrics[color]['lastPrinted'] = self.metrics[color]['curr']
            lossPerc = 0#self.metrics[color]['lost']/(self.metrics[color]['curr'] - self.metrics[color]['first'] + 1)
            print("Player", color, "current packetID: ", packetID)
            print("        ", "lost ", self.metrics[color]['lost'], " packets so far (" , lossPerc , "%)\n") 
    
    
    #Generates the message to send to a client
    def generateMessage(self, packetID):
        b = bytearray(struct.pack('!hh',packetID,len(self.players.keys()))) 

        for p in self.players.keys():
            b += self.players[p].toBytes()

        for s in self.shots.keys():
            for sh in self.shots[s]:
                b += sh.toBytes()
        return b


    #Server thread that runs a specififc client connection
    def clientHandler(self,color,ipPort):
        print("Player", color, "communication thread launched!\n        ", "client at",str(ipPort),"\n")

        outSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

        packetID = 0
        clock = pg.time.Clock()
        while not self.killSessions[color]:
            clock.tick(int(util.framerate/util.netrate))
            if self.killSessions[color]:
                break
            
            currTime = datetime.utcnow()
            if (currTime-self.metrics[color]['lastTime']).total_seconds() > self.timeout:
                del self.players[color]
                del self.shots[color]
                del self.metrics[color]
                del self.killSessions[color]
                self.outIps.remove(ipPort[0])
                print("Player", color, "session timed out...") 
                break  
            message = self.generateMessage(packetID)
            outSocket.sendto(message,ipPort)
            packetID += 1
            if self.players[color].health <= 0:
                self.killSessions[color] = True
                del self.players[color]
                del self.shots[color]
                del self.metrics[color]
                del self.killSessions[color]
                self.outIps.remove(ipPort[0])
                break


        outSocket.close()
        print("Player", color, "communication thread terminated!")
    