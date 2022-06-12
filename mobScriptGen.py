from numpy import random
import math
import argparse


def parser():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-n',
                        help='Node list',
                        nargs='+',
                        default=[15, 16, 18])
    
    parser.add_argument('-x',
                        help='X min and max',
                        nargs=2,
                        type=int,
                        default=[500, 900])

    parser.add_argument('-y',
                        help='Y min and max',
                        nargs=2,
                        type=int,
                        default=[200, 650])

    parser.add_argument('-s',
                        help='Mean speed', 
                        default=30)

    parser.add_argument('-d',
                        help='Minimum movement distance',
                        default=100)

    parser.add_argument('-p',
                        help='Mean period between movements',
                        default=5)

    parser.add_argument('-t',
                        help='Max time',
                        default=30)

    parser.add_argument('-sdp',
                        help='Normal distribution std deviation (Position)',
                        default=100)

    parser.add_argument('-sds',
                        help='Normal distribution std deviation (Speed)',
                        default=10)

    parser.add_argument('-sdt',
                        help='Normal distribution std deviation (Time)',
                        default=1)

    parser.add_argument('-stop',
                        help='No movement',
                        action='store_true')

    value = parser.parse_args()

    return value.x[0],value.x[1],value.y[0],value.y[1],value.n,int(value.s),int(value.d),int(value.p),int(value.t),int(value.sdp),int(value.sds),int(value.sdt),value.stop

minX, maxX, minY, maxY, nodes, meanSpeed, minDist, meanMovPeriod, maxTime, sdp, sds, sdt, stop = parser()


print(f"X from {minX} to {maxX}\nY from {minY} to {maxY}")
print(f"Nodes: {nodes}\nMean speed: {meanSpeed}\nMinimum distance: {minDist}")
print(f"Mean period between movements: {meanMovPeriod}\nMax time: {maxTime}")
print(f"Positions standard deviation: {sdp}\nSpeed standard deviation: {sds}\nTime standard deviation: {sdt}")

nodesDict = {}
for n in nodes:
    nodesDict[n] = {}

center = (int((minX+maxX)/2),int((minY+maxY)/2))


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
    x = random.normal(loc=center[0],scale=sdp)
    while x > maxX or x < minX:
        x = random.normal(loc=center[0],scale=sdp)
        
    y = random.normal(loc=center[1],scale=sdp)
    while y > maxY or y < minY:
        y = random.normal(loc=center[1],scale=sdp)
        
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
            x = random.normal(loc=center[0],scale=sdp)
            y = random.normal(loc=center[1],scale=sdp)
            while x > maxX or x < minX or y > maxY or y < minY or dist(nodesDict[n]['lastPos'],(x,y)) < minDist:
                x = random.normal(loc=center[0],scale=sdp)
                y = random.normal(loc=center[1],scale=sdp)

            nodesDict[n]['lastPos'] = (x,y)
            speed = random.normal(loc=meanSpeed,scale=sds)
            
            nodesDict[n]['str'] += moveStr(n,nodesDict[n]['time'],x,y,speed) 
            nodesDict[n]['time'] += random.normal(loc=meanMovPeriod,scale=sdt)
        
        x,y = nodesDict[n]['firstPos']
        speed = random.normal(loc=meanSpeed,scale=sds)
        nodesDict[n]['str'] += moveStr(n,nodesDict[n]['time'],x,y,speed) 
        
        
    if stop:
        return nodesStr()
    else:
        return nodesStr()+movesStr()       
        

with open("movementScript.scen", 'w+') as f:
    f.truncate(0)
    f.seek(0)
    f.write(generate().strip())

print("\nDone!")