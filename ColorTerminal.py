
import os

import json

from enum import Enum

import tkinter as tk
from tkinter import messagebox
from tkinter.font import Font
from tkinter.colorchooser import askcolor

from functools import partial

import serial
import serial.tools.list_ports

import time
import datetime

import threading
import queue

import re

################################
# Constants

SETTINGS_FILE_NAME_ = "CTsettings.json"

################################
# Trace

class LogLevel(Enum):
    ERROR = 0
    WARNING = 1
    INFO = 2
    DEBUG = 3

def traceLog(level,msg):    
    timestamp = datetime.datetime.now()
    micros = int(timestamp.microsecond/1000)
    timeString = timestamp.strftime("%H:%M:%S") + "." + '{:03d}'.format(micros)

    print(timeString + " [" + level.name + "] " + msg)

################################
# Settings

class Sets:

    DEFAULT_WINDOW_SIZE         = "MainWindow_defaultWindowSize"    
    
    BACKGROUND_COLOR            = "TextArea_backgroundColor"
    SELECT_BACKGROUND_COLOR     = "TextArea_selectBackgroundColor"
    TEXT_COLOR                  = "TextArea_textColor"
    FONT_FAMILY                 = "TextArea_fontFamily"
    FONT_SIZE                   = "TextArea_fontSize"
    MAX_LINE_BUFFER             = "TextArea_maxLineBuffer"

    LOG_FILE_PATH               = "LogFile_logFilePath"
    LOG_FILE_BASE_NAME          = "LogFile_logFileBaseName"
    LOG_FILE_TIMESTAMP          = "LogFile_logFileTimestamp"

    LINE_COLOR_MAP              = "LineColorMap"

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
        self.settings[self.DEFAULT_WINDOW_SIZE]     = settingsJson.get(self.DEFAULT_WINDOW_SIZE,"1100x600")

        # Text Area                
        self.settings[self.BACKGROUND_COLOR]        = settingsJson.get(self.BACKGROUND_COLOR,"#000000")        
        self.settings[self.SELECT_BACKGROUND_COLOR] = settingsJson.get(self.SELECT_BACKGROUND_COLOR,"#303030")
        self.settings[self.TEXT_COLOR]              = settingsJson.get(self.TEXT_COLOR,"#FFFFFF")
        self.settings[self.FONT_FAMILY]             = settingsJson.get(self.FONT_FAMILY,"Consolas")
        self.settings[self.FONT_SIZE]               = settingsJson.get(self.FONT_SIZE,10)
        self.settings[self.MAX_LINE_BUFFER]         = settingsJson.get(self.MAX_LINE_BUFFER,4000)

        # Log File
        self.settings[self.LOG_FILE_PATH]           = settingsJson.get(self.LOG_FILE_PATH,"Logs")
        self.settings[self.LOG_FILE_BASE_NAME]      = settingsJson.get(self.LOG_FILE_BASE_NAME,"SerialLog_")
        self.settings[self.LOG_FILE_TIMESTAMP]      = settingsJson.get(self.LOG_FILE_TIMESTAMP,"%Y.%m.%d_%H.%M.%S")

        # Line Color Map
        self.settings[self.LINE_COLOR_MAP]          = settingsJson.get(self.LINE_COLOR_MAP,{})

        try:
            with open(self.jsonFileName,"w") as jsonFile:
                json.dump(self.settings,jsonFile,indent=4)
        except:
            traceLog(LogLevel.WARNING,"Error updating settings file")
            pass

    
    def get(self,option):
        # No keycheck, should fail if wrong key
        return self.settings[option]
        
    def setOption(self,option,value):
        
        self.settings[option] = value

        # print("Saving option " + str(option) + " with value " + str(value))

        try:
            with open(self.jsonFileName,"w") as jsonFile:
                json.dump(self.settings,jsonFile,indent=4)
        except FileNotFoundError:
            traceLog(LogLevel.WARNING,"Settings file not found. Not able to save setting")
            pass

    # Static for now

    # Time Stamp
    timeStampBracket = ["[","]"]
    timeDeltaBracket = ["(",")"]
    timeStampRegex = "\\" + timeStampBracket[0] + ".{12}\\" + timeStampBracket[1] + " \\" + timeDeltaBracket[0] + ".{6,12}\\" + timeDeltaBracket[1]

    # Other Colors
    STATUS_CONNECT_BACKGROUND_COLOR = "#008800"    
    STATUS_WORKING_BACKGROUND_COLOR = "gray"    
    STATUS_DISCONNECT_BACKGROUND_COLOR = "#CC0000"
    STATUS_TEXT_COLOR = "white"

    # Connect Status Lines
    CONNECT_LINE_TEXT = " Connected to port\n"
    connectLineRegex = "\\" + timeStampBracket[0] + ".{8}\\" + timeStampBracket[1] + CONNECT_LINE_TEXT
    CONNECT_LINE_BACKGROUND_COLOR = "#008800"
    CONNECT_LINE_SELECT_BACKGROUND_COLOR = "#084C08"

    disconnectLineText = " Disconnected from port. Log file "
    disconnectLineRegex = "\\" + timeStampBracket[0] + ".{8}\\" + timeStampBracket[1] + disconnectLineText
    DISCONNECT_LINE_BACKGROUND_COLOR = "#880000"
    DISCONNECT_LINE_SELECT_BACKGROUND_COLOR = "#4C0808"

    CONNECT_COLOR_TAG = "CONNECT_COLOR_TAG"
    DISCONNECT_COLOR_TAG = "DISCONNECT_COLOR_TAG"    

    # Hide line
    HIDE_LINE_FONT_COLOR = "#808080"
    HIDELINE_COLOR_TAG = "HIDELINE_COLOR_TAG"


settings_ = Sets(SETTINGS_FILE_NAME_)

settings_.reload()

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

NO_SERIAL_PORT_ = "None"

################################
# Flags, counters and queues

readFlag_ = 1
processFlag_ = 1
logFlag_ = 1

updateGuiFlag_ = 1
updateGuiJob_ = None

appState_ = ConnectState.DISCONNECTED

closeProgram_ = False

endLine_ = 1

processQueue_ = queue.Queue()
logQueue_ = queue.Queue()
guiQueue_ = queue.Queue()

