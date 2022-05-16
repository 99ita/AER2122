import socket
import struct

#f-4; h-2; ?-1;

#x1 y1 ang color id kill
#f  f  f   h     h  ?

s = "abd"

s = bytes(s,'utf-8')
p = struct.pack("I%ds" % (len(s),), len(s), s)

(i,), p = struct.unpack("I", p[:4]), p[4:]
s_f, p = p[:i], p[i:]

print(s_f.decode('utf-8'))