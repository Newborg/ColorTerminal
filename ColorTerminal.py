
import os

import json

from enum import Enum

import tkinter as tk
from tkinter import messagebox
from tkinter.font import Font
from tkinter.colorchooser import askcolor
from tkinter.ttk import Notebook

from functools import partial

# import serial
import serial.tools.list_ports

import time
import datetime

import threading
import queue

import re

# ColorTerminal
from traceLog import traceLog,LogLevel
import settings as Sets
from customTypes import ConnectState, PrintLine
import spinner
import optionsView
import search

# from workers import *
from workers import readerWorker

################################
# Custom types

# class ConnectState(Enum):
#     CONNECTED = 1
#     DISCONNECTED = 0

# class SerialLine:
#     def __init__(self, data, timestamp):
#         self.data = data
#         self.timestamp = timestamp

# class PrintLine:
#     def __init__(self, line, lineTags, updatePreviousLine = False):
#         self.line = line
#         self.lineTags = lineTags
#         self.updatePreviousLine = updatePreviousLine

################################
# Connection Controller

class ConnectController:

    def __init__(self,settings,rootClass):
        self._settings_ = settings
        self._rootClass_ = rootClass
        self._root_ = rootClass.root

        self._closeProgram_ = False

        self._readerWorker_ = None
        self._processWorker_ = None
        self._logWriterWorker_ = None
        self._highlightWorker_ = None
        self._guiWorker_ = None

        self._statusFrame_ = None

        self._appState_ = ConnectState.DISCONNECTED

    def linkWorkers(self,workers):
        self._readerWorker_ = workers.readerWorker
        self._processWorker_ = workers.processWorker
        self._logWriterWorker_ = workers.logWriterWorker
        self._highlightWorker_ = workers.highlightWorker
        self._guiWorker_ = workers.guiWorker

    def linkStatusFrame(self,statusFrame):
        self._statusFrame_ = statusFrame

    def connectSerial(self):

        traceLog(LogLevel.INFO,"Connect to serial")

        if self._readerWorker_:
            self._readerWorker_.startWorker()

        if self._processWorker_:
            self._processWorker_.startWorker()

        if self._logWriterWorker_:
            self._logWriterWorker_.startWorker()


    def disconnectSerial(self,close=False):
        self._closeProgram_ = close
        # Disconnect will block, so must be done in different thread
        disconnectThread = threading.Thread(target=self._disconnectSerialProcess_,name="Disconnect")
        disconnectThread.start()

    def _disconnectSerialProcess_(self):
        traceLog(LogLevel.INFO,"Disconnect from serial")

        # Stop serial reader
        self._readerWorker_.stopWorker()

        # Empty process queue and stop process thread
        self._processWorker_.stopWorker()

        # Empty log queue and stop log writer thread
        self._logWriterWorker_.stopWorker()

        # Add disconnect line if connected
        if self._appState_ == ConnectState.CONNECTED:
            timestamp = datetime.datetime.now()
            timeString = Sets.timeStampBracket[0] + timestamp.strftime("%H:%M:%S") + Sets.timeStampBracket[1]

            disconnectLine = timeString + Sets.disconnectLineText + self._logWriterWorker_.lastLogFileInfo + "\n"

            self._highlightWorker_.highlightQueue.put(disconnectLine)


        traceLog(LogLevel.INFO,"Main worker threads stopped")

        self._statusFrame_.setStatusLabel("DISCONNECTED",Sets.STATUS_DISCONNECT_BACKGROUND_COLOR)
        self._appState_ = ConnectState.DISCONNECTED

        if self._closeProgram_:

            self._highlightWorker_.stopWorker(emptyQueue=False)

            self._guiWorker_.stopWorker()

            # Close tkinter window (close program)
            self._root_.after(100,self._rootClass_.destroyWindow)

    def setAppState(self,state):
        self._appState_ = state

    def getAppState(self):
        return self._appState_

    def changeAppState(self,state):

        # TODO Maybe change to toggle function

        if state == ConnectState.CONNECTED:
            self._statusFrame_.setConnectButtonText("Disconnect")
            self.connectSerial()
            self._statusFrame_.setStatusLabel("CONNECTING...",Sets.STATUS_WORKING_BACKGROUND_COLOR)

        elif state == ConnectState.DISCONNECTED:
            self._statusFrame_.setConnectButtonText("Connect")
            self.disconnectSerial()
            self._statusFrame_.setStatusLabel("DISCONNECTING...",Sets.STATUS_WORKING_BACKGROUND_COLOR)

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

