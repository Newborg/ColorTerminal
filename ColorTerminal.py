
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

# fontFamily = "DejaVu Sans Mono"
fontFamily = "Consolas"
fontSize = 10

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

logFilePath = r"Logs"
logFileBaseName = "SerialLog_"
logFileTimestamp = r"%Y.%m.%d_%H.%M.%S"

statusConnectBackgroundColor = "#008800"
statusWorkingBackgroundColor = "gray"
statusDisconnectBackgroundColor = "#CC0000"
statusTextColor = "white"

textConnectBackgroundColor = "#008800"
textDisconnectBackgroundColor = "#880000"

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

NO_SERIAL_PORT = "None"

CONNECT_COLOR_TAG = "CONNECT_COLOR_TAG"
DISCONNECT_COLOR_TAG = "DISCONNECT_COLOR_TAG"

################################
# Flags, counters and queues

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

linesInLogFile = 0
lastLogFileInfo = ""

################################
# Trace

class logLevel(Enum):
    ERROR = 0
    WARNING = 1
    INFO = 2
    DEBUG = 3

def TraceLog(level,msg):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(timestamp + " [" + level.name + "] " + msg)


################################
# Root frame

root = tk.Tk()

def on_closing():
    if messagebox.askokcancel("Quit", "Do you want to quit?"):        
        global closeProgram
        closeProgram = True
        disconnectSerial()

def destroyWindow():    
    TraceLog(logLevel.INFO,"Closing main window")
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

root.title("Color Terminal")
root.geometry(defaultWindowSize)


################################
# Status frame

def connectSerial():    

    TraceLog(logLevel.INFO,"Connect to serial")

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

    root.after(50,waitForInput)

def disconnectSerial():
    # Disconnect will block, so must be done in different thread
    disconnectThread = threading.Thread(target=disconnectSerialProcess)
    disconnectThread.start()

def disconnectSerialProcess():    
    TraceLog(logLevel.INFO,"Disconnect from serial")
    
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

  

    TraceLog(logLevel.INFO,"All worker threads stopped")
    
    setStatusLabel("DISCONNECTED",statusDisconnectBackgroundColor)
    global appState
    appState = connectState.DISCONNECTED

    if closeProgram:
        # Close tkinter window (close program)
        # TODO not a very nice way to do this :/  
        root.after(100,destroyWindow)
    else:
        # Add disconnect info line to main text
        root.after(10,addDisconnectLine)   


def scanSerialPorts():

    serialPortDict = dict()

    comPorts = serial.tools.list_ports.comports()

    for comPort in comPorts:
        try:
            with serial.Serial(comPort.device, 115200, timeout=2) as ser:                
                serialPortDict[comPort.device] = comPort.description
        except serial.SerialException:            
            TraceLog(logLevel.DEBUG,"scanSerialPorts: " + comPort.device + " already open")            

    return serialPortDict

def reloadSerialPorts():

    global serialPorts
    serialPorts = scanSerialPorts()

    if serialPorts:
        serialPortList.clear()
        serialPortList.extend(sorted(list(serialPorts.keys())))
        serialPortVar.set(serialPortList[0])
        serialPortVar.trace("w",updateSerialPortSelect)

        # Delete options
        serialPortOption["menu"].delete(0,"end")        

        # Add new options
        for port in serialPortList:
            serialPortOption["menu"].add_command(label=port, command=tk._setit(serialPortVar,port))

        serialPortOption.config(state=tk.NORMAL)
        serialPortLabel.config(text=serialPorts[serialPortVar.get()])

        connectButton.config(state=tk.NORMAL)

        
    else:
        serialPortVar.set(NO_SERIAL_PORT)
        serialPortLabel.config(text="No serial port found")
        serialPortOption.config(state=tk.DISABLED)
        connectButton.config(state=tk.DISABLED)



def setAppState(state):

    if state == connectState.CONNECTED:        
        connectButton.config(text="Disconnect")
        connectSerial()        
        setStatusLabel("CONNECTING...",statusWorkingBackgroundColor)

    elif state == connectState.DISCONNECTED:        
        connectButton.config(text="Connect")
        disconnectSerial()        
        setStatusLabel("DISCONNECTING...",statusWorkingBackgroundColor)

# Button Commands

def connectButtonCommand():
    
    if appState == connectState.DISCONNECTED:
        # Connect to serial
        setAppState(connectState.CONNECTED)

    elif appState == connectState.CONNECTED:
        # Close down reader
        setAppState(connectState.DISCONNECTED)


def goToEndButtonCommand():
    T.see(tk.END)

def clearButtonCommand():
    T.config(state=tk.NORMAL)
    T.delete(1.0,tk.END)
    T.config(state=tk.DISABLED)

def updateSerialPortSelect(*args):
    if serialPortVar.get() == NO_SERIAL_PORT:        
        serialPortLabel.config(text=NO_SERIAL_PORT)
    else:
        serialPortLabel.config(text=serialPorts[serialPortVar.get()])

def setStatusLabel(labelText, bgColor):
    statusLabel.config(text=labelText, bg=bgColor)
    statusLabelHeader.config(bg=bgColor)

topFrame = tk.Frame(root)

