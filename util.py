import math
import argparse

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

#Player constants




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

#Player tunes
pWidth = 48
pHeight = 32
sDefaultSize = 30
sDamage = 5

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
    return abs((x1 * (y2 - y3) + x2 * (y3 - y1)
                + x3 * (y1 - y2)) / 2.0)
 
 
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

class Shot():
    def __init__(self,data):
        aux = data.split(',')
        self.x1 = float(aux[0])
        self.y1 = float(aux[1])
        self.ang = float(aux[2])
        self.color = int(aux[3])
        self.x2 = self.x1 + sDefaultSize*math.cos(self.ang)
        self.y2 = self.y1 + sDefaultSize*math.sin(self.ang)
    
    def toString(self):
        return self.x1 + ',' + self.y1 + ',' + self.ang + ',' + self.color + '_'




class Player():
    def __init__(self,data,addr,port):
        aux = data.split(',')
        self.x = float(aux[0])
        self.y = float(aux[1])
        self.ang = float(aux[2])
        self.color = int(aux[3])
        self.health = int(aux[4])
        self.triangle = generate_triangle((self.x,self.y), pWidth, pHeight, self.ang)
        self.addr = addr
        self.port = port

    def toString(self):
        return self.x + ',' + self.y + ',' + self.ang + ',' + self.color + ',' + self.health + '_'



def resolve_colision(shot, player):
    if is_inside(player.triangle, shot.x1, shot.y1) or is_inside(player.triangle, shot.x2, shot.y2):
        if player.health > 0:
            player.health -= sDamage
        else:
             player.health = 0
        shot = None

    return shot,player