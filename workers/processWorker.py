
import queue
import threading

import datetime

from traceLog import traceLog,LogLevel
import settings as Sets

class ProcessWorker:

    def __init__(self,settings):
        self._settings_ = settings
        self._processFlag_ = False

        self._processThread_ = None
        self.processQueue = queue.Queue()

        self._highlightWorker_ = None
        self._logWriterWorker_ = None

    ##############
    # Public Interface

    def startWorker(self):

        if self._highlightWorker_ and self._logWriterWorker_:
            if not self._processFlag_:
                self._processFlag_ = True
                self._processThread_ = threading.Thread(target=self._processWorker_,daemon=True,name="Process")
                self._processThread_.start()
            else:
                traceLog(LogLevel.ERROR,"Not able to start process thread. Thread already enabled")
        else:
            traceLog(LogLevel.ERROR,"Not able to start process thread. Highlight or logWriter not set")


    def stopWorker(self,emptyQueue=True):
        "Stop process worker. Will block until thread is done"

        if self._processFlag_:
            if emptyQueue:
                self.processQueue.join()

            self._processFlag_ = False

            if self._processThread_:
                if self._processThread_.isAlive():
                    self._processThread_.join()

    def linkWorkers(self,workers):
        self._highlightWorker_ = workers.highlightWorker
        self._logWriterWorker_ = workers.logWriterWorker

    ##############
    # Main Worker

    def _processWorker_(self):

        # Create connect line
        timestamp = datetime.datetime.now()
        timeString = Sets.timeStampBracket[0] + timestamp.strftime("%H:%M:%S") + Sets.timeStampBracket[1]
        connectLine = timeString + Sets.CONNECT_LINE_TEXT
        self._highlightWorker_.highlightQueue.put(connectLine)

        lastTimestamp = 0

        while self._processFlag_:
            try:
                line = self.processQueue.get(True,0.2)
                self.processQueue.task_done()

                # Timestamp
                micros = int(line.timestamp.microsecond/1000)
                timeString = Sets.timeStampBracket[0] + line.timestamp.strftime("%H:%M:%S") + "." + '{:03d}'.format(micros) + Sets.timeStampBracket[1]

                # Timedelta
                if not lastTimestamp:
                    lastTimestamp = line.timestamp

                timedelta = line.timestamp - lastTimestamp

                hours, remainder = divmod(timedelta.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)

                hourstring = ""
                if hours != 0:
                    hourstring = "{:02d}:".format(hours)

                minutstring = ""
                if minutes != 0:
                    minutstring = "{:02d}:".format(minutes)

                if minutstring:
                    secondstring = "{:02d}.{:03d}".format(seconds, int(timedelta.microseconds/1000))
                else:
                    secondstring = "{:2d}.{:03d}".format(seconds, int(timedelta.microseconds/1000))

                timeDeltaString = Sets.timeDeltaBracket[0] + hourstring + minutstring + secondstring + Sets.timeDeltaBracket[1]

                lastTimestamp = line.timestamp

                # Replace newline
                newData = line.data.rstrip() + "\n"

                # Construct newLine string
                newLine = timeString + " " + timeDeltaString + " " + newData

                self._highlightWorker_.highlightQueue.put(newLine)
                self._logWriterWorker_.logQueue.put(newLine)

            except queue.Empty:
                pass