reloadGuiBuffer_ = False

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
        timeString = Sets.timeStampBracket[0] + timestamp.strftime("%H:%M:%S") + Sets.timeStampBracket[1]
        
        disconnectLine = timeString + Sets.disconnectLineText + lastLogFileInfo_ + "\n"    
        
        highlightWorker_.highlightQueue.put(disconnectLine)
        # highlightQueue_.put(disconnectLine)

    traceLog(LogLevel.INFO,"Main worker threads stopped")
    
    setStatusLabel("DISCONNECTED",Sets.STATUS_DISCONNECT_BACKGROUND_COLOR)
    
    appState_ = ConnectState.DISCONNECTED

    if closeProgram_:

        highlightWorker_.stopWorker(emptyQueue=False)
                
        stopGuiWorker()

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

    global serialPorts_
    serialPorts_ = scanSerialPorts()

    if serialPorts_:
        serialPortList_.clear()
        serialPortList_.extend(sorted(list(serialPorts_.keys())))
        serialPortVar_.set(serialPortList_[0])
        serialPortVar_.trace("w",updateSerialPortSelect)

        # Delete options
        serialPortOption_["menu"].delete(0,"end")        

        # Add new options
        for port in serialPortList_:
            serialPortOption_["menu"].add_command(label=port, command=tk._setit(serialPortVar_,port))

        serialPortOption_.config(state=tk.NORMAL)
        serialPortLabel_.config(text=serialPorts_[serialPortVar_.get()])

        connectButton_.config(state=tk.NORMAL)
        
    else:
        serialPortVar_.set(NO_SERIAL_PORT_)
        serialPortLabel_.config(text="No serial port found")
        serialPortOption_.config(state=tk.DISABLED)
        connectButton_.config(state=tk.DISABLED)



def setAppState(state):

    if state == ConnectState.CONNECTED:        
        connectButton_.config(text="Disconnect")
        connectSerial()        
        setStatusLabel("CONNECTING...",Sets.STATUS_WORKING_BACKGROUND_COLOR)

    elif state == ConnectState.DISCONNECTED:        
        connectButton_.config(text="Connect")
        disconnectSerial()        
        setStatusLabel("DISCONNECTING...",Sets.STATUS_WORKING_BACKGROUND_COLOR)

# Button Commands

def connectButtonCommand():
    
    if appState_ == ConnectState.DISCONNECTED:
        # Connect to serial
        setAppState(ConnectState.CONNECTED)

    elif appState_ == ConnectState.CONNECTED:
        # Close down reader
        setAppState(ConnectState.DISCONNECTED)


def goToEndButtonCommand():
    T_.see(tk.END)

def clearButtonCommand():    
    highlightWorker_.clearLineBuffer()

    T_.config(state=tk.NORMAL)
    T_.delete(1.0,tk.END)
    T_.config(state=tk.DISABLED)

    updateWindowBufferLineCount(0)

def updateSerialPortSelect(*args):
    if serialPortVar_.get() == NO_SERIAL_PORT_:        
        serialPortLabel_.config(text=NO_SERIAL_PORT_)
    else:
        serialPortLabel_.config(text=serialPorts_[serialPortVar_.get()])

def reloadBufferCommand():    
    highlightWorker_.reloadLineBuffer()

def hideLinesCommand():    
    highlightWorker_.toggleHideLines()
    reloadBufferCommand()

def showOptionsView():
    optionsView_.show(highlightWorker_.getLineColorMap())

def setStatusLabel(labelText, bgColor):
    statusLabel_.config(text=labelText, bg=bgColor)
    statusLabelHeader_.config(bg=bgColor)

topFrame_ = tk.Frame(root)

statusLabel_ = tk.Label(topFrame_,text="DISCONNECTED", width=20, anchor=tk.W, fg=Sets.STATUS_TEXT_COLOR, bg=Sets.STATUS_DISCONNECT_BACKGROUND_COLOR)
statusLabel_.pack(side=tk.RIGHT,padx=(0,18))

statusLabelHeader_ = tk.Label(topFrame_,text="   Status:", anchor=tk.W, fg=Sets.STATUS_TEXT_COLOR, bg=Sets.STATUS_DISCONNECT_BACKGROUND_COLOR)
statusLabelHeader_.pack(side=tk.RIGHT)

connectButton_ = tk.Button(topFrame_,text="Connect", command=connectButtonCommand, width=10)
connectButton_.pack(side=tk.LEFT)

goToEndButton_ = tk.Button(topFrame_,text="Go to end", command=goToEndButtonCommand, width=10)
goToEndButton_.pack(side=tk.LEFT)

# reloadBufferButton_ = tk.Button(topFrame_,text="Reload buffer", command=reloadBufferCommand, width=10)
# reloadBufferButton_.pack(side=tk.LEFT)

# hideLinesButton_ = tk.Button(topFrame_,text="Hide Lines", command=hideLinesCommand, width=10)
# hideLinesButton_.pack(side=tk.LEFT)

clearButton_ = tk.Button(topFrame_,text="Clear", command=clearButtonCommand, width=10)
clearButton_.pack(side=tk.LEFT,padx=(0,40))

optionsButton_ = tk.Button(topFrame_,text="Options", command=showOptionsView, width=10)
optionsButton_.pack(side=tk.LEFT,padx=(0,40))

serialPortReloadButton_ = tk.Button(topFrame_,text="Reload ports", command=reloadSerialPorts, width=10)
serialPortReloadButton_.pack(side=tk.LEFT)

serialPortVar_ = tk.StringVar(topFrame_)
serialPortList_ = [""]
serialPortOption_ = tk.OptionMenu(topFrame_,serialPortVar_,*serialPortList_)
serialPortOption_.pack(side=tk.LEFT)

serialPortLabel_ = tk.Label(topFrame_,text="", anchor=tk.W)
serialPortLabel_.pack(side=tk.LEFT)

topFrame_.pack(side=tk.TOP, fill=tk.X)

serialPorts_ = dict()
reloadSerialPorts()

################################
# Text frame (main window)

def textFrameClearTags(tagNames):
    # clear existing tags
    for tagName in tagNames:        
        T_.tag_delete(tagName)



def createTextFrameLineColorTag():
    lineColorMap = highlightWorker_.getLineColorMap()

    for key in sorted(lineColorMap.keys()):      
        T_.tag_configure(key, foreground=lineColorMap[key]["color"])

def reloadLineColorMapAndTags():
    
    lineColorMapKeys = highlightWorker_.getLineColorMap().keys()
    textFrameClearTags(lineColorMapKeys)

    highlightWorker_.reloadLineColorMap()

    createTextFrameLineColorTag()


