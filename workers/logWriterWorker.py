
import os

import queue
import threading

import datetime

from traceLog import traceLog,LogLevel
import settings as Sets


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