import math
import argparse
import random

#Game constants
wWidth = 860 
wHeight = 640 
framerate = 60 #FPS
netrate = 5 #Every <netrate> frames a packet will be sent to server
backgroundFile = 'dark-space-minimal-art-4k-ll.jpg' 

#Player constants
pWidth = 48
pHeight = 32
pAcc = 0.35*(60/framerate)
pDrag = 0.92
pShieldCooldown = int(120*(framerate/60))
pShieldActive = int(80*(framerate/60))
pShotCooldown = int(20*(framerate/60))
pDefaultHealth = 100
pDefaultRotation = 3*(60/framerate)

#Shot constants
sDefaultVel = int(10*(60/framerate))
sDefaultTTL = int(150*(framerate/60))
sDefaultSize = 30
sDamage = 5

#Colors
black = (0,0,0) #1
grey = (128,128,128) #2
white = (255,255,255) #3
red = (255,0,0) #4
lime = (0,255,0) #5
blue = (0,0,255) #6
yellow = (255,255,0) #7
cyan = (0,255,255) #8
magenta = (255,0,255) #9

def encode_color(color):
    if color == black:
        return 1
    if color == grey:
        return 2
    if color == white:
        return 3
    if color == red:
        return 4
    if color == lime:
        return 5
    if color == blue:
        return 6
    if color == yellow:
        return 7
    if color == cyan:
        return 8
    if color == magenta:
        return 9

def decode_color(color):
    if color == 1:
        return black         
    if color == 2:
        return grey
    if color == 3:
        return white
    if color == 4:
        return red
    if color == 5:
        return lime
    if color == 6:
        return blue
    if color == 7:
        return yellow
    if color == 8:
        return cyan
    if color == 9:
        return magenta

########################################################################################################

#Arguments parsers
def clientParsing():
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
    
    return a.id,(a.s[0],int(a.s[1])),(a.c[0],int(a.c[1]))
    
def serverParsing():
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
    
    return (a.s[0],int(a.s[1])),int(a.t[0])

#---------------------------------------------------------------

#Game logic

def random_pos(pad):
    return (random.randrange(pad,wWidth - pad),random.randrange(pad,wHeight - pad))

def generate_triangle(center,width,height,angle):
    x,y = center
    w = int(width/2)
    h = int(height/2)

    alpha = angle * (math.pi/180)
    beta = (angle + 90) * (math.pi/180)

    xx = int(x - math.cos(alpha)*w)
    yy = int(y - math.sin(alpha)*w)

    aX = int(xx - math.cos(beta)*h)
    aY = int(yy - math.sin(beta)*h)
    
    bX = int(xx + math.cos(beta)*h)
    bY = int(yy + math.sin(beta)*h)

    cX = int(x + math.cos(alpha)*w)
    cY = int(y + math.sin(alpha)*w)

    return [(aX,aY), (bX,bY), (cX,cY)]

def area(x1, y1, x2, y2, x3, y3):
    return abs((x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2)) / 2.0)
 
def is_inside(triangle, x, y):
    x1, y1 = triangle[0]
    x2, y2 = triangle[1] 
    x3, y3 = triangle[2]
    A = area(x1, y1, x2, y2, x3, y3)
    A1 = area(x, y, x2, y2, x3, y3)
    A2 = area(x1, y1, x, y, x3, y3)
    A3 = area(x1, y1, x2, y2, x, y)
    if(A == A1 + A2 + A3):
        return True
    else:
        return False

def resolve_colision(shot, player):
    if is_inside(player.triangle, shot.x1, shot.y1) or is_inside(player.triangle, shot.x2, shot.y2):
        if player.health > 0:
            player.health -= sDamage
        else:
            player.health = 0
        shot = None

    return shot,player

#---------------------------------------------------------------

#Simplified game classes
class sShot():
    def __init__(self,data):
        aux = data.split(',')
        self.x1 = float(aux[0])
        self.y1 = float(aux[1])
        self.ang = float(aux[2])
        self.color = int(aux[3])
        self.x2 = self.x1 + sDefaultSize*math.cos(self.ang)
        self.y2 = self.y1 + sDefaultSize*math.sin(self.ang)
    
    def toString(self):
        return str(self.x1) + ',' + str(self.y1) + ',' + str(self.ang) + ',' + str(self.color) + ':'

class sPlayer():
    def __init__(self,data,addr,port):
        aux = data.split(',')
        self.x = float(aux[0])
        self.y = float(aux[1])
        self.ang = float(aux[2])
        self.color = int(aux[3])
        self.health = int(aux[4])
        self.shield = int(aux[5])
         
        self.triangle = generate_triangle((self.x,self.y), pWidth, pHeight, self.ang)
        self.addr = addr
        self.port = port

    def toString(self):
        return str(self.x) + ',' + str(self.y) + ',' + str(self.ang) + ',' + str(self.color) + ',' + str(self.health) + ',' + str(self.shield) + ':'



