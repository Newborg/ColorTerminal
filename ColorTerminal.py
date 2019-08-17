
import os
import sys
import argparse

import tkinter as tk
from tkinter import messagebox

import datetime

import threading

# ColorTerminal
from traceLog import traceLog,LogLevel
import settings as Sets
from customTypes import ConnectState
import optionsView
import search

from views import controlFrame, textFrame, bottomFrame

from workers import readerWorker, processWorker, logWriterWorker, highlightWorker, guiWorker

################################
# Version information

VERSION_ = "1.0.2"

################################
# Icon

RELATIVE_ICON_PATH_ = r"icons\Icon03.ico"

################################
# Connection Controller

class ConnectController:

    def __init__(self,settings,rootClass):
        self._settings = settings
        self._rootClass = rootClass
        self._root = rootClass.root

        self._closeProgram = False

        self._readerWorker = None
        self._processWorker = None
        self._logWriterWorker = None
        self._highlightWorker = None
        self._guiWorker = None

        self._controlFrame = None

        self._appState = ConnectState.DISCONNECTED

    def linkWorkers(self,workers):
        self._readerWorker = workers.readerWorker
        self._processWorker = workers.processWorker
        self._logWriterWorker = workers.logWriterWorker
        self._highlightWorker = workers.highlightWorker
        self._guiWorker = workers.guiWorker

    def linkControlFrame(self,controlFrame):
        self._controlFrame = controlFrame

    def connectSerial(self):

        traceLog(LogLevel.INFO,"Connect to serial")

        if self._readerWorker:
            self._readerWorker.startWorker()

        if self._processWorker:
            self._processWorker.startWorker()

        if self._logWriterWorker:
            self._logWriterWorker.startWorker()


    def disconnectSerial(self,close=False):
        self._closeProgram = close
        # Disconnect will block, so must be done in different thread
        disconnectThread = threading.Thread(target=self._disconnectSerialProcess,name="Disconnect")
        disconnectThread.start()

    def _disconnectSerialProcess(self):
        traceLog(LogLevel.INFO,"Disconnect from serial")

        # Stop serial reader
        self._readerWorker.stopWorker()

        # Empty process queue and stop process thread
        self._processWorker.stopWorker()

        # Empty log queue and stop log writer thread
        self._logWriterWorker.stopWorker()

        # Add disconnect line if connected
        if self._appState == ConnectState.DISCONNECTING:
            timestamp = datetime.datetime.now()
            timeString = Sets.timeStampBracket[0] + timestamp.strftime("%H:%M:%S") + Sets.timeStampBracket[1]

            disconnectLine = timeString + Sets.disconnectLineText + self._logWriterWorker.lastLogFileInfo + "\n"

            self._highlightWorker.highlightQueue.put(disconnectLine)


        traceLog(LogLevel.INFO,"Main worker threads stopped")

        self.changeAppState(ConnectState.DISCONNECTED)

        if self._closeProgram:

            self._highlightWorker.stopWorker(emptyQueue=False)

            self._guiWorker.stopWorker()

            # Close tkinter window (close program)
            self._root.after(100,self._rootClass.destroyWindow)

    def getAppState(self):
        return self._appState

    def changeAppState(self,newState:ConnectState,extraInfo=""):

        self._appState = newState

        if newState == ConnectState.CONNECTING:
            self._controlFrame.setConnectButtonText("Disconnect")
            self._controlFrame.disableConnectButtons()
            self._controlFrame.disablePortButtons()
            self.connectSerial()
            self._controlFrame.setStatusLabel("CONNECTING...",Sets.STATUS_WORKING_BACKGROUND_COLOR)

        elif newState == ConnectState.CONNECTED:
            self._controlFrame.setConnectButtonText("Disconnect")
            self._controlFrame.enableConnectButtons()
            self._controlFrame.disablePortButtons()
            self._controlFrame.setStatusLabel("CONNECTED to " + str(extraInfo),Sets.STATUS_CONNECT_BACKGROUND_COLOR)

        elif newState == ConnectState.DISCONNECTING:
            self._controlFrame.setConnectButtonText("Connect")
            self._controlFrame.disableConnectButtons()
            self._controlFrame.disablePortButtons()
            self.disconnectSerial()
            self._controlFrame.setStatusLabel("DISCONNECTING...",Sets.STATUS_WORKING_BACKGROUND_COLOR)

        elif newState == ConnectState.DISCONNECTED:
            self._controlFrame.setConnectButtonText("Connect")
            self._controlFrame.enableConnectButtons()
            self._controlFrame.enablePortButtons()
            self._controlFrame.setStatusLabel("DISCONNECTED",Sets.STATUS_DISCONNECT_BACKGROUND_COLOR)


################################
# Root frame

class RootClass:

    def __init__(self,settings,iconPath):
        self._settings_ = settings

        self.root = tk.Tk()

        self.root.iconbitmap(iconPath)

        self._connectController_ = None

        self.root.protocol("WM_DELETE_WINDOW", self._onClosing_)

        self.root.title("Color Terminal v" + VERSION_)
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
# Workers

