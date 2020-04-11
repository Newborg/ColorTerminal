from multiprocessing.connection import Client
import sys
import time

address = ('localhost', 6000)
try:
    conn = Client(address, authkey=b"secret password asd")    
    conn.send("close")
    # can also send arbitrary objects:
    # conn.send(['a', 2.5, None, int, sum])
    conn.close()
# except :
    # print("WinError")
except ConnectionRefusedError:
    print("Connection refused")
    print("(Listener likely not started)")
except Exception as e:
    print("Not able to connect")
    print(e.args)
    print(type(e).__name__)
