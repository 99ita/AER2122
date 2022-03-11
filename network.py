from cProfile import run
import socket
from datetime import datetime
from queue import Queue
import threading
import util
import argparse

def client():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('id',
                        help='Player ID',
                        type=int)
    parser.add_argument('-s', 
                        metavar=('ip','port'),
                        help='Server IP(v6) and port',
                        type=str,
                        nargs=2,
                        default=['::1','5555'])
    parser.add_argument('-c',
                        metavar=('ip','port'),
                        help='Client IP(v6) and port',
                        type=str,
                        nargs=2,
                        default=['::1','5556'])
    a = parser.parse_args()
    
    return a.id,a.s[0],int(a.s[1]),a.c[0],int(a.c[1])
    
def server():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-s', 
                        metavar=('ip','port'),
                        help='Server IP(v6) and port',
                        type=str,
                        nargs=2,
                        default=['::1','5555'])
    parser.add_argument('-t',
                        metavar='seconds',
                        help='Timeout',
                        type=int,
                        nargs=1,
                        default=10)

    a = parser.parse_args()
    
    return a.s[0],int(a.s[1]),a.t
    

class NetworkClient():
    def __init__(self, serverIP, serverPort, clientIP, clientPort):
        self.outSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.serverIP_Port = (serverIP,serverPort)

        self.inSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.inSocket.bind((clientIP,clientPort))

        self.packetID = 0


    def send(self,data):
        self.outSocket.sendto(data.encode("utf-8"), self.serverIP_Port)
        self.packetID += 1

        
class NetworkServer():
    def __init__(self, serverIP, serverPort, timeout):
        self.inSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.inSocket.bind((serverIP,serverPort))
        self.inSocket.settimeout(timeout)
        
        self.metrics = {}
        
        self.shots = {}
        self.players = {}

        self.wakeClients = threading.Event()

        self.kill = False

    def run(self):
        print("Server started!\nWaiting for messages...\n")
        while True:
            self.receive()
            
            
    def receive(self):
        self.wakeClients.clear()
        try:
            data,addr = self.inSocket.recvfrom(1024)
        except:
            self.kill = True
            self.wakeClients.set()
            
            self.inSocket.close()
            print("Server Killed!")
            exit()
        
        decoded = data.decode("utf-8")
        clientPort,packetID,decoded = decoded.split(' ')
        playerStr,shotsStr = decoded.split('_')
        shotsStr = shotsStr.split(':')

        currTime = datetime.utcnow()

        p = util.Player(playerStr,addr,clientPort)
        self.players[p.color] = p

        self.shots[p.color] = []
        for s in shotsStr:
            if len(s) > 2:
                self.shots[p.color].append(util.Shot(s))

        self.sessionControl(p.color, packetID, currTime, addr, clientPort)

        self.wakeClients.set()



    def sessionControl(self, color, packetID, time, addr, clientPort):
        if not color in self.metrics:
            print("Player ", color, " session initiated...")
            
            t = threading.Thread(target=self.clientThread, 
                                args=(self.wakeClients,color,(addr,clientPort),))
            t.start()

            self.metrics[color] = {}
            self.metrics[color]['lastPrinted'] = -10000
            self.metrics[color]['first'] = int(packetID)
            self.metrics[color]['lastTime'] = time
            self.metrics[color]['curr'] = int(packetID)
            self.metrics[color]['lost'] = 0
        else:
            self.metrics[color]['lastTime'] = time
            self.metrics[color]['last'] = self.metrics[color]['curr']
            self.metrics[color]['curr'] = int(packetID)
            self.metrics[color]['lost'] += self.metrics[color]['curr'] - self.metrics[color]['last'] - 1

            if self.metrics[color]['curr'] - self.metrics[color]['lastPrinted'] >= 100:
                self.metrics[color]['lastPrinted'] = self.metrics[color]['curr']
                lossPerc = self.metrics[color]['lost']/(self.metrics[color]['curr'] - self.metrics[color]['first'])
                print("Player ", color, " current packetID: ", packetID)
                print("Player ", color, " lost ", self.metrics[color]['lost'], " packets so far (" , lossPerc , "%)") 
    
    
    #packetid_vida-jogador_jogador_-tiro_tiro_
    def generateMessage(self, packetID, color):
        s = str(packetID) + "_" + str(self.players[color].health) + "-"

        for c in self.players.keys():
            if self.players[c].color != color:
                s += self.players[c].toString()
        s += "-"

        for c in self.shots.keys():
            if self.players[c].color != color:
                s += self.players[c].toString()
        
        return s



    def clientThread(self,e,color,ipPort):
        print("Player ", color, " communication thread launched!")

        outSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

        packetID = 0

        while not self.kill:
            e.wait()
            
            currTime = datetime.utcnow()
            if (currTime-self.metrics[color]['lastTime']).total_seconds() > 10:
                del self.players[color]
                del self.shots[color]
                del self.metrics[color]
                print("Player ", color, " session timed out (10s)...") 
                break    
            
            message = self.generateMessage(packetID, color)

            #outSocket.sendto(message.encode("utf-8"),ipPort)
            print(message)
            packetID += 1


        outSocket.close()
        print("Player ", color, " communication thread terminated!")



n = NetworkServer("::1",5555,10)
n.run()
        
        





    