def reloadTextFrame():

    traceLog(LogLevel.DEBUG,"Reload text frame")

    tFont = Font(family=settings_.get(Sets.FONT_FAMILY), size=settings_.get(Sets.FONT_SIZE))

    T_.config(background=settings_.get(Sets.BACKGROUND_COLOR),\
             selectbackground=settings_.get(Sets.SELECT_BACKGROUND_COLOR),\
             foreground=settings_.get(Sets.TEXT_COLOR), font=tFont)


middleFrame_ = tk.Frame(root)

fontList_ = tk.font.families()
if not settings_.get(Sets.FONT_FAMILY) in fontList_:
    traceLog(LogLevel.WARNING,"Font \"" + settings_.get(Sets.FONT_FAMILY) + "\" not found in system")

tFont_ = Font(family=settings_.get(Sets.FONT_FAMILY), size=settings_.get(Sets.FONT_SIZE))

T_ = tk.Text(middleFrame_, height=1, width=1, background=settings_.get(Sets.BACKGROUND_COLOR),\
            selectbackground=settings_.get(Sets.SELECT_BACKGROUND_COLOR),\
            foreground=settings_.get(Sets.TEXT_COLOR), font=tFont_)

T_.config(state=tk.DISABLED)

# Set up scroll bar
yscrollbar_=tk.Scrollbar(middleFrame_, orient=tk.VERTICAL, command=T_.yview)
yscrollbar_.pack(side=tk.RIGHT, fill=tk.Y)
T_["yscrollcommand"]=yscrollbar_.set
T_.pack(side=tk.LEFT, fill=tk.BOTH, expand = tk.YES)


T_.tag_configure(Sets.CONNECT_COLOR_TAG, background=Sets.CONNECT_LINE_BACKGROUND_COLOR, selectbackground=Sets.CONNECT_LINE_SELECT_BACKGROUND_COLOR)
T_.tag_configure(Sets.DISCONNECT_COLOR_TAG, background=Sets.DISCONNECT_LINE_BACKGROUND_COLOR, selectbackground=Sets.DISCONNECT_LINE_SELECT_BACKGROUND_COLOR)
T_.tag_configure(Sets.HIDELINE_COLOR_TAG, foreground=Sets.HIDE_LINE_FONT_COLOR)

middleFrame_.pack(side=tk.TOP, fill=tk.BOTH, expand = tk.YES)



################################
# Bottom frame

bottomFrame_ = tk.Frame(root)

statLabel1_ = tk.Label(bottomFrame_,text="Lines in window buffer 0/" + str(settings_.get(Sets.MAX_LINE_BUFFER)), width=30, anchor=tk.W)
statLabel1_.pack(side=tk.LEFT)

statLabel2_ = tk.Label(bottomFrame_,text="", width=30, anchor=tk.W)
statLabel2_.pack(side=tk.LEFT)

statLabel3_ = tk.Label(bottomFrame_,text="", width=60, anchor=tk.E)
statLabel3_.pack(side=tk.RIGHT,padx=(0,18))

bottomFrame_.pack(side=tk.BOTTOM, fill=tk.X)

def updateWindowBufferLineCount(count=-1):
    
    global endLine_

    if count != -1:        
        endLine_ = count+1
    
    statLabel1_.config(text="Lines in window buffer " + str(endLine_-1) + "/" + str(settings_.get(Sets.MAX_LINE_BUFFER)))




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
        with serial.Serial(serialPortVar_.get(), 115200, timeout=2) as ser:
            
            # TODO should be done in GUI thread
            setStatusLabel("CONNECTED to " + str(ser.name),Sets.STATUS_CONNECT_BACKGROUND_COLOR)         
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
    timeString = Sets.timeStampBracket[0] + timestamp.strftime("%H:%M:%S") + Sets.timeStampBracket[1]
    connectLine = timeString + Sets.CONNECT_LINE_TEXT
    # highlightQueue_.put(connectLine)
    highlightWorker_.highlightQueue.put(connectLine)

    lastTimestamp = 0

    while processFlag_:
        try:
            line = processQueue_.get(True,0.2)
            processQueue_.task_done()

            # Timestamp
            micros = int(line.timestamp.microsecond/1000)
            timeString = Sets.timeStampBracket[0] + line.timestamp.strftime("%H:%M:%S") + "." + '{:03d}'.format(micros) + Sets.timeStampBracket[1]

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
            
            timeDeltaString = Sets.timeDeltaBracket[0] + hourstring + minutstring + secondstring + Sets.timeDeltaBracket[1]

            lastTimestamp = line.timestamp

            # Replace newline
            newData = line.data.rstrip() + "\n"
            
            # Construct newLine string
            newLine = timeString + " " + timeDeltaString + " " + newData

            # highlightQueue_.put(newLine)
            highlightWorker_.highlightQueue.put(newLine)
            logQueue_.put(newLine)
            
        except queue.Empty:
            pass




################################
# Highlight worker

