import threading
import serial
import serial.tools.list_ports
import datetime

from traceLog import traceLog,LogLevel
import settings as Sets
from customTypes import ConnectState,SerialLine

class ReaderWorker:

    def __init__(self,settings,rootClass,controlFrame):
        self._settings_ = settings
        self._root_ = rootClass.root
        self._controlFrame_ = controlFrame

        self._readFlag_ = False

        self._readerThread_ = None

        self._connectController_ = None

        self._processWorker_ = None


    ##############
    # Public Interface

    def startWorker(self):

        if self._processWorker_:
            if not self._readFlag_:
                self._readFlag_ = True
                self._readerThread_ = threading.Thread(target=self._readerWorker_,daemon=True,name="Reader")
                self._readerThread_.start()
            else:
                traceLog(LogLevel.ERROR,"Not able to start reader thread. Thread already enabled")
        else:
            traceLog(LogLevel.ERROR,"Not able to start reader thread. Process worker not set")


    def stopWorker(self):
        "Stop reader worker. Will block until thread is done"

        if self._readFlag_:
            self._readFlag_ = False

            if self._readerThread_:
                if self._readerThread_.isAlive():
                    self._readerThread_.join()

    def linkConnectController(self,connectController):
        self._connectController_ = connectController

    def linkWorkers(self,workers):
        self._processWorker_ = workers.processWorker


    ##############
    # Main Worker

    def _readerWorker_(self):

        try:
            with serial.Serial(self._controlFrame_.getSerialPortVar(), 115200, timeout=2) as ser:

                # TODO should be done in GUI thread
                self._controlFrame_.setStatusLabel("CONNECTED to " + str(ser.name),Sets.STATUS_CONNECT_BACKGROUND_COLOR)
                self._connectController_.setAppState(ConnectState.CONNECTED)

                try:
                    while self._readFlag_:

                        line = ser.readline()
                        timestamp = datetime.datetime.now()

                        if line:
                            inLine = SerialLine(line.decode("utf-8"),timestamp)
                            self._processWorker_.processQueue.put(inLine)

                except serial.SerialException as e:
                    traceLog(LogLevel.ERROR,"Serial read error: " + str(e))
                    # Change program state to disconnected
                    self._root_.after(10,self._connectController_.changeAppState,ConnectState.DISCONNECTED)

        except serial.SerialException as e:
            traceLog(LogLevel.ERROR,str(e))
            # In case other threads are still starting up,
            # wait for 2 sec
            # Then change program state to disconnected
            self._root_.after(2000,self._connectController_.changeAppState,ConnectState.DISCONNECTED)