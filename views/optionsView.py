import tkinter as tk
from tkinter.font import Font
from tkinter.colorchooser import askcolor
from tkinter.ttk import Notebook

from collections import Counter

from functools import partial
import threading

from traceLog import traceLog,LogLevel
import settings as Sets
import spinner
import util

from frames import textFrame as TF

class OptionsView:

    def __init__(self,settings,root,iconPath,comController):
        self._settings = settings
        self._root = root
        self._iconPath = iconPath
        self._comController = comController

        self._highlightWorker = None
        self._guiWorker = None

        self._showing = False
        self._saving = False

        self._textFrame:TF.TextFrame = None

    def linkWorkers(self,workers):
        self._highlightWorker = workers.highlightWorker
        self._guiWorker = workers.guiWorker

    def linkTextFrame(self,textFrame):
        self._textFrame = textFrame

    def _onClosing(self,savingSettings=False):

        # Delete all variable observers
        for settingsLine in list(self._setsDict.values()):
            for entry in list(settingsLine.entries.values()):
                try:
                    entry.var.trace_vdelete("w",entry.observer)
                except:
                    pass

        # Delete all view elements
        del self._setsDict

        # Close window
        self._view.destroy()

        if not savingSettings:
            self._showing = False

    class SettingsLineTemplate:
        def __init__(self,setGroup,setId,setDisplayName,setType):
            self.setGroup = setGroup
            self.setId = setId
            self.setDisplayName = setDisplayName
            self.setType = setType

    class SettingsLine:
        def __init__(self,group):
            self.group = group
            self.entries = dict()

    class LineColorSettingsLine(SettingsLine):
        def __init__(self,group):
            super().__init__(group)
            self.lineFrame = None

    class Entry:
        def __init__(self,entryType,entryVar):
            self.label:tk.Label = None
            self.var = None
            self.observer = None
            self.input:tk.Entry = None
            self.button:tk.Button = None
            self.data = OptionsView.EntryData(entryType,entryVar)

        def isVarUpdated(self):
            updated = False
            try:
                updated = self.var.get() != self.data.entryVar
            except AttributeError:
                traceLog(LogLevel.ERROR,"Tkinter var in OptionsView not initiated")
                updated = True
            return updated

    class EntryData:
        def __init__(self,entryType,entryVar):
            self.entryType = entryType
            self.entryVar = entryVar
            self.validation = OptionsView.EntryDataValidation(OptionsView.ENTRY_VALIDATION_OK,"white","")

    class EntryDataValidation:
        def __init__(self,status,backgroundColor,infoText):
            self.status = status
            self.backgroundColor = backgroundColor
            self.infoText = infoText

    ENTRY_TYPE_COLOR = "typeColor"
    ENTRY_TYPE_STRING = "typeString"
    ENTRY_TYPE_INT = "typeInt"
    ENTRY_TYPE_REGEX = "typeRegex"
    ENTRY_TYPE_TOGGLE = "typeToggle"
    ENTRY_TYPE_OTHER = "typeOther"

    ENTRY_VALIDATION_OK = "entryValidationOk"
    ENTRY_VALIDATION_FAILED = "entryValidationFailed"
    ENTRY_VALIDATION_DUPLICATE = "entryValidationDuplicate"

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

    def show(self):

        # Only allow one options view at a time # TODO Can be done with a global var, then a global instance of OptionsView is not needed
        if not self._showing:

            self._showing = True

            self._lineColorMap = self._textFrame.getLineColorMap()

            self._view = tk.Toplevel(self._root)
            self._view.title("Options")
            self._view.protocol("WM_DELETE_WINDOW", self._onClosing)

            self._view.iconbitmap(self._iconPath)

            self._setsDict = dict()

            ##############################
            # TAB CONTROL

            self._tabsFrame = tk.Frame(self._view)
            self._tabsFrame.grid(row=0,column=0,sticky="nsew")
            self._view.columnconfigure(0,weight=1)
            self._view.rowconfigure(0,weight=1)

            self._tabControl = Notebook(self._tabsFrame,padding=10)

            self._tabControl.grid(row=0,column=0,sticky=tk.N)
            self._tabList = list()

            ##############################
            # TEXT EXAMPLE

            logExample = self._loadLogExample()
            exampleTextFrameHeightMin = 400
            exampleTextFrameWidth = 650

            self._exampleTextFrame = tk.Frame(self._tabsFrame,height=exampleTextFrameHeightMin,width=exampleTextFrameWidth)
            self._exampleTextFrame.grid(row=0,column=1, padx=(0,10), pady=(10,10), sticky="nsew")
            self._exampleTextFrame.grid_propagate(False)
            self._tabsFrame.columnconfigure(1,weight=1)
            self._tabsFrame.rowconfigure(0,weight=1)

            tFont = Font(family=self._settings.get(Sets.TEXTAREA_FONT_FAMILY), size=self._settings.get(Sets.TEXTAREA_FONT_SIZE))
            self._exampleText = tk.Text(self._exampleTextFrame,height=1, width=2,\
                                            background=self._settings.get(Sets.TEXTAREA_BACKGROUND_COLOR),\
                                            selectbackground=self._settings.get(Sets.TEXTAREA_SELECT_BACKGROUND_COLOR),\
                                            foreground=self._settings.get(Sets.TEXTAREA_COLOR),\
                                            font=tFont)
            self._exampleText.grid(row=0,column=0, padx=(0,0), pady=(10,0),sticky="nsew")
            self._exampleTextFrame.columnconfigure(0,weight=1)
            self._exampleTextFrame.rowconfigure(0,weight=1)

            self._updateExampleTextLineWrap(self._settings.get(Sets.TEXTAREA_LINE_WRAP))

            self._exampleText.insert(1.0,logExample)

            xscrollbar=tk.Scrollbar(self._exampleTextFrame, orient=tk.HORIZONTAL, command=self._exampleText.xview)
            xscrollbar.grid(row=1,column=0,sticky=tk.W+tk.E)
            self._exampleText["xscrollcommand"]=xscrollbar.set

            yscrollbar=tk.Scrollbar(self._exampleTextFrame, orient=tk.VERTICAL, command=self._exampleText.yview)
            yscrollbar.grid(row=0,column=1,sticky=tk.N+tk.S)
            self._exampleText["yscrollcommand"]=yscrollbar.set

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

            self._deletedLineColorRows = list()

            ###############
            # Tab: Text Area

            self._textAreaFrame = tk.Frame(self._tabControl,padx=5,pady=5)
            self._textAreaFrame.grid(row=0,column=0,sticky=tk.N)
            self._tabControl.add(self._textAreaFrame, text="Text Area")
            self._tabList.append(self.GROUP_TEXT_AREA)

            setLines = list()
            setLines.append(self.SettingsLineTemplate(self.GROUP_TEXT_AREA, Sets.TEXTAREA_BACKGROUND_COLOR, "Background Color", self.ENTRY_TYPE_COLOR))
            setLines.append(self.SettingsLineTemplate(self.GROUP_TEXT_AREA, Sets.TEXTAREA_SELECT_BACKGROUND_COLOR, "Background Color Select", self.ENTRY_TYPE_COLOR))
            setLines.append(self.SettingsLineTemplate(self.GROUP_TEXT_AREA, Sets.TEXTAREA_COLOR, "Text Color", self.ENTRY_TYPE_COLOR))
            setLines.append(self.SettingsLineTemplate(self.GROUP_TEXT_AREA, Sets.TEXTAREA_FONT_FAMILY, "Font Family", self.ENTRY_TYPE_STRING))
            setLines.append(self.SettingsLineTemplate(self.GROUP_TEXT_AREA, Sets.TEXTAREA_FONT_SIZE, "Font Size", self.ENTRY_TYPE_INT))
            setLines.append(self.SettingsLineTemplate(self.GROUP_TEXT_AREA, Sets.TEXTAREA_LINE_WRAP, "Line Wrap", self.ENTRY_TYPE_TOGGLE))

            self._setsDict.update(self._createStandardRows(self._textAreaFrame,setLines,0))


            ###############
            # Tab: Search

            self._searchFrame = tk.Frame(self._tabControl,padx=5,pady=5)
            self._searchFrame.grid(row=0,column=0,sticky=tk.N)
            self._tabControl.add(self._searchFrame, text="Search")
            self._tabList.append(self.GROUP_SEARCH)

            setLines = list()
            setLines.append(self.SettingsLineTemplate(self.GROUP_SEARCH, Sets.SEARCH_MATCH_COLOR, "Search match background color", self.ENTRY_TYPE_COLOR))
            setLines.append(self.SettingsLineTemplate(self.GROUP_SEARCH, Sets.SEARCH_SELECTED_COLOR, "Search selected background color", self.ENTRY_TYPE_COLOR))
            setLines.append(self.SettingsLineTemplate(self.GROUP_SEARCH, Sets.SEARCH_SELECTED_LINE_COLOR, "Search selected line background color", self.ENTRY_TYPE_COLOR))

            self._setsDict.update(self._createStandardRows(self._searchFrame,setLines,0))

            ###############
            # Tab: Logging

            self._loggingFrame = tk.Frame(self._tabControl,padx=5,pady=5)
            self._loggingFrame.grid(row=0,column=0,sticky=tk.N)
            self._tabControl.add(self._loggingFrame, text="Logging")
            self._tabList.append(self.GROUP_LOGGING)

            setLines = list()
            setLines.append(self.SettingsLineTemplate(self.GROUP_LOGGING, Sets.LOG_FILE_PATH, "Log file path", self.ENTRY_TYPE_OTHER))
            setLines.append(self.SettingsLineTemplate(self.GROUP_LOGGING, Sets.LOG_FILE_BASE_NAME, "Log file base name", self.ENTRY_TYPE_OTHER))
            setLines.append(self.SettingsLineTemplate(self.GROUP_LOGGING, Sets.LOG_FILE_TIMESTAMP, "Time stamp", self.ENTRY_TYPE_OTHER))

            self._setsDict.update(self._createStandardRows(self._loggingFrame,setLines,0))


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


            # print("Number of settings " + str(len(self._setsDict)))


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
        tempLineColorRows = dict()
        # Sort settings to guarantee right order of line coloring
        for rowId in sorted(tempSetsDict.keys()):

            if Sets.LINE_COLOR_MAP in rowId:
                tempLineColorMap[rowId] = dict()
                tempLineColorRows[rowId] = tempSetsDict[rowId]

            for entryName in tempSetsDict[rowId].entries.keys():
                setting = tempSetsDict[rowId].entries[entryName].var.get()
                if Sets.LINE_COLOR_MAP in rowId:
                    tempLineColorMap[rowId][entryName] = setting
                else:
                    self._settings.setOption(rowId,setting)

        self._settings.setOption(Sets.LINE_COLOR_MAP,tempLineColorMap)

        # Once settings have been saved, allow for reopen of options view
        self._showing = False

        # Get registered textFrames
        textFrames = self._comController.getTextFrames()
        
        # Delete line color tags
        for deletedRowData in self._deletedLineColorRows:
            for textFrame in textFrames:
                textFrame.deleteTextTag(deletedRowData["tagName"])

        # Process added or updated line color rows
        for rowId in tempLineColorRows.keys():
            if tempLineColorRows[rowId].entries["regex"].isVarUpdated():
                if tempLineColorRows[rowId].entries["regex"].data.entryVar:
                    oldTagName = TF.createLineColorTagName(tempLineColorRows[rowId].entries["regex"].data.entryVar)
                    for textFrame in textFrames:
                        textFrame.deleteTextTag(oldTagName)
                    # print("Delete edited row id: " + rowId)
                for textFrame in textFrames:
                    textFrame.createAndAddLineColorTag(tempLineColorRows[rowId].entries["regex"].var.get(),tempLineColorRows[rowId].entries["color"].var.get())
                # print("Added line color row: " + rowId)

            elif tempLineColorRows[rowId].entries["color"].isVarUpdated():
                tagName = TF.createLineColorTagName(tempLineColorRows[rowId].entries["regex"].var.get())
                for textFrame in textFrames:                    
                    textFrame.updateTagColor(tagName,tempLineColorRows[rowId].entries["color"].var.get())


        # Reorder line color tags
        rowIds = sorted(tempLineColorRows.keys())
        if rowIds:
            preTagName = TF.createLineColorTagName(tempLineColorRows[rowIds[0]].entries["regex"].var.get())
            for rowId in rowIds[1:-1]:
                tagName = TF.createLineColorTagName(tempLineColorRows[rowId].entries["regex"].var.get())
                for textFrame in textFrames:                    
                    textFrame.textArea.tag_raise(tagName,aboveThis=preTagName)
                preTagName = tagName

        # print(*self._textFrame.textArea.tag_names(),sep=", ")

        # Reload main interface
        for textFrame in textFrames:
            textFrame.reloadLineColorMap()
            textFrame.reloadTextFrame()

        # Start workers
        self._highlightWorker.startWorker()
        self._guiWorker.startWorker()

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
                # TODO Use getRowNum??
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
                        tempTextColorMap.append((self._setsDict[rowId].entries["regex"].var.get(), \
                                                 self._setsDict[rowId].entries["regex"].data, \
                                                 self._setsDict[rowId].entries["color"].var.get(), \
                                                 self._setsDict[rowId].entries["color"].data))

                        # Remove rows to edit from view
                        self._setsDict[rowId].lineFrame.destroy()
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
                        deletedRowData = dict()
                        deletedRowData["tagName"] = TF.createLineColorTagName(tempTextColorMap[0][0])
                        self._deletedLineColorRows.append(deletedRowData)
                        del tempTextColorMap[0]


                    # Recreate saved rows
                    for i,(regexVar,regexData,colorVar,colorData) in enumerate(tempTextColorMap):
                        rowId = self._getRowId(indexToChange[i])
                        self._setsDict[rowId] = self._createSingleLineColorRow(self._lineColoringFrame,indexToChange[i],rowId,regexVar,colorVar)
                        self._setsDict[rowId].entries["regex"].data = regexData
                        self._setsDict[rowId].entries["color"].data = colorData

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
        colorLine = self.LineColorSettingsLine(self.GROUP_LINE_COLORING)

        colorLine.lineFrame = tk.Frame(parent,highlightcolor=self.ROW_HIGHLIGHT_COLOR,highlightthickness=2)
        colorLine.lineFrame.grid(row=row,column=0)
        colorLine.lineFrame.bind("<Button-1>",partial(self._focusInSet,rowId))
        colorLine.lineFrame.bind("<FocusOut>",partial(self._focusOut,rowId))

        regexEntry = self.Entry(self.ENTRY_TYPE_REGEX,regex)
        entryName = "regex"

        regexEntry.label = tk.Label(colorLine.lineFrame,text="Regex")
        regexEntry.label.grid(row=0,column=0)
        regexEntry.label.bind("<Button-1>",partial(self._focusInSet,rowId))
        regexEntry.var = tk.StringVar(colorLine.lineFrame)
        regexEntry.var.set(regex)
        regexEntry.observer = regexEntry.var.trace("w",partial(self._validateInput,rowId,entryName))

        regexEntry.input = tk.Entry(colorLine.lineFrame,textvariable=regexEntry.var,width=30,takefocus=False)
        regexEntry.input.grid(row=0,column=1)
        regexEntry.input.bind("<Button-1>",partial(self._focusInLog,rowId))


        colorLine.entries[entryName] = regexEntry

        colorEntry = self.Entry(self.ENTRY_TYPE_COLOR,color)
        entryName = "color"

        colorEntry.label = tk.Label(colorLine.lineFrame,text="Color")
        colorEntry.label.grid(row=0,column=2)
        colorEntry.label.bind("<Button-1>",partial(self._focusInSet,rowId))

        colorEntry.var = tk.StringVar(colorLine.lineFrame)
        colorEntry.var.set(color)
        colorEntry.observer = colorEntry.var.trace("w",partial(self._validateInput,rowId,entryName))
        colorEntry.input = tk.Entry(colorLine.lineFrame,textvariable=colorEntry.var,width=10,takefocus=False)
        colorEntry.input.grid(row=0,column=3)
        colorEntry.input.bind("<Button-1>",partial(self._focusInLog,rowId))

        colorEntry.button = tk.Button(colorLine.lineFrame,bg=color,width=3,command=partial(self._getColor,rowId,entryName,True))
        colorEntry.button.grid(row=0,column=4,padx=4)
        colorEntry.button.bind("<Button-1>",partial(self._focusInSet,rowId))


        colorLine.entries[entryName] = colorEntry

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
            setRow = self.SettingsLine(setLine.setGroup)
            entry = self.Entry(setLine.setType,self._settings.get(setLine.setId))

            entryName = "entry"

            # TODO Add frame and highlight to colors (remember column widths and alignment)

            entry.label = tk.Label(parent,text=setLine.setDisplayName)
            entry.label.grid(row=row,column=0,sticky=tk.W)

            ########
            # Entry variable
            if setLine.setType == self.ENTRY_TYPE_INT:
                entry.var = tk.IntVar(parent)
            else:
                entry.var = tk.StringVar(parent)

            # Init entry var
            entry.var.set(self._settings.get(setLine.setId))
            # TODO use tkinter validateCommand
            entry.observer = entry.var.trace("w",partial(self._validateInput,setLine.setId,entryName))

            ########
            # Input field
            if setLine.setType == self.ENTRY_TYPE_TOGGLE:
                # TODO create better toggle values (link to specific settings)
                toggleButtonFrame = tk.Frame(parent)
                toggleButtonFrame.grid(row=row,column=1,sticky=tk.E+tk.W)
                toggleButtonFrame.grid_columnconfigure(0,weight=1)
                toggleButtonFrame.grid_columnconfigure(1,weight=1)
                onButton = tk.Radiobutton(toggleButtonFrame,text="On",variable=entry.var, indicatoron=False,value="on")
                onButton.grid(row=0,column=0,sticky=tk.E+tk.W)
                offButton = tk.Radiobutton(toggleButtonFrame,text="Off",variable=entry.var, indicatoron=False,value="off")
                offButton.grid(row=0,column=1,sticky=tk.E+tk.W)
            else:                
                # TODO Find better solution for entry width
                entry.input = tk.Entry(parent,textvariable=entry.var,width=int(maxLen*1.5),takefocus=False)
                entry.input.grid(row=row,column=1)

            ########
            # Color button
            if setLine.setType == self.ENTRY_TYPE_COLOR:
                entry.button = tk.Button(parent,bg=self._settings.get(setLine.setId),width=3,command=partial(self._getColor,setLine.setId,entryName))
                entry.button.grid(row=row,column=2,padx=4)

            setRow.entries[entryName] = entry
            setDict[setLine.setId] = setRow

            row += 1

        return setDict



    ####################################
    # View Interaction

    def _focusOut(self,rowId,event):
        self._lastFocusOutRowId = rowId

    def _focusInSet(self,rowId,event=0):
        self._setsDict[rowId].lineFrame.focus_set()
        self._focusInLog(rowId,event)

    def _focusInLog(self,rowId,event=0):
        self._lastFocusInRowId = rowId
        if self._lastFocusOutRowId == rowId:
            self._lastFocusOutRowId = ""

    def _getColor(self,rowId,entry,highlight=False):

        if highlight:
            hg = self._setsDict[rowId].lineFrame.cget("highlightbackground")
            self._setsDict[rowId].lineFrame.config(highlightbackground=self.ROW_HIGHLIGHT_COLOR)

        currentColor = self._setsDict[rowId].entries[entry].button.cget("bg")

        if not self._isValidColor(currentColor):
            currentColor = None

        color = askcolor(initialcolor=currentColor,parent=self._view)

        if color[1] != None:
            self._setsDict[rowId].entries[entry].var.set(color[1])
            self._setsDict[rowId].entries[entry].button.config(bg=color[1])

        if highlight:
            self._setsDict[rowId].lineFrame.config(highlightbackground=hg)
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
                tFont = Font(family=self._setsDict[Sets.TEXTAREA_FONT_FAMILY].entries[entryName].var.get(),\
                            size=self._setsDict[Sets.TEXTAREA_FONT_SIZE].entries[entryName].var.get())
                self._exampleText.config(background=self._setsDict[Sets.TEXTAREA_BACKGROUND_COLOR].entries[entryName].var.get(),\
                                                selectbackground=self._setsDict[Sets.TEXTAREA_SELECT_BACKGROUND_COLOR].entries[entryName].var.get(),\
                                                foreground=self._setsDict[Sets.TEXTAREA_COLOR].entries[entryName].var.get(),\
                                                font=tFont)

                lineWrapString = self._setsDict[Sets.TEXTAREA_LINE_WRAP].entries[entryName].var.get()
                if lineWrapString == "on":
                    self._updateExampleTextLineWrap(Sets.LINE_WRAP_ON)
                elif lineWrapString == "off":
                    self._updateExampleTextLineWrap(Sets.LINE_WRAP_OFF)
                    
            except tk.TclError:
                pass

        elif group == self.GROUP_SEARCH:

            searchString = "Main"
            
            # Create search tags            
            self._exampleText.tag_configure(Sets.SEARCH_SELECTED_LINE_COLOR, \
                                            background=self._setsDict[Sets.SEARCH_SELECTED_LINE_COLOR].entries[entryName].var.get(),\
                                            selectbackground=util.lightOrDarkenColor(self._setsDict[Sets.SEARCH_SELECTED_LINE_COLOR].entries[entryName].var.get(),Sets.SELECTED_LINE_DARKEN_COLOR))
            self._exampleText.tag_configure(Sets.SEARCH_MATCH_COLOR, \
                                            background=self._setsDict[Sets.SEARCH_MATCH_COLOR].entries[entryName].var.get(),\
                                            selectbackground=util.lightOrDarkenColor(self._setsDict[Sets.SEARCH_MATCH_COLOR].entries[entryName].var.get(),Sets.SELECTED_LINE_DARKEN_COLOR))
            self._exampleText.tag_configure(Sets.SEARCH_SELECTED_COLOR, \
                                            background=self._setsDict[Sets.SEARCH_SELECTED_COLOR].entries[entryName].var.get(), \
                                            selectbackground=util.lightOrDarkenColor(self._setsDict[Sets.SEARCH_SELECTED_COLOR].entries[entryName].var.get(),Sets.SELECTED_LINE_DARKEN_COLOR))

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
                    lineInfo["regex"] = self._setsDict[rowId].entries["regex"].var.get()
                    lineInfo["color"] = self._setsDict[rowId].entries["color"].var.get()
                    lineInfo["tagName"] = TF.createLineColorTagName(lineInfo["regex"])
                    tempLineColorMap.append(lineInfo)

            # Apply new line colors
            for lineInfo in tempLineColorMap:
                self._exampleText.tag_configure(lineInfo["tagName"],foreground=lineInfo["color"])

                countVar = tk.StringVar()
                start = 1.0
                while True:
                    pos = self._exampleText.search(lineInfo["regex"],start,stopindex=tk.END,count=countVar,nocase=False,regexp=True)
                    if not pos:
                        break
                    else:
                        self._exampleText.tag_add(lineInfo["tagName"],pos,pos + "+" + countVar.get() + "c")
                        start = pos + "+1c"

    def _updateExampleTextLineWrap(self,lineWrapState):
        
        if lineWrapState == Sets.LINE_WRAP_ON:
            self._exampleText.config(wrap=tk.CHAR)
        else:
            self._exampleText.config(wrap=tk.NONE)


    ####################################
    # Entry Validation

    def _validateInput(self,rowId,entryName,*args):

        # Get variable
        try:
            settingsLine:self.SettingsLine = self._setsDict[rowId]
            entry:self.Entry = settingsLine.entries[entryName]
            varIn = entry.var.get()
            validationStatus = self.ENTRY_VALIDATION_OK
        except tk.TclError:
            # print("Tcl Error")
            validationStatus = self.ENTRY_VALIDATION_FAILED

        if validationStatus == self.ENTRY_VALIDATION_OK:

            # Check Colors
            if entry.data.entryType == self.ENTRY_TYPE_COLOR:
                if self._isValidColor(varIn):
                    # print("Color " + str(color))
                    entry.button.config(background=varIn)
                    validationStatus = self.ENTRY_VALIDATION_OK
                else:
                    validationStatus = self.ENTRY_VALIDATION_FAILED

            # Check regex
            if entry.data.entryType == self.ENTRY_TYPE_REGEX:  
              
                # Validate regex
                if self._isValidRegex(varIn):
                    entry.data.validation.status = self.ENTRY_VALIDATION_OK
                else:
                    entry.data.validation.status = self.ENTRY_VALIDATION_FAILED

                self._updateAllRegexEntries()
                
                validationStatus = entry.data.validation.status


            # Check font family
            if rowId == Sets.TEXTAREA_FONT_FAMILY:
                if self._isValidFontFamily(varIn):
                    validationStatus = self.ENTRY_VALIDATION_OK
                else:
                    validationStatus = self.ENTRY_VALIDATION_FAILED

            # Check font size
            if rowId == Sets.TEXTAREA_FONT_SIZE:
                if self._isValidFontSize(varIn):
                    validationStatus = self.ENTRY_VALIDATION_OK
                else:
                    validationStatus = self.ENTRY_VALIDATION_FAILED

        
        #######
        # Update validation info

        if validationStatus == self.ENTRY_VALIDATION_OK:
            entry.data.validation.status = self.ENTRY_VALIDATION_OK
            entry.data.validation.backgroundColor = "white"
            entry.data.validation.infoText = ""
        elif validationStatus == self.ENTRY_VALIDATION_FAILED:
            entry.data.validation.status = self.ENTRY_VALIDATION_FAILED
            entry.data.validation.backgroundColor = "red"
            entry.data.validation.infoText = "Non-valid input."

        if not entry.data.entryType == self.ENTRY_TYPE_TOGGLE:
            entry.input.config(background=entry.data.validation.backgroundColor)

        infoText = ""
        for key in self._setsDict.keys():
            for (entryKey,entryItem) in self._setsDict[key].entries.items():
                if entryItem.data.validation.status != self.ENTRY_VALIDATION_OK:
                    entryId = key + "_" + entryKey
                    if infoText:
                        infoText += "\n"
                    infoText += entryId + ": " + entryItem.data.validation.infoText
        
        if infoText:
            self._optionsInfoLabel.config(text=infoText)
            self._setSaveButtonState(tk.DISABLED)
        else:
            self._optionsInfoLabel.config(text="")
            self._setSaveButtonState(tk.NORMAL)
            self._updateExampleText(settingsLine.group)

   
   

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

    def _updateAllRegexEntries(self):
        # Get all regex                
        regexList = list()
        for key in self._setsDict.keys():
            try:
                value = self._setsDict[key].entries["regex"].var.get()
                regexList.append(value)
            except KeyError:
                pass

        # Find any duplicate entries
        regexListCount = Counter(regexList)
        regexDuplicateList = [regex for regex, count in regexListCount.items() if count > 1]

        # Update all duplicate regex entries
        for key in self._setsDict.keys():
            try:
                regexEntry = self._setsDict[key].entries["regex"]
                # Only update status if entry validation status is not currently failed
                if regexEntry.data.validation.status != self.ENTRY_VALIDATION_FAILED:
                    # Mark duplicates
                    if regexEntry.var.get() in regexDuplicateList:                                                            
                        # print("New duplicate: " + regexEntry.var.get())
                        regexEntry.data.validation.status = self.ENTRY_VALIDATION_DUPLICATE
                        regexEntry.data.validation.backgroundColor = "yellow"
                        regexEntry.data.validation.infoText = "Duplicate regex entry not allowed."
                    else:
                        # Clear previous duplicates that are now valid
                        if regexEntry.data.validation.status == self.ENTRY_VALIDATION_DUPLICATE:
                            # print("Clear duplicate: " + regexEntry.var.get())
                            regexEntry.data.validation.status = self.ENTRY_VALIDATION_OK
                            regexEntry.data.validation.backgroundColor = "white"
                            regexEntry.data.validation.infoText = ""

                    regexEntry.input.config(background=regexEntry.data.validation.backgroundColor)
            except KeyError:
                pass


    ####################################
    # Misc

    def _getRowId(self,rowNum):
        return Sets.LINE_COLOR_MAP + "{:02d}".format(rowNum)