
import os
import io
import sys
import argparse

import tkinter as tk
# from tkinter import messagebox

import datetime

import threading

# import multiprocessing.connection as multi_con


# ColorTerminal
from traceLog import traceLog,LogLevel
import settings as Sets
from customTypes import ConnectState
# import search
from views import mainView, fileView, optionsView

from workers import readerWorker, processWorker, logWriterWorker, highlightWorker, guiWorker

import comManager

################################
# Version information

VERSION_ = "1.2.0"

################################
# Icon

RELATIVE_ICON_PATH_ = r"resources\Icon03.ico"

################################
# Connection Controller

class ConnectController:

    def __init__(self,settings,mainView):
        self._settings = settings
        self._mainView = mainView
        self._root = mainView.root

        self._closeProgram = False

        self._readerWorker = None
        self._processWorker = None
        self._logWriterWorker = None
        self._highlightWorker = None
        self._guiWorker = None

        self._appState = ConnectState.DISCONNECTED

    def linkWorkers(self,workers):
        self._readerWorker = workers.readerWorker
        self._processWorker = workers.processWorker
        self._logWriterWorker = workers.logWriterWorker
        self._highlightWorker = workers.highlightWorker
        self._guiWorker = workers.guiWorker

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
            self._root.after(100,self._mainView.destroyWindow)

    def getAppState(self):
        return self._appState

    def changeAppState(self,newState:ConnectState,extraInfo=""):

        self._appState = newState

        if newState == ConnectState.CONNECTING:
            self._mainView.controlFrame.setConnectButtonText("Disconnect")
            self._mainView.controlFrame.disableConnectButtons()
            self._mainView.controlFrame.disablePortButtons()
            self.connectSerial()
            self._mainView.controlFrame.setStatusLabel("CONNECTING...",Sets.STATUS_WORKING_BACKGROUND_COLOR)

        elif newState == ConnectState.CONNECTED:
            self._mainView.controlFrame.setConnectButtonText("Disconnect")
            self._mainView.controlFrame.enableConnectButtons()
            self._mainView.controlFrame.disablePortButtons()
            self._mainView.controlFrame.setStatusLabel("CONNECTED to " + str(extraInfo),Sets.STATUS_CONNECT_BACKGROUND_COLOR)

        elif newState == ConnectState.DISCONNECTING:
            self._mainView.controlFrame.setConnectButtonText("Connect")
            self._mainView.controlFrame.disableConnectButtons()
            self._mainView.controlFrame.disablePortButtons()
            self.disconnectSerial()
            self._mainView.controlFrame.setStatusLabel("DISCONNECTING...",Sets.STATUS_WORKING_BACKGROUND_COLOR)

        elif newState == ConnectState.DISCONNECTED:
            self._mainView.controlFrame.setConnectButtonText("Connect")
            self._mainView.controlFrame.enableConnectButtons()
            self._mainView.controlFrame.enablePortButtons()
            self._mainView.controlFrame.setStatusLabel("DISCONNECTED",Sets.STATUS_DISCONNECT_BACKGROUND_COLOR)

################################
# Text frame manager

class TextFrameManager:

    def __init__(self):
        pass
        self.textFrames = list()

    def registerTextFrame(self,textFrame):
        if not textFrame in self.textFrames:
             self.textFrames.append(textFrame)

    def unregisterTextFrame(self,textFrame):
        if textFrame in self.textFrames:
            self.textFrames.remove(textFrame)

    def getTextFrames(self):
        return self.textFrames

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

stdoutFilePath_ = "CTstdout.txt"

parser = argparse.ArgumentParser()
parser.add_argument("-c","--enableConsole",help="send stdout and stderr to console, otherwise this is written to " + stdoutFilePath_,action="store_true")
parser.add_argument("logFilePath",metavar="Path",nargs="?",help="(optional) path of logfile to open ",default="")
args = parser.parse_args()

if not args.enableConsole:
    tempStdout_ = io.StringIO()
    sys.stdout = sys.stderr = tempStdout_

################################################################
################################################################

# PyInstaller bundle check

iconPath_ = RELATIVE_ICON_PATH_
isRunningPython_ = True

if hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS'):
    traceLog(LogLevel.INFO,"Running in a PyInstaller bundle")
    bundle_dir = getattr(sys,'_MEIPASS')
    iconPath_ = os.path.join(bundle_dir,RELATIVE_ICON_PATH_)
    isRunningPython_ = False
