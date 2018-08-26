
import os

import tkinter as tk
from tkinter import messagebox
from tkinter.font import Font

import serial
import serial.tools.list_ports

from enum import Enum

import time
import datetime

import threading
import queue

import re

################################
# Settings

backgroundColor = "#101010"
selectBackgroundColor = "#303030"
textColor = "#FFFFFF"

# Good colors
# Green: #00E000 (limit use)
# Red: #FF8080
# Blue: #00D0D0
# Yellow: #CCDF32
# Orange: #EFC090
# Purple: #79ABFF

# Highlight setup
highlightMap = {
        "Main::.*":"#EFC090",
        ".*TM::.*":"#00D0D0",
        "TM::LevelSensorsI2C=>":"#FF8080",
        "GUI::.*":"#79ABFF",
        }

# Max number of lines in windows
maxLineBuffer = 4000

defaultWindowSize = "1100x600" # px

logFilePath = r"C:\tools\Terminals\HomeMade\Logs"
logFileBaseName = "SerialLog_"
logFileTimestamp = r"%Y.%m.%d_%H.%M.%S"
# logFileTimestamp = r"%Y.%m.%d_%H.00"

################################
# Custom types

class connectState(Enum):
    CONNECTED = 1
    DISCONNECTED = 0

class serialLine:        
    def __init__(self, data, timestamp):
        self.data = data
        self.timestamp = timestamp
        
class printLine:        
    def __init__(self, line, highlights):
        self.line = line
        self.highlights = highlights

################################
# Flags and queues

readFlag = 1
processFlag = 1
logFlag = 1
updateGuiFlag = 1

appState = connectState.DISCONNECTED

closeProgram = False

endLine = 0

readQueue = queue.Queue()
processQueue = queue.Queue()
logQueue = queue.Queue()

#  TODO better var name
firstConnectLineWritten = False

################################
# Root frame

root = tk.Tk()

def on_closing():
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
        print("Closing")
        global closeProgram
        closeProgram = True
        disconnectSerial()

def destroyWindow():
    print("Closing main window")
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

root.title("Color Terminal")
root.geometry(defaultWindowSize)


################################
# Status frame

def connectSerial():
    print("Connect to serial")
    global readFlag        
    readFlag = 1
    global processFlag
    processFlag = 1
    global logFlag
    logFlag = 1
    global updateGuiFlag
    updateGuiFlag = 1

    global readerThread
    readerThread = threading.Thread(target=reader,daemon=True)
    global processThread
    processThread = threading.Thread(target=process,daemon=True)
    global logThread
    logThread = threading.Thread(target=logWriter,daemon=True)

    readerThread.start()
    processThread.start()
    logThread.start()

    global firstConnectLineWritten
    firstConnectLineWritten = False

    root.after(200,waitForInput)

def disconnectSerial():
    # Disconnect will block, so must be done in different thread
    disconnectThread = threading.Thread(target=disconnectSerialProcess)
    disconnectThread.start()

def disconnectSerialProcess():
    print("Disconnect from serial")
    
    # Stop serial reader
    global readFlag        
    readFlag = 0    
    if readerThread.isAlive():
        readerThread.join()

    # Empty reader queue and stop process thread       
    readQueue.join()
    global processFlag
    processFlag = 0    
    if processThread.isAlive(): 
        processThread.join()

    # Empty process queue and stop GUI update loop
    processQueue.join()
    global updateGuiFlag
    updateGuiFlag = 0

    # Empty log queue and stop log writer thread   
    logQueue.join()
    global logFlag
    logFlag = 0 
    if logThread.isAlive():
        logThread.join()

    print("All threads stopped")

    statusLabel.config(text="DISCONNECTED", fg="red")
    global appState
    appState = connectState.DISCONNECTED

    # Close tkinter window (close program)
    # TODO not a very nice way to do this :/    
    if closeProgram:
        root.after(100,destroyWindow)


def scanSerialPorts():

    serialPortDict = dict()

    comPorts = serial.tools.list_ports.comports()

    for comPort in comPorts:
        try:
            with serial.Serial(comPort.device, 115200, timeout=2) as ser:
                # print("Port " + str(comPort.device) + " OK. Name: " + ser.name)
                serialPortDict[comPort.device] = comPort.description
        except serial.SerialException as e:
            print("ERROR: " + str(e))

    return serialPortDict


# Button Commands

