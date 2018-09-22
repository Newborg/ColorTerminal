
import os

import json

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
# Constants

SETTINGS_FILE_NAME = "CTsettings.json"

################################
# Trace

class LogLevel(Enum):
    ERROR = 0
    WARNING = 1
    INFO = 2
    DEBUG = 3

def traceLog(level,msg):
    # timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    timestamp = datetime.datetime.now()
    micros = int(timestamp.microsecond/1000)
    timeString = timestamp.strftime("%H:%M:%S") + "." + '{:03d}'.format(micros)

    print(timeString + " [" + level.name + "] " + msg)

################################
# Settings

class Sets:

    DEFAULT_WINDOW_SIZE         = "defaultWindowSize"

    BACKGROUND_COLOR            = "backgroundColor"
    SELECT_BACKGROUND_COLOR     = "selectBackgroundColor"
    TEXT_COLOR                  = "textColor"
    FONT_FAMILY                 = "fontFamily"
    FONT_SIZE                   = "fontSize"
    MAX_LINE_BUFFER             = "maxLineBuffer"

    LOG_FILE_PATH               = "logFilePath"
    LOG_FILE_BASE_NAME          = "logFileBaseName"
    LOG_FILE_TIMESTAMP          = "logFileTimestamp"

    TEXT_COLOR_MAP              = "textColorMap"

    def __init__(self,jsonFileName):
        self.jsonFileName = jsonFileName
        self.settings = dict()

    def reload(self):

        settingsJson = dict()

        try:
            with open(self.jsonFileName,"r") as jsonFile:
                settingsJson = json.load(jsonFile)
        except FileNotFoundError:
            traceLog(LogLevel.WARNING,"Settings file not found. Using default values")
            pass

        # Main Window
        self.settings[self.DEFAULT_WINDOW_SIZE]     = settingsJson.get("MainWindow",{}).get("defaultWindowSize","1100x600") # px

        # Text Area
        self.settings[self.BACKGROUND_COLOR]        = settingsJson.get("TextArea",{}).get("backgroundColor","#F3F3F3") # Testing color
        self.settings[self.SELECT_BACKGROUND_COLOR] = settingsJson.get("TextArea",{}).get("selectBackgroundColor","#303030")
        self.settings[self.TEXT_COLOR]              = settingsJson.get("TextArea",{}).get("textColor","#FFFFFF")
        self.settings[self.FONT_FAMILY]             = settingsJson.get("TextArea",{}).get("fontFamily","Consolas")
        self.settings[self.FONT_SIZE]               = settingsJson.get("TextArea",{}).get("fontSize",10)
        self.settings[self.MAX_LINE_BUFFER]         = settingsJson.get("TextArea",{}).get("maxLineBuffer",4000)

        # Log File
        self.settings[self.LOG_FILE_PATH]           = settingsJson.get("LogFile",{}).get("logFilePath","Logs")
        self.settings[self.LOG_FILE_BASE_NAME]      = settingsJson.get("LogFile",{}).get("logFileBaseName","SerialLog_")
        self.settings[self.LOG_FILE_TIMESTAMP]      = settingsJson.get("LogFile",{}).get("logFileTimestamp","%Y.%m.%d_%H.%M.%S")

        # Text Color Map
        self.settings[self.TEXT_COLOR_MAP]          = settingsJson.get("TextColoring",{})



    def get(self,option):
        # No keycheck, should fail if wrong key
        return self.settings[option]
        

settings_ = Sets(SETTINGS_FILE_NAME)

settings_.reload()

# Time Stamp
timeStampBracket = ["[","]"]
timeDeltaBracket = ["(",")"]
timeStampRegex = "\\" + timeStampBracket[0] + ".{12}\\" + timeStampBracket[1] + " \\" + timeDeltaBracket[0] + ".{6,12}\\" + timeDeltaBracket[1]

# Other Colors
statusConnectBackgroundColor = "#008800"
statusWorkingBackgroundColor = "gray"
statusDisconnectBackgroundColor = "#CC0000"
statusTextColor = "white"

# Connect Status Lines
connectLineText = " Connected to port\n"
connectLineRegex = "\\" + timeStampBracket[0] + ".{8}\\" + timeStampBracket[1] + connectLineText
connectLineBackgroundColor = "#008800"
connectLineSelectBackgroundColor = "#084C08"

