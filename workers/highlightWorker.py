
import queue
import threading

import re

from traceLog import traceLog,LogLevel
import settings as Sets
from customTypes import PrintLine

# from frames import textFrame

class HighlightWorker():

    def __init__(self,settings,mainView):
        self._settings = settings
        self._mainView = mainView

        self._logFileBaseName = self._settings.get(Sets.LOG_FILE_BASE_NAME)

        self._lineColorMap = dict()

        self._lineBuffer = list()

        self._guiWorker = None

        self._consecutiveLinesHidden = 0
        self._hideLineMap = list()
        self._hideLineMap.append("GUI::.*")
        self._hideLineMap.append("Main::.*")
        self._hideLinesFlag = False

        self._highlightFlag = False

        self.highlightQueue = queue.Queue()

        self._reloadLineBuffer = False
        self.isReloadingLineBuffer = False

        self._replaceLineBufferString = False

    ##############
    # Public Interface

    def linkWorkers(self,workers):
        self._guiWorker = workers.guiWorker
    
    def startWorker(self):

        if self._guiWorker != None:
            if not self._highlightFlag:

                self._reloadLineColorMap()

                self._highlightFlag = True
                self._highlightThread = threading.Thread(target=self._highlightWorker,daemon=True,name="Highlight")
                self._highlightThread.start()
                # print("Highlight worker started")
            else:
                traceLog(LogLevel.ERROR,"Not able to start higlight thread. Thread already enabled")
        else:
            traceLog(LogLevel.ERROR,"Not able to start higlight thread. Gui worker not defined")

    def stopWorker(self,emptyQueue=True):
        "Stop highlight worker. Will block until thread is done"

        if self._highlightFlag:
            if emptyQueue:
                self.highlightQueue.join()

            self._highlightFlag = False

            if self._highlightThread.isAlive():
                self._highlightThread.join()


    def reloadLineBuffer(self):
        self._reloadLineBuffer = True
        # print("Highlight reloadLineBuffer")

    def clearLineBuffer(self):
        # print("Clear line buffer")
        self._lineBuffer.clear()

    def toggleHideLines(self):
        if self._hideLinesFlag:
            self._hideLinesFlag = False
        else:
            self._hideLinesFlag = True

    def replaceLineBufferString(self,oldString,newString,replaceAll=False):

        if not self._replaceLineBufferString:

            self._stringReplaceOld = oldString
            self._stringReplaceNew = newString
            self._replaceAllInstances = replaceAll

            self._replaceLineBufferString = True
                

    ##############
    # Internal

    def _reloadLineColorMap(self):
        self._lineColorMap = self._mainView.textFrame.getLineColorMap()

    def _locateLineTags(self,line):
        # Locate highlights
        highlights = list()
        for lineColorRowId in self._lineColorMap.keys():            
            match = re.search(self._lineColorMap[lineColorRowId]["regex"],line)
            if match:
                highlights.append((self._lineColorMap[lineColorRowId]["tagName"],match.start(),match.end()))

        match = re.search(Sets.connectLineRegex,line)
        if match:
            highlights.append((Sets.CONNECT_COLOR_TAG,"0","0+1l"))

        match = re.search(Sets.disconnectLineRegex,line)
        if match:
            highlights.append((Sets.DISCONNECT_COLOR_TAG,"0","0+1l"))
            
            fileNameRegex = self._settings.get(Sets.LOG_FILE_BASE_NAME) + ".*" + Sets.LOG_FILE_TYPE
            fileNameMatch = re.search(fileNameRegex,line)
            if fileNameMatch:
                # print("File name: " + fileNameMatch.group(0))
                highlights.append((Sets.LOG_FILE_LINK_TAG,fileNameMatch.start(),fileNameMatch.end()))


        return highlights

    def _getHideLineColorTags(self):
        highlights = list()
        highlights.append((Sets.HIDELINE_COLOR_TAG,"0","0+1l"))
        return highlights

    def _addToLineBuffer(self,rawline):

        lineBufferSize = len(self._lineBuffer)

        self._lineBuffer.append(rawline)

        if lineBufferSize > self._settings.get(Sets.TEXTAREA_MAX_LINE_BUFFER):
            del self._lineBuffer[0]

    def _hideLines(self,line):

        if self._hideLinesFlag:
            tempConsecutiveLinesHidden = 0

            for keys in self._hideLineMap:
                match = re.search(keys,line)
                if match:
                    tempConsecutiveLinesHidden = 1
                    break

            if tempConsecutiveLinesHidden == 1:
                self._consecutiveLinesHidden += 1
            else:
                self._consecutiveLinesHidden = 0
        else:
            self._consecutiveLinesHidden = 0

        return self._consecutiveLinesHidden

    def _getTimeStamp(self,line):

        # This is based on the settings of ColorTerminal
        # If you load a log file from another program, this might not work

        match = re.search(Sets.timeStampRegex,line)
        if match:
            return match.group(0)
        else:
            return ""

    ##############
    # Main Worker

    def _highlightWorker(self):

        while self._highlightFlag:

            ######
            # Get new line from queue
            newLine = ""
            try:
                newLine = self.highlightQueue.get(True,0.2)
                self.highlightQueue.task_done()

            except queue.Empty:
                pass

            ######
            # Process new line or process a buffer reload
            if newLine or self._reloadLineBuffer:

                if newLine:
                    self._addToLineBuffer(newLine)

                linesToProcess = list()

                if self._reloadLineBuffer:
                    self._reloadLineBuffer = False

                    linesToProcess = self._lineBuffer

                    # Wait for GUI queue to be empty and gui update to be done,
                    # otherwise some lines can be lost, when GUI is cleared
                    self._guiWorker.guiQueue.join()
                    self._guiWorker.guiEvent.wait()

                    self.isReloadingLineBuffer = True

                    # print("reload high lines " + str(len(self._lineBuffer_)))
                    # traceLog(LogLevel.DEBUG, "Reload Line Buffer")

                else:
                    linesToProcess.append(newLine)

                for line in linesToProcess:

                    consecutiveLinesHidden = self._hideLines(line)
                    if consecutiveLinesHidden == 0:
                        lineTags = self._locateLineTags(line)
                        pLine = PrintLine(line,lineTags)
                    else:
                        hideInfoLine = self._getTimeStamp(line) + " Lines hidden: " + str(consecutiveLinesHidden) + "\n"
                        lineTags = self._getHideLineColorTags()
                        if consecutiveLinesHidden > 1:
                            pLine = PrintLine(hideInfoLine,lineTags,True)
                        else:
                            pLine = PrintLine(hideInfoLine,lineTags,False)

                    self._guiWorker.guiQueue.put(pLine)

                if self.isReloadingLineBuffer:

                    self._guiWorker.guiReloadEvent.clear()
                    self.isReloadingLineBuffer = False
                    self._guiWorker.reloadGuiBuffer()

                    # Wait for gui to have processed new buffer
                    self._guiWorker.guiReloadEvent.wait()

            ######
            # Check if a line has to be updated in the buffer
            if self._replaceLineBufferString:
                                
                for idx,line in enumerate(self._lineBuffer):                
                    if line.find(self._stringReplaceOld) != -1:
                        self._lineBuffer[idx] = line.replace(self._stringReplaceOld,self._stringReplaceNew)
                        if not self._replaceAllInstances:
                            break

                self._replaceLineBufferString = False
                