class HighlightWorker():

    def __init__(self,settings):
        self._settings_ = settings        

        self._lineColorMap_ = dict()

        self._lineBuffer_ = list()

        self._consecutiveLinesHidden_ = 0
        self._hideLineMap_ = list()
        self._hideLineMap_.append("GUI::.*")
        self._hideLineMap_.append("Main::.*")
        self._hideLinesFlag_ = False

        self._highlightFlag_ = False

        self.highlightQueue = queue.Queue()

        self._reloadLineBuffer_ = False
        self.isReloadingLineBuffer = False

        self.reloadLineColorMap()

    ##############
    # Public Interface

    def startWorker(self):
        
        if not self._highlightFlag_:        
            self._highlightFlag_ = True     
            self._highlightThread_ = threading.Thread(target=self._highlightWorker_,daemon=True,name="Highlight")
            self._highlightThread_.start()
            # print("Highlight worker started")
        else:
            traceLog(LogLevel.ERROR,"Not able to start higlight thread. Thread already enabled")

    def stopWorker(self,emptyQueue=True):
        "Stop highlight worker. Will block until thread is done"

        # TODO Check if startWorker has been called?

        if emptyQueue:
            self.highlightQueue.join()

        self._highlightFlag_ = False
        
        if self._highlightThread_.isAlive():
            self._highlightThread_.join()


    def getLineColorMap(self):
        return self._lineColorMap_

    def reloadLineColorMap(self):

        if not self._highlightFlag_:
            self._lineColorMap_.clear()
            self._lineColorMap_ = self._settings_.get(Sets.LINE_COLOR_MAP)
            traceLog(LogLevel.DEBUG,"HighligthWorker, reload line color map done")
        else:
            traceLog(LogLevel.ERROR,"HighligthWorker active. Not able to reload color map")
    
    def reloadLineBuffer(self):
        self._reloadLineBuffer_ = True
        # print("Highlight reloadLineBuffer")
    
    def clearLineBuffer(self):
        # print("Clear line buffer")
        self._lineBuffer_.clear()

    def toggleHideLines(self):
        if self._hideLinesFlag_:
            self._hideLinesFlag_ = False
        else:
            self._hideLinesFlag_ = True        

    ##############
    # Internal

    def _locateLineTags_(self,line):
        # Locate highlights
        highlights = list()
        for tagName in self._lineColorMap_.keys():
            match = re.search(self._lineColorMap_[tagName]["regex"],line)                
            if match:
                highlights.append((tagName,match.start(),match.end())) 

        match = re.search(Sets.connectLineRegex,line)
        if match:  
            highlights.append((Sets.CONNECT_COLOR_TAG,"0","0+1l"))

        match = re.search(Sets.disconnectLineRegex,line)
        if match:  
            highlights.append((Sets.DISCONNECT_COLOR_TAG,"0","0+1l"))

        return highlights

    def _getHideLineColorTags_(self):
        highlights = list()
        highlights.append((Sets.HIDELINE_COLOR_TAG,"0","0+1l"))
        return highlights

    def _addToLineBuffer_(self,rawline):

        lineBufferSize = len(self._lineBuffer_)

        self._lineBuffer_.append(rawline)

        if lineBufferSize > self._settings_.get(Sets.MAX_LINE_BUFFER):
            del self._lineBuffer_[0]

    def _hideLines_(self,line):

        if self._hideLinesFlag_:
            tempConsecutiveLinesHidden = 0

            for keys in self._hideLineMap_:
                match = re.search(keys,line)                
                if match:
                    tempConsecutiveLinesHidden = 1
                    break
            
            if tempConsecutiveLinesHidden == 1:
                self._consecutiveLinesHidden_ += 1
            else:
                self._consecutiveLinesHidden_ = 0
        else:
            self._consecutiveLinesHidden_ = 0

        return self._consecutiveLinesHidden_

    def _getTimeStamp_(self,line):

        # This is based on the settings of ColorTerminal
        # If you load a log file from another program, this might not work

        match = re.search(Sets.timeStampRegex,line)
        if match:
            return match.group(0)
        else:
            return ""

    ##############
    # Main Worker

    def _highlightWorker_(self):
    
        global reloadGuiBuffer_

        while self._highlightFlag_:

            newLine = ""
            
            try:
                newLine = self.highlightQueue.get(True,0.2)
                self.highlightQueue.task_done()

            except queue.Empty:
                pass

            if newLine or self._reloadLineBuffer_:
                
                if newLine:
                    self._addToLineBuffer_(newLine)
                
                linesToProcess = list()

                if self._reloadLineBuffer_:
                    self._reloadLineBuffer_ = False
                    
                    linesToProcess = self._lineBuffer_

                    # Wait for GUI queue to be empty and gui update to be done,
                    # otherwise some lines can be lost, when GUI is cleared
                    guiQueue_.join()                                    
                    guiEvent_.wait()

                    self.isReloadingLineBuffer = True

                    # print("reload high lines " + str(len(self._lineBuffer_)))                    
                    # traceLog(LogLevel.DEBUG, "Reload Line Buffer")

                else:
                    linesToProcess.append(newLine)
                
                for line in linesToProcess:

                    consecutiveLinesHidden = self._hideLines_(line)
                    if consecutiveLinesHidden == 0:
                        lineTags = self._locateLineTags_(line)                
                        pLine = PrintLine(line,lineTags)  
                    else:
                        hideInfoLine = self._getTimeStamp_(line) + " Lines hidden: " + str(consecutiveLinesHidden) + "\n"
                        lineTags = self._getHideLineColorTags_()
                        if consecutiveLinesHidden > 1: 
                            pLine = PrintLine(hideInfoLine,lineTags,True)  
                        else:
                            pLine = PrintLine(hideInfoLine,lineTags,False)  

                    guiQueue_.put(pLine)   
                
                if self.isReloadingLineBuffer:  
                    
                    guiReloadEvent_.clear()
                    self.isReloadingLineBuffer = False
                    reloadGuiBuffer_ = True
                    
                    # Wait for gui to have processed new buffer
                    # guiQueue_.join()   
                    guiReloadEvent_.wait()
                    # print("reload high done")

################################
# Log writer worker

def logWriterWorker():

    timestamp = datetime.datetime.now().strftime(settings_.get(Sets.LOG_FILE_TIMESTAMP))

    filename = settings_.get(Sets.LOG_FILE_BASE_NAME) + timestamp + ".txt"
    fullFilename = os.path.join(settings_.get(Sets.LOG_FILE_PATH),filename)

    os.makedirs(os.path.dirname(fullFilename), exist_ok=True)

    # TODO: Do not update UI from this thread
    statLabel3_.config(text="Saving to log file: " + filename, fg="black")

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

    statLabel3_.config(text="Log file saved: " + lastLogFileInfo_, fg="green")

################################
# GUI worker

def insertLine(newLine):

    global endLine_

    # Control window scolling
    bottomVisibleLine = int(T_.index("@0,%d" % T_.winfo_height()).split(".")[0])
    endLine_ = int(T_.index(tk.END).split(".")[0])
    T_.insert(tk.END, newLine)
    if (bottomVisibleLine >= (endLine_-1)):
        T_.see(tk.END)

    # Limit number of lines in window
    if endLine_ > settings_.get(Sets.MAX_LINE_BUFFER):
        T_.delete(1.0,2.0)

def updateLastLine(newLine):
    lastline = T_.index("end-2c").split(".")[0]    
    T_.delete(lastline + ".0",lastline +".0+1l")     
    T_.insert(lastline + ".0", newLine)
    # I don't think there is a need for scrolling?
    

