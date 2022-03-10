import socket
from struct import pack
import util
import sys
from datetime import datetime

#Message


#Data
shots = {}
players = {}
playersInfo = {}


if not len(sys.argv) == 2:
    print("Wrong Call!")
    exit()


ipv6 = sys.argv[1]
port = 5555

sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
sock.bind((ipv6, port))

while True:
    sock.settimeout(10)
    
    try:
        data,addr = sock.recvfrom(1024)
    except TimeoutError:
        print("Server timed out (10s)")
        exit()

    decoded = data.decode("utf-8")
    
    packetID,decoded = decoded.split(' ')
    playerStr,shotsStr = decoded.split('_')
    shotsStr = shotsStr.split(':')

    p = util.Player(playerStr,addr)
    players[p.color] = p
    shots[p.color] = []

    currTime = datetime.utcnow()

    if not p.color in playersInfo:
        print("Player ", p.color, " session initiated...")
        playersInfo[p.color] = {}
        playersInfo[p.color]['lastPrinted'] = -10000
        playersInfo[p.color]['first'] = int(packetID)
        playersInfo[p.color]['lastTime'] = currTime
        playersInfo[p.color]['curr'] = int(packetID)
        playersInfo[p.color]['lost'] = 0
    else:
        playersInfo[p.color]['lastTime'] = currTime
        playersInfo[p.color]['last'] = playersInfo[p.color]['curr']
        playersInfo[p.color]['curr'] = int(packetID)
        playersInfo[p.color]['lost'] += playersInfo[p.color]['curr'] - playersInfo[p.color]['last'] - 1

        
    if playersInfo[p.color]['curr'] - playersInfo[p.color]['lastPrinted'] >= 100:
        playersInfo[p.color]['lastPrinted'] = playersInfo[p.color]['curr']
        lossPerc = playersInfo[p.color]['lost']/(playersInfo[p.color]['curr'] - playersInfo[p.color]['first'] + 1)
        print("Player ", p.color, " current packetID: ", packetID)
        print("Player ", p.color, " lost ", playersInfo[p.color]['lost'], " packets so far (" , lossPerc , "%)") 



    for s in shotsStr:
        if len(s) > 2:
            shots[p.color].append(util.Shot(s))


    timedOut = []
    for key in playersInfo.keys():
        if (currTime-playersInfo[key]['lastTime']).total_seconds() > 10:
            timedOut.append(key)

    for k in timedOut:
        del players[k]
        del shots[k]
        del playersInfo[k]
        print("\n\n\n\n\n\n\n\nPlayer ", players[key].color, " session timed out (10s)...")
            