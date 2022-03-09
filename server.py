import socket
import util
import sys

#Message


#Data
shots = {}
players = {}
playersLoss = {}


if not len(sys.argv) == 2:
    print("Wrong Call!")
    exit()


ipv6 = sys.argv[1]
port = 5555

sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
sock.bind((ipv6, port))

while True:
    data,addr = sock.recvfrom(1024)
    decoded = data.decode("utf-8")
    print(decoded)
    
    packetID,decoded = decoded.split(' ')
    playerStr,shotsStr = decoded.split('_')
    shotsStr = shotsStr.split(':')

    p = util.Player(playerStr,addr)
    players[p.color] = p
    shots[p.color] = []

    if not p.color in playersLoss:
        playersLoss[p.color] = {}
        playersLoss[p.color]['curr'] = int(packetID)
        playersLoss[p.color]['lost'] = 0
    else:
        playersLoss[p.color]['last'] = playersLoss[p.color]['curr']
        playersLoss[p.color]['curr'] = int(packetID)
        playersLoss[p.color]['lost'] += playersLoss[p.color]['curr'] - playersLoss[p.color]['last'] - 1
        #print("Player ", p.color, " packets lost: ", playersLoss[p.color]['lost'])

    for s in shotsStr:
        if len(s) > 2:
            shots[addr].append(util.Shot(s))

