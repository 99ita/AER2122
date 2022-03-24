import traceback
import socket
from datetime import datetime
import threading
import util
import pygame as pg
import time


printInterval = 3*(util.framerate/util.netrate)

#Network class for the client communications
class NetworkClient():
    def __init__(self, serverPair, clientPair, game):
        self.outSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.serverPair = serverPair

        self.clientPair = clientPair
        self.inSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.inSocket.bind(self.clientPair)
    

        self.packetID = 0

        self.metrics = {}

        self.game = game

    def send(self,player,shots):
        message = str(self.clientPair[1]) + " " + str(self.packetID) + " " + player.toString()
        for s in shots:
            message += s.toString()
        
        self.outSocket.sendto(message.encode("utf-8"), self.serverPair)
        self.packetID += 1


    def sessionControl(self,fst,packetID):
        self.metrics['now'] = time.time()
        if fst:
            nPackets = 0
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
            print("Current packetID: ", packetID)
            print("        ", "lost ", self.metrics['lost'], " packets so far (" , lossPerc , "%)") 
            print("        ", dif, "packets/s")
            self.metrics['nPackets'] = 0
            self.metrics['lastTime'] = self.metrics['now']


        return False

    def resolvePlayers(self,str):
        str = str.split(":")
        self.game.sPlayers = {}
        for s in str:
            if len(s) > 2:
                p = util.sPlayer(s,0,0)
                if p != None:
                    self.game.sPlayers[p.color] = p

    def resolveShots(self,str):
        str = str.split(":")
        self.game.sShots = []
        for s in str:
            if len(s) > 2:
                sh = util.sShot(s)
                if sh != None:
                    self.game.sShots.append(sh)

    

    def serverListener(self):
        print("Server listener thread started...\n")
        fst = True
        nPackets = 0
        try:
            while True:
                data,addr = self.inSocket.recvfrom(1024)
                data = data.decode("utf-8")
                packetID,playersStr,shotsStr = data.split(" ")
                

                fst = self.sessionControl(fst,packetID)

                self.resolvePlayers(playersStr)
                self.resolveShots(shotsStr)
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

        self.wakeClients = threading.Event()

        self.killSessions = {}

            
    #Server loop, listens and parses new messages on a port shared by all clients, and populates the data structures
    def run(self):
        print("Server started!\nWaiting for messages...\n")
        while True:
            self.wakeClients.clear()
            try:
                data,addr = self.inSocket.recvfrom(1024)
            except:
                for k in self.killSessions.keys():
                    self.killSessions[k] = True

                self.wakeClients.set()
                
                self.inSocket.close()
                print("Server timed out!")
                exit()
            
            decoded = data.decode("utf-8")
            clientPort,packetID,decoded = decoded.split(' ')
            playerStr,shotsStr = decoded.split('_')
            shotsStr = shotsStr.split(':')

            clientPort = int(clientPort)

            currTime = datetime.utcnow()

            p = util.sPlayer(playerStr,addr,clientPort)
            self.players[p.color] = p

            self.shots[p.color] = []
            for s in shotsStr:
                if len(s) > 2:
                    self.shots[p.color].append(util.sShot(s))

            self.sessionControl(p.color, packetID, currTime, addr, clientPort)
            self.resolveHits()
            self.wakeClients.set()

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

            t = threading.Thread(target=self.clientHandler, args=(self.wakeClients,color,(addr[0],clientPort),))
            t.start()
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
    #packetid_vida jogador_jogador_ tiro_tiro_
    def generateMessage(self, packetID, color):
        s = str(packetID) + " "

        for c in self.players.keys():
            s += self.players[c].toString()
        s += " "

        for c in self.shots.keys():
            for sh in self.shots[c]:
                s += sh.toString()
        return s


    #Server thread that runs a specififc client connection
    def clientHandler(self,e,color,ipPort):
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
                print("Player", color, "session timed out...") 
                self.killSessions[color] = True   
            
            if self.killSessions[color]:
                break

            message = self.generateMessage(packetID, color).encode("utf-8")

            outSocket.sendto(message,ipPort)
            packetID += 1


        outSocket.close()
        print("Player", color, "communication thread terminated!")
    