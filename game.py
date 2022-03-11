from operator import sub
import sys
import pygame as pg
import math 
import socket
import util


#Class to define a client shots
class Shot():
    def __init__(self,x,y,ang,color,shots):
        self.x = x
        self.y = y 
        self.ang = ang * (math.pi/180)
        self.color = color

        self.vel = util.sDefaultVel
        self.ttl = util.sDefaultTTL
        self.size = util.sDefaultSize
        
        self.a = (self.x,self.y)
        self.b = (self.x + self.size*math.cos(self.ang),self.y + self.size*math.sin(self.ang))

        self.shots = shots
        shots.append(self)

    #Creates a string to be sent to the server
    def toString(self):
        return str(self.x) + ',' + str(self.y) + ',' + str(self.ang) + ',' + str(util.encode_color(self.color)) + ':'

    #Entity movement logic
    def move(self):
        self.x += self.vel*math.cos(self.ang)
        self.y += self.vel*math.sin(self.ang)
        
        if self.x > util.WIDTH:
            self.x -= util.WIDTH
        
        if self.y > util.HEIGHT:
            self.shots.remove(self)

        if self.x < 0:
            self.x = util.WIDTH + self.x

        if self.y < 0:
            self.shots.remove(self)

    #Draws this entity on 'win'
    def draw(self,win):
        self.a = (self.x,self.y)
        self.b = (self.x + self.size*math.cos(self.ang),self.y + self.size*math.sin(self.ang))
        
        pg.draw.line(win, self.color, self.a, self.b, 2)

    #Updates entity per tick
    def update(self):
        self.move()
        if self.ttl > 0:
            self.ttl -= 1
        else:
            self.shots.remove(self)

        self.a = (self.x,self.y)
        self.b = (self.x + self.size*math.cos(self.ang),self.y + self.size*math.sin(self.ang))





#Class to define the client player
class Player(pg.sprite.Sprite):
    def __init__(self,pos,color,shots):
        self.x, self.y = pos
        self.w = util.pWidth
        self.h = util.pHeight
        self.color = color

        self.shield = False
        self.shieldCooldown = util.pShieldCooldown

        self.shotCooldown = util.pShotCooldown

        self.health = util.pDefaultHealth

        self.acc = util.pAcc
        self.velX = 0
        self.velY = 0
        self.ang = 0

        self.triangle = util.generate_triangle((self.x,self.y), self.w, self.h, self.ang)
        self.shots = shots

    #Creates a string to be sent to the server
    def toString(self):    
        return str(self.x) + ',' + str(self.y) + ',' + str(self.ang) + ',' + str(util.encode_color(self.color)) + ',' + str(self.health) + '_'

    #Draws this entity on 'win'
    def draw(self, win):
        self.triangle = util.generate_triangle((self.x,self.y), self.w, self.h, self.ang)

        _,_,c = self.triangle

        if self.shield:
            fill = 0
        else:
            fill = 2
            if self.shieldCooldown == 0:
                pg.draw.circle(win,self.color,(self.x,self.y),8)
                #pg.draw.circle(win,self.color,a,4)
                #pg.draw.circle(win,self.color,b,4)

        if self.shotCooldown == 0:
            pg.draw.circle(win,util.grey,c,4)

        pg.draw.polygon(win, self.color, self.triangle, fill)


    #Entity movement logic
    def move(self):
        #Natural drag
        self.velX *= util.pDrag
        self.velY *= util.pDrag

        self.x += self.velX
        self.y += self.velY
        
        if self.x > util.WIDTH:
            self.x -= util.WIDTH
        
        if self.y > util.HEIGHT:
            self.y = util.HEIGHT

        if self.x < 0:
            self.x = util.WIDTH + self.x

        if self.y < 0:
            self.y = 0#HEIGHT + self.y

    #Applies changes to entity when a key is pressed
    def key_press(self):
        keys = pg.key.get_pressed()
        
        if keys[pg.K_w]:
            self.velX += self.acc*(math.cos(self.ang * (math.pi/180)))
            self.velY += self.acc*(math.sin(self.ang * (math.pi/180)))

        if keys[pg.K_a]:
            if self.ang - util.pDefaultRotation < -180:
                self.ang = 180 - (util.pDefaultRotation - (self.ang + 180))
            else:
                self.ang -= util.pDefaultRotation

        if keys[pg.K_s]:
            self.velX -= self.acc*(math.cos(self.ang * (math.pi/180)))
            self.velY -= self.acc*(math.sin(self.ang * (math.pi/180)))

        if keys[pg.K_d]:             
            if self.ang + util.pDefaultRotation > 180:
                self.ang = -180 + (util.pDefaultRotation - (180 - self.ang))
            else:
                self.ang += util.pDefaultRotation

        if keys[pg.K_e]:
            if self.shieldCooldown == 0 and not self.shield:
                self.shield = True
                self.shieldCooldown = util.pShieldActive

        if keys[pg.K_SPACE]:
            if self.shotCooldown == 0:
                self.shotCooldown = util.pShotCooldown
                x,y = self.triangle[2]
                Shot(x,y,self.ang,self.color,self.shots)

    #Updates entity per tick
    def update(self):
        self.key_press()
        self.move()

        if self.shieldCooldown > 0:
            self.shieldCooldown -= 1
        if self.shieldCooldown == 0 and self.shield:
            self.shield = False
            self.shieldCooldown = util.pShieldCooldown

        if self.shotCooldown > 0:
            self.shotCooldown -= 1
        
        self.triangle = util.generate_triangle((self.x,self.y), self.w, self.h, self.ang)


#Class to launch the game client
class Game():
    def __init__(self):
        self.id, self.serverPair, self.clientPair = util.clientParsing()

        self.win = pg.display.set_mode((util.WIDTH,util.HEIGHT))
        pg.display.set_caption("MicroShips")
        self.background = pg.image.load(util.backgroundFile)
        self.background = pg.transform.scale(self.background, (util.WIDTH, util.HEIGHT))

        self.shots = []
        self.player = Player(util.random_pos(50),util.decode_color(self.id),self.shots)
        

        self.kill = False
    
    def redraw_win(self,win):
        win.blit(self.background,(0,0))
        for s in self.shots:
            s.draw(win)
        self.player.draw(win)
        pg.display.flip()

    
    def main(self):
        packetID = 0

        inSock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        #inSock.bind(self.clientPair)
        
        outSock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)


        run = True

        clock = pg.time.Clock()
        while run:
            clock.tick(util.TICKRATE)

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    run = False
                    pg.quit()

            if not run: break

            self.player.update()
            message = str(self.clientPair[1]) + " " + str(packetID) + " " + self.player.toString()
            
            for s in self.shots:
                s.update()
                message += s.toString()

            self.redraw_win(self.win)
            outSock.sendto(message.encode("utf-8"), self.serverPair)
            packetID += 1

        


g = Game()
g.main()

