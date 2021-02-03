import os

import tkinter as tk

from traceLog import traceLog,LogLevel
import settings as Sets
import spinner

import time

from frames import textFrame


class FileView:

    def __init__(self,settings,root,comController,filePathFull):
        self._settings = settings
        self._root = root
        self._comController = comController

        # View
        self._view = tk.Toplevel(self._root)
        self._view.title(os.path.basename(filePathFull))
        self._view.protocol("WM_DELETE_WINDOW", self._onClosing)

        self._view.iconbitmap(self._settings.get(Sets.ICON_PATH_FULL))
        self._view.geometry(self._settings.get(Sets.DEFAULT_WINDOW_SIZE))

        # Control Frame
        # self._topFrame = tk.Frame(self._view)

        # self._connectButton = tk.Button(self._topFrame,text="Testing", width=10)
        # self._connectButton.pack(side=tk.LEFT)

        # self._topFrame.pack(side=tk.TOP, fill=tk.X)

        # Text Frame
        self._textFrame = textFrame.TextFrame(self._settings,self._view,self._comController)

        # Bottom Frame
        # self._bottomFrame = tk.Frame(self._view)
        # self._statLabel = tk.Label(self._bottomFrame,text="Testing", width=30, anchor=tk.W)
        # self._statLabel.pack(side=tk.LEFT)
        # self._bottomFrame.pack(side=tk.BOTTOM, fill=tk.X)

        readError = False

        # Add file content
        self._lines = list()
        try:
            with open(filePathFull,"r") as file:
                # lines = file.read()
                self._lines = file.readlines()
        except FileNotFoundError:
            traceLog(LogLevel.WARNING,"File not found")
            readError = True
        except UnicodeDecodeError:
            traceLog(LogLevel.ERROR,"File format is wrong")
            self._lines = list()
            readError = True


        if self._lines:

            print(len(self._lines))

            # Draw the first 100 lines to speed up window launch
            self._firstDrawLines = 100
            if len(self._lines) < self._firstDrawLines:
                self._firstDrawLines = len(self._lines)

            self._textFrame.textArea.config(state=tk.NORMAL)
            self._textFrame.textArea.insert(tk.END, "".join(self._lines[0:self._firstDrawLines]))
            self._textFrame.textArea.config(state=tk.DISABLED)

            self._textFrame.addAllLineColorTagsToText()

            # Focus on new window
            self._view.focus_set()

            # add spinner
            self._loadSpinner = spinner.Spinner(self._view)
            self._loadSpinner.show(indicators=False,message="Loading File...")

            self._root.after(5,self._drawRemainingLines)

        if readError:
            self._onClosing()

    def _drawRemainingLines(self):

        self._textFrame.textArea.config(state=tk.NORMAL)
        self._textFrame.textArea.insert(tk.END, "".join(self._lines[self._firstDrawLines:]))
        self._textFrame.textArea.config(state=tk.DISABLED)

        self._textFrame.addAllLineColorTagsToText()

        self._loadSpinner.close()

    def _onClosing(self):

        self._textFrame.close()

        # Close window
        self._view.destroy()



