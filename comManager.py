import threading
import multiprocessing.connection as multi_con
import time

from traceLog import traceLog,LogLevel
from views import fileView

class ComManager:

    def __init__(self,settings,ctHomeEnvVarFound,inputFileName):
        self._settings = settings
        self._homeFound = ctHomeEnvVarFound
        self._root = None

        self._filePath = inputFileName

        self._listenerRegistered = False

        self._address = ("localhost", 6543)
        self._authKey = b"ColorTerminal_Secret"

        self._listenerFlag = True

        self._comManagerInitEvent = threading.Event()
        self._externalConnectorsLinkedEvent = threading.Event()

        self._listenerThread = threading.Thread(target=self._listenerProcess,daemon=True,name="ComListener")
        self._listenerThread.start()

        # Wait for initial setup to finish (will check if listener is already running)
        self._comManagerInitEvent.wait()


    def linkExternalConnectors(self,mainView,textFrameManager):
        self._root = mainView.root
        self._textFrameManager = textFrameManager

        self._externalConnectorsLinkedEvent.set()

    def isListenerRegistered(self):
        return self._listenerRegistered

    def _listenerProcess(self):
        try:
            with multi_con.Listener(address=self._address, authkey=self._authKey) as listener:
                self._listenerRegistered = True
                self._comManagerInitEvent.set()
                traceLog(LogLevel.DEBUG,"ComManager: Listener registered")

                self._externalConnectorsLinkedEvent.wait()
                traceLog(LogLevel.DEBUG,"ComManager: Listener started")

                # TODO: If filename is received at start of program, also start text view
                if self._filePath:
                    self._root.after(10,self._openFile,self._filePath)

                while self._listenerFlag:

                    conn = listener.accept() # Will block until connection is accepted

                    try:
                        msg = conn.recv() # blocking until something is received
                        self._root.after(10,self._openFile,msg)
                    except EOFError:
                        pass

                    conn.close()

                    time.sleep(0.05) # No need to loop crazy fast

        except OSError:
            traceLog(LogLevel.INFO,"ComManager: Socket address already used. Com listener likely already running")
            self._clientSend(self._filePath)
        except multi_con.AuthenticationError:
            traceLog(LogLevel.WARNING,"ComManager: Listener authentication error")
        except Exception as e:
            traceLog(LogLevel.ERROR,"ComManager: Listener exception [%s]: %s" % (str(type(e).__name__), str(e)))

        self._comManagerInitEvent.set()

    def _clientSend(self,data):
        try:
            client = multi_con.Client(address=self._address,authkey=self._authKey)
            client.send(data)
            client.close()
        except ConnectionRefusedError:
            traceLog(LogLevel.ERROR,"ComManager: Client connection refused. Listener likely not started")
        except multi_con.AuthenticationError:
            traceLog(LogLevel.WARNING,"ComManager: Client authentication error")
        except Exception as e:
            traceLog(LogLevel.ERROR,"ComManager: Client exception [%s]: %s" % (str(type(e).__name__), str(e)))

    def _openFile(self,filePath):
        if self._homeFound:
            traceLog(LogLevel.INFO,"ComManager: Open file %s from explorer" % filePath)
            fileView.FileView(self._settings,self._root,self._textFrameManager,filePath)
        else:
            traceLog(LogLevel.WARNING,"ComManager: CT home path not found in env var. Not able to open file")