disconnectLineText = " Disconnected from port. Log file "
disconnectLineRegex = "\\" + timeStampBracket[0] + ".{8}\\" + timeStampBracket[1] + disconnectLineText
disconnectLineBackgroundColor = "#880000"
disconnectLineSelectBackgroundColor = "#4C0808"

# Hide line
hideLineFontColor = "#808080"

# Line/text coloring
textColorMap = settings_.get(Sets.TEXT_COLOR_MAP)

# Good colors
# Green: #00E000 (limit use)
# Red: #FF8080
# Blue: #00D0D0
# Yellow: #CCDF32
# Orange: #EFC090
# Purple: #79ABFF


################################
# Custom types

class ConnectState(Enum):
    CONNECTED = 1
    DISCONNECTED = 0

class SerialLine:        
    def __init__(self, data, timestamp):
        self.data = data
        self.timestamp = timestamp
        
class PrintLine:        
    def __init__(self, line, lineTags, updatePreviousLine = False):
        self.line = line
        self.lineTags = lineTags
        self.updatePreviousLine = updatePreviousLine     

NO_SERIAL_PORT = "None"

CONNECT_COLOR_TAG = "CONNECT_COLOR_TAG"
DISCONNECT_COLOR_TAG = "DISCONNECT_COLOR_TAG"
HIDELINE_COLOR_TAG = "HIDELINE_COLOR_TAG"

################################
# Flags, counters and queues

readFlag_ = 1
processFlag_ = 1
logFlag_ = 1

highlightFlag_ = 1
updateGuiFlag_ = 1

appState_ = ConnectState.DISCONNECTED

closeProgram_ = False

endLine_ = 1

processQueue_ = queue.Queue()
highlightQueue_ = queue.Queue()
logQueue_ = queue.Queue()
guiQueue_ = queue.Queue()

# Buffer from raw line input (input for process worker)
lineBuffer_ = list()
reloadLineBuffer_ = False
reloadGuiBuffer_ = False

hideLines_ = False

linesInLogFile_ = 0
lastLogFileInfo_ = ""

################################################################
################################################################
# 
# 
# 
# TKINTER GUI ELEMENTS
# 
# 
# 
################################################################
################################################################

################################
# Root frame

root = tk.Tk()

def on_closing():
    if messagebox.askokcancel("Quit", "Do you want to quit?"):        
        global closeProgram_
        closeProgram_ = True
        disconnectSerial()

def destroyWindow():    
    traceLog(LogLevel.INFO,"Closing main window")
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

root.title("Color Terminal")
root.geometry(settings_.get(Sets.DEFAULT_WINDOW_SIZE))


################################
# Status frame

def connectSerial():    

    traceLog(LogLevel.INFO,"Connect to serial")

    global readFlag_        
    readFlag_ = 1
    global processFlag_
    processFlag_ = 1
    global logFlag_
    logFlag_ = 1
    
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
    traceLog(LogLevel.INFO,"Disconnect from serial")
    
    global appState_

    # Stop serial reader
    global readFlag_        
    readFlag_ = 0        
    if readerThread.isAlive():
        readerThread.join()

    # Empty process queue and stop process thread       
    processQueue_.join()
    global processFlag_
    processFlag_ = 0      
    if processThread.isAlive(): 
        processThread.join()

    # Empty log queue and stop log writer thread   
    logQueue_.join()
    global logFlag_
    logFlag_ = 0     
    if logThread.isAlive():
        logThread.join()

    # Add disconnect line if connected     
    if appState_ == ConnectState.CONNECTED:
        timestamp = datetime.datetime.now()
        timeString = timeStampBracket[0] + timestamp.strftime("%H:%M:%S") + timeStampBracket[1]
        
        disconnectLine = timeString + disconnectLineText + lastLogFileInfo_ + "\n"    

        highlightQueue_.put(disconnectLine)

    traceLog(LogLevel.INFO,"Main worker threads stopped")
    
    setStatusLabel("DISCONNECTED",statusDisconnectBackgroundColor)
    
    appState_ = ConnectState.DISCONNECTED

    if closeProgram_:

        # Empty highlight queue and stop highlight thread   
        highlightQueue_.join()
        global highlightFlag_
        highlightFlag_ = 0 
        if highlightThread.isAlive():
            highlightThread.join()

        # Empty gui queue and stop GUI update loop
        guiQueue_.join()
        global updateGuiFlag_
        updateGuiFlag_ = 0

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
            traceLog(LogLevel.DEBUG,"scanSerialPorts: " + comPort.device + " already open")            

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

    if state == ConnectState.CONNECTED:        
        connectButton.config(text="Disconnect")
        connectSerial()        
        setStatusLabel("CONNECTING...",statusWorkingBackgroundColor)

    elif state == ConnectState.DISCONNECTED:        
        connectButton.config(text="Connect")
        disconnectSerial()        
        setStatusLabel("DISCONNECTING...",statusWorkingBackgroundColor)