class RootClass:

    def __init__(self,settings):
        self._settings_ = settings

        self.root = tk.Tk()

        self._connectController_ = None

        self.root.protocol("WM_DELETE_WINDOW", self._onClosing_)

        self.root.title("Color Terminal")
        self.root.geometry(self._settings_.get(Sets.DEFAULT_WINDOW_SIZE))

    def linkConnectController(self,connectController):
        self._connectController_ = connectController

    def destroyWindow(self):
        traceLog(LogLevel.INFO,"Closing main window")
        self.root.destroy()

    def _onClosing_(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self._connectController_.disconnectSerial(close=True)



################################
# Status frame

class StatusFrame:

    def __init__(self,settings,rootClass,search,optionsView):
        self._settings_ = settings
        self._root_ = rootClass.root
        self._textArea_ = None
        self._bottomFrame_ = None
        self._search_ = search
        self._optionsView_ = optionsView


        self._serialPorts_ = dict()
        self._serialPortList_ = [""]

        self._connectController_ = None
        self._highlightWorker_ = None

        self._root_.bind("<Alt-e>", self._goToEndButtonCommand_)

        # Create widgets
        self._topFrame_ = tk.Frame(self._root_)

        self._statusLabel_ = tk.Label(self._topFrame_,text="DISCONNECTED", width=20, anchor=tk.W, fg=Sets.STATUS_TEXT_COLOR, bg=Sets.STATUS_DISCONNECT_BACKGROUND_COLOR)
        self._statusLabel_.pack(side=tk.RIGHT,padx=(0,18))

        self._statusLabelHeader_ = tk.Label(self._topFrame_,text="   Status:", anchor=tk.W, fg=Sets.STATUS_TEXT_COLOR, bg=Sets.STATUS_DISCONNECT_BACKGROUND_COLOR)
        self._statusLabelHeader_.pack(side=tk.RIGHT)

        self._connectButton_ = tk.Button(self._topFrame_,text="Connect", command=self._connectButtonCommand_, width=10)
        self._connectButton_.pack(side=tk.LEFT)

        self._goToEndButton_ = tk.Button(self._topFrame_,text="Go to end", command=self._goToEndButtonCommand_, width=10, underline=6)
        self._goToEndButton_.pack(side=tk.LEFT)

        # reloadBufferButton_ = tk.Button(topFrame_,text="Reload buffer", command=reloadBufferCommand, width=10)
        # reloadBufferButton_.pack(side=tk.LEFT)

        # hideLinesButton_ = tk.Button(topFrame_,text="Hide Lines", command=hideLinesCommand, width=10)
        # hideLinesButton_.pack(side=tk.LEFT)

        self._clearButton_ = tk.Button(self._topFrame_,text="Clear", command=self._clearButtonCommand_, width=10)
        self._clearButton_.pack(side=tk.LEFT,padx=(0,40))

        self._optionsButton_ = tk.Button(self._topFrame_,text="Options", command=self._showOptionsView_, width=10)
        self._optionsButton_.pack(side=tk.LEFT,padx=(0,40))

        self._serialPortReloadButton_ = tk.Button(self._topFrame_,text="Reload ports", command=self._reloadSerialPorts_, width=10)
        self._serialPortReloadButton_.pack(side=tk.LEFT)

        self._serialPortVar_ = tk.StringVar(self._topFrame_)
        self._serialPortOption_ = tk.OptionMenu(self._topFrame_,self._serialPortVar_,*self._serialPortList_)
        self._serialPortOption_.pack(side=tk.LEFT)

        self._serialPortLabel_ = tk.Label(self._topFrame_,text="", anchor=tk.W)
        self._serialPortLabel_.pack(side=tk.LEFT)

        self._topFrame_.pack(side=tk.TOP, fill=tk.X)


        self._reloadSerialPorts_()

    NO_SERIAL_PORT = "None"

    ##############
    # Public Interface

    def linkConnectController(self,connectController):
        self._connectController_ = connectController

    def linkWorkers(self,workers):
        self._highlightWorker_ = workers.highlightWorker

    def linkTextFrame(self,textFrame):
        self._textArea_ = textFrame.textArea

    def linkBottomFrame(self,bottomFrame):
        self._bottomFrame_ = bottomFrame

    def setConnectButtonText(self,text):
        self._connectButton_.config(text=text)

    def setStatusLabel(self,labelText, bgColor):
        self._statusLabel_.config(text=labelText, bg=bgColor)
        self._statusLabelHeader_.config(bg=bgColor)

    def getSerialPortVar(self):
        return self._serialPortVar_.get()

    ##############
    # Internal

    def _connectButtonCommand_(self):

        appState = self._connectController_.getAppState()

        if appState == ConnectState.DISCONNECTED:
            # Connect to serial
            self._connectController_.changeAppState(ConnectState.CONNECTED)

        elif appState == ConnectState.CONNECTED:
            # Close down reader
            self._connectController_.changeAppState(ConnectState.DISCONNECTED)

    def _goToEndButtonCommand_(self,*args):
        self._textArea_.see(tk.END)

    def _clearButtonCommand_(self,*args):

        self._search_.close()

        self._highlightWorker_.clearLineBuffer()

        self._textArea_.config(state=tk.NORMAL)
        self._textArea_.delete(1.0,tk.END)
        self._textArea_.config(state=tk.DISABLED)

        self._bottomFrame_.updateWindowBufferLineCount_(0)

    def _reloadBufferCommand_(self):
        self._highlightWorker_.reloadLineBuffer()

    def _hideLinesCommand_(self):
        self._highlightWorker_.toggleHideLines()
        self._reloadBufferCommand_()

    def _showOptionsView_(self):
        self._search_.close()
        self._optionsView_.show(self._highlightWorker_.getLineColorMap())

    def _scanSerialPorts_(self):

        serialPortDict = dict()

        comPorts = serial.tools.list_ports.comports()

        for comPort in comPorts:
            try:
                with serial.Serial(comPort.device, 115200, timeout=2):
                    serialPortDict[comPort.device] = comPort.description
            except serial.SerialException:
                traceLog(LogLevel.DEBUG,"scanSerialPorts: " + comPort.device + " already open")

        return serialPortDict

    def _reloadSerialPorts_(self):

        self._serialPorts_ = self._scanSerialPorts_()

        if self._serialPorts_:
            self._serialPortList_.clear()
            self._serialPortList_.extend(sorted(list(self._serialPorts_.keys())))
            self._serialPortVar_.set(self._serialPortList_[0])
            self._serialPortVar_.trace("w",self._updateSerialPortSelect_)

            # Delete options
            self._serialPortOption_["menu"].delete(0,"end")

            # Add new options
            for port in self._serialPortList_:
                self._serialPortOption_["menu"].add_command(label=port, command=tk._setit(self._serialPortVar_,port))

            self._serialPortOption_.config(state=tk.NORMAL)
            self._serialPortLabel_.config(text=self._serialPorts_[self._serialPortVar_.get()])

            self._connectButton_.config(state=tk.NORMAL)

        else:
            self._serialPortVar_.set(self.NO_SERIAL_PORT)
            self._serialPortLabel_.config(text="No serial port found")
            self._serialPortOption_.config(state=tk.DISABLED)
            self._connectButton_.config(state=tk.DISABLED)

    def _updateSerialPortSelect_(self,*args):
        if self._serialPortVar_.get() == self.NO_SERIAL_PORT:
            self._serialPortLabel_.config(text=self.NO_SERIAL_PORT)
        else:
            self._serialPortLabel_.config(text=self._serialPorts_[self._serialPortVar_.get()])


################################
# Text frame

class TextFrame:

    def __init__(self,settings,rootClass):
        self._settings_ = settings
        self._root_ = rootClass.root

        self._highlightWorker_ = None

        self._textFrame_ = tk.Frame(self._root_)

        fontList_ = tk.font.families()
        if not self._settings_.get(Sets.FONT_FAMILY) in fontList_:
            traceLog(LogLevel.WARNING,"Font \"" + self._settings_.get(Sets.FONT_FAMILY) + "\" not found in system")

        tFont_ = Font(family=self._settings_.get(Sets.FONT_FAMILY), size=self._settings_.get(Sets.FONT_SIZE))

        self.textArea = tk.Text(self._textFrame_, height=1, width=1, background=self._settings_.get(Sets.BACKGROUND_COLOR),\
                                selectbackground=self._settings_.get(Sets.SELECT_BACKGROUND_COLOR),\
                                foreground=self._settings_.get(Sets.TEXT_COLOR), font=tFont_)

        self.textArea.config(state=tk.DISABLED)

        # Set up scroll bar
        yscrollbar_=tk.Scrollbar(self._textFrame_, orient=tk.VERTICAL, command=self.textArea.yview)
        yscrollbar_.pack(side=tk.RIGHT, fill=tk.Y)
        self.textArea["yscrollcommand"]=yscrollbar_.set
        self.textArea.pack(side=tk.LEFT, fill=tk.BOTH, expand = tk.YES)


        self.textArea.tag_configure(Sets.CONNECT_COLOR_TAG, background=Sets.CONNECT_LINE_BACKGROUND_COLOR, selectbackground=Sets.CONNECT_LINE_SELECT_BACKGROUND_COLOR)
        self.textArea.tag_configure(Sets.DISCONNECT_COLOR_TAG, background=Sets.DISCONNECT_LINE_BACKGROUND_COLOR, selectbackground=Sets.DISCONNECT_LINE_SELECT_BACKGROUND_COLOR)
        self.textArea.tag_configure(Sets.HIDELINE_COLOR_TAG, foreground=Sets.HIDE_LINE_FONT_COLOR)

        self._textFrame_.pack(side=tk.TOP, fill=tk.BOTH, expand = tk.YES)


    def linkWorkers(self,workers):
        self._highlightWorker_ = workers.highlightWorker

    def createTextFrameLineColorTag(self):
        lineColorMap = self._highlightWorker_.getLineColorMap()

        for key in sorted(lineColorMap.keys()):
             self.textArea.tag_configure(key, foreground=lineColorMap[key]["color"])

    def reloadLineColorMapAndTags(self):

        lineColorMapKeys = self._highlightWorker_.getLineColorMap().keys()
        self._textFrameClearTags_(lineColorMapKeys)

        self._highlightWorker_.reloadLineColorMap()

        self.createTextFrameLineColorTag()

    def reloadTextFrame(self):

        traceLog(LogLevel.DEBUG,"Reload text frame")

        tFont = Font(family=self._settings_.get(Sets.FONT_FAMILY), size=self._settings_.get(Sets.FONT_SIZE))

        self.textArea.config(background=self._settings_.get(Sets.BACKGROUND_COLOR),\
                            selectbackground=self._settings_.get(Sets.SELECT_BACKGROUND_COLOR),\
                            foreground=self._settings_.get(Sets.TEXT_COLOR), font=tFont)

    def _textFrameClearTags_(self,tagNames):
        # clear existing tags
        for tagName in tagNames:
            self.textArea.tag_delete(tagName)



################################
# Bottom frame

class BottomFrame:

    def __init__(self,settings,rootClass):
        self._settings_ = settings
        self._root_ = rootClass.root

        self._bottomFrame_ = tk.Frame(self._root_)

        self._statLabel1_ = tk.Label(self._bottomFrame_,text="Lines in window buffer 0/" + str(self._settings_.get(Sets.MAX_LINE_BUFFER)), width=30, anchor=tk.W)
        self._statLabel1_.pack(side=tk.LEFT)

        self._statLabel2_ = tk.Label(self._bottomFrame_,text="", width=30, anchor=tk.W)
        self._statLabel2_.pack(side=tk.LEFT)

        self._statLabel3_ = tk.Label(self._bottomFrame_,text="", width=60, anchor=tk.E)
        self._statLabel3_.pack(side=tk.RIGHT,padx=(0,18))

        self._bottomFrame_.pack(side=tk.BOTTOM, fill=tk.X)

    def updateWindowBufferLineCount(self,count):
        self._statLabel1_.config(text="Lines in window buffer " + str(count) + "/" + str(self._settings_.get(Sets.MAX_LINE_BUFFER)))

    def updateLogFileLineCount(self,count):
        self._statLabel2_.config(text="Lines in log file " + str(count))

    def updateLogFileInfo(self,info,color,useRootAfter=False):

        if useRootAfter:
            self._root_.after(10,self._updateLogFileInfo_,info,color)
        else:
            self._updateLogFileInfo_(info,color)

    def _updateLogFileInfo_(self,info,color):
        self._statLabel3_.config(text=info,fg=color)



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

# class ReaderWorker:

#     def __init__(self,settings,rootClass,statusFrame):
#         self._settings_ = settings
#         self._root_ = rootClass.root
#         self._statusFrame_ = statusFrame

#         self._readFlag_ = False

#         self._readerThread_ = None

#         self._connectController_ = None

#         self._processWorker_ = None


#     ##############
#     # Public Interface

#     def startWorker(self):

#         if self._processWorker_:
#             if not self._readFlag_:
#                 self._readFlag_ = True
#                 self._readerThread_ = threading.Thread(target=self._readerWorker_,daemon=True,name="Reader")
#                 self._readerThread_.start()
#             else:
#                 traceLog(LogLevel.ERROR,"Not able to start reader thread. Thread already enabled")
#         else:
#             traceLog(LogLevel.ERROR,"Not able to start reader thread. Process worker not set")


#     def stopWorker(self):
#         "Stop reader worker. Will block until thread is done"

#         if self._readFlag_:
#             self._readFlag_ = False

#             if self._readerThread_:
#                 if self._readerThread_.isAlive():
#                     self._readerThread_.join()

#     def linkConnectController(self,connectController):
#         self._connectController_ = connectController

#     def linkWorkers(self,workers):
#         self._processWorker_ = workers.processWorker


#     ##############
#     # Main Worker

#     def _readerWorker_(self):

#         try:
#             with serial.Serial(self._statusFrame_.getSerialPortVar(), 115200, timeout=2) as ser:

#                 # TODO should be done in GUI thread
#                 self._statusFrame_.setStatusLabel("CONNECTED to " + str(ser.name),Sets.STATUS_CONNECT_BACKGROUND_COLOR)
#                 self._connectController_.setAppState(ConnectState.CONNECTED)

#                 try:
#                     while self._readFlag_:

#                         line = ser.readline()
#                         timestamp = datetime.datetime.now()

#                         if line:
#                             inLine = SerialLine(line.decode("utf-8"),timestamp)
#                             self._processWorker_.processQueue.put(inLine)

#                 except serial.SerialException as e:
#                     traceLog(LogLevel.ERROR,"Serial read error: " + str(e))
#                     # Change program state to disconnected
#                     self._root_.after(10,self._connectController_.changeAppState,ConnectState.DISCONNECTED)

#         except serial.SerialException as e:
#             traceLog(LogLevel.ERROR,str(e))
#             # In case other threads are still starting up,
#             # wait for 2 sec
#             # Then change program state to disconnected
#             self._root_.after(2000,self._connectController_.changeAppState,ConnectState.DISCONNECTED)



################################
# Process worker

class ProcessWorker:

    def __init__(self,settings):
        self._settings_ = settings
        self._processFlag_ = False

        self._processThread_ = None
        self.processQueue = queue.Queue()

        self._highlightWorker_ = None
        self._logWriterWorker_ = None

    ##############
    # Public Interface

    def startWorker(self):

        if self._highlightWorker_ and self._logWriterWorker_:
            if not self._processFlag_:
                self._processFlag_ = True
                self._processThread_ = threading.Thread(target=self._processWorker_,daemon=True,name="Process")
                self._processThread_.start()
            else:
                traceLog(LogLevel.ERROR,"Not able to start process thread. Thread already enabled")
        else:
            traceLog(LogLevel.ERROR,"Not able to start process thread. Highlight or logWriter not set")


    def stopWorker(self,emptyQueue=True):
        "Stop process worker. Will block until thread is done"

        if self._processFlag_:
            if emptyQueue:
                self.processQueue.join()

            self._processFlag_ = False

            if self._processThread_:
                if self._processThread_.isAlive():
                    self._processThread_.join()

    def linkWorkers(self,workers):
        self._highlightWorker_ = workers.highlightWorker
        self._logWriterWorker_ = workers.logWriterWorker

    ##############
    # Main Worker

    def _processWorker_(self):

        # Create connect line
        timestamp = datetime.datetime.now()
        timeString = Sets.timeStampBracket[0] + timestamp.strftime("%H:%M:%S") + Sets.timeStampBracket[1]
        connectLine = timeString + Sets.CONNECT_LINE_TEXT
        self._highlightWorker_.highlightQueue.put(connectLine)

        lastTimestamp = 0

        while self._processFlag_:
            try:
                line = self.processQueue.get(True,0.2)
                self.processQueue.task_done()

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

                self._highlightWorker_.highlightQueue.put(newLine)
                self._logWriterWorker_.logQueue.put(newLine)

            except queue.Empty:
                pass




################################
# Highlight worker

class HighlightWorker():

    def __init__(self,settings):
        self._settings_ = settings

        self._lineColorMap_ = dict()

        self._lineBuffer_ = list()

        self._guiWorker_ = None

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

    def linkWorkers(self,workers):
        self._guiWorker_ = workers.guiWorker

    def startWorker(self):

        if self._guiWorker_ != None:
            if not self._highlightFlag_:
                self._highlightFlag_ = True
                self._highlightThread_ = threading.Thread(target=self._highlightWorker_,daemon=True,name="Highlight")
                self._highlightThread_.start()
                # print("Highlight worker started")
            else:
                traceLog(LogLevel.ERROR,"Not able to start higlight thread. Thread already enabled")
        else:
            traceLog(LogLevel.ERROR,"Not able to start higlight thread. Gui worker not defined")

    def stopWorker(self,emptyQueue=True):
        "Stop highlight worker. Will block until thread is done"

        if self._highlightFlag_:
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
                    self._guiWorker_.guiQueue.join()
                    self._guiWorker_.guiEvent.wait()

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

                    self._guiWorker_.guiQueue.put(pLine)

                if self.isReloadingLineBuffer:

                    self._guiWorker_.guiReloadEvent.clear()
                    self.isReloadingLineBuffer = False
                    self._guiWorker_.reloadGuiBuffer()

                    # Wait for gui to have processed new buffer
                    self._guiWorker_.guiReloadEvent.wait()

################################
# Log writer worker

class LogWriterWorker:

    def __init__(self,settings):
        self._settings_ = settings
        self._logFlag_ = False

        self._bottomFrame_ = None

        self._logThread_ = None
        self.logQueue = queue.Queue()

        self.linesInLogFile = 0
        self.lastLogFileInfo = ""

    def linkBottomFrame(self,bottomFrame):
        self._bottomFrame_ = bottomFrame

    def startWorker(self):

        if not self._logFlag_:
            self._logFlag_ = True
            self._logThread_ = threading.Thread(target=self._logWriterWorker_,daemon=True,name="Log")
            self._logThread_.start()
        else:
            traceLog(LogLevel.ERROR,"Not able to start log thread. Thread already enabled")


    def stopWorker(self,emptyQueue=True):
        "Stop log worker. Will block until thread is done"

        if self._logFlag_:

            if emptyQueue:
                self.logQueue.join()

            self._logFlag_ = False

            if self._logThread_:
                if self._logThread_.isAlive():
                    self._logThread_.join()

    def _logWriterWorker_(self):

        timestamp = datetime.datetime.now().strftime(self._settings_.get(Sets.LOG_FILE_TIMESTAMP))

        filename = self._settings_.get(Sets.LOG_FILE_BASE_NAME) + timestamp + ".txt"
        fullFilename = os.path.join(self._settings_.get(Sets.LOG_FILE_PATH),filename)

        os.makedirs(os.path.dirname(fullFilename), exist_ok=True)

        self._bottomFrame_.updateLogFileInfo("Saving to log file: " + filename,"black",useRootAfter=True)

        self.linesInLogFile = 0

        with open(fullFilename,"a") as file:
            while self._logFlag_:
                try:
                    logLine = self.logQueue.get(True,0.2)
                    self.logQueue.task_done()
                    file.write(logLine)
                    self.linesInLogFile += 1
                except queue.Empty:
                    pass

        filesize = os.path.getsize(fullFilename)
        self.lastLogFileInfo = filename + " (Size " + "{:.3f}".format(filesize/1024) + "KB)"

        self._bottomFrame_.updateLogFileInfo("Log file saved: " + self.lastLogFileInfo,"green",useRootAfter=True)

################################
# GUI worker

class GuiWorker:

    def __init__(self,settings,rootClass,search):
        self._settings_ = settings
        self._root_ = rootClass.root
        self._textArea_ = None
        self._bottomFrame_ = None
        self._search_ = search
        self._highlightWorker_ = None
        self._logWriterWorker_ = None

        self._endLine_ = 1

        self.guiQueue = queue.Queue()

        self.guiEvent = threading.Event()
        self.guiEvent.set() # wait will not block

        self.guiReloadEvent = threading.Event()
        self.guiReloadEvent.set()
        self._updateGuiJob_ = None

        self._updateGuiFlag_ = False
        self._reloadGuiBuffer_ = False

    ##############
    # Public Interface

    def linkWorkers(self,workers):
        self._highlightWorker_ = workers.highlightWorker
        self._logWriterWorker_ = workers.logWriterWorker

    def linkTextFrame(self,textFrame):
        self._textArea_ = textFrame.textArea

    def linkBottomFrame(self,bottomFrame):
        self._bottomFrame_ = bottomFrame

    def startWorker(self):

        if self._highlightWorker_ != None and self._logWriterWorker_ != None:
            self._cancelGuiJob_()
            self._updateGuiFlag_ = True
            self._updateGuiJob_ = self._root_.after(50,self._waitForInput_)
        else:
            traceLog(LogLevel.ERROR,"Gui Worker: highlight or logwriter not set.")


    def stopWorker(self):
        "Will block until GUI worker is done. GUI queue is always emptied before stop."

        self._cancelGuiJob_()

        self._updateGuiFlag_ = False
        time.sleep(0.05) # This might not be needed, but is just to be sure that the updateGui function has not started
        self.guiEvent.wait()

    def reloadGuiBuffer(self):
        self._reloadGuiBuffer_ = True

    ##############
    # Internal

    def _insertLine_(self,newLine):

        # Control window scolling
        bottomVisibleLine = int(self._textArea_.index("@0,%d" % self._textArea_.winfo_height()).split(".")[0])
        self._endLine_ = int(self._textArea_.index(tk.END).split(".")[0])
        self._textArea_.insert(tk.END, newLine)
        if (bottomVisibleLine >= (self._endLine_-1)):
            self._textArea_.see(tk.END)

        # Limit number of lines in window
        if self._endLine_ > self._settings_.get(Sets.MAX_LINE_BUFFER):
            self._textArea_.delete(1.0,2.0)

    def _updateLastLine_(self,newLine):
        lastline = self._textArea_.index("end-2c").split(".")[0]
        self._textArea_.delete(lastline + ".0",lastline +".0+1l")
        self._textArea_.insert(lastline + ".0", newLine)
        # I don't think there is a need for scrolling?

    ##############
    # Main Worker

    def _updateGUI_(self):

        reloadInitiated = False

        receivedLines = list()

        if not self._highlightWorker_.isReloadingLineBuffer:

            try:
                # We have to make sure that the queue is empty before continuing
                while True:
                    receivedLines.append(self.guiQueue.get_nowait())
                    self.guiQueue.task_done()


            except queue.Empty:

                # Open text widget for editing
                self._textArea_.config(state=tk.NORMAL)

                if self._reloadGuiBuffer_:
                    self._reloadGuiBuffer_ = False
                    reloadInitiated = True
                    linesToReload = len(receivedLines)
                    traceLog(LogLevel.DEBUG,"Reload GUI buffer (Len " + str(linesToReload) + ")")

                    # Clear window
                    self._textArea_.delete(1.0,tk.END)

                for msg in receivedLines:
                    if msg.updatePreviousLine:
                        self._updateLastLine_(msg.line)
                    else:
                        self._insertLine_(msg.line)

                    # Highlight/color text
                    lastline = self._textArea_.index("end-2c").split(".")[0]
                    for lineTag in msg.lineTags:
                        self._textArea_.tag_add(lineTag[0],lastline + "." + str(lineTag[1]),lastline + "." + str(lineTag[2]))

                # Disable text widget edit
                self._textArea_.config(state=tk.DISABLED)

            if receivedLines:
                self._bottomFrame_.updateWindowBufferLineCount(self._endLine_-1)
                self._bottomFrame_.updateLogFileLineCount("Lines in log file " + str(self._logWriterWorker_.linesInLogFile))

                self._search_.search(searchStringUpdated=False)

            if reloadInitiated:
                self.guiReloadEvent.set()
                traceLog(LogLevel.DEBUG,"Reload GUI buffer done")



    def _cancelGuiJob_(self):
        if self._updateGuiJob_ is not None:
            self._root_.after_cancel(self._updateGuiJob_)
            self._updateGuiJob_ = None

    def _waitForInput_(self):
        if self._updateGuiFlag_:
            self.guiEvent.clear()
            self._updateGUI_()
            self.guiEvent.set()
            self._updateGuiJob_ = self._root_.after(100,self._waitForInput_)


class Workers:

    def __init__(self,readerWorker,processWorker,logWriterWorker,highlightWorker,guiWorker):
        self.readerWorker = readerWorker
        self.processWorker = processWorker
        self.logWriterWorker = logWriterWorker
        self.highlightWorker = highlightWorker
        self.guiWorker = guiWorker

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

# Settings
SETTINGS_FILE_NAME_ = "CTsettings.json"
settings_ = Sets.Settings(SETTINGS_FILE_NAME_)
settings_.reload()

# Root
rootClass_ = RootClass(settings_)

# Main Controllers
connectController_ = ConnectController(settings_,rootClass_)

# Views
search_ = search.Search(settings_)
optionsView_ = optionsView.OptionsView(settings_,rootClass_)
statusFrame_ = StatusFrame(settings_,rootClass_,search_,optionsView_)
textFrame_ = TextFrame(settings_,rootClass_)
bottomFrame_ = BottomFrame(settings_,rootClass_)

# Workers
readerWorker_ = readerWorker.ReaderWorker(settings_,rootClass_,statusFrame_)
processWorker_ = ProcessWorker(settings_)
logWriterWorker_ = LogWriterWorker(settings_)
highlightWorker_ = HighlightWorker(settings_)
guiWorker_ = GuiWorker(settings_,rootClass_,search_)

# Common class with link to all workers
workers_ = Workers(readerWorker_,processWorker_,logWriterWorker_,highlightWorker_,guiWorker_)


# Link modules
rootClass_.linkConnectController(connectController_)

search_.linkTextFrame(textFrame_)

optionsView_.linkTextFrame(textFrame_)
optionsView_.linkWorkers(workers_)

statusFrame_.linkTextFrame(textFrame_)
statusFrame_.linkBottomFrame(bottomFrame_)
statusFrame_.linkConnectController(connectController_)
statusFrame_.linkWorkers(workers_)

textFrame_.linkWorkers(workers_)

connectController_.linkStatusFrame(statusFrame_)
connectController_.linkWorkers(workers_)

readerWorker_.linkConnectController(connectController_)
readerWorker_.linkWorkers(workers_)

processWorker_.linkWorkers(workers_)

logWriterWorker_.linkBottomFrame(bottomFrame_)

highlightWorker_.linkWorkers(workers_)

guiWorker_.linkTextFrame(textFrame_)
guiWorker_.linkBottomFrame(bottomFrame_)
guiWorker_.linkWorkers(workers_)


# Start
highlightWorker_.startWorker()
guiWorker_.startWorker()

textFrame_.createTextFrameLineColorTag()

# def down(e):
#     print("DOWN raw: " + str(e))
#     print("DOWN: " + e.char)
    # if e.char == 'n':
        # pass

# def up(e):
#     print("UP: " + e.char)

rootClass_.root.bind('<Control-f>', search_.show)
# root.bind('<KeyPress>', down)
# root.bind('<KeyRelease>', up)



traceLog(LogLevel.INFO,"Main loop started")

rootClass_.root.mainloop()

traceLog(LogLevel.INFO,"Main loop done")