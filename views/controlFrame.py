
import tkinter as tk

import serial.tools.list_ports

from traceLog import traceLog,LogLevel
import settings as Sets
from customTypes import ConnectState

class ControlFrame:

    def __init__(self,settings,rootClass,search,optionsView):
        self._settings = settings
        self._root = rootClass.root
        self._textFrame = None
        self._textArea = None
        self._bottomFrame = None
        self._search = search
        self._optionsView = optionsView


        self._serialPorts = dict()
        self._serialPortList = [""]

        self._connectController = None
        self._highlightWorker = None

        self._root.bind("<Alt-e>", self._goToEndButtonCommand)

        # Create widgets
        self._topFrame = tk.Frame(self._root)

        self._statusLabel = tk.Label(self._topFrame,text="DISCONNECTED", width=20, anchor=tk.W, fg=Sets.STATUS_TEXT_COLOR, bg=Sets.STATUS_DISCONNECT_BACKGROUND_COLOR)
        self._statusLabel.pack(side=tk.RIGHT,padx=(0,18))

        self._statusLabelHeader = tk.Label(self._topFrame,text="   Status:", anchor=tk.W, fg=Sets.STATUS_TEXT_COLOR, bg=Sets.STATUS_DISCONNECT_BACKGROUND_COLOR)
        self._statusLabelHeader.pack(side=tk.RIGHT)

        self._connectButton = tk.Button(self._topFrame,text="Connect", command=self._connectButtonCommand, width=10)
        self._connectButton.pack(side=tk.LEFT)

        self._goToEndButton = tk.Button(self._topFrame,text="Go to end", command=self._goToEndButtonCommand, width=10, underline=6)
        self._goToEndButton.pack(side=tk.LEFT)

        # reloadBufferButton_ = tk.Button(topFrame_,text="Reload buffer", command=reloadBufferCommand, width=10)
        # reloadBufferButton_.pack(side=tk.LEFT)

        # hideLinesButton_ = tk.Button(topFrame_,text="Hide Lines", command=hideLinesCommand, width=10)
        # hideLinesButton_.pack(side=tk.LEFT)

        # self._lineWrapToggleButton = tk.Button(self._topFrame,text="Line Wrap", command=self._lineWrapToggleCommmand, width=10)
        # self._lineWrapToggleButton.pack(side=tk.LEFT)

        self._clearButton = tk.Button(self._topFrame,text="Clear", command=self._clearButtonCommand, width=10)
        self._clearButton.pack(side=tk.LEFT,padx=(0,40))

        self._optionsButton = tk.Button(self._topFrame,text="Options", command=self._showOptionsView, width=10)
        self._optionsButton.pack(side=tk.LEFT,padx=(0,40))

        self._serialPortReloadButton = tk.Button(self._topFrame,text="Reload ports", command=self._reloadSerialPorts, width=10)
        self._serialPortReloadButton.pack(side=tk.LEFT)

        self._serialPortVar = tk.StringVar(self._topFrame)
        self._serialPortOption = tk.OptionMenu(self._topFrame,self._serialPortVar,*self._serialPortList)
        self._serialPortOption.pack(side=tk.LEFT)

        self._serialPortLabel = tk.Label(self._topFrame,text="", anchor=tk.W)
        self._serialPortLabel.pack(side=tk.LEFT)

        self._topFrame.pack(side=tk.TOP, fill=tk.X)


        self._reloadSerialPorts()

    NO_SERIAL_PORT = "None"

    ##############
    # Public Interface

    def linkConnectController(self,connectController):
        self._connectController = connectController

    def linkWorkers(self,workers):
        self._highlightWorker = workers.highlightWorker

    def linkTextFrame(self,textFrame):
        self._textFrame = textFrame
        self._textArea = textFrame.textArea

    def linkBottomFrame(self,bottomFrame):
        self._bottomFrame = bottomFrame

    def setConnectButtonText(self,text):
        self._connectButton.config(text=text)

    def setStatusLabel(self,labelText, bgColor):
        self._statusLabel.config(text=labelText, bg=bgColor)
        self._statusLabelHeader.config(bg=bgColor)

    def getSerialPortVar(self):
        return self._serialPortVar.get()

    def enablePortButtons(self):
        self._serialPortReloadButton.config(state=tk.NORMAL)
        self._serialPortOption.config(state=tk.NORMAL)

    def disablePortButtons(self):
        self._serialPortReloadButton.config(state=tk.DISABLED)
        self._serialPortOption.config(state=tk.DISABLED)

    ##############
    # Internal

    def _connectButtonCommand(self):

        appState = self._connectController.getAppState()

        if appState == ConnectState.DISCONNECTED:
            # Connect to serial
            self._connectController.changeAppState(ConnectState.CONNECTED)

        elif appState == ConnectState.CONNECTED:
            # Close down reader
            self._connectController.changeAppState(ConnectState.DISCONNECTED)

    def _goToEndButtonCommand(self,*args):
        self._textArea.see(tk.END)

    def _clearButtonCommand(self,*args):

        self._search.close()

        self._highlightWorker.clearLineBuffer()

        self._textArea.config(state=tk.NORMAL)
        self._textArea.delete(1.0,tk.END)
        self._textArea.config(state=tk.DISABLED)

        self._bottomFrame.updateWindowBufferLineCount(0)

    def _reloadBufferCommand(self):
        self._highlightWorker.reloadLineBuffer()

    def _hideLinesCommand(self):
        self._highlightWorker.toggleHideLines()
        self._reloadBufferCommand()

    def _lineWrapToggleCommmand(self):
        lineWrapState = self._settings.get(Sets.TEXTAREA_LINE_WRAP)
        if lineWrapState == Sets.LINE_WRAP_ON:
            self._textFrame.updateLineWrap(Sets.LINE_WRAP_OFF)
            self._settings.setOption(Sets.TEXTAREA_LINE_WRAP,Sets.LINE_WRAP_OFF)
        else:
            self._textFrame.updateLineWrap(Sets.LINE_WRAP_ON)
            self._settings.setOption(Sets.TEXTAREA_LINE_WRAP,Sets.LINE_WRAP_ON)

    def _showOptionsView(self):
        self._search.close()
        self._optionsView.show()

    def _scanSerialPorts(self):

        serialPortDict = dict()

        comPorts = serial.tools.list_ports.comports()

        for comPort in comPorts:
            try:
                with serial.Serial(comPort.device, 115200, timeout=2):
                    serialPortDict[comPort.device] = comPort.description
            except serial.SerialException:
                traceLog(LogLevel.DEBUG,"scanSerialPorts: " + comPort.device + " already open")

        return serialPortDict

    def _reloadSerialPorts(self):

        self._serialPorts = self._scanSerialPorts()

        if self._serialPorts:
            self._serialPortList.clear()
            self._serialPortList.extend(sorted(list(self._serialPorts.keys())))
            self._serialPortVar.set(self._serialPortList[0])
            self._serialPortVar.trace("w",self._updateSerialPortSelect)

            # Delete options
            self._serialPortOption["menu"].delete(0,"end")

            # Add new options
            for port in self._serialPortList:
                self._serialPortOption["menu"].add_command(label=port, command=tk._setit(self._serialPortVar,port))

            self._serialPortOption.config(state=tk.NORMAL)
            self._serialPortLabel.config(text=self._serialPorts[self._serialPortVar.get()])

            self._connectButton.config(state=tk.NORMAL)

        else:
            self._serialPortVar.set(self.NO_SERIAL_PORT)
            self._serialPortLabel.config(text="No serial port found")
            self._serialPortOption.config(state=tk.DISABLED)
            self._connectButton.config(state=tk.DISABLED)

    def _updateSerialPortSelect(self,*args):
        if self._serialPortVar.get() == self.NO_SERIAL_PORT:
            self._serialPortLabel.config(text=self.NO_SERIAL_PORT)
        else:
            self._serialPortLabel.config(text=self._serialPorts[self._serialPortVar.get()])
