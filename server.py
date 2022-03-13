import network
import util



if __name__ == "__main__":
    ipPort, t = util.serverParsing()

    n = network.NetworkServer(ipPort,t)
    n.run()