def connectButtonCommand():
    global appState
    if appState == connectState.DISCONNECTED:
        # Connect to serial
        connectButton.config(text="Disconnect")
        connectSerial()
        # statusLabel.config(text="CONNECTED", fg="green")
        # appState = connectState.CONNECTED
    elif appState == connectState.CONNECTED:
        # Close down reader
        connectButton.config(text="Connect")
        disconnectSerial()
        statusLabel.config(text="DISCONNECTING...", fg="gray")
        # appState = connectState.DISCONNECTED

def goToEndButtonCommand():
    T.see(tk.END)

def clearButtonCommand():
    T.config(state=tk.NORMAL)
    T.delete(1.0,tk.END)
    T.config(state=tk.DISABLED)

def updateSerialPortSelect(*args):
    serialPortLabel.config(text=serialPorts[serialPortVar.get()])

topFrame = tk.Frame(root)

# TODO show line count

statusLabel = tk.Label(topFrame,text="DISCONNECTED", width=20, anchor=tk.W, fg="red")
statusLabel.pack(side=tk.RIGHT)

statusLabelHeader = tk.Label(topFrame,text="Status:", anchor=tk.W)
statusLabelHeader.pack(side=tk.RIGHT)

connectButton = tk.Button(topFrame,text="Connect", command=connectButtonCommand, width=10)
connectButton.pack(side=tk.LEFT)

goToEndButton = tk.Button(topFrame,text="Go to end", command=goToEndButtonCommand, width=10)
goToEndButton.pack(side=tk.LEFT)

clearButton = tk.Button(topFrame,text="Clear", command=clearButtonCommand, width=10)
clearButton.pack(side=tk.LEFT,padx=(0,40))


serialPortVar = tk.StringVar(topFrame)

def reloadSerialPorts():
    serialPorts = scanSerialPorts()

    global serialPortVar

    if serialPorts:
        serialPortList = sorted(list(serialPorts.keys()))
        serialPortVar.set(serialPortList[0])
        serialPortVar.trace("w",updateSerialPortSelect)
        serialPortOption = tk.OptionMenu(topFrame,serialPortVar,*serialPortList)
        serialPortOption.pack(side=tk.LEFT)
        serialPortLabel = tk.Label(topFrame,text=serialPorts[serialPortVar.get()], anchor=tk.W)
        serialPortLabel.pack(side=tk.LEFT)
    else:
        # Unload serial port var
        serialPortLabel = tk.Label(topFrame,text="No serial port found", anchor=tk.W)
        serialPortLabel.pack(side=tk.LEFT)
        connectButton.config(state=tk.DISABLED)

reloadSerialPorts()

topFrame.pack(side=tk.TOP, fill=tk.X)


################################
# Text frame (main window)

middleFrame = tk.Frame(root)

tFont = Font(family="DejaVu Sans Mono", size=10)
# tFont = Font(family="monaco", size=10)
# tFont = Font(family="courier", size=10)


T = tk.Text(middleFrame, height=1, width=1, background=backgroundColor, selectbackground=selectBackgroundColor,\
            foreground=textColor, font=tFont)

T.config(state=tk.DISABLED)

# Set up scroll bar
yscrollbar=tk.Scrollbar(middleFrame, orient=tk.VERTICAL, command=T.yview)
yscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
T["yscrollcommand"]=yscrollbar.set
T.pack(side=tk.LEFT, fill=tk.BOTH, expand = tk.YES)

for key,val in highlightMap.items():
    T.tag_configure(key, foreground=val)

T.tag_configure("Reconnect", background="green")

middleFrame.pack(side=tk.TOP, fill=tk.BOTH, expand = tk.YES)

################################
# Bottom frame

bottomFrame = tk.Frame(root)

statLabel1 = tk.Label(bottomFrame,text="Window line buffer 0/" + str(maxLineBuffer), width=30, anchor=tk.W)
statLabel1.pack(side=tk.LEFT)

statLabel2 = tk.Label(bottomFrame,text="", width=30, anchor=tk.W)
statLabel2.pack(side=tk.LEFT)

statLabel3 = tk.Label(bottomFrame,text="", width=60, anchor=tk.E)
statLabel3.pack(side=tk.RIGHT)

bottomFrame.pack(side=tk.BOTTOM, fill=tk.X)

################################
# Workers

def reader():

    try:
        with serial.Serial(serialPortVar.get(), 115200, timeout=2) as ser:

            statusLabel.config(text="CONNECTED to " + str(ser.name), fg="green")
            global appState
            appState = connectState.CONNECTED

            try:
                while readFlag:          
                    line = ser.readline()
                    timestamp = datetime.datetime.now()

                    if line:     
                        inLine = serialLine(line.decode("utf-8"),timestamp)
                        readQueue.put(inLine)

            except serial.SerialException as e:
                print("ERROR: Serial read error: " + str(e))

    except serial.SerialException as e:
        print("ERROR: " + str(e))



