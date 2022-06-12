
import traceback
import threading
import pygame as pg
import math 
import network
import util
import random
import struct

def health_bar(player,win,a,b):
    width = (player.health/util.pDefaultHealth) * (util.pWidth*0.9)/2
    pad = 6

    dX = (a[0]+b[0])/2
    dY = (a[1]+b[1])/2

    sin = math.sin(player.ang*(math.pi/180))
    cos = math.cos(player.ang*(math.pi/180)) 


    aX = (dX - width * sin) - pad*cos
    aY = (dY + width * cos) - pad*sin

    bX = (dX + width * sin) - pad*cos
    bY = (dY - width * cos) - pad*sin

    pg.draw.line(win, util.white, (aX,aY), (bX,bY), 4)

#Class to define a client shot
class Shot():
    def __init__(self,x,y,ang,color,shots,id):
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
        self.kill = False
        self.id = id

    #Creates a string to be sent to the server
    def toBytes(self):
        return bytearray(struct.pack('!fffhh?',self.x,self.y,self.ang,util.encode_color(self.color),self.id,self.kill))
        

    #Entity movement logic
    def move(self):
        self.x += self.vel*math.cos(self.ang)
        self.y += self.vel*math.sin(self.ang)
        
        if self.x > util.wWidth:
            self.x -= util.wWidth
        
        if self.y > util.wHeight:
            self.kill = True

        if self.x < 0:
            self.x = util.wWidth + self.x

        if self.y < 0:
            self.kill = True

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
            self.kill = True
            
        if self.kill: 
            self.shots.remove(self)

        self.a = (self.x,self.y)
        self.b = (self.x + self.size*math.cos(self.ang),self.y + self.size*math.sin(self.ang))





