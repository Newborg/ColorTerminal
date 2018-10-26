
import tkinter as tk

import serial.tools.list_ports

from traceLog import traceLog,LogLevel
import settings as Sets
from customTypes import ConnectState

class ControlFrame:

    def __init__(self,settings,rootClass,search,optionsView):
        self._settings_ = settings
        self._root_ = rootClass.root
        self._textArea_ = None
        self._bottomFrame_ = None
        self._search_ = search
        self._optionsView_ = optionsView


        self._serialPorts_ = dict()
        self._serialPortList_ = [""]

        self._connectController_ = None
        self._highlightWorker_ = None

        self._root_.bind("<Alt-e>", self._goToEndButtonCommand_)

        # Create widgets
        self._topFrame_ = tk.Frame(self._root_)

        self._statusLabel_ = tk.Label(self._topFrame_,text="DISCONNECTED", width=20, anchor=tk.W, fg=Sets.STATUS_TEXT_COLOR, bg=Sets.STATUS_DISCONNECT_BACKGROUND_COLOR)
        self._statusLabel_.pack(side=tk.RIGHT,padx=(0,18))

        self._statusLabelHeader_ = tk.Label(self._topFrame_,text="   Status:", anchor=tk.W, fg=Sets.STATUS_TEXT_COLOR, bg=Sets.STATUS_DISCONNECT_BACKGROUND_COLOR)
        self._statusLabelHeader_.pack(side=tk.RIGHT)

        self._connectButton_ = tk.Button(self._topFrame_,text="Connect", command=self._connectButtonCommand_, width=10)
        self._connectButton_.pack(side=tk.LEFT)

        self._goToEndButton_ = tk.Button(self._topFrame_,text="Go to end", command=self._goToEndButtonCommand_, width=10, underline=6)
        self._goToEndButton_.pack(side=tk.LEFT)

        # reloadBufferButton_ = tk.Button(topFrame_,text="Reload buffer", command=reloadBufferCommand, width=10)
        # reloadBufferButton_.pack(side=tk.LEFT)

        # hideLinesButton_ = tk.Button(topFrame_,text="Hide Lines", command=hideLinesCommand, width=10)
        # hideLinesButton_.pack(side=tk.LEFT)

        self._clearButton_ = tk.Button(self._topFrame_,text="Clear", command=self._clearButtonCommand_, width=10)
        self._clearButton_.pack(side=tk.LEFT,padx=(0,40))

        self._optionsButton_ = tk.Button(self._topFrame_,text="Options", command=self._showOptionsView_, width=10)
        self._optionsButton_.pack(side=tk.LEFT,padx=(0,40))

        self._serialPortReloadButton_ = tk.Button(self._topFrame_,text="Reload ports", command=self._reloadSerialPorts_, width=10)
        self._serialPortReloadButton_.pack(side=tk.LEFT)

        self._serialPortVar_ = tk.StringVar(self._topFrame_)
        self._serialPortOption_ = tk.OptionMenu(self._topFrame_,self._serialPortVar_,*self._serialPortList_)
        self._serialPortOption_.pack(side=tk.LEFT)

        self._serialPortLabel_ = tk.Label(self._topFrame_,text="", anchor=tk.W)
        self._serialPortLabel_.pack(side=tk.LEFT)

        self._topFrame_.pack(side=tk.TOP, fill=tk.X)


        self._reloadSerialPorts_()

    NO_SERIAL_PORT = "None"

    ##############
    # Public Interface

    def linkConnectController(self,connectController):
        self._connectController_ = connectController

    def linkWorkers(self,workers):
        self._highlightWorker_ = workers.highlightWorker

    def linkTextFrame(self,textFrame):
        self._textArea_ = textFrame.textArea

    def linkBottomFrame(self,bottomFrame):
        self._bottomFrame_ = bottomFrame

    def setConnectButtonText(self,text):
        self._connectButton_.config(text=text)

    def setStatusLabel(self,labelText, bgColor):
        self._statusLabel_.config(text=labelText, bg=bgColor)
        self._statusLabelHeader_.config(bg=bgColor)

    def getSerialPortVar(self):
        return self._serialPortVar_.get()

    ##############
    # Internal

    def _connectButtonCommand_(self):

        appState = self._connectController_.getAppState()

        if appState == ConnectState.DISCONNECTED:
            # Connect to serial
            self._connectController_.changeAppState(ConnectState.CONNECTED)

        elif appState == ConnectState.CONNECTED:
            # Close down reader
            self._connectController_.changeAppState(ConnectState.DISCONNECTED)

    def _goToEndButtonCommand_(self,*args):
        self._textArea_.see(tk.END)

    def _clearButtonCommand_(self,*args):

        self._search_.close()

        self._highlightWorker_.clearLineBuffer()

        self._textArea_.config(state=tk.NORMAL)
        self._textArea_.delete(1.0,tk.END)
        self._textArea_.config(state=tk.DISABLED)

        self._bottomFrame_.updateWindowBufferLineCount(0)

    def _reloadBufferCommand_(self):
        self._highlightWorker_.reloadLineBuffer()

    def _hideLinesCommand_(self):
        self._highlightWorker_.toggleHideLines()
        self._reloadBufferCommand_()

    def _showOptionsView_(self):
        self._search_.close()
        self._optionsView_.show(self._highlightWorker_.getLineColorMap())

    def _scanSerialPorts_(self):

        serialPortDict = dict()

        comPorts = serial.tools.list_ports.comports()

        for comPort in comPorts:
            try:
                with serial.Serial(comPort.device, 115200, timeout=2):
                    serialPortDict[comPort.device] = comPort.description
            except serial.SerialException:
                traceLog(LogLevel.DEBUG,"scanSerialPorts: " + comPort.device + " already open")

        return serialPortDict

    def _reloadSerialPorts_(self):

        self._serialPorts_ = self._scanSerialPorts_()

        if self._serialPorts_:
            self._serialPortList_.clear()
            self._serialPortList_.extend(sorted(list(self._serialPorts_.keys())))
            self._serialPortVar_.set(self._serialPortList_[0])
            self._serialPortVar_.trace("w",self._updateSerialPortSelect_)

            # Delete options
            self._serialPortOption_["menu"].delete(0,"end")

            # Add new options
            for port in self._serialPortList_:
                self._serialPortOption_["menu"].add_command(label=port, command=tk._setit(self._serialPortVar_,port))

            self._serialPortOption_.config(state=tk.NORMAL)
            self._serialPortLabel_.config(text=self._serialPorts_[self._serialPortVar_.get()])

            self._connectButton_.config(state=tk.NORMAL)

        else:
            self._serialPortVar_.set(self.NO_SERIAL_PORT)
            self._serialPortLabel_.config(text="No serial port found")
            self._serialPortOption_.config(state=tk.DISABLED)
            self._connectButton_.config(state=tk.DISABLED)

    def _updateSerialPortSelect_(self,*args):
        if self._serialPortVar_.get() == self.NO_SERIAL_PORT:
            self._serialPortLabel_.config(text=self.NO_SERIAL_PORT)
        else:
            self._serialPortLabel_.config(text=self._serialPorts_[self._serialPortVar_.get()])