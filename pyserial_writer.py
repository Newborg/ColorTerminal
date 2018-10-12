
import serial
import time
import msvcrt
import threading

keepWriting = 1

# logFile = "log_example_small.txt"
logFile = "log_search.txt"

def writer():

    with open(logFile,"r") as file:
        lines = file.readlines()

    i = 0

    with serial.Serial('COM2', 115200, timeout=2, write_timeout=2) as ser:
        
        print(ser)

        try:
            while keepWriting:
                try:                
                    ser.write(str.encode(lines[i],encoding="utf-8"))                
                    i = i + 1
                    if i == len(lines):
                        i = 0
                    time.sleep(0.1)
                except serial.SerialTimeoutException:
                    pass


        except KeyboardInterrupt:
            pass

        print("Writer Thread Done")


writerThread = threading.Thread(target=writer,daemon=True,name="Writer")
writerThread.start()

print("Press q to quit")

while True:
    pressedKey = msvcrt.getwch()
    if pressedKey == 'q':
        keepWriting = 0
        break
    time.sleep(0.5)    

print("Quitting...")

if writerThread.isAlive(): 
    writerThread.join()
   
print("Done writing")
        