statusLabel = tk.Label(topFrame,text="DISCONNECTED", width=20, anchor=tk.W, fg=statusTextColor, bg=statusDisconnectBackgroundColor)
statusLabel.pack(side=tk.RIGHT,padx=(0,18))

statusLabelHeader = tk.Label(topFrame,text="   Status:", anchor=tk.W, fg=statusTextColor, bg=statusDisconnectBackgroundColor)
statusLabelHeader.pack(side=tk.RIGHT)

connectButton = tk.Button(topFrame,text="Connect", command=connectButtonCommand, width=10)
connectButton.pack(side=tk.LEFT)

goToEndButton = tk.Button(topFrame,text="Go to end", command=goToEndButtonCommand, width=10)
goToEndButton.pack(side=tk.LEFT)

clearButton = tk.Button(topFrame,text="Clear", command=clearButtonCommand, width=10)
clearButton.pack(side=tk.LEFT,padx=(0,40))

serialPortReloadButton = tk.Button(topFrame,text="Reload ports", command=reloadSerialPorts, width=10)
serialPortReloadButton.pack(side=tk.LEFT)

serialPortVar = tk.StringVar(topFrame)
serialPortList = [""]
serialPortOption = tk.OptionMenu(topFrame,serialPortVar,*serialPortList)
serialPortOption.pack(side=tk.LEFT)

serialPortLabel = tk.Label(topFrame,text="", anchor=tk.W)
serialPortLabel.pack(side=tk.LEFT)

topFrame.pack(side=tk.TOP, fill=tk.X)

serialPorts = dict()
reloadSerialPorts()

################################
# Text frame (main window)

middleFrame = tk.Frame(root)

fontList = tk.font.families()
if not fontFamily in fontList:
    TraceLog(logLevel.WARNING,"Font \"" + fontFamily + "\" not found in system")

tFont = Font(family=fontFamily, size=fontSize)

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

T.tag_configure(CONNECT_COLOR_TAG, background=textConnectBackgroundColor)
T.tag_configure(DISCONNECT_COLOR_TAG, background=textDisconnectBackgroundColor)

middleFrame.pack(side=tk.TOP, fill=tk.BOTH, expand = tk.YES)

def addDisconnectLine():

    timestamp = datetime.datetime.now()
    timeString = "(" + timestamp.strftime("%H:%M:%S") + ")"
    
    T.config(state=tk.NORMAL)
    insertLine(timeString + " Disconnected from port. Log file " + lastLogFileInfo + "\n")
    T.config(state=tk.DISABLED)

    lastline = T.index("end-2c").split(".")[0]
    T.tag_add(DISCONNECT_COLOR_TAG,lastline + ".0","end-1c")

    updateWindowBufferLineCount()

    

################################
# Bottom frame

bottomFrame = tk.Frame(root)

statLabel1 = tk.Label(bottomFrame,text="Window line buffer 0/" + str(maxLineBuffer), width=30, anchor=tk.W)
statLabel1.pack(side=tk.LEFT)

statLabel2 = tk.Label(bottomFrame,text="", width=30, anchor=tk.W)
statLabel2.pack(side=tk.LEFT)

statLabel3 = tk.Label(bottomFrame,text="", width=60, anchor=tk.E)
statLabel3.pack(side=tk.RIGHT,padx=(0,18))

bottomFrame.pack(side=tk.BOTTOM, fill=tk.X)

def updateWindowBufferLineCount():
    statLabel1.config(text="Window line buffer " + str(endLine-1) + "/" + str(maxLineBuffer))

################################
# Workers

def reader():

    try:
        with serial.Serial(serialPortVar.get(), 115200, timeout=2) as ser:
             
            setStatusLabel("CONNECTED to " + str(ser.name),statusConnectBackgroundColor)         
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
                TraceLog(logLevel.ERROR,"Serial read error: " + str(e))
                # Change program state to disconnected                
                root.after(10,setAppState,connectState.DISCONNECTED)

    except serial.SerialException as e:        
        TraceLog(logLevel.ERROR,str(e))
        # In case other threads are still starting up,
        # wait for 2 sec        
        # Then change program state to disconnected                
        root.after(2000,setAppState,connectState.DISCONNECTED)



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

    global linesInLogFile
    linesInLogFile = 0

    with open(fullFilename,"a") as file:
        while processFlag:
            try:
                logLine = logQueue.get(True,0.2)  
                logQueue.task_done()              
                file.write(logLine)
                linesInLogFile += 1                       
            except queue.Empty:
                pass

    filesize = os.path.getsize(fullFilename)

    global lastLogFileInfo    
    lastLogFileInfo = filename + " (Size " + "{:.3f}".format(filesize/1024) + "KB)"

    statLabel3.config(text="Log file saved: " + lastLogFileInfo, fg="green")
        

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
        T.tag_add(CONNECT_COLOR_TAG,lastline + ".0","end-1c")

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
    
    updateWindowBufferLineCount()
    statLabel2.config(text="Lines in log file " + str(linesInLogFile))

def waitForInput():
    if updateGuiFlag:
        updateGUI()
        root.after(100,waitForInput)


################################
# 


readerThread = threading.Thread()
processThread = threading.Thread()
logThread = threading.Thread()

TraceLog(logLevel.INFO,"Main loop started")

root.mainloop()

TraceLog(logLevel.INFO,"Main loop done")


