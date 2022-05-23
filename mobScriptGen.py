from statistics import mean
from numpy import random
import math
import matplotlib.pyplot as plt
import seaborn as sns

maxTime = 30 #sec
meanSpeed = 30
meanMovPeriod = 5 #sec
minDist = 100
nodes = [15,16,18]
nodesDict = {}
for n in nodes:
    nodesDict[n] = {}

minX = 500
maxX = 900
minY = 200
maxY = 650
center = (int((minX+maxX)/2),int((minY+maxY)/2))
# X 500-900
# Y 200-650  
# Center (700,425)

def nodesStr():
    r = ""
    for n in nodes:
        r += nodeStr(n,nodesDict[n]['firstPos'])
    return r    

def nodeStr(n,pos):
    x,y = pos
    return f"$node_({n}) set X_ {round(x,2)}\n$node_({n}) set Y_ {round(y,2)}\n$node_({n}) set Z_ 0\n"

def movesStr():
    r = ""
    for n in nodes:
        r += nodesDict[n]['str']
    return r

def moveStr(n,t,x,y,s):
    return f'$ns_ at {round(t,2)} "$node_({n}) setdest {round(x,2)} {round(y,2)} {round(s,2)}"\n'    



def newPos():
    x = random.normal(loc=center[0],scale=100)
    while x > maxX or x < minX:
        x = random.normal(loc=center[0],scale=100)
        
    y = random.normal(loc=center[1],scale=100)
    while y > maxY or y < minY:
        y = random.normal(loc=center[1],scale=100)
        
    return (x,y)

def dist(p1,p2):
    return math.sqrt(((p1[0]-p2[0])**2)+((p1[1]-p2[1])**2))

def generate():
    for n in nodes:
        nodesDict[n]['firstPos'] = newPos()
        nodesDict[n]['lastPos'] = nodesDict[n]['firstPos']
        nodesDict[n]['time'] = 0
        nodesDict[n]['str'] = ""
        while nodesDict[n]['time'] < maxTime:
            x = random.normal(loc=center[0],scale=100)
            y = random.normal(loc=center[1],scale=100)
            while x > maxX or x < minX or y > maxY or y < minY or dist(nodesDict[n]['lastPos'],(x,y)) < 50:
                x = random.normal(loc=center[0],scale=100)
                y = random.normal(loc=center[1],scale=100)

            nodesDict[n]['lastPos'] = (x,y)
            speed = random.normal(loc=meanSpeed,scale=10)
            
            nodesDict[n]['str'] += moveStr(n,nodesDict[n]['time'],x,y,speed) 
            nodesDict[n]['time'] += random.normal(loc=meanMovPeriod,scale=1)
        
        x,y = nodesDict[n]['firstPos']
        speed = random.normal(loc=meanSpeed,scale=10)
        nodesDict[n]['str'] += moveStr(n,nodesDict[n]['time'],x,y,speed) 
        
        

    return nodesStr()+movesStr()       
        

with open("movementScript.scen", 'w+') as f:
    f.truncate(0)
    f.seek(0)
    f.write(generate().strip())

print("Done!\n")