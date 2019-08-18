
import os

import queue
import threading

import datetime

from traceLog import traceLog,LogLevel
import settings as Sets


class LogWriterWorker:

    def __init__(self,settings,mainView):
        self._settings = settings
        self._mainView = mainView

        self._logFlag = False

        self._logThread = None
        self.logQueue = queue.Queue()

        self.linesInLogFile = 0
        self.lastLogFileInfo = ""

    def startWorker(self):

        if not self._logFlag:
            self._logFlag = True
            self._logThread = threading.Thread(target=self._logWriterWorker,daemon=True,name="Log")
            self._logThread.start()
        else:
            traceLog(LogLevel.ERROR,"Not able to start log thread. Thread already enabled")


    def stopWorker(self,emptyQueue=True):
        "Stop log worker. Will block until thread is done"

        if self._logFlag:

            if emptyQueue:
                self.logQueue.join()

            self._logFlag = False

            if self._logThread:
                if self._logThread.isAlive():
                    self._logThread.join()

    def _logWriterWorker(self):

        timestamp = datetime.datetime.now().strftime(self._settings.get(Sets.LOG_FILE_TIMESTAMP))

        filename = self._settings.get(Sets.LOG_FILE_BASE_NAME) + timestamp + Sets.LOG_FILE_TYPE
        fullFilename = os.path.join(self._settings.get(Sets.LOG_FILE_PATH),filename)

        os.makedirs(os.path.dirname(fullFilename), exist_ok=True)

        self._mainView.bottomFrame.updateLogFileInfo("Saving to log file: " + filename,"black",useRootAfter=True)

        self.linesInLogFile = 0

        with open(fullFilename,"a") as file:
            while self._logFlag:
                try:
                    logLine = self.logQueue.get(True,0.2)
                    self.logQueue.task_done()
                    file.write(logLine)
                    self.linesInLogFile += 1
                except queue.Empty:
                    pass

        filesize = os.path.getsize(fullFilename)
        self.lastLogFileInfo = filename + " (Size " + "{:.3f}".format(filesize/1024) + "KB)"

        self._mainView.bottomFrame.updateLogFileInfo("Log file saved: " + self.lastLogFileInfo,"green",useRootAfter=True)