def process():
    
    lastTimestamp = 0

    while processFlag:
        try:
            line = readQueue.get(True,0.2)
            readQueue.task_done()

            # Timestamp
            micros = int(line.timestamp.microsecond/1000)
            timeString = "(" + line.timestamp.strftime("%H:%M:%S") + "." + '{:03d}'.format(micros) + ")"


            # Timedelta
            if not lastTimestamp:
                lastTimestamp = line.timestamp

            timedelta = line.timestamp - lastTimestamp
            
            hours, remainder = divmod(timedelta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            hourstring = ""
            if hours != 0:
                hourstring = "{:02d}:".format(hours)

            minutstring = ""
            if minutes != 0:
                minutstring = "{:02d}:".format(minutes)

            if minutstring:
                secondstring = "{:02d}.{:03d}".format(seconds, int(timedelta.microseconds/1000))
            else:
                secondstring = "{:2d}.{:03d}".format(seconds, int(timedelta.microseconds/1000))
            
            timeDeltaString = "(" + hourstring + minutstring + secondstring + ")"

            lastTimestamp = line.timestamp

            # Replace newline
            newData = line.data.rstrip() + "\n"
            
            # Construct newLine string
            newLine = timeString + " " + timeDeltaString + " " + newData

            # Locate highlights
            highlights = list()
            for keys in highlightMap:
                match = re.search(keys,newLine)                
                if match:
                    highlights.append((keys,match.start(),match.end()))                    
            
            
            pLine = printLine(newLine,highlights)
            
            processQueue.put(pLine)
            logQueue.put(newLine)

            
        except queue.Empty:
            pass
        
def logWriter():

    timestamp = datetime.datetime.now().strftime(logFileTimestamp)

    filename = logFileBaseName + timestamp + ".txt"
    fullFilename = os.path.join(logFilePath,filename)

    os.makedirs(os.path.dirname(fullFilename), exist_ok=True)

    statLabel3.config(text="Saving to log file: " + filename, fg="black")

    with open(fullFilename,"a") as file:
        while processFlag:
            try:
                logLine = logQueue.get(True,0.2)  
                logQueue.task_done()              
                file.write(logLine)                
            except queue.Empty:
                pass

    filesize = os.path.getsize(fullFilename)

    statLabel3.config(text="Log file saved: " + filename + " (Size " + str(filesize/1000) + "KB)", fg="green")
        

def insertLine(newLine):

    global endLine

    # Control window scolling
    bottomVisibleLine = int(T.index("@0,%d" % T.winfo_height()).split(".")[0])
    endLine = int(T.index(tk.END).split(".")[0])
    T.insert(tk.END, newLine)
    if (bottomVisibleLine >= (endLine-1)):
        T.see(tk.END)

    # Limit number of lines in window
    if endLine > maxLineBuffer:
        T.delete(1.0,2.0)

def updateGUI():

    global endLine
    global firstConnectLineWritten

    if not firstConnectLineWritten:

        timestamp = datetime.datetime.now()
        timeString = "(" + timestamp.strftime("%H:%M:%S") + ")"
        
        T.config(state=tk.NORMAL)
        insertLine(timeString + " Connected to port\n")
        T.config(state=tk.DISABLED)

        lastline = T.index("end-2c").split(".")[0]
        T.tag_add("Reconnect",lastline + ".0","end-1c")

        firstConnectLineWritten = True


    try:     
        # Open text widget for editing
        T.config(state=tk.NORMAL)

        # If many lines are available, add them X at a time, to avoid locking the UI for too long
        for i in range(100):

            msg = processQueue.get_nowait()
            processQueue.task_done()
            
            insertLine(msg.line)

            # Highlight/color text
            lastline = T.index("end-2c").split(".")[0]
        
            for high in msg.highlights:
                T.tag_add(high[0],lastline + "." + str(high[1]),lastline + "." + str(high[2]))
            
            
    except queue.Empty:
        pass

    finally:
        # Disable text widget edit
        T.config(state=tk.DISABLED)

    statLabel1.config(text="Window line buffer " + str(endLine-1) + "/" + str(maxLineBuffer))

def waitForInput():
    if updateGuiFlag:
        updateGUI()
        root.after(100,waitForInput)


################################
# 


readerThread = threading.Thread()
processThread = threading.Thread()
logThread = threading.Thread()

print("Main loop started")


root.mainloop()

print("Main loop done")

