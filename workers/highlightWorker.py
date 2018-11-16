
import queue
import threading

import re

from traceLog import traceLog,LogLevel
import settings as Sets
from customTypes import PrintLine

from views import textFrame

class HighlightWorker():

    def __init__(self,settings):
        self._settings_ = settings

        self._logFileBaseName_ = self._settings_.get(Sets.LOG_FILE_BASE_NAME)

        self._lineColorMap_ = dict()

        self._lineBuffer_ = list()

        self._guiWorker_ = None

        self._textFrame_:textFrame.TextFrame = None

        self._consecutiveLinesHidden_ = 0
        self._hideLineMap_ = list()
        self._hideLineMap_.append("GUI::.*")
        self._hideLineMap_.append("Main::.*")
        self._hideLinesFlag_ = False

        self._highlightFlag_ = False

        self.highlightQueue = queue.Queue()

        self._reloadLineBuffer_ = False
        self.isReloadingLineBuffer = False

        self._replaceLineBufferString_ = False

    ##############
    # Public Interface

    def linkWorkers(self,workers):
        self._guiWorker_ = workers.guiWorker
    
    def linkTextFrame(self,textFrame):
        self._textFrame_ = textFrame

    def startWorker(self):

        if self._guiWorker_ != None and self._textFrame_ != None:
            if not self._highlightFlag_:

                self._reloadLineColorMap_()

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

    def replaceLineBufferString(self,oldString,newString,replaceAll=False):

        if not self._replaceLineBufferString_:

            self._stringReplaceOld_ = oldString
            self._stringReplaceNew_ = newString
            self._replaceAllInstances_ = replaceAll

            self._replaceLineBufferString_ = True
                

    ##############
    # Internal

    def _reloadLineColorMap_(self):
        self._lineColorMap_ = self._textFrame_.getLineColorMap()

    def _locateLineTags_(self,line):
        # Locate highlights
        highlights = list()
        for lineColorRowId in self._lineColorMap_.keys():            
            match = re.search(self._lineColorMap_[lineColorRowId]["regex"],line)
            if match:
                highlights.append((self._lineColorMap_[lineColorRowId]["tagName"],match.start(),match.end()))

        match = re.search(Sets.connectLineRegex,line)
        if match:
            highlights.append((Sets.CONNECT_COLOR_TAG,"0","0+1l"))

        match = re.search(Sets.disconnectLineRegex,line)
        if match:
            highlights.append((Sets.DISCONNECT_COLOR_TAG,"0","0+1l"))
            
            fileNameRegex = self._settings_.get(Sets.LOG_FILE_BASE_NAME) + ".*" + Sets.LOG_FILE_TYPE
            fileNameMatch = re.search(fileNameRegex,line)
            if fileNameMatch:
                # print("File name: " + fileNameMatch.group(0))
                highlights.append((Sets.LOG_FILE_LINK_TAG,fileNameMatch.start(),fileNameMatch.end()))


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

            ######
            # Check if a line has to be updated in the buffer
            if self._replaceLineBufferString_:
                                
                for idx,line in enumerate(self._lineBuffer_):                
                    if line.find(self._stringReplaceOld_) != -1:
                        self._lineBuffer_[idx] = line.replace(self._stringReplaceOld_,self._stringReplaceNew_)
                        if not self._replaceAllInstances_:
                            break

                self._replaceLineBufferString_ = False
                