def updateGUI():

    global endLine_    
    global reloadGuiBuffer_
    
    reloadInitiated = False

    receivedLines = list()

    if not highlightWorker_.isReloadingLineBuffer:

        try:     
            # We have to make sure that the queue is empty before continuing
            while True:            
                receivedLines.append(guiQueue_.get_nowait())
                guiQueue_.task_done()            


        except queue.Empty:

            # Open text widget for editing
            T_.config(state=tk.NORMAL)
            
            if reloadGuiBuffer_:            
                reloadGuiBuffer_ = False
                reloadInitiated = True
                linesToReload = len(receivedLines)
                traceLog(LogLevel.DEBUG,"Reload GUI buffer (Len " + str(linesToReload) + ")")              
                
                # Clear window
                T_.delete(1.0,tk.END)

            for msg in receivedLines:
                if msg.updatePreviousLine:
                    updateLastLine(msg.line)
                else:              
                    insertLine(msg.line)

                # Highlight/color text
                lastline = T_.index("end-2c").split(".")[0]
                for lineTag in msg.lineTags:
                    T_.tag_add(lineTag[0],lastline + "." + str(lineTag[1]),lastline + "." + str(lineTag[2]))

            # Disable text widget edit
            T_.config(state=tk.DISABLED)

        updateWindowBufferLineCount()
        statLabel2_.config(text="Lines in log file " + str(linesInLogFile_))

        if reloadInitiated:        
            guiReloadEvent_.set()
            traceLog(LogLevel.DEBUG,"Reload GUI buffer done")   

def startGuiWorker():

    cancelGuiJob()    

    global updateGuiFlag_
    updateGuiFlag_ = 1 

    global updateGuiJob_
    updateGuiJob_ = root.after(50,waitForInput)
   

def stopGuiWorker():
    "Will block until GUI worker is done. GUI queue is always emptied before stop."

    cancelGuiJob()

    global updateGuiFlag_
    updateGuiFlag_ = 0
    time.sleep(0.05) # This might not be needed, but is just to be sure that the updateGui function has not started
    guiEvent_.wait()

def cancelGuiJob():
    global updateGuiJob_
    if updateGuiJob_ is not None:
        root.after_cancel(updateGuiJob_)
        updateGuiJob_ = None

def waitForInput():
    global updateGuiJob_
    if updateGuiFlag_:
        guiEvent_.clear()        
        updateGUI()
        guiEvent_.set()
        updateGuiJob_ = root.after(100,waitForInput)






################################################################
################################################################
# 
# 
# 
# OPTIONS VIEW
# 
# 
# 
################################################################
################################################################


