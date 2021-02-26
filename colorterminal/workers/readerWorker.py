import threading
import serial
import serial.tools.list_ports
import datetime

from traceLog import traceLog,LogLevel
from customTypes import ConnectState,SerialLine

class ReaderWorker:

    def __init__(self,settings,mainView):
        self._settings = settings
        self._mainView = mainView
        self._root = mainView.root

        self._readFlag = False

        self._readerThread = None

        self._connectController = None

        self._processWorker = None


    ##############
    # Public Interface

    def startWorker(self):

        if self._processWorker:
            if not self._readFlag:
                self._readFlag = True
                self._readerThread = threading.Thread(target=self._readerWorker,daemon=True,name="Reader")
                self._readerThread.start()
            else:
                traceLog(LogLevel.ERROR,"Not able to start reader thread. Thread already enabled")
        else:
            traceLog(LogLevel.ERROR,"Not able to start reader thread. Process worker not set")


    def stopWorker(self):
        "Stop reader worker. Will block until thread is done"

        if self._readFlag:
            self._readFlag = False

            if self._readerThread:
                if self._readerThread.is_alive():
                    self._readerThread.join()

    def linkConnectController(self,connectController):
        self._connectController = connectController

    def linkWorkers(self,workers):
        self._processWorker = workers.processWorker


    ##############
    # Main Worker

    def _readerWorker(self):

        try:
            with serial.Serial(self._mainView.controlFrame.getSerialPortVar(), 115200, timeout=1) as ser:

                self._root.after(10,self._connectController.changeAppState,ConnectState.CONNECTED,str(ser.name))

                try:
                    while self._readFlag:

                        line = ser.readline()
                        timestamp = datetime.datetime.now()

                        if line:
                            inLine = SerialLine(line.decode(encoding="utf-8",errors="backslashreplace"),timestamp)
                            self._processWorker.processQueue.put(inLine)

                except serial.SerialException as e:
                    traceLog(LogLevel.ERROR,"Serial read error: " + str(e))
                    # Change program state to disconnecting
                    self._root.after(10,self._connectController.changeAppState,ConnectState.DISCONNECTING)

        except serial.SerialException as e:
            traceLog(LogLevel.ERROR,str(e))
            # In case other threads are still starting up,
            # wait for 2 sec
            # Then change program state to disconnecting
            self._root.after(2000,self._connectController.changeAppState,ConnectState.DISCONNECTING)
