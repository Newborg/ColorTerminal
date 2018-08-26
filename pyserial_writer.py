
import serial
import time


with open("log_example_small.txt","r") as file:
    lines = file.readlines()

i = 0


with serial.Serial('COM2', 115200, timeout=2) as ser:
    
    print(ser)

    try:
        while True:
            ser.write(str.encode(lines[i],encoding="utf-8"))
            # print(lines[i])
            i = i + 1
            if i == len(lines):
                i = 0
            time.sleep(0.05)     
    except KeyboardInterrupt:
        pass

    
    
        
print("Done writing")
        