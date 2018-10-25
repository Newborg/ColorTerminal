
import tkinter as tk
from tkinter.font import Font

from traceLog import traceLog,LogLevel
import settings as Sets


class TextFrame:

    def __init__(self,settings,rootClass):
        self._settings_ = settings
        self._root_ = rootClass.root

        self._highlightWorker_ = None

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

        self._textFrame_.pack(side=tk.TOP, fill=tk.BOTH, expand = tk.YES)


    def linkWorkers(self,workers):
        self._highlightWorker_ = workers.highlightWorker

    def createTextFrameLineColorTag(self):
        lineColorMap = self._highlightWorker_.getLineColorMap()

        for key in sorted(lineColorMap.keys()):
             self.textArea.tag_configure(key, foreground=lineColorMap[key]["color"])

    def reloadLineColorMapAndTags(self):

        lineColorMapKeys = self._highlightWorker_.getLineColorMap().keys()
        self._textFrameClearTags_(lineColorMapKeys)

        self._highlightWorker_.reloadLineColorMap()

        self.createTextFrameLineColorTag()

    def reloadTextFrame(self):

        traceLog(LogLevel.DEBUG,"Reload text frame")

        tFont = Font(family=self._settings_.get(Sets.FONT_FAMILY), size=self._settings_.get(Sets.FONT_SIZE))

        self.textArea.config(background=self._settings_.get(Sets.BACKGROUND_COLOR),\
                            selectbackground=self._settings_.get(Sets.SELECT_BACKGROUND_COLOR),\
                            foreground=self._settings_.get(Sets.TEXT_COLOR), font=tFont)

    def _textFrameClearTags_(self,tagNames):
        # clear existing tags
        for tagName in tagNames:
            self.textArea.tag_delete(tagName)