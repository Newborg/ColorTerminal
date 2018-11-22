
import tkinter as tk

import settings as Sets

class BottomFrame:

    def __init__(self,settings,rootClass):
        self._settings = settings
        self._root = rootClass.root

        self._bottomFrame = tk.Frame(self._root)

        self._statLabel1 = tk.Label(self._bottomFrame,text="Lines in window buffer 0/" + str(self._settings.get(Sets.MAX_LINE_BUFFER)), width=30, anchor=tk.W)
        self._statLabel1.pack(side=tk.LEFT)

        self._statLabel2 = tk.Label(self._bottomFrame,text="", width=30, anchor=tk.W)
        self._statLabel2.pack(side=tk.LEFT)

        self._statLabel3 = tk.Label(self._bottomFrame,text="", width=60, anchor=tk.E)
        self._statLabel3.pack(side=tk.RIGHT,padx=(0,18))

        self._bottomFrame.pack(side=tk.BOTTOM, fill=tk.X)

    def updateWindowBufferLineCount(self,count):
        self._statLabel1.config(text="Lines in window buffer " + str(count) + "/" + str(self._settings.get(Sets.MAX_LINE_BUFFER)))

    def updateLogFileLineCount(self,count):
        self._statLabel2.config(text="Lines in log file " + str(count))

    def updateLogFileInfo(self,info,color,useRootAfter=False):

        if useRootAfter:
            self._root.after(10,self._updateLogFileInfo,info,color)
        else:
            self._updateLogFileInfo(info,color)

    def _updateLogFileInfo(self,info,color):
        self._statLabel3.config(text=info,fg=color)
