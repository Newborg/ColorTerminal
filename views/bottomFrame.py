
import tkinter as tk

import settings as Sets

class BottomFrame:

    def __init__(self,settings,rootClass):
        self._settings_ = settings
        self._root_ = rootClass.root

        self._bottomFrame_ = tk.Frame(self._root_)

        self._statLabel1_ = tk.Label(self._bottomFrame_,text="Lines in window buffer 0/" + str(self._settings_.get(Sets.MAX_LINE_BUFFER)), width=30, anchor=tk.W)
        self._statLabel1_.pack(side=tk.LEFT)

        self._statLabel2_ = tk.Label(self._bottomFrame_,text="", width=30, anchor=tk.W)
        self._statLabel2_.pack(side=tk.LEFT)

        self._statLabel3_ = tk.Label(self._bottomFrame_,text="", width=60, anchor=tk.E)
        self._statLabel3_.pack(side=tk.RIGHT,padx=(0,18))

        self._bottomFrame_.pack(side=tk.BOTTOM, fill=tk.X)

    def updateWindowBufferLineCount(self,count):
        self._statLabel1_.config(text="Lines in window buffer " + str(count) + "/" + str(self._settings_.get(Sets.MAX_LINE_BUFFER)))

    def updateLogFileLineCount(self,count):
        self._statLabel2_.config(text="Lines in log file " + str(count))

    def updateLogFileInfo(self,info,color,useRootAfter=False):

        if useRootAfter:
            self._root_.after(10,self._updateLogFileInfo_,info,color)
        else:
            self._updateLogFileInfo_(info,color)

    def _updateLogFileInfo_(self,info,color):
        self._statLabel3_.config(text=info,fg=color)