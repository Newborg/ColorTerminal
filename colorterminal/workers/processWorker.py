
import queue
import threading
import string

import datetime

from traceLog import traceLog,LogLevel
import settings as Sets

class ProcessWorker:

    def __init__(self,settings):
        self._settings = settings
        self._processFlag = False

        self._processThread = None
        self.processQueue = queue.Queue()

        self._highlightWorker = None
        self._logWriterWorker = None

        self._nonprintable = set([chr(i) for i in range(128)]).difference(string.printable)

    ##############
    # Public Interface

    def startWorker(self):

        if self._highlightWorker and self._logWriterWorker:
            if not self._processFlag:
                self._processFlag = True
                self._processThread = threading.Thread(target=self._processWorker,daemon=True,name="Process")
                self._processThread.start()
            else:
                traceLog(LogLevel.ERROR,"Not able to start process thread. Thread already enabled")
        else:
            traceLog(LogLevel.ERROR,"Not able to start process thread. Highlight or logWriter not set")


    def stopWorker(self,emptyQueue=True):
        "Stop process worker. Will block until thread is done"

        if self._processFlag:
            if emptyQueue:
                self.processQueue.join()

            self._processFlag = False

            if self._processThread:
                if self._processThread.isAlive():
                    self._processThread.join()

    def linkWorkers(self,workers):
        self._highlightWorker = workers.highlightWorker
        self._logWriterWorker = workers.logWriterWorker

    ##############
    # Main Worker

    def _processWorker(self):

        # Create connect line
        timestamp = datetime.datetime.now()
        timeString = Sets.timeStampBracket[0] + timestamp.strftime("%H:%M:%S") + Sets.timeStampBracket[1]
        connectLine = timeString + Sets.CONNECT_LINE_TEXT
        self._highlightWorker.highlightQueue.put(connectLine)

        lastTimestamp = 0

        while self._processFlag:
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

                # Remove non-printable characters
                newData = line.data.translate({ord(character):"\\u%04d" % ord(character) for character in self._nonprintable})
                # Replace newline
                newData = newData.rstrip() + "\n"

                # Construct newLine string
                newLine = timeString + " " + timeDeltaString + " " + newData

                self._highlightWorker.highlightQueue.put(newLine)
                self._logWriterWorker.logQueue.put(newLine)

            except queue.Empty:
                pass