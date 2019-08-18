import queue
import threading
import time

import tkinter as tk

from traceLog import traceLog,LogLevel
import settings as Sets

class GuiWorker:

    def __init__(self,settings,mainView):
        self._settings = settings
        self._mainView = mainView
        self._root = mainView.root
        
        self._textArea = mainView.textFrame.textArea
        
        self._highlightWorker = None
        self._logWriterWorker = None

        self._scrollingEnabled = True

        self.guiQueue = queue.Queue()

        self.guiEvent = threading.Event()
        self.guiEvent.set() # wait will not block

        self.guiReloadEvent = threading.Event()
        self.guiReloadEvent.set()
        self._updateGuiJob = None

        self._updateGuiFlag = False
        self._reloadGuiBuffer = False

    ##############
    # Public Interface

    def linkWorkers(self,workers):
        self._highlightWorker = workers.highlightWorker
        self._logWriterWorker = workers.logWriterWorker

    def startWorker(self):

        if self._highlightWorker != None and self._logWriterWorker != None:
            if not self._updateGuiFlag:
                self._cancelGuiJob()
                self._updateGuiFlag = True
                self._updateGuiJob = self._root.after(50,self._waitForInput)
            # else:
            #     traceLog(LogLevel.ERROR,"Not able to start gui thread. Thread already enabled")
        else:
            traceLog(LogLevel.ERROR,"Gui Worker: highlight or logwriter not set.")


    def stopWorker(self):
        "Will block until GUI worker is done. GUI queue is always emptied before stop."

        self._cancelGuiJob()
        self._updateGuiFlag = False
        self.guiEvent.wait()

    def reloadGuiBuffer(self):
        self._reloadGuiBuffer = True

    def enableScrolling(self):
        self._scrollingEnabled = True

    def disableScrolling(self):
        self._scrollingEnabled = False

    ##############
    # Internal

    def _insertLine(self,newLine):

        # Control window scolling
        bottomVisibleLine = int(self._textArea.index("@0,%d" % self._textArea.winfo_height()).split(".")[0])
        endLine = int(self._textArea.index(tk.END).split(".")[0])

        self._textArea.insert(tk.END, newLine)
        if self._scrollingEnabled and (bottomVisibleLine >= (endLine-2)):
            self._textArea.see(tk.END)

        # Limit number of lines in window
        if (endLine-1) > self._settings.get(Sets.TEXTAREA_MAX_LINE_BUFFER):
            self._textArea.delete(1.0,2.0)

    def _updateLastLine(self,newLine):
        lastline = self._textArea.index("end-2c").split(".")[0]
        self._textArea.delete(lastline + ".0",lastline +".0+1l")
        self._textArea.insert(lastline + ".0", newLine)
        # I don't think there is a need for scrolling?

    ##############
    # Main Worker

    def _updateGUI(self):

        reloadInitiated = False

        receivedLines = list()

        if not self._highlightWorker.isReloadingLineBuffer:

            lastline = 0

            lastLineAtStart = int(self._textArea.index("end-2c").split(".")[0])
            linesInserted = 0

            try:
                # We have to make sure that the queue is empty before continuing
                while True:
                    receivedLines.append(self.guiQueue.get_nowait())
                    self.guiQueue.task_done()


            except queue.Empty:

                # Open text widget for editing
                self._textArea.config(state=tk.NORMAL)

                if self._reloadGuiBuffer:
                    self._reloadGuiBuffer = False
                    reloadInitiated = True
                    linesToReload = len(receivedLines)
                    traceLog(LogLevel.DEBUG,"Reload GUI buffer (Len " + str(linesToReload) + ")")

                    # Clear window
                    self._textArea.delete(1.0,tk.END)

                for msg in receivedLines:
                    if msg.updatePreviousLine:
                        self._updateLastLine(msg.line)
                    else:
                        self._insertLine(msg.line)
                        linesInserted += 1

                    # Highlight/color text
                    lastline = self._textArea.index("end-2c").split(".")[0]
                    for lineTag in msg.lineTags:
                        self._textArea.tag_add(lineTag[0],lastline + "." + str(lineTag[1]),lastline + "." + str(lineTag[2]))

                # Disable text widget edit
                self._textArea.config(state=tk.DISABLED)

            lastLineAtEnd = int(self._textArea.index("end-2c").split(".")[0])

            if receivedLines:
                self._mainView.bottomFrame.updateWindowBufferLineCount(lastline)
                self._mainView.bottomFrame.updateLogFileLineCount(self._logWriterWorker.linesInLogFile)

                numberOfLinesDeleted = linesInserted - (lastLineAtEnd - lastLineAtStart)
                self._mainView.textFrame.searchLinesAdded(numberOfLinesAdded=linesInserted,numberOfLinesDeleted=numberOfLinesDeleted,lastLine=lastLineAtEnd)

            if reloadInitiated:
                self.guiReloadEvent.set()
                traceLog(LogLevel.DEBUG,"Reload GUI buffer done")



    def _cancelGuiJob(self):
        if self._updateGuiJob:
            self._root.after_cancel(self._updateGuiJob)
            self._updateGuiJob = None

    def _waitForInput(self):
        self.guiEvent.clear()
        if self._updateGuiFlag:
            self._updateGUI()
            self._updateGuiJob = self._root.after(100,self._waitForInput)
        self.guiEvent.set()
