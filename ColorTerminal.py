
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

# Text color setup
textColorMap = {
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

timeStampBracket = ["[","]"]
timeDeltaBracket = ["(",")"]

connectLineText = " Connected to port\n"
connectLineRegex = "\\" + timeStampBracket[0] + ".{8}\\" + timeStampBracket[1] + connectLineText
connectLineBackgroundColor = "#008800"
connectLineSelectBackgroundColor = "#084C08"

disconnectLineText = " Disconnected from port. Log file "
disconnectLineRegex = "\\" + timeStampBracket[0] + ".{8}\\" + timeStampBracket[1] + disconnectLineText
disconnectLineBackgroundColor = "#880000"
disconnectLineSelectBackgroundColor = "#4C0808"

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
    def __init__(self, line, lineTags):
        self.line = line
        self.lineTags = lineTags        

NO_SERIAL_PORT = "None"

CONNECT_COLOR_TAG = "CONNECT_COLOR_TAG"
DISCONNECT_COLOR_TAG = "DISCONNECT_COLOR_TAG"

################################
# Flags, counters and queues

readFlag = 1
processFlag = 1
logFlag = 1

highlightFlag = 1
updateGuiFlag = 1

appState = connectState.DISCONNECTED

closeProgram = False

endLine = 0

processQueue = queue.Queue()
highlightQueue = queue.Queue()
logQueue = queue.Queue()
guiQueue = queue.Queue()

# Buffer from raw line input (input for process worker)
lineBuffer = list()
reloadLineBuffer = False

guiBuffer = list()
reloadGuiBuffer = False

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
    
    global readerThread
    readerThread = threading.Thread(target=readerWorker,daemon=True,name="Reader")
    global processThread
    processThread = threading.Thread(target=processWorker,daemon=True,name="Process")
    global logThread    
    logThread = threading.Thread(target=logWriterWorker,daemon=True,name="Log")

    readerThread.start()
    processThread.start()
    logThread.start()  


def disconnectSerial():
    # Disconnect will block, so must be done in different thread
    disconnectThread = threading.Thread(target=disconnectSerialProcess,name="Disconnect")
    disconnectThread.start()

def disconnectSerialProcess():    
    TraceLog(logLevel.INFO,"Disconnect from serial")
    
    global appState

    # Stop serial reader
    global readFlag        
    readFlag = 0        
    if readerThread.isAlive():
        readerThread.join()

    # Empty process queue and stop process thread       
    processQueue.join()
    global processFlag
    processFlag = 0      
    if processThread.isAlive(): 
        processThread.join()

    # Empty log queue and stop log writer thread   
    logQueue.join()
    global logFlag
    logFlag = 0     
    if logThread.isAlive():
        logThread.join()

    # Add disconnect line if connected     
    if appState == connectState.CONNECTED:
        timestamp = datetime.datetime.now()
        timeString = timeStampBracket[0] + timestamp.strftime("%H:%M:%S") + timeStampBracket[1]
        
        disconnectLine = timeString + disconnectLineText + lastLogFileInfo + "\n"    

        highlightQueue.put(disconnectLine)

    TraceLog(logLevel.INFO,"Main worker threads stopped")
    
    setStatusLabel("DISCONNECTED",statusDisconnectBackgroundColor)
    
    appState = connectState.DISCONNECTED

    if closeProgram:

        # Empty highlight queue and stop highlight thread   
        highlightQueue.join()
        global highlightFlag
        highlightFlag = 0 
        if highlightThread.isAlive():
            highlightThread.join()

        # Empty gui queue and stop GUI update loop
        guiQueue.join()
        global updateGuiFlag
        updateGuiFlag = 0

        # Close tkinter window (close program)
        # TODO not a very nice way to do this :/  
        root.after(100,destroyWindow)    


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

def reloadBufferCommand():
    global reloadLineBuffer
    reloadLineBuffer = True

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

reloadBufferButton = tk.Button(topFrame,text="Reload buffer", command=reloadBufferCommand, width=10)
reloadBufferButton.pack(side=tk.LEFT)

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

for key,val in textColorMap.items():
    T.tag_configure(key, foreground=val)

T.tag_configure(CONNECT_COLOR_TAG, background=connectLineBackgroundColor, selectbackground=connectLineSelectBackgroundColor)
T.tag_configure(DISCONNECT_COLOR_TAG, background=disconnectLineBackgroundColor, selectbackground=disconnectLineSelectBackgroundColor)

middleFrame.pack(side=tk.TOP, fill=tk.BOTH, expand = tk.YES)

# def addDisconnectLine():

#     timestamp = datetime.datetime.now()
#     timeString = timeStampBracket[0] + timestamp.strftime("%H:%M:%S") + timeStampBracket[1]
    
#     T.config(state=tk.NORMAL)
#     insertLine(timeString + disconnectLineText + lastLogFileInfo + "\n")
#     T.config(state=tk.DISABLED)

#     lastline = T.index("end-2c").split(".")[0]
#     T.tag_add(DISCONNECT_COLOR_TAG,lastline + ".0","end-1c")
#     # T.tag_add(DISCONNECT_COLOR_TAG,lastline + ".0",lastline + ".0+1l")

#     updateWindowBufferLineCount()

    

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
# Reader worker

def readerWorker():

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
                        processQueue.put(inLine)                         

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



################################
# Process worker

def processWorker():

    # Create connect line
    timestamp = datetime.datetime.now()
    timeString = timeStampBracket[0] + timestamp.strftime("%H:%M:%S") + timeStampBracket[1]
    connectLine = timeString + connectLineText
    highlightQueue.put(connectLine)

    lastTimestamp = 0

    while processFlag:
        try:
            line = processQueue.get(True,0.2)
            processQueue.task_done()

            # Timestamp
            micros = int(line.timestamp.microsecond/1000)
            timeString = timeStampBracket[0] + line.timestamp.strftime("%H:%M:%S") + "." + '{:03d}'.format(micros) + timeStampBracket[1]

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
            
            timeDeltaString = timeDeltaBracket[0] + hourstring + minutstring + secondstring + timeDeltaBracket[1]

            lastTimestamp = line.timestamp

            # Replace newline
            newData = line.data.rstrip() + "\n"
            
            # Construct newLine string
            newLine = timeString + " " + timeDeltaString + " " + newData

            highlightQueue.put(newLine)
            logQueue.put(newLine)
            
        except queue.Empty:
            pass




################################
# Highlight worker

def locateLineTags(line):
    # Locate highlights
    highlights = list()
    for keys in textColorMap:
        match = re.search(keys,line)                
        if match:
            highlights.append((keys,match.start(),match.end())) 


    match = re.search(connectLineRegex,line)
    if match:  
        highlights.append((CONNECT_COLOR_TAG,"0","0+1l"))

    match = re.search(disconnectLineRegex,line)
    if match:  
        highlights.append((DISCONNECT_COLOR_TAG,"0","0+1l"))

    return highlights


def addToLineBuffer(rawline):

    global lineBuffer

    lineBufferSize = len(lineBuffer)

    lineBuffer.append(rawline)

    if lineBufferSize > maxLineBuffer:
        lineBuffer[0].remove()

def highlightWorker():
    
    global reloadLineBuffer
    global guiBuffer
    global reloadGuiBuffer

    while highlightFlag:

        if reloadLineBuffer:
            reloadLineBuffer = False

            TraceLog(logLevel.INFO, "Reload line buffer")

            guiBuffer.clear()

            for line in lineBuffer:
                match = re.search(".*Main::.*",line)                
                if not match:                        
                    lineTags = locateLineTags(line)                        
                    pLine = printLine(line,lineTags)
                    guiBuffer.append(pLine)

            reloadGuiBuffer = True 

        try:
            newLine = highlightQueue.get(True,0.2)
            highlightQueue.task_done()

            addToLineBuffer(newLine)

            lineTags = locateLineTags(newLine)                
            pLine = printLine(newLine,lineTags)                
            guiQueue.put(pLine)

        except queue.Empty:
            pass

################################
# Log writer worker

def logWriterWorker():

    timestamp = datetime.datetime.now().strftime(logFileTimestamp)

    filename = logFileBaseName + timestamp + ".txt"
    fullFilename = os.path.join(logFilePath,filename)

    os.makedirs(os.path.dirname(fullFilename), exist_ok=True)

    statLabel3.config(text="Saving to log file: " + filename, fg="black")

    global linesInLogFile
    linesInLogFile = 0

    with open(fullFilename,"a") as file:
        while logFlag:            
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

################################
# GUI worker

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
    global reloadGuiBuffer

    try:     
        # Open text widget for editing
        T.config(state=tk.NORMAL)

        if reloadGuiBuffer:
            reloadGuiBuffer = False            

            TraceLog(logLevel.INFO,"Reload GUI buffer")
            # Clear window
            T.delete(1.0,tk.END)

            for pLine in guiBuffer:
                insertLine(pLine.line)

                # Highlight/color text
                lastline = T.index("end-2c").split(".")[0]
            
                for lineTag in pLine.lineTags:
                    T.tag_add(lineTag[0],lastline + "." + str(lineTag[1]),lastline + "." + str(lineTag[2]))

        # If many lines are available, add them X at a time, to avoid locking the UI for too long
        for i in range(100):

            msg = guiQueue.get_nowait()
            guiQueue.task_done()
            
            insertLine(msg.line)

            # Highlight/color text
            lastline = T.index("end-2c").split(".")[0]
        
            for lineTag in msg.lineTags:
                T.tag_add(lineTag[0],lastline + "." + str(lineTag[1]),lastline + "." + str(lineTag[2]))

            
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

highlightThread = threading.Thread(target=highlightWorker,daemon=True,name="Highlight")
highlightThread.start()



root.after(50,waitForInput)


TraceLog(logLevel.INFO,"Main loop started")

root.mainloop()

TraceLog(logLevel.INFO,"Main loop done")