class Workers:

    def __init__(self,readerWorker,processWorker,logWriterWorker,highlightWorker,guiWorker):
        self.readerWorker = readerWorker
        self.processWorker = processWorker
        self.logWriterWorker = logWriterWorker
        self.highlightWorker = highlightWorker
        self.guiWorker = guiWorker


################################################################
################################################################

# Input arguments and stdout control

stdoutFile = "CTstdout.txt"

parser = argparse.ArgumentParser()
parser.add_argument("-c","--enableConsole",help="send stdout and stderr to console, otherwise this is written to " + stdoutFile,action="store_true")
args = parser.parse_args()

if not args.enableConsole:
    sys.stdout = sys.stderr = open(stdoutFile,"a")    

################################################################
################################################################

# PyInstaller bundle check

iconPath_ = RELATIVE_ICON_PATH_

if hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS'):
    traceLog(LogLevel.INFO,"Running in a PyInstaller bundle")    
    bundle_dir = getattr(sys,'_MEIPASS')    
    iconPath_ = os.path.join(bundle_dir,RELATIVE_ICON_PATH_)    
else:    
    traceLog(LogLevel.INFO,"Running in a normal Python process")    

################################################################
################################################################



# Settings
SETTINGS_FILE_NAME_ = "CTsettings.json"
settings_ = Sets.Settings(SETTINGS_FILE_NAME_)
settings_.reload()

# Root
rootClass_ = RootClass(settings_,iconPath_)

# Main Controllers
connectController_ = ConnectController(settings_,rootClass_)

# Views
search_ = search.Search(settings_)
optionsView_ = optionsView.OptionsView(settings_,rootClass_,iconPath_)
controlFrame_ = controlFrame.ControlFrame(settings_,rootClass_,search_,optionsView_)
textFrame_ = textFrame.TextFrame(settings_,rootClass_,iconPath_)
bottomFrame_ = bottomFrame.BottomFrame(settings_,rootClass_)

# Workers
readerWorker_ = readerWorker.ReaderWorker(settings_,rootClass_,controlFrame_)
processWorker_ = processWorker.ProcessWorker(settings_)
logWriterWorker_ = logWriterWorker.LogWriterWorker(settings_)
highlightWorker_ = highlightWorker.HighlightWorker(settings_)
guiWorker_ = guiWorker.GuiWorker(settings_,rootClass_,search_)
# Common class with link to all workers
workers_ = Workers(readerWorker_,processWorker_,logWriterWorker_,highlightWorker_,guiWorker_)

################################
# Link modules
rootClass_.linkConnectController(connectController_)

search_.linkTextFrame(textFrame_)
search_.linkWorkers(workers_)

optionsView_.linkTextFrame(textFrame_)
optionsView_.linkWorkers(workers_)

controlFrame_.linkTextFrame(textFrame_)
controlFrame_.linkBottomFrame(bottomFrame_)
controlFrame_.linkConnectController(connectController_)
controlFrame_.linkWorkers(workers_)

textFrame_.linkWorkers(workers_)

connectController_.linkControlFrame(controlFrame_)
connectController_.linkWorkers(workers_)

readerWorker_.linkConnectController(connectController_)
readerWorker_.linkWorkers(workers_)

processWorker_.linkWorkers(workers_)

logWriterWorker_.linkBottomFrame(bottomFrame_)

highlightWorker_.linkWorkers(workers_)
highlightWorker_.linkTextFrame(textFrame_)

guiWorker_.linkTextFrame(textFrame_)
guiWorker_.linkBottomFrame(bottomFrame_)
guiWorker_.linkWorkers(workers_)

################################
# Start
highlightWorker_.startWorker()
guiWorker_.startWorker()

rootClass_.root.bind('<Control-f>', search_.show)


import renameFileView


# TESTING
# def down(e):
#     print("DOWN raw: " + str(e))
#     print("DOWN: " + e.char)
#     if e.char == 'n':
#         addDataToProcessQueue()
#         pass

# def up(e):
#     print("UP: " + e.char)

# rootClass_.root.bind('<KeyPress>', down)
# rootClass_.root.bind('<KeyRelease>', up)




# BULK DATA LOAD FOR DEBUG

# _logFile = r"_testing\log_example_small.txt"

# from customTypes import SerialLine

# def addDataToProcessQueue(*args):
#     with open(_logFile,"r") as file:
#         lines = file.readlines()

#     print("Debug, lines loaded: " + str(len(lines)))

#     linesToAdd = 3500

#     loops = int(linesToAdd / len(lines))

#     for _ in range(loops):
#         for line in lines:
#             timestamp = datetime.datetime.now()
#             inLine = SerialLine(line,timestamp)
#             processWorker_.processQueue.put(inLine)

#     print("Debug, lines added to view: " + str(loops*len(lines)))

# rootClass_.root.bind('<Control-n>', addDataToProcessQueue)


traceLog(LogLevel.INFO,"Main loop started")

rootClass_.root.mainloop()

traceLog(LogLevel.INFO,"Main loop done")

if not args.enableConsole:
    sys.stdout.close()