class OptionsView:

    def __init__(self,root,settings):
        self.root = root
        self.settings = settings
        
        self.showing = False
        self.saving = False
    
    def onClosing(self,savingSettings=False): 
        
        # Delete all variable observers
        for rowId in self.setsDict.keys():
            try:
                observer = self.setsDict[rowId]["observer"]
                self.setsDict[rowId]["var"].trace_vdelete("w",observer)   
            except KeyError:
                pass
        
        # Delete all view elements
        del self.setsDict        

        # Close window
        self.view.destroy()
        
        if not savingSettings:
            self.showing = False
        
    class SetLine:
        def __init__(self,setGroup,setId,setDisplayName,setType):            
            self.setGroup = setGroup
            self.setId = setId
            self.setDisplayName = setDisplayName
            self.setType = setType

    TYPE_COLOR = "typeColor"
    TYPE_STRING = "typeString"
    TYPE_INT = "typeInt"
    TYPE_OTHER = "typeOther"

    GROUP_TEXT_AREA = "groupTextArea"
    GROUP_LOGGING = "groupLogging"
    GROUP_LINE_COLORING = "groupLineColoring"

    EDIT_UP = "editUp"
    EDIT_DOWN = "editDown"
    EDIT_DELETE = "editDelete"

    ROW_HIGHLIGHT_COLOR = "gray"

    def show(self,lineColorMap):
        
        # Only allow one options view at a time
        if not self.showing:

            self.showing = True            

            self.lineColorMap = lineColorMap
            
            self.view = tk.Toplevel(self.root)
            self.view.title("Options")
            self.view.protocol("WM_DELETE_WINDOW", self.onClosing)

            self.setsDict = dict()

            ###############
            # Text Area

            self.textAreaFrame = tk.LabelFrame(self.view,text="Text Area")
            self.textAreaFrame.grid(row=0,column=0,padx=(10,10),pady=10,sticky=tk.N)

            setLines = list()
            setLines.append(self.SetLine(self.GROUP_TEXT_AREA, Sets.BACKGROUND_COLOR, "Background Color", self.TYPE_COLOR))
            setLines.append(self.SetLine(self.GROUP_TEXT_AREA, Sets.SELECT_BACKGROUND_COLOR, "Background Color Select", self.TYPE_COLOR))
            setLines.append(self.SetLine(self.GROUP_TEXT_AREA, Sets.TEXT_COLOR, "Text Color", self.TYPE_COLOR))
            setLines.append(self.SetLine(self.GROUP_TEXT_AREA, Sets.FONT_FAMILY, "Font Family", self.TYPE_STRING))
            setLines.append(self.SetLine(self.GROUP_TEXT_AREA, Sets.FONT_SIZE, "Font Size", self.TYPE_INT))

            
            self.setsDict.update(self.createStandardRows(self.textAreaFrame,setLines,0))

            
            tFont = Font(family=self.settings.get(Sets.FONT_FAMILY), size=self.settings.get(Sets.FONT_SIZE))

            self.exampleText = tk.Text(self.textAreaFrame,height=1,width=2,\
                                    background=self.settings.get(Sets.BACKGROUND_COLOR),\
                                    selectbackground=self.settings.get(Sets.SELECT_BACKGROUND_COLOR),\
                                    foreground=self.settings.get(Sets.TEXT_COLOR),\
                                    font=tFont)

            self.exampleText.grid(row=5,column=0,columnspan=3,sticky=tk.W+tk.E)
            self.exampleText.insert(1.0,"[12:34:56.789] Main::test")

            ###############
            # Logging

            self.loggingFrame = tk.LabelFrame(self.view,text="Logging")
            self.loggingFrame.grid(row=0,column=1,padx=(0,10),pady=10,sticky=tk.N)

            setLines = list()
            setLines.append(self.SetLine(self.GROUP_LOGGING, Sets.LOG_FILE_PATH, "Log file path", self.TYPE_OTHER))
            setLines.append(self.SetLine(self.GROUP_LOGGING, Sets.LOG_FILE_BASE_NAME, "Log file base name", self.TYPE_OTHER))
            setLines.append(self.SetLine(self.GROUP_LOGGING, Sets.LOG_FILE_TIMESTAMP, "Time stamp", self.TYPE_OTHER))

            self.setsDict.update(self.createStandardRows(self.loggingFrame,setLines,0))


            ###############
            # Line Coloring 

            self.lineColoringFrame = tk.LabelFrame(self.view,text="Line Coloring")
            self.lineColoringFrame.grid(row=0,column=2,padx=(0,10),pady=10,sticky=tk.N)

            self.setsDict.update(self.createLineColorRows(self.lineColoringFrame,self.lineColorMap))

            upButton = tk.Button(self.lineColoringFrame,text="UP",command=partial(self.editLineColorRow,self.EDIT_UP))
            upButton.grid(row=0,column=2,padx=2)

            downButton = tk.Button(self.lineColoringFrame,text="DOWN",command=partial(self.editLineColorRow,self.EDIT_DOWN))
            downButton.grid(row=1,column=2,padx=2)

            self.deleteButton = tk.Button(self.lineColoringFrame,text="Delete",command=partial(self.editLineColorRow,self.EDIT_DELETE))
            self.deleteButton.grid(row=2,column=2,padx=2)
            self.lastFocusInRowId = ""
            self.lastFocusOutRowId = ""        

            self.newButtonRow = len(self.lineColorMap)
            self.newButton  = tk.Button(self.lineColoringFrame,text="New Line",command=partial(self.addNewEmptyLineColor,self.lineColoringFrame))
            self.newButton.grid(row=self.newButtonRow,column=0,sticky=tk.W,padx=(2,100),pady=2)
            
            ###############
            # Control buttons

            self.optionsButtonsFrame = tk.Frame(self.view)
            self.optionsButtonsFrame.grid(row=1,column=2,padx=(0,10),pady=(0,10),sticky=tk.E)

            self.optionsCancelButton = tk.Button(self.optionsButtonsFrame,text="Cancel",command=self.onClosing)
            self.optionsCancelButton.grid(row=0,column=0,padx=5)

            self.optionsSaveButton = tk.Button(self.optionsButtonsFrame,text="Save",command=self.saveSettings)
            self.optionsSaveButton.grid(row=0,column=1)
            if self.saving:
                self.optionsSaveButton.config(state=tk.DISABLED)
            else:
                self.optionsSaveButton.config(state=tk.NORMAL)
    
    def saveSettings(self):

        saveSettingsThread = threading.Thread(target=self.saveSettingsProcess,name="SaveSettings")
        saveSettingsThread.start()

        self.saving = True

    def setSaveButtonState(self,state):
        if self.showing:
            try:
                self.optionsSaveButton.config(state=state)
            except:
                # Catch if function is called while save button does not exist
                traceLog(LogLevel.ERROR,"Error updating save button state")


    def saveSettingsProcess(self):
        # Saving will block, so must be done in different thread
        
        # setsDict will be deleted in the onClosing function
        tempSetsDict = self.setsDict
        
        # Close options view
        root.after(10,self.onClosing,True)

        # Show saving message
        saveSpinner = Spinner(self.root)
        saveSpinner.show(indicators=False,message="Reloading View")
        
        # Stop workers using the settings
        highlightWorker_.stopWorker(emptyQueue=False)        
        stopGuiWorker()        
        
        # Save all settings
        tempLineColorMap = dict()
        # Sort settings to guarantee right order of line coloring
        for key in sorted(tempSetsDict.keys()):
            if not Sets.LINE_COLOR_MAP in key:
                self.settings.setOption(key,tempSetsDict[key]["var"].get())
            else:
                tempLineColorMap[key] = dict()
                tempLineColorMap[key]["regex"] = tempSetsDict[key]["regexVar"].get()
                tempLineColorMap[key]["color"] = tempSetsDict[key]["var"].get()                
            
        self.settings.setOption(Sets.LINE_COLOR_MAP,tempLineColorMap)

        # Once settings have been saved, allow for reopen of options view
        self.showing = False

        # Reload main interface
        reloadLineColorMapAndTags()
        reloadTextFrame()
        
        # Start hilightworker to prepare buffer reload
        highlightWorker_.startWorker()  
                
        # Reload line/gui buffer
        reloadBufferCommand()        
        guiReloadEvent_.clear()

        # Start gui worker to process new buffer
        startGuiWorker()

        # Wait for GUI worker to have processed the new buffer
        guiReloadEvent_.wait()

        # Remove spinner
        saveSpinner.close()   

        # Update save button, if window has been opened again
        root.after(10,self.setSaveButtonState,tk.NORMAL)     
        self.saving = False
    

    ####################################
    # View Creation

    def addNewEmptyLineColor(self,parent):
        # print("New Button " + str(self.newButtonRow))

        self.newButton.grid(row=self.newButtonRow+1)

        rowId = self.getRowId(self.newButtonRow)
        self.setsDict[rowId] = self.createSingleLineColorRow(self.lineColoringFrame,self.newButtonRow,rowId,"","white")

        self.newButtonRow += 1

    def editLineColorRow(self,edit):
        # print("Last focus in " + self.lastFocusInRowId)
        # print("Last focus out " + self.lastFocusOutRowId)

        # If lastFocusIn is not the same as lastFocusOut,
        # we know that lastFocusIn is currently selected.
        if self.lastFocusInRowId != self.lastFocusOutRowId:
            if Sets.LINE_COLOR_MAP in self.lastFocusInRowId:
                # print("EDIT: " + self.lastFocusInRowId)

                # Get row number
                rowNum = int(self.lastFocusInRowId.replace(Sets.LINE_COLOR_MAP,""))
                
                # Find index of rows to edit                
                indexToChange = list()
                if edit == self.EDIT_UP:
                    if rowNum > 0:                                
                        indexToChange = [rowNum-1, rowNum]
                elif edit == self.EDIT_DOWN:
                    if rowNum < (self.newButtonRow - 1):                    
                        indexToChange = [rowNum, rowNum+1]
                elif edit == self.EDIT_DELETE:                    
                    indexToChange = range(rowNum,self.newButtonRow)
                        
                if indexToChange:   

                    tempTextColorMap = list()                               
                    for i in indexToChange:
                        # Save regex and color
                        rowId = self.getRowId(i)
                        tempTextColorMap.append((self.setsDict[rowId]["regexVar"].get(),self.setsDict[rowId]["var"].get()))

                        # Remove rows to edit from view
                        self.setsDict[rowId]["lineFrame"].destroy()
                        del self.setsDict[rowId]
                    
                    # Reorder or delete saved rows
                    newRowNum = -1
                    if edit == self.EDIT_UP:                        
                        tempTextColorMap[1], tempTextColorMap[0] = tempTextColorMap[0], tempTextColorMap[1]
                        newRowNum = rowNum-1
                    elif edit == self.EDIT_DOWN:                        
                        tempTextColorMap[1], tempTextColorMap[0] = tempTextColorMap[0], tempTextColorMap[1]
                        newRowNum = rowNum+1
                    elif edit == self.EDIT_DELETE:                        
                        del tempTextColorMap[0]
                    
                    # Recreate saved rows                       
                    for i,(regex,color) in enumerate(tempTextColorMap):
                        rowId = self.getRowId(indexToChange[i])             
                        self.setsDict[rowId] = self.createSingleLineColorRow(self.lineColoringFrame,indexToChange[i],rowId,regex,color)

                    # If move up or down, refocus
                    if newRowNum > -1:
                        rowId = self.getRowId(newRowNum)
                        self.focusInSet(rowId)
                    # If delete, update row count and move newButton
                    else:                        
                        self.newButtonRow = self.newButtonRow - 1 
                        self.newButton.grid(row=self.newButtonRow)
                        self.lastFocusInRowId = ""
    

    def createLineColorRows(self,parent,lineColorMap):
        setDict = dict()
        for rowId in sorted(lineColorMap.keys()):
            rowNum = int(rowId.replace(Sets.LINE_COLOR_MAP,""))
            setDict[rowId] = self.createSingleLineColorRow(parent,rowNum,rowId,lineColorMap[rowId]["regex"],lineColorMap[rowId]["color"])

        return setDict

    def createSingleLineColorRow(self,parent,row,rowId,regex,color):        
        colorLine = dict()        

        colorLine["lineFrame"] = tk.Frame(parent,highlightcolor=self.ROW_HIGHLIGHT_COLOR,highlightthickness=2)
        colorLine["lineFrame"].grid(row=row,column=0)        
        colorLine["lineFrame"].bind("<Button-1>",partial(self.focusInSet,rowId))        
        colorLine["lineFrame"].bind("<FocusOut>",partial(self.focusOut,rowId))

        colorLine["regexLabel"] = tk.Label(colorLine["lineFrame"],text="Regex")
        colorLine["regexLabel"].grid(row=0,column=0)
        colorLine["regexLabel"].bind("<Button-1>",partial(self.focusInSet,rowId))
        
        colorLine["regexVar"] = tk.StringVar(colorLine["lineFrame"])
        colorLine["regexVar"].set(regex)
        # colorLine["var"].trace("w",self.validateInput)                    
        colorLine["regexInput"] = tk.Entry(colorLine["lineFrame"],textvariable=colorLine["regexVar"],width=30)
        colorLine["regexInput"].grid(row=0,column=1)
        colorLine["regexInput"].bind("<Button-1>",partial(self.focusInLog,rowId))

        colorLine["colorLabel"] = tk.Label(colorLine["lineFrame"],text="Color")
        colorLine["colorLabel"].grid(row=0,column=2)
        colorLine["colorLabel"].bind("<Button-1>",partial(self.focusInSet,rowId))

        colorLine["var"] = tk.StringVar(colorLine["lineFrame"],name=rowId)
        colorLine["var"].set(color)      
        colorLine["observer"] = colorLine["var"].trace("w",self.validateInput)                                   
        colorLine["input"] = tk.Entry(colorLine["lineFrame"],textvariable=colorLine["var"],width=10)
        colorLine["input"].grid(row=0,column=3)
        colorLine["input"].bind("<Button-1>",partial(self.focusInLog,rowId))
        
        colorLine["button"] = tk.Button(colorLine["lineFrame"],bg=color,width=3,command=partial(self.getColor,rowId,True))
        colorLine["button"].grid(row=0,column=4,padx=4)
        colorLine["button"].bind("<Button-1>",partial(self.focusInSet,rowId))        

        colorLine["type"] = self.TYPE_COLOR
        colorLine["group"] = self.GROUP_LINE_COLORING

        return colorLine

    def createStandardRows(self,parent,setLines,startRow):
        setDict = dict()

        # Find longest entry in settings
        maxLen = 0
        for setLine in setLines:
            setLen = len(str(self.settings.get(setLine.setId)))
            if setLen > maxLen:
                maxLen = setLen

        row = startRow
        for setLine in setLines:
            setRow = dict()

            # TODO Add frame and highlight to colors (remember column widths and alignment)

            setRow["label"] = tk.Label(parent,text=setLine.setDisplayName)
            setRow["label"].grid(row=row,column=0,sticky=tk.W)
            if setLine.setType == self.TYPE_INT:    
                setRow["var"] = tk.IntVar(parent,name=setLine.setId)
            else:
                setRow["var"] = tk.StringVar(parent,name=setLine.setId)
            setRow["var"].set(self.settings.get(setLine.setId))            
            # TODO use tkinter validateCommand
            setRow["observer"] = setRow["var"].trace("w",self.validateInput)                        
            # TODO Find better solution for entry width            
            setRow["input"] = tk.Entry(parent,textvariable=setRow["var"],width=int(maxLen*1.5))
            setRow["input"].grid(row=row,column=1)
            if setLine.setType == self.TYPE_COLOR:                
                setRow["button"] = tk.Button(parent,bg=self.settings.get(setLine.setId),width=3,command=partial(self.getColor,setLine.setId))
                setRow["button"].grid(row=row,column=2,padx=4)

            setRow["type"] = setLine.setType
            setRow["group"] = setLine.setGroup
            setDict[setLine.setId] = setRow

            row += 1

        return setDict



    ####################################
    # View Interaction

    def focusOut(self,rowId,event):        
        self.lastFocusOutRowId = rowId

    def focusInSet(self,rowId,event=0):        
        self.setsDict[rowId]["lineFrame"].focus_set()   
        self.focusInLog(rowId,event)

    def focusInLog(self,rowId,event=0):        
        self.lastFocusInRowId = rowId
        if self.lastFocusOutRowId == rowId:
            self.lastFocusOutRowId = ""

    def getColor(self,rowId,highlight=False):
        
        if highlight:
            hg = self.setsDict[rowId]["lineFrame"].cget("highlightbackground")
            self.setsDict[rowId]["lineFrame"].config(highlightbackground=self.R)
        
        currentColor = self.setsDict[rowId]["button"].cget("bg")

        if not self.isValidColor(currentColor):
            currentColor = None

        color = askcolor(initialcolor=currentColor,parent=self.view) 

        if color[1] != None:
            self.setsDict[rowId]["var"].set(color[1])
            self.setsDict[rowId]["button"].config(bg=color[1])

        if highlight:
            self.setsDict[rowId]["lineFrame"].config(highlightbackground=hg)
            self.focusInLog(rowId)
            

    ####################################
    # Entry Validation

    def validateInput(self,*args):        
        # print(args)               

        # TODO Cleanup/redo!

        # Get variable
        varIn = None
        try:    
            varIn = self.setsDict[args[0]]["var"].get()
            isValid = True
        except tk.TclError:
            # print("Tcl Error")
            isValid = False

        if isValid:

            # Check Colors
            if self.setsDict[args[0]]["type"] == self.TYPE_COLOR:
                color = varIn
                isValid = self.isValidColor(color)
                if isValid:
                    # print("Color " + str(color))
                    self.setsDict[args[0]]["button"].config(background=color)

            # Check font family
            if args[0] == Sets.FONT_FAMILY:
                isValid = self.isValidFontFamily(varIn)

            # Check font size
            if args[0] == Sets.FONT_SIZE:
                isValid = self.isValidFontSize(varIn)

            if isValid and self.setsDict[args[0]]["group"] == self.GROUP_TEXT_AREA:
                # Update example line
                try:
                    tFont = Font(family=self.setsDict[Sets.FONT_FAMILY]["var"].get(),\
                                size=self.setsDict[Sets.FONT_SIZE]["var"].get())                
                    self.exampleText.config(background=self.setsDict[Sets.BACKGROUND_COLOR]["var"].get(),\
                                            selectbackground=self.setsDict[Sets.SELECT_BACKGROUND_COLOR]["var"].get(),\
                                            foreground=self.setsDict[Sets.TEXT_COLOR]["var"].get(),\
                                            font=tFont)
                except tk.TclError:
                    # print("Tcl Error")
                    pass       

        if isValid:
            self.setsDict[args[0]]["input"].config(background="white")
        else:
            self.setsDict[args[0]]["input"].config(background="red")

    # TODO validate regex

    def isValidColor(self,colorString):
        isValid = True
        try:
            tk.Label(None,background=colorString)
        except tk.TclError:
            # print("Color Error")
            isValid = False
        return isValid

    def isValidFontFamily(self,family):
        fontList = tk.font.families()
        return family in fontList

    def isValidFontSize(self,size):
        isValid = True
        try:
            Font(size=size)
        except tk.TclError:
            # print("Font Size Error")
            isValid = False

        if isValid:
            if int(size) < 1:
                isValid = False

        return isValid
    
    ####################################
    # Misc

    def getRowId(self,rowNum):
        return Sets.LINE_COLOR_MAP + "{:02d}".format(rowNum)


