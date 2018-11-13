import tkinter as tk
from tkinter.font import Font
from tkinter.colorchooser import askcolor
from tkinter.ttk import Notebook

from functools import partial
import threading

from traceLog import traceLog,LogLevel
import settings as Sets
import spinner

class OptionsView:

    def __init__(self,settings,rootClass):
        self._settings = settings
        self._root = rootClass.root
        self._highlightWorker = None
        self._guiWorker = None

        self._showing = False
        self._saving = False

        self._textFrame = None

    def linkWorkers(self,workers):
        self._highlightWorker = workers.highlightWorker
        self._guiWorker = workers.guiWorker

    def linkTextFrame(self,textFrame):
        self._textFrame = textFrame        

    def _onClosing(self,savingSettings=False):

        # Delete all variable observers
        for rowId in self._setsDict.keys():
            for entry in self._setsDict[rowId].keys():
                if not "lineFrame" in entry:
                    try:
                        observer = self._setsDict[rowId][entry]["observer"]
                        self._setsDict[rowId][entry]["var"].trace_vdelete("w",observer)
                    except KeyError:
                        pass

        # Delete all view elements
        del self._setsDict

        # Close window
        self._view.destroy()

        if not savingSettings:
            self._showing = False

    class SetLine:
        def __init__(self,setGroup,setId,setDisplayName,setType):
            self.setGroup = setGroup
            self.setId = setId
            self.setDisplayName = setDisplayName
            self.setType = setType

    TYPE_COLOR = "typeColor"
    TYPE_STRING = "typeString"
    TYPE_INT = "typeInt"
    TYPE_REGEX = "typeRegex"
    TYPE_OTHER = "typeOther"

    GROUP_TEXT_AREA = "groupTextArea"
    GROUP_SEARCH = "groupSearch"
    GROUP_LOGGING = "groupLogging"
    GROUP_LINE_COLORING = "groupLineColoring"

    EDIT_UP = "editUp"
    EDIT_DOWN = "editDown"
    EDIT_DELETE = "editDelete"

    ROW_HIGHLIGHT_COLOR = "gray"

    LOG_EXAMPLE_FILE = "log_example.txt"

    def _loadLogExample(self):
        log = "[12:34:56.789] Main::test\n[12:34:56.789] Main::TestTwo"
        try:
            with open(self.LOG_EXAMPLE_FILE,"r") as file:
                log = file.read()
        except FileNotFoundError:
            traceLog(LogLevel.WARNING,"Log example file not found. Using default example")
            pass
        return log

    def show(self,lineColorMap):

        # Only allow one options view at a time
        if not self._showing:

            self._showing = True

            self._lineColorMap = lineColorMap

            self._view = tk.Toplevel(self._root)
            self._view.title("Options")
            self._view.protocol("WM_DELETE_WINDOW", self._onClosing)

            self._setsDict = dict()

            self._notValidEntries = list()

            ##############################
            # TAB CONTROL

            self._tabsFrame = tk.Frame(self._view)
            self._tabsFrame.grid(row=0,column=0)

            self._tabControl = Notebook(self._tabsFrame,padding=10)

            self._tabControl.grid(row=0,column=0,sticky=tk.N)
            self._tabList = list()

            ##############################
            # TEXT EXAMPLE

            logExample = self._loadLogExample()
            exampleTextFrameHeightMin = 280
            exampleTextFrameWidth = 600

            self._exampleTextFrame = tk.Frame(self._tabsFrame,height=exampleTextFrameHeightMin,width=exampleTextFrameWidth)
            self._exampleTextFrame.grid(row=0,column=1, padx=(0,10), pady=(10,10), sticky=tk.N+tk.S)
            self._exampleTextFrame.grid_propagate(False)
            self._exampleTextFrame.grid_columnconfigure(0,weight=1)
            self._exampleTextFrame.grid_rowconfigure(0,weight=1)

            tFont = Font(family=self._settings.get(Sets.FONT_FAMILY), size=self._settings.get(Sets.FONT_SIZE))
            self._exampleText = tk.Text(self._exampleTextFrame,height=1, width=2, \
                                            wrap=tk.NONE,\
                                            background=self._settings.get(Sets.BACKGROUND_COLOR),\
                                            selectbackground=self._settings.get(Sets.SELECT_BACKGROUND_COLOR),\
                                            foreground=self._settings.get(Sets.TEXT_COLOR),\
                                            font=tFont)
            self._exampleText.grid(row=0,column=0, padx=(0,0), pady=(10,0),sticky=tk.E+tk.W+tk.N+tk.S)

            self._exampleText.insert(1.0,logExample)

            xscrollbar=tk.Scrollbar(self._exampleTextFrame, orient=tk.HORIZONTAL, command=self._exampleText.xview)
            xscrollbar.grid(row=1,column=0,sticky=tk.W+tk.E)
            self._exampleText["xscrollcommand"]=xscrollbar.set

            yscrollbar=tk.Scrollbar(self._exampleTextFrame, orient=tk.VERTICAL, command=self._exampleText.yview)
            yscrollbar.grid(row=0,column=1,sticky=tk.N+tk.S)
            self._exampleText["yscrollcommand"]=yscrollbar.set

            ###############
            # Tab: Text Area

            self._textAreaFrame = tk.Frame(self._tabControl,padx=5,pady=5)
            self._textAreaFrame.grid(row=0,column=0,sticky=tk.N)
            self._tabControl.add(self._textAreaFrame, text="Text Area")
            self._tabList.append(self.GROUP_TEXT_AREA)

            setLines = list()
            setLines.append(self.SetLine(self.GROUP_TEXT_AREA, Sets.BACKGROUND_COLOR, "Background Color", self.TYPE_COLOR))
            setLines.append(self.SetLine(self.GROUP_TEXT_AREA, Sets.SELECT_BACKGROUND_COLOR, "Background Color Select", self.TYPE_COLOR))
            setLines.append(self.SetLine(self.GROUP_TEXT_AREA, Sets.TEXT_COLOR, "Text Color", self.TYPE_COLOR))
            setLines.append(self.SetLine(self.GROUP_TEXT_AREA, Sets.FONT_FAMILY, "Font Family", self.TYPE_STRING))
            setLines.append(self.SetLine(self.GROUP_TEXT_AREA, Sets.FONT_SIZE, "Font Size", self.TYPE_INT))

            self._setsDict.update(self._createStandardRows(self._textAreaFrame,setLines,0))


            ###############
            # Tab: Search

            self._searchFrame = tk.Frame(self._tabControl,padx=5,pady=5)
            self._searchFrame.grid(row=0,column=0,sticky=tk.N)
            self._tabControl.add(self._searchFrame, text="Search")
            self._tabList.append(self.GROUP_SEARCH)

            setLines = list()
            setLines.append(self.SetLine(self.GROUP_SEARCH, Sets.SEARCH_MATCH_COLOR, "Search match background color", self.TYPE_COLOR))
            setLines.append(self.SetLine(self.GROUP_SEARCH, Sets.SEARCH_SELECTED_COLOR, "Search selected background color", self.TYPE_COLOR))
            setLines.append(self.SetLine(self.GROUP_SEARCH, Sets.SEARCH_SELECTED_LINE_COLOR, "Search selected line background color", self.TYPE_COLOR))

            self._setsDict.update(self._createStandardRows(self._searchFrame,setLines,0))

            ###############
            # Tab: Logging

            self._loggingFrame = tk.Frame(self._tabControl,padx=5,pady=5)
            self._loggingFrame.grid(row=0,column=0,sticky=tk.N)
            self._tabControl.add(self._loggingFrame, text="Logging")
            self._tabList.append(self.GROUP_LOGGING)

            setLines = list()
            setLines.append(self.SetLine(self.GROUP_LOGGING, Sets.LOG_FILE_PATH, "Log file path", self.TYPE_OTHER))
            setLines.append(self.SetLine(self.GROUP_LOGGING, Sets.LOG_FILE_BASE_NAME, "Log file base name", self.TYPE_OTHER))
            setLines.append(self.SetLine(self.GROUP_LOGGING, Sets.LOG_FILE_TIMESTAMP, "Time stamp", self.TYPE_OTHER))

            self._setsDict.update(self._createStandardRows(self._loggingFrame,setLines,0))


            ###############
            # Tab: Line Coloring

            self._lineColoringFrame = tk.Frame(self._tabControl,padx=5,pady=5)
            self._lineColoringFrame.grid(row=0,column=0,sticky=tk.N)
            self._tabControl.add(self._lineColoringFrame, text="Line Coloring")
            self._tabList.append(self.GROUP_LINE_COLORING)

            self._setsDict.update(self._createLineColorRows(self._lineColoringFrame,self._lineColorMap))

            upButton = tk.Button(self._lineColoringFrame,text="UP",command=partial(self._editLineColorRow,self.EDIT_UP))
            upButton.grid(row=0,column=2,padx=2)

            downButton = tk.Button(self._lineColoringFrame,text="DOWN",command=partial(self._editLineColorRow,self.EDIT_DOWN))
            downButton.grid(row=1,column=2,padx=2)

            deleteButton = tk.Button(self._lineColoringFrame,text="Delete",command=partial(self._editLineColorRow,self.EDIT_DELETE))
            deleteButton.grid(row=2,column=2,padx=2)
            self._lastFocusInRowId = ""
            self._lastFocusOutRowId = ""

            self._newButtonRow = len(self._lineColorMap)
            self._newButton  = tk.Button(self._lineColoringFrame,text="New Line",command=partial(self._addNewEmptyLineColor,self._lineColoringFrame))
            self._newButton.grid(row=self._newButtonRow,column=0,sticky=tk.W,padx=(2,100),pady=2)




            ##############################
            # CONTROL ROW

            self._optionsControlFrame = tk.Frame(self._view)
            self._optionsControlFrame.grid(row=1,column=0,padx=(10,10),pady=(0,10),sticky=tk.W+tk.E)

            self._optionsInfoLabel = tk.Label(self._optionsControlFrame,text="",justify=tk.LEFT)
            self._optionsInfoLabel.grid(row=0,column=0,sticky=tk.W)
            self._optionsControlFrame.columnconfigure(0,weight=1)

            self._optionsCancelButton = tk.Button(self._optionsControlFrame,text="Cancel",command=self._onClosing)
            self._optionsCancelButton.grid(row=0,column=1,padx=5,sticky=tk.E)

            self._optionsSaveButton = tk.Button(self._optionsControlFrame,text="Save",command=self._saveSettings)
            self._optionsSaveButton.grid(row=0,column=2,sticky=tk.E)
            if self._saving:
                self._optionsSaveButton.config(state=tk.DISABLED)
            else:
                self._optionsSaveButton.config(state=tk.NORMAL)

            self._tabControl.bind("<<NotebookTabChanged>>",self._tabChanged)

    def _saveSettings(self):

        saveSettingsThread = threading.Thread(target=self._saveSettingsProcess,name="SaveSettings")
        saveSettingsThread.start()

        self._saving = True

    def _setSaveButtonState(self,state):
        if self._showing:
            try:
                self._optionsSaveButton.config(state=state)
            except:
                # Catch if function is called while save button does not exist
                traceLog(LogLevel.ERROR,"Error updating save button state")


    def _saveSettingsProcess(self):
        # Saving will block, so must be done in different thread

        # setsDict will be deleted in the onClosing function
        tempSetsDict = self._setsDict

        # Close options view
        self._root.after(10,self._onClosing,True)

        # Show saving message
        saveSpinner = spinner.Spinner(self._root)
        saveSpinner.show(indicators=False,message="Reloading View")

        # Stop workers using the settings
        self._highlightWorker.stopWorker(emptyQueue=False)
        self._guiWorker.stopWorker()

        # Save all settings
        tempLineColorMap = dict()
        # Sort settings to guarantee right order of line coloring
        for rowId in sorted(tempSetsDict.keys()):

            if Sets.LINE_COLOR_MAP in rowId:
                tempLineColorMap[rowId] = dict()

            for entry in tempSetsDict[rowId].keys():
                if not "lineFrame" in entry:
                    setting = tempSetsDict[rowId][entry]["var"].get()

                    if Sets.LINE_COLOR_MAP in rowId:
                        tempLineColorMap[rowId][entry] = setting
                    else:
                        self._settings.setOption(rowId,setting)

        self._settings.setOption(Sets.LINE_COLOR_MAP,tempLineColorMap)

        # Once settings have been saved, allow for reopen of options view
        self._showing = False

        # Reload main interface
        self._textFrame.reloadLineColorMapAndTags()
        self._textFrame.reloadTextFrame()

        # Start highlightworker to prepare buffer reload
        self._highlightWorker.startWorker()

        # Reload line/gui buffer
        self._highlightWorker.reloadLineBuffer()
        self._guiWorker.guiReloadEvent.clear()

        # Start gui worker to process new buffer
        self._guiWorker.startWorker()

        # Wait for GUI worker to have processed the new buffer
        self._guiWorker.guiReloadEvent.wait()

        # Remove spinner
        saveSpinner.close()

        # Update save button, if window has been opened again
        self._root.after(10,self._setSaveButtonState,tk.NORMAL)
        self._saving = False


    ####################################
    # View Creation

    def _addNewEmptyLineColor(self,parent):
        # print("New Button " + str(self.newButtonRow))

        self._newButton.grid(row=self._newButtonRow+1)

        rowId = self._getRowId(self._newButtonRow)
        self._setsDict[rowId] = self._createSingleLineColorRow(self._lineColoringFrame,self._newButtonRow,rowId,"","white")

        self._newButtonRow += 1

    def _editLineColorRow(self,edit):
        # print("Last focus in " + self.lastFocusInRowId)
        # print("Last focus out " + self.lastFocusOutRowId)

        # If lastFocusIn is not the same as lastFocusOut,
        # we know that lastFocusIn is currently selected.
        if self._lastFocusInRowId != self._lastFocusOutRowId:
            if Sets.LINE_COLOR_MAP in self._lastFocusInRowId:
                # print("EDIT: " + self.lastFocusInRowId)

                # Get row number
                rowNum = int(self._lastFocusInRowId.replace(Sets.LINE_COLOR_MAP,""))

                # Find index of rows to edit
                indexToChange = list()
                if edit == self.EDIT_UP:
                    if rowNum > 0:
                        indexToChange = [rowNum-1, rowNum]
                elif edit == self.EDIT_DOWN:
                    if rowNum < (self._newButtonRow - 1):
                        indexToChange = [rowNum, rowNum+1]
                elif edit == self.EDIT_DELETE:
                    indexToChange = range(rowNum,self._newButtonRow)

                if indexToChange:

                    tempTextColorMap = list()
                    for i in indexToChange:
                        # Save regex and color
                        rowId = self._getRowId(i)
                        tempTextColorMap.append((self._setsDict[rowId]["regex"]["var"].get(),self._setsDict[rowId]["color"]["var"].get()))

                        # Remove rows to edit from view
                        self._setsDict[rowId]["lineFrame"].destroy()
                        del self._setsDict[rowId]

                    # Reorder or delete saved rows
                    newRowNum = -1
                    if edit == self.EDIT_UP:
                        tempTextColorMap[1], tempTextColorMap[0] = tempTextColorMap[0], tempTextColorMap[1]
                        newRowNum = rowNum-1
                    elif edit == self.EDIT_DOWN:
                        tempTextColorMap[1], tempTextColorMap[0] = tempTextColorMap[0], tempTextColorMap[1]
                        newRowNum = rowNum+1
                    elif edit == self.EDIT_DELETE:
                        del tempTextColorMap[0]

                    # Recreate saved rows
                    for i,(regex,color) in enumerate(tempTextColorMap):
                        rowId = self._getRowId(indexToChange[i])
                        self._setsDict[rowId] = self._createSingleLineColorRow(self._lineColoringFrame,indexToChange[i],rowId,regex,color)

                    # If move up or down, refocus
                    if newRowNum > -1:
                        rowId = self._getRowId(newRowNum)
                        self._focusInSet(rowId)
                    # If delete, update row count and move newButton
                    else:
                        self._newButtonRow = self._newButtonRow - 1
                        self._newButton.grid(row=self._newButtonRow)
                        self._lastFocusInRowId = ""


                    self._updateExampleText(self.GROUP_LINE_COLORING)


    def _createLineColorRows(self,parent,lineColorMap):
        setDict = dict()
        for rowId in sorted(lineColorMap.keys()):
            rowNum = int(rowId.replace(Sets.LINE_COLOR_MAP,""))
            setDict[rowId] = self._createSingleLineColorRow(parent,rowNum,rowId,lineColorMap[rowId]["regex"],lineColorMap[rowId]["color"])

        return setDict

    def _createSingleLineColorRow(self,parent,row,rowId,regex,color):
        colorLine = dict()

        colorLine["lineFrame"] = tk.Frame(parent,highlightcolor=self.ROW_HIGHLIGHT_COLOR,highlightthickness=2)
        colorLine["lineFrame"].grid(row=row,column=0)
        colorLine["lineFrame"].bind("<Button-1>",partial(self._focusInSet,rowId))
        colorLine["lineFrame"].bind("<FocusOut>",partial(self._focusOut,rowId))

        regexEntry = dict()
        entryName = "regex"

        regexEntry["label"] = tk.Label(colorLine["lineFrame"],text="Regex")
        regexEntry["label"].grid(row=0,column=0)
        regexEntry["label"].bind("<Button-1>",partial(self._focusInSet,rowId))
        regexEntry["var"] = tk.StringVar(colorLine["lineFrame"])
        regexEntry["var"].set(regex)
        regexEntry["observer"] = regexEntry["var"].trace("w",partial(self._validateInput,rowId,entryName))

        regexEntry["input"] = tk.Entry(colorLine["lineFrame"],textvariable=regexEntry["var"],width=30,takefocus=False) # Will this work?
        regexEntry["input"].grid(row=0,column=1)
        regexEntry["input"].bind("<Button-1>",partial(self._focusInLog,rowId))

        regexEntry["type"] = self.TYPE_REGEX
        regexEntry["group"] = self.GROUP_LINE_COLORING

        colorLine[entryName] = regexEntry


        colorEntry = dict()
        entryName = "color"

        colorEntry["label"] = tk.Label(colorLine["lineFrame"],text="Color")
        colorEntry["label"].grid(row=0,column=2)
        colorEntry["label"].bind("<Button-1>",partial(self._focusInSet,rowId))

        colorEntry["var"] = tk.StringVar(colorLine["lineFrame"])
        colorEntry["var"].set(color)
        colorEntry["observer"] = colorEntry["var"].trace("w",partial(self._validateInput,rowId,entryName))
        colorEntry["input"] = tk.Entry(colorLine["lineFrame"],textvariable=colorEntry["var"],width=10,takefocus=False)
        colorEntry["input"].grid(row=0,column=3)
        colorEntry["input"].bind("<Button-1>",partial(self._focusInLog,rowId))

        colorEntry["button"] = tk.Button(colorLine["lineFrame"],bg=color,width=3,command=partial(self._getColor,rowId,entryName,True))
        colorEntry["button"].grid(row=0,column=4,padx=4)
        colorEntry["button"].bind("<Button-1>",partial(self._focusInSet,rowId))

        colorEntry["type"] = self.TYPE_COLOR
        colorEntry["group"] = self.GROUP_LINE_COLORING

        colorLine[entryName] = colorEntry

        return colorLine

    def _createStandardRows(self,parent,setLines,startRow):
        setDict = dict()

        # Find longest entry in settings
        maxLen = 0
        for setLine in setLines:
            setLen = len(str(self._settings.get(setLine.setId)))
            if setLen > maxLen:
                maxLen = setLen

        row = startRow
        for setLine in setLines:
            setRow = dict()
            entry = dict()

            entryName = "entry"

            # TODO Add frame and highlight to colors (remember column widths and alignment)

            entry["label"] = tk.Label(parent,text=setLine.setDisplayName)
            entry["label"].grid(row=row,column=0,sticky=tk.W)

            if setLine.setType == self.TYPE_INT:
                entry["var"] = tk.IntVar(parent)
            else:
                entry["var"] = tk.StringVar(parent)
            entry["var"].set(self._settings.get(setLine.setId))
            # TODO use tkinter validateCommand
            entry["observer"] = entry["var"].trace("w",partial(self._validateInput,setLine.setId,entryName))
            # TODO Find better solution for entry width
            entry["input"] = tk.Entry(parent,textvariable=entry["var"],width=int(maxLen*1.5),takefocus=False)
            entry["input"].grid(row=row,column=1)
            if setLine.setType == self.TYPE_COLOR:
                entry["button"] = tk.Button(parent,bg=self._settings.get(setLine.setId),width=3,command=partial(self._getColor,setLine.setId,entryName))
                entry["button"].grid(row=row,column=2,padx=4)

            entry["type"] = setLine.setType
            entry["group"] = setLine.setGroup
            setRow[entryName] = entry
            setDict[setLine.setId] = setRow

            row += 1

        return setDict



    ####################################
    # View Interaction

    def _focusOut(self,rowId,event):
        self._lastFocusOutRowId = rowId

    def _focusInSet(self,rowId,event=0):
        self._setsDict[rowId]["lineFrame"].focus_set()
        self._focusInLog(rowId,event)

    def _focusInLog(self,rowId,event=0):
        self._lastFocusInRowId = rowId
        if self._lastFocusOutRowId == rowId:
            self._lastFocusOutRowId = ""

    def _getColor(self,rowId,entry,highlight=False):

        if highlight:
            hg = self._setsDict[rowId]["lineFrame"].cget("highlightbackground")
            self._setsDict[rowId]["lineFrame"].config(highlightbackground=self.ROW_HIGHLIGHT_COLOR)

        currentColor = self._setsDict[rowId][entry]["button"].cget("bg")

        if not self._isValidColor(currentColor):
            currentColor = None

        color = askcolor(initialcolor=currentColor,parent=self._view)

        if color[1] != None:
            self._setsDict[rowId][entry]["var"].set(color[1])
            self._setsDict[rowId][entry]["button"].config(bg=color[1])

        if highlight:
            self._setsDict[rowId]["lineFrame"].config(highlightbackground=hg)
            self._focusInLog(rowId)

    # class WidgetSize:
    #     def __init__(self,width,height,posx,posy):
    #         self.width = width
    #         self.height = height
    #         self.posx = posx
    #         self.posy = posy

    # def _getWidgetSize_(self,widget):

    #     width = widget.winfo_width()
    #     height = widget.winfo_height()
    #     posx = widget.winfo_x()
    #     posy = widget.winfo_y()

    #     return self.WidgetSize(width,height,posx,posy)

    def _tabChanged(self,event):
        self._view.focus_set()
        self._updateExampleText(self._tabList[self._tabControl.index("current")])

    def _updateExampleText(self,group):

        #####################
        # Setup

        # Delete all search tags
        self._exampleText.tag_delete(Sets.SEARCH_SELECTED_LINE_COLOR)
        self._exampleText.tag_delete(Sets.SEARCH_MATCH_COLOR)
        self._exampleText.tag_delete(Sets.SEARCH_SELECTED_COLOR)

        # Delete all current line color tags
        tagNames = self._exampleText.tag_names()
        for tagName in tagNames:
            if Sets.LINE_COLOR_MAP in tagName:
                self._exampleText.tag_delete(tagName)

        entryName = "entry"
        if group == self.GROUP_TEXT_AREA:
            # General text area
            try:
                tFont = Font(family=self._setsDict[Sets.FONT_FAMILY][entryName]["var"].get(),\
                            size=self._setsDict[Sets.FONT_SIZE][entryName]["var"].get())
                self._exampleText.config(background=self._setsDict[Sets.BACKGROUND_COLOR][entryName]["var"].get(),\
                                                selectbackground=self._setsDict[Sets.SELECT_BACKGROUND_COLOR][entryName]["var"].get(),\
                                                foreground=self._setsDict[Sets.TEXT_COLOR][entryName]["var"].get(),\
                                                font=tFont)
            except tk.TclError:
                pass

        elif group == self.GROUP_SEARCH:

            searchString = "Main"

            # Create search tags
            self._exampleText.tag_configure(Sets.SEARCH_SELECTED_LINE_COLOR, background=self._setsDict[Sets.SEARCH_SELECTED_LINE_COLOR][entryName]["var"].get())
            self._exampleText.tag_configure(Sets.SEARCH_MATCH_COLOR, background=self._setsDict[Sets.SEARCH_MATCH_COLOR][entryName]["var"].get())
            self._exampleText.tag_configure(Sets.SEARCH_SELECTED_COLOR, background=self._setsDict[Sets.SEARCH_SELECTED_COLOR][entryName]["var"].get())

            # Do search
            countVar = tk.StringVar()
            results = list()
            start = 1.0
            while True:
                pos = self._exampleText.search(searchString,start,stopindex=tk.END,count=countVar,nocase=False,regexp=False)
                if not pos:
                    break
                else:
                    results.append((pos,pos + "+" + countVar.get() + "c"))
                    start = pos + "+1c"

            # Add search tags
            first = True
            for result in results:
                self._exampleText.tag_add(Sets.SEARCH_MATCH_COLOR, result[0], result[1])
                if first:
                    first = False
                    self._exampleText.tag_add(Sets.SEARCH_SELECTED_COLOR, result[0], result[1])
                    selectLine = result[0].split(".")[0]
                    self._exampleText.tag_add(Sets.SEARCH_SELECTED_LINE_COLOR, selectLine + ".0", selectLine + ".0+1l")



        if group == self.GROUP_LINE_COLORING or group == self.GROUP_SEARCH:

            # Get line color map from view
            tempLineColorMap = list()
            for rowId in sorted(self._setsDict.keys()):
                if Sets.LINE_COLOR_MAP in rowId:
                    lineInfo = dict()
                    lineInfo["rowId"] = rowId
                    lineInfo["regex"] = self._setsDict[rowId]["regex"]["var"].get()
                    lineInfo["color"] = self._setsDict[rowId]["color"]["var"].get()
                    tempLineColorMap.append(lineInfo)

            # Apply new line colors
            for lineInfo in tempLineColorMap:
                self._exampleText.tag_configure(lineInfo["rowId"],foreground=lineInfo["color"])

                countVar = tk.StringVar()
                start = 1.0
                while True:
                    pos = self._exampleText.search(lineInfo["regex"],start,stopindex=tk.END,count=countVar,nocase=False,regexp=True)
                    if not pos:
                        break
                    else:
                        self._exampleText.tag_add(lineInfo["rowId"],pos,pos + "+" + countVar.get() + "c")
                        start = pos + "+1c"



    ####################################
    # Entry Validation

    def _validateInput(self,rowId,entryName,*args):

        # Get variable
        varIn = None
        try:
            varIn = self._setsDict[rowId][entryName]["var"].get()
            isValid = True
        except tk.TclError:
            # print("Tcl Error")
            isValid = False

        if isValid:

            # Check Colors
            if self._setsDict[rowId][entryName]["type"] == self.TYPE_COLOR:
                color = varIn
                isValid = self._isValidColor(color)
                if isValid:
                    # print("Color " + str(color))
                    self._setsDict[rowId][entryName]["button"].config(background=color)

            # Check regex
            if self._setsDict[rowId][entryName]["type"] == self.TYPE_REGEX:
                isValid = self._isValidRegex(varIn)

            # Check font family
            if rowId == Sets.FONT_FAMILY:
                isValid = self._isValidFontFamily(varIn)

            # Check font size
            if rowId == Sets.FONT_SIZE:
                isValid = self._isValidFontSize(varIn)

            if isValid:
                self._updateExampleText(self._setsDict[rowId][entryName]["group"])

        entryId = rowId + "_" + entryName

        try:
            self._notValidEntries.remove(entryId)
        except ValueError:
            pass

        if isValid:
            self._setsDict[rowId][entryName]["input"].config(background="white")
        else:
            self._setsDict[rowId][entryName]["input"].config(background="red")
            self._notValidEntries.append(entryId)

        infoText = ""
        for notValidEntry in self._notValidEntries:
            if infoText:
                infoText += "\n"
            infoText += notValidEntry + " not valid."

        if infoText:
            self._optionsInfoLabel.config(text=infoText)
        else:
            self._optionsInfoLabel.config(text="")

        if self._notValidEntries:
            self._setSaveButtonState(tk.DISABLED)
        else:
            self._setSaveButtonState(tk.NORMAL)


    def _isValidColor(self,colorString):
        isValid = True
        try:
            tk.Label(None,background=colorString)
        except tk.TclError:
            # print("Color Error")
            isValid = False
        return isValid

    def _isValidFontFamily(self,family):
        fontList = tk.font.families()
        return family in fontList

    def _isValidFontSize(self,size):
        isValid = True
        try:
            Font(size=size)
        except tk.TclError:
            # print("Font Size Error")
            isValid = False

        if isValid:
            if int(size) < 1:
                isValid = False

        return isValid

    def _isValidRegex(self,regex):
        isValid = True
        try:
            # re.compile(regex) # Tkinter does not allow all regex, so this cannot be used
            self._exampleText.search(regex,1.0,stopindex=tk.END,regexp=True)
        except:
            isValid = False
        return isValid

    ####################################
    # Misc

    def _getRowId(self,rowNum):
        return Sets.LINE_COLOR_MAP + "{:02d}".format(rowNum)