else:
    traceLog(LogLevel.INFO,"Running in a normal Python process")

################################################################
################################################################

# ColorTerminal home

homePathFull_ = os.getcwd()
if isRunningPython_:
    CT_HOME_ENV_VARIABLE = "CT_HOME_PYTHON"
else:
    CT_HOME_ENV_VARIABLE = "CT_HOME"

ctHomeEnvVarFound_ = CT_HOME_ENV_VARIABLE in os.environ
if ctHomeEnvVarFound_:
    homePathFull_ = os.environ[CT_HOME_ENV_VARIABLE]
    traceLog(LogLevel.INFO,"Environment variable %s found: %s" % (CT_HOME_ENV_VARIABLE, str(homePathFull_)))
else:
    traceLog(LogLevel.INFO,"Environment variable %s not found. Assuming home is: %s" % (CT_HOME_ENV_VARIABLE, str(homePathFull_)))
    traceLog(LogLevel.INFO,"    Not able to launch file viewer from explorer")

# Check of ColorTerminal can be found in home path
mainApplicationFound = False
for item in os.listdir(homePathFull_):
    if item == "colorterminal":
        mainApplicationFound = True
        traceLog(LogLevel.INFO,"Main application found in home path")
        break

if not mainApplicationFound:
    traceLog(LogLevel.ERROR,"ColorTerminal application not found at home path: " + str(homePathFull_))
    input("Press Enter to exit...")
    sys.exit()

# Setup requiring home path
iconPathFull_ = os.path.join(homePathFull_,iconPath_)

if not args.enableConsole:
    stdoutFilePathFull_ = os.path.join(homePathFull_,stdoutFilePath_)
    stdoutFile = open(stdoutFilePathFull_,"a")

    # Copy temp output to file
    stdoutFile.write(tempStdout_.getvalue())
    tempStdout_.close()

    sys.stdout = sys.stderr = stdoutFile


################################################################
################################################################

# Settings
SETTINGS_FILE_NAME_ = "CTsettings.json"
settingsFileFullPath = os.path.join(homePathFull_,SETTINGS_FILE_NAME_)
settings_ = Sets.Settings(settingsFileFullPath)
settings_.reload()

settings_.setOption(Sets.CT_HOMEPATH_FULL,homePathFull_)
settings_.setOption(Sets.ICON_PATH_FULL,iconPathFull_)

################################################################
################################################################

# Open message listener
comManager_ = comManager.ComManager(settings_,ctHomeEnvVarFound_,args.logFilePath)
if not comManager_.isListenerRegistered():
    # Application already running, exit
    sys.exit()

################################################################
################################################################



# Communication Controller (used to communicate update to text frames)
textFrameManager_ = TextFrameManager()

# Main View (root)
mainView_ = mainView.MainView(settings_,VERSION_,textFrameManager_)

# Main Controllers
connectController_ = ConnectController(settings_,mainView_)

# Workers
readerWorker_ = readerWorker.ReaderWorker(settings_,mainView_)
processWorker_ = processWorker.ProcessWorker(settings_)
logWriterWorker_ = logWriterWorker.LogWriterWorker(settings_,mainView_)
highlightWorker_ = highlightWorker.HighlightWorker(settings_,mainView_)
guiWorker_ = guiWorker.GuiWorker(settings_,mainView_)
# Common class with link to all workers
workers_ = Workers(readerWorker_,processWorker_,logWriterWorker_,highlightWorker_,guiWorker_)

################################
# Link modules
mainView_.linkConnectController(connectController_)
mainView_.linkWorkers(workers_)

comManager_.linkExternalConnectors(mainView_,textFrameManager_)

connectController_.linkWorkers(workers_)

readerWorker_.linkConnectController(connectController_)
readerWorker_.linkWorkers(workers_)
processWorker_.linkWorkers(workers_)
highlightWorker_.linkWorkers(workers_)
guiWorker_.linkWorkers(workers_)

################################
# Start
highlightWorker_.startWorker()
guiWorker_.startWorker()

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

# mainView_.root.bind('<Control-n>', addDataToProcessQueue)


traceLog(LogLevel.INFO,"Main loop started")

mainView_.root.mainloop()

traceLog(LogLevel.INFO,"Main loop done")

################################
# Cleanup


if not args.enableConsole:
    sys.stdout.close()