# Button Commands

def connectButtonCommand():
    
    if appState_ == ConnectState.DISCONNECTED:
        # Connect to serial
        setAppState(ConnectState.CONNECTED)

    elif appState_ == ConnectState.CONNECTED:
        # Close down reader
        setAppState(ConnectState.DISCONNECTED)


def goToEndButtonCommand():
    T.see(tk.END)

def clearButtonCommand():
    global lineBuffer_
    lineBuffer_.clear()

    T.config(state=tk.NORMAL)
    T.delete(1.0,tk.END)
    T.config(state=tk.DISABLED)

def updateSerialPortSelect(*args):
    if serialPortVar.get() == NO_SERIAL_PORT:        
        serialPortLabel.config(text=NO_SERIAL_PORT)
    else:
        serialPortLabel.config(text=serialPorts[serialPortVar.get()])

def reloadBufferCommand():
    global reloadLineBuffer_
    reloadLineBuffer_ = True

def hideLinesCommand():
    global hideLines_
    if hideLines_:
        hideLines_ = False
    else:
        hideLines_ = True

    reloadBufferCommand()


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

hideLinesButton = tk.Button(topFrame,text="Hide Lines", command=hideLinesCommand, width=10)
hideLinesButton.pack(side=tk.LEFT)

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
if not settings_.get(Sets.FONT_FAMILY) in fontList:
    traceLog(LogLevel.WARNING,"Font \"" + settings_.get(Sets.FONT_FAMILY) + "\" not found in system")

tFont = Font(family=settings_.get(Sets.FONT_FAMILY), size=settings_.get(Sets.FONT_SIZE))

T = tk.Text(middleFrame, height=1, width=1, background=settings_.get(Sets.BACKGROUND_COLOR),\
            selectbackground=settings_.get(Sets.SELECT_BACKGROUND_COLOR),\
            foreground=settings_.get(Sets.TEXT_COLOR), font=tFont)

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
T.tag_configure(HIDELINE_COLOR_TAG, foreground=hideLineFontColor)

middleFrame.pack(side=tk.TOP, fill=tk.BOTH, expand = tk.YES)
   

################################
# Bottom frame

bottomFrame = tk.Frame(root)

statLabel1 = tk.Label(bottomFrame,text="Window line buffer 0/" + str(settings_.get(Sets.MAX_LINE_BUFFER)), width=30, anchor=tk.W)
statLabel1.pack(side=tk.LEFT)

statLabel2 = tk.Label(bottomFrame,text="", width=30, anchor=tk.W)
statLabel2.pack(side=tk.LEFT)

statLabel3 = tk.Label(bottomFrame,text="", width=60, anchor=tk.E)
statLabel3.pack(side=tk.RIGHT,padx=(0,18))

bottomFrame.pack(side=tk.BOTTOM, fill=tk.X)

def updateWindowBufferLineCount():
    statLabel1.config(text="Window line buffer " + str(endLine_-1) + "/" + str(settings_.get(Sets.MAX_LINE_BUFFER)))




################################################################
################################################################
# 
# 
# 
# WORKERS
# 
# 
# 
################################################################
################################################################

################################
# Reader worker

