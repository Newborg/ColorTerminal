
import serial
import time
import msvcrt
import threading

keepWriting = 1

logFile = "log_example_small.txt"
# logFile = "log_search.txt"

timePeriod = 0.2

def writer():

    with open(logFile,"r") as file:
        lines = file.readlines()

    i = 0

    customOutFreq = 5

    with serial.Serial('COM2', 115200, timeout=2, write_timeout=2) as ser:

        print(ser)

        try:
            while keepWriting:
                try:
                    ser.write(str.encode(lines[i],encoding="utf-8"))
                    i = i + 1

                    if i % customOutFreq == 0:
                        # i = 0
                        time.sleep(timePeriod)
                        ser.write(b"\x41\x06\x42\x02\x42\x04\x42\x42\x43\xFE\x41\x42\x43\xFE\x41\x42\x43")
                        ser.write(str.encode("\n",encoding="utf-8"))
                    
                    if i == len(lines):
                        i = 0
                        for _ in range(10):
                            ser.write(str.encode("FASTLINE\n",encoding="utf-8"))

                    time.sleep(timePeriod)

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
