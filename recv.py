import socket
import struct

#f-4; h-2; ?-1;

#x1 y1 ang color id kill
#f  f  f   h     h  ?
s = struct.pack("!iffhh?",5,2.2,3.3,4,5,True)

e, = struct.unpack("!i",s[:4])

print(e)

ba = bytearray(s)

ba += bytearray(b'0') + bytearray(struct.pack("!fffhh?",6.6,7.7,8.8,9,10,False))


spl = ba.split(b'0')
print(spl)

print(struct.unpack('!fffhh?', spl[0]))

print(s)

fst = 0
snd = 17

ll = []
while True:
    try: 
        ll.append(struct.unpack('!fffhh?', ba[fst:snd]))
        fst += 17
        snd += 17
    except: break

print(ll)