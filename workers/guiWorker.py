import queue
import threading
import time

import tkinter as tk

from traceLog import traceLog,LogLevel
import settings as Sets

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