def readerWorker():

    try:
        with serial.Serial(serialPortVar.get(), 115200, timeout=2) as ser:
            
            # TODO should be done in GUI thread
            setStatusLabel("CONNECTED to " + str(ser.name),statusConnectBackgroundColor)         
            global appState_
            appState_ = ConnectState.CONNECTED

            try:
                while readFlag_:                
                    
                    line = ser.readline()
                    timestamp = datetime.datetime.now()

                    if line:     
                        inLine = SerialLine(line.decode("utf-8"),timestamp)
                        processQueue_.put(inLine)                         

            except serial.SerialException as e:
                traceLog(LogLevel.ERROR,"Serial read error: " + str(e))
                # Change program state to disconnected                
                root.after(10,setAppState,ConnectState.DISCONNECTED)

    except serial.SerialException as e:        
        traceLog(LogLevel.ERROR,str(e))
        # In case other threads are still starting up,
        # wait for 2 sec        
        # Then change program state to disconnected                
        root.after(2000,setAppState,ConnectState.DISCONNECTED)



################################
# Process worker

def processWorker():

    # Create connect line
    timestamp = datetime.datetime.now()
    timeString = timeStampBracket[0] + timestamp.strftime("%H:%M:%S") + timeStampBracket[1]
    connectLine = timeString + connectLineText
    highlightQueue_.put(connectLine)

    lastTimestamp = 0

    while processFlag_:
        try:
            line = processQueue_.get(True,0.2)
            processQueue_.task_done()

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

            highlightQueue_.put(newLine)
            logQueue_.put(newLine)
            
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

def hideLineColorTags(line):
    highlights = list()
    highlights.append((HIDELINE_COLOR_TAG,"0","0+1l"))
    return highlights

def addToLineBuffer(rawline):

    global lineBuffer_

    lineBufferSize = len(lineBuffer_)

    lineBuffer_.append(rawline)

    if lineBufferSize > settings_.get(Sets.MAX_LINE_BUFFER):
        del lineBuffer_[0]


consecutiveLinesHidden_ = 0
hideLineMap = list()
hideLineMap.append("GUI::.*")
hideLineMap.append("Main::.*")

def hideLines(line):

    global consecutiveLinesHidden_

    if hideLines_:
        tempConsecutiveLinesHidden = 0

        for keys in hideLineMap:
            match = re.search(keys,line)                
            if match:
                tempConsecutiveLinesHidden = 1
                break
        
        if tempConsecutiveLinesHidden == 1:
            consecutiveLinesHidden_ += 1
        else:
            consecutiveLinesHidden_ = 0
    else:
        consecutiveLinesHidden_ = 0

    return consecutiveLinesHidden_

def getTimeStamp(line):

    # This is based on the settings of ColorTerminal
    # If you load a log file from another program, this might not work

    match = re.search(timeStampRegex,line)
    if match:
        return match.group(0)
    else:
        return ""
    
def highlightWorker():
    
    global reloadLineBuffer_    
    global reloadGuiBuffer_

    while highlightFlag_:

        newLine = ""

        try:
            newLine = highlightQueue_.get(True,0.2)
            highlightQueue_.task_done()

        except queue.Empty:
            pass

        if newLine or reloadLineBuffer_:
            
            if newLine:
                addToLineBuffer(newLine)
            
            linesToProcess = list()

            if reloadLineBuffer_:
                # Wait for gui queue to be empty, 
                # otherwise some lines can be lost, when GUI is cleared
                guiQueue_.join()                
                linesToProcess = lineBuffer_
                traceLog(LogLevel.DEBUG, "Reload Line Buffer")

            else:
                linesToProcess.append(newLine)
            
            for line in linesToProcess:

                consecutiveLinesHidden = hideLines(line)
                if consecutiveLinesHidden == 0:
                    lineTags = locateLineTags(line)                
                    pLine = PrintLine(line,lineTags)  
                else:
                    hideInfoLine = getTimeStamp(line) + " Lines hidden: " + str(consecutiveLinesHidden) + "\n"
                    lineTags = hideLineColorTags(hideInfoLine)
                    if consecutiveLinesHidden > 1: 
                        pLine = PrintLine(hideInfoLine,lineTags,True)  
                    else:
                        pLine = PrintLine(hideInfoLine,lineTags,False)  

                guiQueue_.put(pLine)   
            
            

            if reloadLineBuffer_:  
                reloadLineBuffer_ = False
                reloadGuiBuffer_ = True
                # Wait for gui to have processed new buffer
                guiQueue_.join()   
                


################################
# Log writer worker

