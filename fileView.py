import os

import tkinter as tk
from tkinter.font import Font

from traceLog import traceLog,LogLevel
import settings as Sets
from util import AutoScrollbar
from views import textFrame


class FileView:

    def __init__(self,settings,rootClass,iconPath,mainTextFrame,fileName):
        self._settings = settings
        self._root = rootClass.root
        self._iconPath = iconPath
        self._mainTextFrame = mainTextFrame

        # View
        self._view = tk.Toplevel(self._root)
        self._view.title(os.path.basename(fileName))
        self._view.protocol("WM_DELETE_WINDOW", self._onClosing)

        self._view.iconbitmap(self._iconPath)
        self._view.geometry(self._settings.get(Sets.DEFAULT_WINDOW_SIZE))

        # Control Frame
        self._topFrame = tk.Frame(self._view)

        self._connectButton = tk.Button(self._topFrame,text="Testing", width=10)
        self._connectButton.pack(side=tk.LEFT)

        self._topFrame.pack(side=tk.TOP, fill=tk.X)

        # Text Frame
        self._textFrame = tk.Frame(self._view)

        tFont = Font(family=self._settings.get(Sets.TEXTAREA_FONT_FAMILY), size=self._settings.get(Sets.TEXTAREA_FONT_SIZE))

        self.textArea = tk.Text(self._textFrame, height=1, width=1, background=self._settings.get(Sets.TEXTAREA_BACKGROUND_COLOR),\
                                selectbackground=self._settings.get(Sets.TEXTAREA_SELECT_BACKGROUND_COLOR),\
                                foreground=self._settings.get(Sets.TEXTAREA_COLOR), font=tFont)

        # Set up scroll bars
        yscrollbar=tk.Scrollbar(self._textFrame, orient=tk.VERTICAL, command=self.textArea.yview)
        yscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.textArea["yscrollcommand"]=yscrollbar.set

        # AutoScrollbar will hide itself when not needed
        xscrollbar=AutoScrollbar(self._textFrame, orient=tk.HORIZONTAL, command=self.textArea.xview)
        xscrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.textArea["xscrollcommand"]=xscrollbar.set

        self.textArea.pack(anchor=tk.W, fill=tk.BOTH, expand = tk.YES)

        self._textFrame.pack(side=tk.TOP, fill=tk.BOTH, expand = tk.YES)

        # Bottom Frame
        self._bottomFrame = tk.Frame(self._view)
        self._statLabel = tk.Label(self._bottomFrame,text="Testing", width=30, anchor=tk.W)
        self._statLabel.pack(side=tk.LEFT)
        self._bottomFrame.pack(side=tk.BOTTOM, fill=tk.X)


        # Add file content
        lines = ""
        try:
            with open(fileName,"r") as file:
                lines = file.read()
        except FileNotFoundError:
            traceLog(LogLevel.WARNING,"File not found")
            pass
   

        self.textArea.insert(tk.END, lines)

        self.textArea.config(state=tk.DISABLED)

        # Apply new line colors
        lineColorMap = self._mainTextFrame.getLineColorMap()          
        for lineInfo in lineColorMap.values():
            self.textArea.tag_configure(lineInfo["tagName"],foreground=lineInfo["color"])

            countVar = tk.StringVar()
            start = 1.0
            while True:
                pos = self.textArea.search(lineInfo["regex"],start,stopindex=tk.END,count=countVar,nocase=False,regexp=True)
                if not pos:
                    break
                else:
                    self.textArea.tag_add(lineInfo["tagName"],pos,pos + "+" + countVar.get() + "c")
                    start = pos + "+1c"



    # def linkWorkers(self,workers):
    #     self._highlightWorker = workers.highlightWorker
    #     self._guiWorker = workers.guiWorker

    def _onClosing(self):
        
        # Close window
        self._view.destroy()

