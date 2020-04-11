
import tkinter as tk
from tkinter import messagebox

from traceLog import traceLog,LogLevel
import settings as Sets

from frames import controlFrame, textFrame, bottomFrame

class MainView:

    def __init__(self,settings,version,textFrameManager):
        self._settings = settings
        self._textFrameManager = textFrameManager

        self.root = tk.Tk()

        self.root.iconbitmap(self._settings.get(Sets.ICON_PATH_FULL))

        self.root.protocol("WM_DELETE_WINDOW", self._onClosing_)

        self.root.title("Color Terminal v" + version)
        self.root.geometry(self._settings.get(Sets.DEFAULT_WINDOW_SIZE))

        self.controlFrame = controlFrame.ControlFrame(self._settings,self.root,self._textFrameManager)
        self.textFrame = textFrame.TextFrame(self._settings,self.root,self._textFrameManager)
        self.bottomFrame = bottomFrame.BottomFrame(self._settings,self.root)

        self._connectController = None

        # Linking
        self.controlFrame.linkTextFrame(self.textFrame)
        self.controlFrame.linkBottomFrame(self.bottomFrame)


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

