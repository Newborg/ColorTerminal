
import tkinter as tk
from tkinter import messagebox

from traceLog import traceLog,LogLevel
import settings as Sets

from frames import controlFrame, textFrame, bottomFrame

class MainView:

    def __init__(self,settings,iconPath,version):
        self._settings = settings

        self.root = tk.Tk()

        self.root.iconbitmap(iconPath)

        self.root.protocol("WM_DELETE_WINDOW", self._onClosing_)

        self.root.title("Color Terminal v" + version)
        self.root.geometry(self._settings.get(Sets.DEFAULT_WINDOW_SIZE))

        self.controlFrame = controlFrame.ControlFrame(self._settings,self.root,iconPath)
        self.textFrame = textFrame.TextFrame(self._settings,self.root,iconPath)
        self.bottomFrame = bottomFrame.BottomFrame(self._settings,self.root,iconPath)

        self._connectController = None

        # Linking
        self.controlFrame.linkTextFrame(self.textFrame)
        self.controlFrame.linkBottomFrame(self.bottomFrame)

        # Key binding
        self.root.bind('<Control-f>', self.textFrame.showSearch)

    def linkConnectController(self,connectController):
        self._connectController = connectController
        self.controlFrame.linkConnectController(connectController)

    def linkWorkers(self,workers):
        self.controlFrame.linkWorkers(workers)
        self.textFrame.linkWorkers(workers)

    def destroyWindow(self):
        traceLog(LogLevel.INFO,"Closing main window")
        self.root.destroy()

    def _onClosing_(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self._connectController.disconnectSerial(close=True)


    ################################
    # Public interface