################################################################
################################################################
# 
# 
# 
# SPINNER
# 
# 
# 
################################################################
################################################################


class Spinner:

    def __init__(self,root):
        self.root = root             
        self.runFlag = True   

    def close(self):

        self.runFlag = False

        try:          
            self.view.after_cancel(self.updateJob)                        
        except AttributeError:
            # print("No job to cancel")
            pass

        try:              
            self.view.destroy()
        except AttributeError:
            # print("No view")
            pass


    def show(self,indicators=True,animate=False,message=""):

        self.animate = animate

        bgColor = "black"
        borderColor = "#777"
        padding = 20

        self.view = tk.Frame(self.root,bg=bgColor,highlightthickness=2,highlightbackground=borderColor)
        self.view.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        ########################
        # Indicators

        if indicators:

            indicatorBaseFrame = tk.Frame(self.view,bg=bgColor)
            indicatorBaseFrame.pack(padx=padding,pady=padding)

            # Setup        
            colors = [bgColor,"#222","#444","#777"]        
            colorSequenceIndexList = [0,0,0,0,0,0,1,2,3,2,1]

            self.updatePeriod_ms = 100
            indicatorX = 20
            indicatorY = 20
            indicatorSpacing = 10
            indicatorCount = 5
            
            # Create color list
            self.colorSequence = list()
            for i in range(len(colorSequenceIndexList)):                
                self.colorSequence.append(colors[colorSequenceIndexList[i]])
            
            self.colorSequenceIndex = 0

            self.indicators = list()
            for i in range(indicatorCount):
                indicator = tk.Frame(indicatorBaseFrame,bg=bgColor,width=indicatorX,height=indicatorY)
                if i > 0: 
                    padx = (0,indicatorSpacing) 
                else: 
                    padx = 0
                # Add indicators right to left, to get movement correct
                indicator.pack(side=tk.RIGHT,padx=padx)            
                self.indicators.append(indicator)
                
            if self.animate:
                self.updateJob = self.view.after(self.updatePeriod_ms,self.updateIndicators)

        ########################
        # Text

        if indicators:
            topPad = 0
        else:
            topPad = padding

        if message:
            textColor = "white"
            font = ("arial",14)
            # font = ("courier new",12)

            indicatorLabel = tk.Label(self.view,text=message,fg=textColor,bg=bgColor,font=font)
            indicatorLabel.pack(padx=padding, pady=(topPad,padding))

    def updateIndicators(self):
        
        colorLen = len(self.colorSequence)

        for index,indicator in enumerate(self.indicators):
            indicator.config(bg=self.colorSequence[self._nextIndex_(colorLen,self.colorSequenceIndex+index)])

        self.colorSequenceIndex = self._nextIndex_(colorLen,self.colorSequenceIndex)

        if self.animate and self.runFlag:
            self.updateJob = self.view.after(self.updatePeriod_ms,self.updateIndicators)

    def _nextIndex_(self,len,currentIndex):
        nextIndex = currentIndex + 1
        if nextIndex >= len:
            nextIndex = 0
        return nextIndex





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

highlightWorker_ = HighlightWorker(settings_)
highlightWorker_.startWorker()

guiEvent_ = threading.Event()
guiEvent_.set() # wait will not block

guiReloadEvent_ = threading.Event()
guiReloadEvent_.set()


optionsView_ = OptionsView(root,settings_)


createTextFrameLineColorTag()
updateGuiJob_ = root.after(50,waitForInput)



# spinner = None

# def down(e):
#     print("DOWN: " + e.char)
#     if e.char == 'n':        
#         optionsView_.show(highlightWorker_.getLineColorMap())        
#     # elif e.char == 'm':
#     #     global spinner
#     #     spinner = Spinner(root)
#     #     spinner.show()
#     # elif e.char == 'b':
#     #     if spinner:
#     #         spinner.close()
#     #         spinner = None

# def up(e):
#     print("UP: " + e.char)

# root.bind('<KeyPress>', down)
# root.bind('<KeyRelease>', up)


traceLog(LogLevel.INFO,"Main loop started")

root.mainloop()

traceLog(LogLevel.INFO,"Main loop done")