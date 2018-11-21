
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

        self._controlFrame_ = None

        self._appState_ = ConnectState.DISCONNECTED

    def linkWorkers(self,workers):
        self._readerWorker_ = workers.readerWorker
        self._processWorker_ = workers.processWorker
        self._logWriterWorker_ = workers.logWriterWorker
        self._highlightWorker_ = workers.highlightWorker
        self._guiWorker_ = workers.guiWorker

    def linkControlFrame(self,controlFrame):
        self._controlFrame_ = controlFrame

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

        self._controlFrame_.setStatusLabel("DISCONNECTED",Sets.STATUS_DISCONNECT_BACKGROUND_COLOR)
        self._controlFrame_.enablePortButtons()
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
            self._controlFrame_.setConnectButtonText("Disconnect")
            self.connectSerial()
            self._controlFrame_.setStatusLabel("CONNECTING...",Sets.STATUS_WORKING_BACKGROUND_COLOR)
            self._controlFrame_.disablePortButtons()

        elif state == ConnectState.DISCONNECTED:
            self._controlFrame_.setConnectButtonText("Connect")
            self.disconnectSerial()
            self._controlFrame_.setStatusLabel("DISCONNECTING...",Sets.STATUS_WORKING_BACKGROUND_COLOR)
            self._controlFrame_.disablePortButtons()

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
controlFrame_ = controlFrame.ControlFrame(settings_,rootClass_,search_,optionsView_)
textFrame_ = textFrame.TextFrame(settings_,rootClass_)
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
