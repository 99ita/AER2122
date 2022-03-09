from operator import sub
import sys
import pygame as pg
import math 
import socket
import struct


#Tamanho da janela
WIDTH = 1280
HEIGHT = 720
TICKRATE = 12






#Lista para guardar os tiros
shots = []

#Cores
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


#Player tunes
pWidth = 48
pHeight = 32
pAcc = 0.35*(60/TICKRATE)
pShieldCooldown = int(120*(TICKRATE/60))
pShieldActive = int(80*(TICKRATE/60))
pShotCooldown = int(100*(TICKRATE/60))
pDefaultHealth = 100
pDefaultRotation = 3*(60/TICKRATE)
sDefaultVel = int(10*(60/TICKRATE))
sDefaultTTL = int(150*(TICKRATE/60))
sDefaultSize = 30


class Shot():
    def __init__(self,x,y,ang,color):
        self.x = x
        self.y = y 
        self.ang = ang * (math.pi/180)
        self.color = color

        self.vel = sDefaultVel
        self.ttl = sDefaultTTL
        self.size = sDefaultSize
        
        self.a = (self.x,self.y)
        self.b = (self.x + self.size*math.cos(self.ang),self.y + self.size*math.sin(self.ang))

        shots.append(self)

    def toString(self):
        return str(self.x) + ',' + str(self.y) + ',' + str(self.ang) + ',' + str(encode_color(self.color)) + ':'


    def move(self):
        self.x += self.vel*math.cos(self.ang)
        self.y += self.vel*math.sin(self.ang)
        
        if self.x > WIDTH:
            self.x -= WIDTH
        
        if self.y > HEIGHT:
            shots.remove(self)

        if self.x < 0:
            self.x = WIDTH + self.x

        if self.y < 0:
            shots.remove(self)

    
    def draw(self,win):
        self.a = (self.x,self.y)
        self.b = (self.x + self.size*math.cos(self.ang),self.y + self.size*math.sin(self.ang))
        
        pg.draw.line(win, self.color, self.a, self.b, 2)

    def update(self):
        self.move()
        if self.ttl > 0:
            self.ttl -= 1
        else:
            shots.remove(self)

        self.a = (self.x,self.y)
        self.b = (self.x + self.size*math.cos(self.ang),self.y + self.size*math.sin(self.ang))





class Player(pg.sprite.Sprite):
    def __init__(self,x,y,color):
        self.x = x
        self.y = y
        self.w = pWidth
        self.h = pHeight
        self.color = color

        self.shield = False
        self.shieldCooldown = pShieldCooldown

        self.shotCooldown = pShotCooldown

        self.health = pDefaultHealth

        self.acc = pAcc
        self.velX = 0
        self.velY = 0
        self.ang = 0

        self.triangle = generate_triangle((self.x,self.y), self.w, self.h, self.ang)



    def toString(self):    
        return str(self.x) + ',' + str(self.y) + ',' + str(self.ang) + ',' + str(encode_color(self.color)) + ',' + str(self.health) + '_'




    def draw(self, win):
        self.triangle = generate_triangle((self.x,self.y), self.w, self.h, self.ang)

        a,b,c = self.triangle

        if self.shield:
            fill = 0
        else:
            fill = 2
            if self.shieldCooldown == 0:
                pg.draw.circle(win,self.color,(self.x,self.y),8)
                #pg.draw.circle(win,self.color,a,4)
                #pg.draw.circle(win,self.color,b,4)

        if self.shotCooldown == 0:
            pg.draw.circle(win,grey,c,4)

        pg.draw.polygon(win, self.color, self.triangle, fill)



    def drag(self):
        self.velX *= 0.92
        self.velY *= 0.92


    def move(self):
        self.x += self.velX
        self.y += self.velY
        
        if self.x > WIDTH:
            self.x -= WIDTH
        
        if self.y > HEIGHT:
            self.y = HEIGHT

        if self.x < 0:
            self.x = WIDTH + self.x

        if self.y < 0:
            self.y = 0#HEIGHT + self.y

    
        
        


    def key_press(self):
        keys = pg.key.get_pressed()
        
        if keys[pg.K_w]:
            self.velX += self.acc*(math.cos(self.ang * (math.pi/180)))
            self.velY += self.acc*(math.sin(self.ang * (math.pi/180)))

        if keys[pg.K_a]:
            if self.ang - pDefaultRotation < -180:
                self.ang = 180 - (pDefaultRotation - (self.ang + 180))
            else:
                self.ang -= pDefaultRotation

        if keys[pg.K_s]:
            self.velX -= self.acc*(math.cos(self.ang * (math.pi/180)))
            self.velY -= self.acc*(math.sin(self.ang * (math.pi/180)))

        if keys[pg.K_d]:             
            if self.ang + pDefaultRotation > 180:
                self.ang = -180 + (pDefaultRotation - (180 - self.ang))
            else:
                self.ang += pDefaultRotation

        if keys[pg.K_e]:
            if self.shieldCooldown == 0 and not self.shield:
                self.shield = True
                self.shieldCooldown = pShieldActive

        if keys[pg.K_SPACE]:
            if self.shotCooldown == 0:
                self.shotCooldown = pShotCooldown
                x,y = self.triangle[2]
                Shot(x,y,self.ang,self.color)

    def update(self):
        self.key_press()
        self.drag()
        self.move()

        if self.shieldCooldown > 0:
            self.shieldCooldown -= 1
        if self.shieldCooldown == 0 and self.shield:
            self.shield = False
            self.shieldCooldown = pShieldCooldown

        if self.shotCooldown > 0:
            self.shotCooldown -= 1
        
        self.triangle = generate_triangle((self.x,self.y), self.w, self.h, self.ang)





#Definições do display 
win = pg.display.set_mode((WIDTH,HEIGHT))
pg.display.set_caption("KSD")
background = black
#all_sprite = pg.sprite.Group



def redraw_win(win,player):
    win.fill(background)
    for s in shots:
        s.draw(win)
    player.draw(win)
    pg.display.flip()

def main():
    packetID = 0


    if not len(sys.argv) == 3:
        print("Wrong Call!")
        exit()
    

    serverIPv6 = sys.argv[2]  # localhost
    serverPort = 5555
    iter = 0
    MESSAGE = "abcd  " + str(iter)
    
    clientIPv6 = "::1"
    clientPort = int(sys.argv[1])

    inSock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    inSock.bind((clientIPv6, clientPort))
    
    outSock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)


    run = True

    p = Player(50,50,blue)
    clock = pg.time.Clock()


    while run:
        clock.tick(TICKRATE)
        for event in pg.event.get():
            if event.type == pg.QUIT:
                run = False
                pg.quit()

        if not run: break

        p.update()
        MESSAGE = str(packetID) + " " + p.toString()
        for s in shots:
            s.update()
            MESSAGE += s.toString()


        redraw_win(win,p)
        outSock.sendto(MESSAGE.encode("utf-8"), (serverIPv6, serverPort))
        packetID += 1

main()
