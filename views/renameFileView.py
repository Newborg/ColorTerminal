
import os
import tkinter as tk

import settings as Sets
from traceLog import traceLog,LogLevel

# Import for intellisense
# from frames.textFrame import TextFrame

# Global
_showing = False

class RenameFile:

    def __init__(self,settings,textFrame,root,iconPath,inputFileName):
        self._settings = settings
        self._textFrame = textFrame
        self._root = root
        self._iconPath = iconPath
        self._inputFileName = inputFileName

        self._show()


    def _close(self,*args):
        global _showing
        _showing = False

        self._view.unbind("<Escape>")
        self._outputFileNameEntry.unbind("<Escape>")

        self._view.destroy()


    def _show(self):

        global _showing

        if not _showing:
            _showing = True

            self._view = tk.Toplevel(self._root,padx=10,pady=10)
            self._view.title("Rename log file")
            self._view.protocol("WM_DELETE_WINDOW", self._close)
            self._view.iconbitmap(self._iconPath)

            # self._view.wm_attributes("-topmost", 1) # On top of all windows :(

            columnOneWidth = 7
            columnThreeWidth = 7

            inputFileNameLen = len(self._inputFileName)

            editFileNameText = self._inputFileName.replace(Sets.LOG_FILE_TYPE,"")

            inputLabel = tk.Label(self._view,text="Rename",width=columnOneWidth,anchor=tk.E)
            inputLabel.grid(row=0,column=0,sticky=tk.E,padx=(0,10))

            self._inputFileNameLabel = tk.Label(self._view,text=self._inputFileName)
            self._inputFileNameLabel.grid(row=0,column=1,sticky=tk.W)

            outputLabel = tk.Label(self._view,text="To",width=columnOneWidth,anchor=tk.E)
            outputLabel.grid(row=1,column=0,sticky=tk.E,padx=(0,10),pady=(5,0))

            self._outputFileNameVar = tk.StringVar(self._view)
            self._outputFileNameVar.set(editFileNameText)

            # self._outputFileNameObserver = self._outputFileNameVar.trace("w",self._entryChanged)

            self._outputFileNameEntry = tk.Entry(self._view,textvariable=self._outputFileNameVar,width=int(inputFileNameLen*1.5))
            self._outputFileNameEntry.grid(row=1,column=1,sticky=tk.W,pady=(5,0))

            outputExtensionLabel = tk.Label(self._view,text=Sets.LOG_FILE_TYPE,width=columnThreeWidth,anchor=tk.W)
            outputExtensionLabel.grid(row=1,column=2,sticky=tk.W)

            buttomFrame = tk.Frame(self._view)
            buttomFrame.grid(row=2,column=0,columnspan=3,sticky=tk.E,pady=(5,0))

            self._cancelButton = tk.Button(buttomFrame,text="Cancel",command=self._close)
            self._cancelButton.grid(row=0,column=0,padx=(0,5))

            self._saveButton = tk.Button(buttomFrame,text="Save",command=self._saveNewFileName)
            self._saveButton.grid(row=0,column=1)

            self._centerWindowInParent()


            self._outputFileNameEntry.icursor(tk.END)
            self._outputFileNameEntry.focus_set()

            self._view.bind("<Escape>",self._close)
            self._outputFileNameEntry.bind("<Escape>",self._close)
            self._outputFileNameEntry.bind("<Return>",self._saveNewFileName)



    # def _entryChanged(self,*args):
    #     print("Entry changed")

    def _saveNewFileName(self,*args):

        newFileName = self._outputFileNameVar.get() + Sets.LOG_FILE_TYPE

        if self._inputFileName != newFileName:

            fullInputFileName = os.path.join(self._settings.get(Sets.LOG_FILE_PATH),self._inputFileName)
            if os.path.isfile(fullInputFileName):
                fullNewFileName = os.path.join(self._settings.get(Sets.LOG_FILE_PATH),newFileName)
                os.rename(fullInputFileName,fullNewFileName)
                self._textFrame.updateDisconnectLineFileName(self._inputFileName,newFileName)
                traceLog(LogLevel.INFO,"Log file name updated to " + newFileName)
            else:
                traceLog(LogLevel.ERROR,"Log file " + self._inputFileName + " not found in log folder")

        self._close()

    def _centerWindowInParent(self):

        parentW = self._root.winfo_width()
        parentH = self._root.winfo_height()
        parentX = self._root.winfo_x()
        parentY = self._root.winfo_y()

        estViewW = self._view.winfo_reqwidth()
        estViewH = self._view.winfo_reqheight()

        estPosX = parentX + (parentW/2) - (estViewW/2)
        estPosY = parentY + (parentH/2) - (estViewH/2)

        geo = "+" + str(int(estPosX)) + "+" + str(int(estPosY))
        self._view.geometry(geo)

        # TODO draw window below main window and move to front when window size has been found.

        # self._root.update_idletasks()

        # viewW = self._view.winfo_width()
        # viewH = self._view.winfo_height()

        # posX = parentX + (parentW/2) - (viewW/2)
        # posY = parentY + (parentH/2) - (viewH/2)

        # geo = str(int(viewW)) + "x" + str(int(viewH)) + "+" + str(int(posX)) + "+" + str(int(posY))
        # self._view.geometry(geo)