def logWriterWorker():

    timestamp = datetime.datetime.now().strftime(settings_.get(Sets.LOG_FILE_TIMESTAMP))

    filename = settings_.get(Sets.LOG_FILE_BASE_NAME) + timestamp + ".txt"
    fullFilename = os.path.join(settings_.get(Sets.LOG_FILE_PATH),filename)

    os.makedirs(os.path.dirname(fullFilename), exist_ok=True)

    # TODO: Do not update UI from this thread
    statLabel3.config(text="Saving to log file: " + filename, fg="black")

    global linesInLogFile_
    linesInLogFile_ = 0

    with open(fullFilename,"a") as file:
        while logFlag_:            
            try:
                logLine = logQueue_.get(True,0.2)  
                logQueue_.task_done()              
                file.write(logLine)
                linesInLogFile_ += 1                       
            except queue.Empty:
                pass
            

    filesize = os.path.getsize(fullFilename)

    global lastLogFileInfo_    
    lastLogFileInfo_ = filename + " (Size " + "{:.3f}".format(filesize/1024) + "KB)"

    statLabel3.config(text="Log file saved: " + lastLogFileInfo_, fg="green")

################################
# GUI worker

def insertLine(newLine):

    global endLine_

    # Control window scolling
    bottomVisibleLine = int(T.index("@0,%d" % T.winfo_height()).split(".")[0])
    endLine_ = int(T.index(tk.END).split(".")[0])
    T.insert(tk.END, newLine)
    if (bottomVisibleLine >= (endLine_-1)):
        T.see(tk.END)

    # Limit number of lines in window
    if endLine_ > settings_.get(Sets.MAX_LINE_BUFFER):
        T.delete(1.0,2.0)

def updateLastLine(newLine):
    lastline = T.index("end-2c").split(".")[0]    
    T.delete(lastline + ".0",lastline +".0+1l")     
    T.insert(lastline + ".0", newLine)
    # I don't think there is a need for scrolling?
    

def updateGUI():

    global endLine_    
    global reloadGuiBuffer_
    
    receivedLines = list()

    try:     
        # We have to make sure that the queue is empty before continuing
        while True:            
            receivedLines.append(guiQueue_.get_nowait())
            guiQueue_.task_done()            
            
    except queue.Empty:

        # Open text widget for editing
        T.config(state=tk.NORMAL)
        
        if reloadGuiBuffer_:            
            traceLog(LogLevel.DEBUG,"Reload GUI buffer")              
            reloadGuiBuffer_ = False  
            
            # Clear window
            T.delete(1.0,tk.END)

        for msg in receivedLines:
            if msg.updatePreviousLine:
                updateLastLine(msg.line)
            else:              
                insertLine(msg.line)

            # Highlight/color text
            lastline = T.index("end-2c").split(".")[0]
            for lineTag in msg.lineTags:
                T.tag_add(lineTag[0],lastline + "." + str(lineTag[1]),lastline + "." + str(lineTag[2]))

        # Disable text widget edit
        T.config(state=tk.DISABLED)

    updateWindowBufferLineCount()
    statLabel2.config(text="Lines in log file " + str(linesInLogFile_))

def waitForInput():
    if updateGuiFlag_:
        updateGUI()
        root.after(100,waitForInput)





################################################################
################################################################
# 
# 
# 
# MAIN LOOP
# 
# 
# 
################################################################
################################################################

readerThread = threading.Thread()
processThread = threading.Thread()
logThread = threading.Thread()

highlightThread = threading.Thread(target=highlightWorker,daemon=True,name="Highlight")
highlightThread.start()

root.after(50,waitForInput)

class optionsView:

    def __init__(self,root):
        self.root = root

    def show(self):
        print("hello")

# def down(e):
#     print("DOWN: " + e.char)
#     if e.char == 'n':
#         testing = optionsView(root)
#         testing.show()
#         # optionsView = tk.Toplevel(root)
#         # optionsView.title("Options View")
#         # l = tk.Label(optionsView,text="HELLOOO")
#         # l.pack()

# def up(e):
#     print("UP: " + e.char)

# root.bind('<KeyPress>', down)
# root.bind('<KeyRelease>', up)






traceLog(LogLevel.INFO,"Main loop started")

root.mainloop()

traceLog(LogLevel.INFO,"Main loop done")


