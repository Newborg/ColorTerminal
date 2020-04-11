# from multiprocessing.connection import Listener
import multiprocessing.connection as con
import time
import os
import sys

address = ('localhost', 6000)     # family is deduced to be 'AF_INET'
try:
    listener = con.Listener(address, authkey=b"secret password")
    print("Listener created")
    conn = listener.accept() # blocking
    print("connection accepted from", listener.last_accepted)
    time.sleep(5)
    while True:
        if conn.poll(timeout=0.1):            
            msg = conn.recv() # blocking        
            # do something with msg
            if msg == "close":
                conn.close()
                break        
        time.sleep(2)
        print("Loooop")
    print("Message received")
    listener.close()
except OSError:
    print("Socket address already used")
except con.AuthenticationError:
    print("AuthenticationError")
except Exception as e:
    print("Not able to start listener")
    print(e.args)
    print(type(e).__name__)