#Class to define the client player
class Player():
    def __init__(self,pos,color,shots,auto):
        self.sId = 0
        self.auto = auto
        self.lastAction = 0

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
    def toBytes(self): 
        return bytearray(struct.pack('!fffhh?',self.x,self.y,self.ang,util.encode_color(self.color),self.health,self.shield))   
        '''if self.shield:
            shld = ',1'
        else:
            shld = ',0'
        return str(self.x) + ',' + str(self.y) + ',' + str(self.ang) + ',' + str(util.encode_color(self.color)) + ',' + str(self.health) + shld + '_'
        '''

    #Draws this entity on 'win'
    def draw(self, win):
        self.triangle = util.generate_triangle((self.x,self.y), self.w, self.h, self.ang)

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
            pg.draw.circle(win,util.grey,c,4)

        pg.draw.polygon(win, self.color, self.triangle, fill)
        health_bar(self,win,a,b)


    #Entity movement logic
    def move(self):
        #Natural drag
        self.velX *= util.pDrag
        self.velY *= util.pDrag

        self.x += self.velX
        self.y += self.velY
        
        if self.x > util.wWidth:
            self.x -= util.wWidth
        
        if self.y > util.wHeight:
            self.y = util.wHeight

        if self.x < 0:
            self.x = util.wWidth + self.x

        if self.y < 0:
            self.y = 0#HEIGHT + self.y

    def move_random(self):
        aAuto = False
        dAuto = False
        eAuto = False
        spaceAuto = False
        
        pad = False

        if not self.auto:
            return aAuto,dAuto,eAuto,spaceAuto


        rand = random.randrange(1,100)

        if rand > 95:
            eAuto = True
        if rand < 5:
            spaceAuto = True


        rand = random.randrange(1,100)

        if self.y > util.wHeight-150:
            pad = True
            if rand > 20:
                if self.ang > -45 and self.ang <= 90:
                    self.lastAction = 0 
                    aAuto = True
                if self.ang < -135 or self.ang > 90: 
                    self.lastAction = 0
                    dAuto = True
        
        
        if self.y < 150:
            pad = True
            if rand > 20:
                if self.ang > -90 and self.ang < 45: 
                    self.lastAction = 0
                    dAuto = True
                if self.ang <= -90 or self.ang > 135: 
                    self.lastAction = 0
                    aAuto = True

        if not pad:
            if self.lastAction == 1:
                if rand > 20:
                    aAuto = True
                    self.lastAction = 1
                else:
                    self.lastAction = 0

            if self.lastAction == 2:
                if rand > 20:
                    dAuto = True
                    self.lastAction = 2
                else:
                    self.lastAction = 0

            
            if self.lastAction == 0:
                if rand > 95:
                    aAuto = True
                    self.lastAction = 1
                elif rand <= 5:
                    dAuto = True
                    self.lastAction = 2
                else:
                    self.lastAction = 0
            
        return aAuto,dAuto,eAuto,spaceAuto

    #Applies changes to entity when a key is pressed
    def key_press(self):
        keys = pg.key.get_pressed()
        aAuto,dAuto,eAuto,spaceAuto = self.move_random()


        if keys[pg.K_w] or self.auto:
            self.velX += self.acc*(math.cos(self.ang * (math.pi/180)))
            self.velY += self.acc*(math.sin(self.ang * (math.pi/180)))

        if keys[pg.K_a] or aAuto:
            if self.ang - util.pDefaultRotation < -180:
                self.ang = 180 - (util.pDefaultRotation - (self.ang + 180))
            else:
                self.ang -= util.pDefaultRotation

        if keys[pg.K_s]:
            self.velX -= self.acc*(math.cos(self.ang * (math.pi/180)))
            self.velY -= self.acc*(math.sin(self.ang * (math.pi/180)))

        if keys[pg.K_d] or dAuto:             
            if self.ang + util.pDefaultRotation > 180:
                self.ang = -180 + (util.pDefaultRotation - (180 - self.ang))
            else:
                self.ang += util.pDefaultRotation

        if keys[pg.K_e] or eAuto:
            if self.shieldCooldown == 0 and not self.shield:
                self.shield = True
                self.shieldCooldown = util.pShieldActive

        if keys[pg.K_SPACE] or spaceAuto:
            if self.shotCooldown == 0:
                self.shotCooldown = util.pShotCooldown
                x,y = self.triangle[2]
                Shot(x,y,self.ang,self.color,self.shots,self.sId)
                self.sId += 1

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
        self.id, self.serverPair, self.clientPair, auto, self.mobile = util.clientParsing()

        self.win = pg.display.set_mode((util.wWidth,util.wHeight))
        pg.display.set_caption("MicroShips")
        self.background = pg.image.load(util.backgroundFile)
        self.background = pg.transform.scale(self.background, (util.wWidth, util.wHeight))

        self.shots = []
        self.player = Player(util.random_pos(50),util.decode_color(self.id),self.shots,auto)
        
        self.kill = False

        self.sPlayers = {}
        self.sShots = []


    def drawServerInfo(self,win):
        for k in self.sPlayers.keys():
            if k == self.id:
                self.player.health = self.sPlayers[self.id].health
            else:
                if self.sPlayers[k].shield == False:
                    fill = 2
                else:
                    fill = 0
                    
                pg.draw.polygon(win, util.decode_color(self.sPlayers[k].color), self.sPlayers[k].triangle, fill)
                a,b,_ = self.sPlayers[k].triangle
                health_bar(self.sPlayers[k],win,a,b)
                
        for s in self.sShots:
            if hasattr(s,'color'):
                if s.color != self.id:
                    pg.draw.line(win, util.decode_color(s.color), (s.x1,s.y1), (s.x2,s.y2), 2)
                else:
                    if s.kill == True:
                        for cs in self.shots:
                            if s.id == cs.id:
                                self.shots.remove(cs)


    def redraw_win(self,win):
        self.player.update()
        for s in self.shots:
            s.update()

        win.blit(self.background,(0,0))
        self.drawServerInfo(win)
        for s in self.shots:
            s.draw(win)
        self.player.draw(win)
        pg.display.flip()

        ''' def first_screen(self):
        run = True
        while run:
            win.fill
            keys = pg.key.get_pressed()'''

        
        

    
    def main(self):
        #q = self.first_screen()
        #if q:
         #   exit()

        n = network.NetworkClient(self)
        t = threading.Thread(target=n.serverListener)
        t.daemon = True
        t.start()

        run = True
        frameCounter = 0
        clock = pg.time.Clock()
        try:
            while run:
                clock.tick(util.framerate)

                for event in pg.event.get():
                    if event.type == pg.QUIT:
                        run = False
                        raise Exception("Quit")

                self.redraw_win(self.win)

                if self.player.health <= 0:
                    run = False
                    raise Exception("Quit")

                frameCounter += 1
                if frameCounter >= util.netrate:
                    frameCounter = 0
                    n.send(self.player,self.shots)
        except:
            print(traceback.format_exc())
            n.inSocket.close()
            n.outSocket.close()
            pg.quit()
            exit()

        

if __name__=="__main__":

    g = Game()
    g.main()

