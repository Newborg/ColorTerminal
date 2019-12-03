import os

import tkinter as tk
from tkinter.font import Font

from traceLog import traceLog,LogLevel
import settings as Sets

from frames import textFrame


class FileView:

    def __init__(self,settings,root,iconPath,comController,fileName):
        self._settings = settings
        self._root = root
        self._iconPath = iconPath        
        self._comController = comController

        # View
        self._view = tk.Toplevel(self._root)
        self._view.title(os.path.basename(fileName))
        self._view.protocol("WM_DELETE_WINDOW", self._onClosing)

        self._view.iconbitmap(self._iconPath)
        self._view.geometry(self._settings.get(Sets.DEFAULT_WINDOW_SIZE))

        # Control Frame
        # self._topFrame = tk.Frame(self._view)

        # self._connectButton = tk.Button(self._topFrame,text="Testing", width=10)
        # self._connectButton.pack(side=tk.LEFT)

        # self._topFrame.pack(side=tk.TOP, fill=tk.X)

        # Text Frame
        self._textFrame = textFrame.TextFrame(self._settings,self._view,self._iconPath,self._comController)


        # Bottom Frame
        # self._bottomFrame = tk.Frame(self._view)
        # self._statLabel = tk.Label(self._bottomFrame,text="Testing", width=30, anchor=tk.W)
        # self._statLabel.pack(side=tk.LEFT)
        # self._bottomFrame.pack(side=tk.BOTTOM, fill=tk.X)


        # Add file content
        lines = ""
        try:
            with open(fileName,"r") as file:
                lines = file.read()
        except FileNotFoundError:
            traceLog(LogLevel.WARNING,"File not found")
        except UnicodeDecodeError:
            traceLog(LogLevel.ERROR,"File format is wrong")
            lines = ""

        if lines:
            self._textFrame.textArea.config(state=tk.NORMAL)
            self._textFrame.textArea.insert(tk.END, lines)
            self._textFrame.textArea.config(state=tk.DISABLED)
            
            self._textFrame.addAllLineColorTagsToText()

            # Focus on new window
            self._view.focus_set()
        else:
            self._onClosing()
        

    def _onClosing(self):
    
        self._textFrame.close()       

        # Close window
        self._view.destroy()



