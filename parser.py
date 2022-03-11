import argparse

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

print(client())
