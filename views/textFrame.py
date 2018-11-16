
import tkinter as tk
from tkinter.font import Font

from traceLog import traceLog,LogLevel
import settings as Sets
import renameFileView

# Import for intellisense 
from workers.highlightWorker import HighlightWorker


def createLineColorTagName(regex):
    return Sets.LINE_COLOR_MAP + "_" + regex.replace(" ","__")

class TextFrame:

    def __init__(self,settings,rootClass):
        self._settings_ = settings
        self._root_ = rootClass.root

        self._lineColorMap_ = dict()

        self._highlightWorker_:HighlightWorker = None

        self._textFrame_ = tk.Frame(self._root_)

        fontList_ = tk.font.families()
        if not self._settings_.get(Sets.FONT_FAMILY) in fontList_:
            traceLog(LogLevel.WARNING,"Font \"" + self._settings_.get(Sets.FONT_FAMILY) + "\" not found in system")

        tFont_ = Font(family=self._settings_.get(Sets.FONT_FAMILY), size=self._settings_.get(Sets.FONT_SIZE))

        self.textArea = tk.Text(self._textFrame_, height=1, width=1, background=self._settings_.get(Sets.BACKGROUND_COLOR),\
                                selectbackground=self._settings_.get(Sets.SELECT_BACKGROUND_COLOR),\
                                foreground=self._settings_.get(Sets.TEXT_COLOR), font=tFont_)

        self.textArea.config(state=tk.DISABLED)

        # Set up scroll bar
        yscrollbar_=tk.Scrollbar(self._textFrame_, orient=tk.VERTICAL, command=self.textArea.yview)
        yscrollbar_.pack(side=tk.RIGHT, fill=tk.Y)
        self.textArea["yscrollcommand"]=yscrollbar_.set
        self.textArea.pack(side=tk.LEFT, fill=tk.BOTH, expand = tk.YES)


        self.textArea.tag_configure(Sets.CONNECT_COLOR_TAG, background=Sets.CONNECT_LINE_BACKGROUND_COLOR, selectbackground=Sets.CONNECT_LINE_SELECT_BACKGROUND_COLOR)
        self.textArea.tag_configure(Sets.DISCONNECT_COLOR_TAG, background=Sets.DISCONNECT_LINE_BACKGROUND_COLOR, selectbackground=Sets.DISCONNECT_LINE_SELECT_BACKGROUND_COLOR)
        self.textArea.tag_configure(Sets.HIDELINE_COLOR_TAG, foreground=Sets.HIDE_LINE_FONT_COLOR)
        self.textArea.tag_configure(Sets.LOG_FILE_LINK_TAG, underline=1)

        self.textArea.tag_bind(Sets.LOG_FILE_LINK_TAG, "<Enter>", self._enter_)
        self.textArea.tag_bind(Sets.LOG_FILE_LINK_TAG, "<Leave>", self._leave_)
        self.textArea.tag_bind(Sets.LOG_FILE_LINK_TAG, "<Button-1>", self._click_)        

        self._textFrame_.pack(side=tk.TOP, fill=tk.BOTH, expand = tk.YES)

        self.reloadLineColorMap()
        self.createAllTextFrameLineColorTag()


    def linkWorkers(self,workers):
        self._highlightWorker_ = workers.highlightWorker

    def reloadLineColorMap(self):
        
        self._lineColorMap_.clear()
        self._lineColorMap_ = self._settings_.get(Sets.LINE_COLOR_MAP)
        # Add tag names to line color map
        for lineColorRowId in self._lineColorMap_.keys():
            self._lineColorMap_[lineColorRowId]["tagName"] = createLineColorTagName(self._lineColorMap_[lineColorRowId]["regex"])

    def getLineColorMap(self):
        return self._lineColorMap_

    def createAllTextFrameLineColorTag(self):        
        for key in sorted(self._lineColorMap_.keys()):            
             self.createTextFrameLineColorTag(self._lineColorMap_[key]["tagName"], self._lineColorMap_[key]["color"])

    def createTextFrameLineColorTag(self,tagName,color):
        self.textArea.tag_configure(tagName, foreground=color)

    def updateTagColor(self,tagName,color): # TODO the same as the above function?
        self.textArea.tag_config(tagName,foreground=color)   

    def deleteTextTag(self,tagName):
        self.textArea.tag_delete(tagName)

    def reloadTextFrame(self):

        traceLog(LogLevel.DEBUG,"Reload text frame")

        tFont = Font(family=self._settings_.get(Sets.FONT_FAMILY), size=self._settings_.get(Sets.FONT_SIZE))

        self.textArea.config(background=self._settings_.get(Sets.BACKGROUND_COLOR),\
                            selectbackground=self._settings_.get(Sets.SELECT_BACKGROUND_COLOR),\
                            foreground=self._settings_.get(Sets.TEXT_COLOR), font=tFont)

    def addLineColorTagToText(self,regex,tagName):

        lastline = int(self.textArea.index("end-2c").split(".")[0])

        for lineNumber in range(1,lastline+1):
            start = str(lineNumber) + ".0"
            end = start + "+1l"
            countVar = tk.StringVar()
            pos = self.textArea.search(regex,start,stopindex=end,count=countVar,nocase=False,regexp=True)
            if pos:
                self.textArea.tag_add(tagName,pos,pos + "+" + countVar.get() + "c")

    def createAndAddLineColorTag(self,regex,color):

        tagName = createLineColorTagName(regex)
        self.createTextFrameLineColorTag(tagName,color)

        self.addLineColorTagToText(regex,tagName)


    # Hyberlink

    def _enter_(self, event):
        self.textArea.config(cursor="hand2")

    def _leave_(self, event):
        self.textArea.config(cursor="")

    def _click_(self, event):

        index = self.textArea.index("@" + str(event.x) + "," + str(event.y))
        
        lineNumber = index.split(".")[0]

        fileNameRegex = self._settings_.get(Sets.LOG_FILE_BASE_NAME) + ".*" + Sets.LOG_FILE_TYPE

        startIndex = str(lineNumber) + ".0"
        stopIndex = startIndex + "+1l"

        countVar = tk.StringVar()
        pos = self.textArea.search(fileNameRegex,startIndex,stopindex=stopIndex,count=countVar,nocase=True,regexp=True)
        if pos:
            fileName = self.textArea.get(pos,pos + "+" + countVar.get() + "c")
            
            renameFileView.RenameFile(self._settings_,self,self._root_,fileName)            
        else:
            traceLog(LogLevel.ERROR, "Internal problem. No valid file name found in line")

    def updateDisconnectLineFileName(self,oldFileName,newFileName):
        
        # Update filename in line buffer
        self._highlightWorker_.replaceLineBufferString(oldFileName,newFileName)

        countVar = tk.StringVar()
        pos = self.textArea.search(oldFileName,"1.0",stopindex=tk.END,count=countVar,nocase=True,regexp=False)
        
        if pos:
            lineNumber = pos.split(".")[0]

            self.textArea.config(state=tk.NORMAL)

            # Remove log file tag from line (needed?)
            self.textArea.tag_remove(Sets.LOG_FILE_LINK_TAG,lineNumber + ".0",lineNumber + ".0+1l")

            # Delete old log file name
            self.textArea.delete(pos,pos + "+" + countVar.get() + "c")

            # Insert new log file name
            self.textArea.insert(pos,newFileName)

            # Add link tag to new file name
            self.textArea.tag_add(Sets.LOG_FILE_LINK_TAG,pos,pos + "+" + str(len(newFileName)) + "c")

            self.textArea.config(state=tk.DISABLED)

