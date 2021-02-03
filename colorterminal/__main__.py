
import os
import io
import sys
import argparse

from tkinter import messagebox

import datetime

import threading

# import multiprocessing.connection as multi_con


# ColorTerminal
from traceLog import traceLog,LogLevel
import settings as Sets
from customTypes import ConnectState
from views import mainView

from workers import readerWorker, processWorker, logWriterWorker, highlightWorker, guiWorker

import comManager

################################
# Version information

VERSION_ = "1.2.3"

################################
# Icon

RELATIVE_ICON_PATH = r"resources\Icon03.ico"

################################
# Connection Controller

class ConnectController:

    def __init__(self,settings,mainView_):
        self._settings = settings
        self._mainView = mainView_
        self._root = mainView_.root

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

    def __init__(self,readerWorker_,processWorker_,logWriterWorker_,highlightWorker_,guiWorker_):
        self.readerWorker = readerWorker_
        self.processWorker = processWorker_
        self.logWriterWorker = logWriterWorker_
        self.highlightWorker = highlightWorker_
        self.guiWorker = guiWorker_




################################################################
################################################################

# Input arguments and stdout control

stdoutFilePath = "CTstdout.txt"

parser = argparse.ArgumentParser()
parser.add_argument("-c","--enableConsole",help="send stdout and stderr to console, otherwise this is written to " + stdoutFilePath,action="store_true")
parser.add_argument("logFilePath",metavar="Path",nargs="?",help="(optional) path of logfile to open ",default="")
args = parser.parse_args()

if not args.enableConsole:
    tempStdout = io.StringIO()
    sys.stdout = sys.stderr = tempStdout

################################################################
################################################################

# PyInstaller bundle check

iconPath_ = RELATIVE_ICON_PATH
isRunningPython = True

if hasattr(sys, 'frozen') and hasattr(sys, '_MEIPASS'):
    traceLog(LogLevel.INFO,"Running in a PyInstaller bundle")
    bundle_dir = getattr(sys,'_MEIPASS')
    iconPath_ = os.path.join(bundle_dir,RELATIVE_ICON_PATH)
    isRunningPython = False
else:
    traceLog(LogLevel.INFO,"Running in a normal Python process")

################################################################
################################################################

# ColorTerminal home

homePathFull = os.getcwd()
if isRunningPython:
    CT_HOME_ENV_VARIABLE = "CT_HOME_PYTHON"
else:
    CT_HOME_ENV_VARIABLE = "CT_HOME"

ctHomeEnvVarFound_ = CT_HOME_ENV_VARIABLE in os.environ
if ctHomeEnvVarFound_:
    homePathFull = os.environ[CT_HOME_ENV_VARIABLE]
    traceLog(LogLevel.INFO,"Environment variable %s found: %s" % (CT_HOME_ENV_VARIABLE, str(homePathFull)))
else:
    traceLog(LogLevel.INFO,"Environment variable %s not found. Assuming home is: %s" % (CT_HOME_ENV_VARIABLE, str(homePathFull)))
    traceLog(LogLevel.INFO,"    Not able to launch file viewer from explorer")

# Check of ColorTerminal can be found in home path
mainApplicationFound = False
for item in os.listdir(homePathFull):
    if isRunningPython:
        if os.path.isdir(os.path.join(homePathFull,item)):
            if item == "colorterminal":
                mainApplicationFound = True
                traceLog(LogLevel.INFO,"Main python application found in home path")
                break
    else:
        if item == "ColorTerminal.exe":
            mainApplicationFound = True
            traceLog(LogLevel.INFO,"Main exe application found in home path")
            break

if not mainApplicationFound:

    message = "ColorTerminal application not found in home path: %s" % homePathFull

    if args.enableConsole:
        traceLog(LogLevel.ERROR,message)

    extendedMessage = message + "\n\nPlease launch application from the correct folder or set the %s environment variable\n\nStartup cancelled" % CT_HOME_ENV_VARIABLE
    messagebox.showerror(title="ColorTerminal Error", message=extendedMessage)
    sys.exit()

# Setup requiring home path
iconPathFull = os.path.join(homePathFull,iconPath_)

if not args.enableConsole:
    stdoutFilePathFull_ = os.path.join(homePathFull,stdoutFilePath)
    stdoutFile = open(stdoutFilePathFull_,"a",buffering=1)

    # Copy temp output to file
    stdoutFile.write(tempStdout.getvalue())
    tempStdout.close()

    sys.stdout = sys.stderr = stdoutFile


################################################################
################################################################

# Settings
settingsObjFILE_NAME_ = "CTsettings.json"
settingsFileFullPath = os.path.join(homePathFull,settingsObjFILE_NAME_)
settingsObj = Sets.Settings(settingsFileFullPath)
settingsObj.reload()

settingsObj.setOption(Sets.CT_HOMEPATH_FULL,homePathFull)
settingsObj.setOption(Sets.ICON_PATH_FULL,iconPathFull)

################################################################
################################################################

# Open message listener
comManager_ = comManager.ComManager(settingsObj,ctHomeEnvVarFound_,args.logFilePath)
if not comManager_.isListenerRegistered():
    # Application already running, exit
    sys.exit()

################################################################
################################################################



# Communication Controller (used to communicate update to text frames)
textFrameManagerObj = TextFrameManager()

# Main View (root)
mainViewObj = mainView.MainView(settingsObj,VERSION_,textFrameManagerObj)

# Main Controllers
connectControllerObj = ConnectController(settingsObj,mainViewObj)

# Workers
readerWorkerObj = readerWorker.ReaderWorker(settingsObj,mainViewObj)
processWorkerObj = processWorker.ProcessWorker(settingsObj)
logWriterWorkerObj = logWriterWorker.LogWriterWorker(settingsObj,mainViewObj)
highlightWorkerObj = highlightWorker.HighlightWorker(settingsObj,mainViewObj)
guiWorkerObj = guiWorker.GuiWorker(settingsObj,mainViewObj)
# Common class with link to all workers
workersObj = Workers(readerWorkerObj,processWorkerObj,logWriterWorkerObj,highlightWorkerObj,guiWorkerObj)

################################
# Link modules
mainViewObj.linkConnectController(connectControllerObj)
mainViewObj.linkWorkers(workersObj)

comManager_.linkExternalConnectors(mainViewObj,textFrameManagerObj)

connectControllerObj.linkWorkers(workersObj)

readerWorkerObj.linkConnectController(connectControllerObj)
readerWorkerObj.linkWorkers(workersObj)
processWorkerObj.linkWorkers(workersObj)
highlightWorkerObj.linkWorkers(workersObj)
guiWorkerObj.linkWorkers(workersObj)

################################
# Start
highlightWorkerObj.startWorker()
guiWorkerObj.startWorker()

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
#             processWorkerObj.processQueue.put(inLine)

#     print("Debug, lines added to view: " + str(loops*len(lines)))

# mainViewObj.root.bind('<Control-n>', addDataToProcessQueue)


traceLog(LogLevel.INFO,"Main loop started")

mainViewObj.root.mainloop()

traceLog(LogLevel.INFO,"Main loop done")

################################
# Cleanup


if not args.enableConsole:
    sys.stdout.close()