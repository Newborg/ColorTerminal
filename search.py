import tkinter as tk
import time


import settings as Sets

class Search:

    def __init__(self,settings):
        self._settings = settings
        self._textField = None
        self._guiWorker = None
        self._showing = False

        self._searchJob = None

        # self._topResults = list()
        # self._bottomResults = list()
        self._results = list()

        self._selectedResultIndex = -1
        self._lineNumberDeleteOffset = 0

        self._bottomLinesSearched = False
        self._searchStartIndex = 0

    def linkTextFrame(self,textFrame):
        self._textField = textFrame.textArea

    def linkWorkers(self,workers):
        self._guiWorker = workers.guiWorker

    def close(self,*event):

        if self._showing:

            self._textField.tag_delete(self.TAG_SEARCH)
            self._textField.tag_delete(self.TAG_SEARCH_SELECT)
            self._textField.tag_delete(self.TAG_SEARCH_SELECT_BG)

            self._focusOut()

            self._entry.unbind("<Escape>")
            self._textField.unbind("<Escape>")

            try:
                self._view.destroy()
                self._showing = False
            except AttributeError:
                pass

    TAG_SEARCH = "tagSearch"
    TAG_SEARCH_SELECT = "tagSearchSelect"
    TAG_SEARCH_SELECT_BG = "tagSearchSelectBg"

    STRING_TRUE = "True"
    STRING_FALSE = "False"

    NO_RESULT_STRING = "No result"

    class Result:
        def __init__(self,line,startColumn,length):
            self.originalLineNumber = line
            self.startColumn = startColumn
            self.length = length

        def getStartAndEndIndex(self,deletedLines):
            pos = str(self.originalLineNumber - deletedLines) + "." + str(self.startColumn)
            endPos = pos + "+" + str(self.length) + "c"
            return (pos,endPos)


    def show(self,*args):

        if not self._showing:

            self._showing = True

            self._view = tk.Frame(self._textField,highlightthickness=2,highlightcolor=self._settings.get(Sets.THEME_COLOR))
            self._view.place(relx=1,x=-5,y=5,anchor=tk.NE)

            self._textField.tag_configure(self.TAG_SEARCH_SELECT_BG, background=self._settings.get(Sets.SEARCH_SELECTED_LINE_COLOR))
            self._textField.tag_configure(self.TAG_SEARCH, background=self._settings.get(Sets.SEARCH_MATCH_COLOR))
            self._textField.tag_configure(self.TAG_SEARCH_SELECT, background=self._settings.get(Sets.SEARCH_SELECTED_COLOR))

            self._var = tk.StringVar(self._view)
            self._var.set("")
            self._var.trace("w",self._searchStringUpdated)

            self._entry = tk.Entry(self._view,textvariable=self._var)
            self._entry.pack(side=tk.LEFT,padx=(4,2))
            self._entry.bind("<Return>",self._selectNextResult) # Enter key
            self._entry.bind("<Next>",self._selectNextResult) # Page down
            self._entry.bind("<Prior>",self._selectPriorResult) # Page up

            self._entry.bind("<FocusIn>",self._focusIn)
            self._entry.bind("<FocusOut>",self._focusOut)

            self._entry.focus_set()            

            self._label = tk.Label(self._view,text=self.NO_RESULT_STRING,width=10,anchor=tk.W)
            self._label.pack(side=tk.LEFT,anchor=tk.E)

            self._caseVar = tk.StringVar(self._view)
            self._caseVar.trace("w",self._searchStringUpdated)
            caseButton = tk.Checkbutton(self._view,text="Aa",variable=self._caseVar,cursor="arrow",onvalue=self.STRING_FALSE,offvalue=self.STRING_TRUE)
            caseButton.pack(side=tk.LEFT)
            caseButton.deselect()

            self._regexVar = tk.StringVar(self._view)
            self._regexVar.trace("w",self._searchStringUpdated)
            regexButton = tk.Checkbutton(self._view,text=".*",variable=self._regexVar,cursor="arrow",onvalue=self.STRING_TRUE,offvalue=self.STRING_FALSE)
            regexButton.pack(side=tk.LEFT)
            regexButton.deselect()

            closeButton = tk.Button(self._view,text="X",command=self.close,cursor="arrow",relief=tk.FLAT)
            closeButton.pack(side=tk.LEFT)

            # Bind escape to close view
            self._textField.bind("<Escape>",self.close)
            self._entry.bind("<Escape>",self.close)

            # Init search settings
            self._nocase = self._caseVar.get() == self.STRING_TRUE
            self._regexp = self._regexVar.get() == self.STRING_TRUE

        else:

            self._entry.focus_set()

    def searchLinesAdded(self,numberOfLinesAdded,numberOfLinesDeleted,lastLine):

        if self._showing:

            string = self._var.get()

            if string:

                # Instead of updating indexes in all results in the result list,
                # we keep track of the lines deleted and use this to offset when an index is needed.
                self._lineNumberDeleteOffset += numberOfLinesDeleted

                # Search in newly added lines
                searchStartIndex = str(lastLine - numberOfLinesAdded + 1) + ".0"
                countVar = tk.StringVar()
                while True:
                    pos = self._textField.search(string,searchStartIndex,stopindex=tk.END,count=countVar,nocase=self._nocase,regexp=self._regexp)
                    if not pos:
                        break
                    else:
                        posSplit = pos.split(".")
                        newLine = int(posSplit[0]) + self._lineNumberDeleteOffset # Add number of deleted line to line number to match existing results in result list
                        column = int(posSplit[1])

                        result = self.Result(newLine,column,int(countVar.get()))
                        self._results.append(result)
                        self._addTag(self.TAG_SEARCH, result)

                        searchStartIndex = pos + "+1c"

                # If lines have been deleted from the window line buffer, find and remove results from these lines
                if numberOfLinesDeleted > 0:
                    resultsDeleted = 0
                    for result in self._results:
                        if (result.originalLineNumber - self._lineNumberDeleteOffset) <= 0:
                            resultsDeleted += 1
                        else:
                            break

                    for _ in range(resultsDeleted):
                        del self._results[0]

                    # Update index of the selected result
                    self._selectedResultIndex = self._selectedResultIndex - resultsDeleted

                    if self._results:
                        # If new selected result is no longer pointing to a valid result, selected first result in list (line with selected result has been deleted)
                        if self._selectedResultIndex < 0 or self._selectedResultIndex >= len(self._results):
                            self._selectedResultIndex = 0

                    else:
                        self._selectedResultIndex = -1

                    self._updateSelectedResultTags()

            self._updateResultInfo()

    def _focusIn(self,*args):
        self._guiWorker.disableScrolling()

    def _focusOut(self,*args):
        self._guiWorker.enableScrolling()

    def _searchStringUpdated(self,*args):

        if self._showing:

            string = self._var.get()

            if self._searchJob:
                self._textField.after_cancel(self._searchJob)
                self._searchJob = None
                if not string:
                    # If search field is empty, the guiWorker has to be started again
                    self._guiWorker.startWorker()

            self._textField.tag_remove(self.TAG_SEARCH_SELECT,1.0,tk.END)
            self._textField.tag_remove(self.TAG_SEARCH_SELECT_BG,1.0,tk.END)
            self._textField.tag_remove(self.TAG_SEARCH,1.0,tk.END)

            
            # Start search at first visible line
            self._searchStartIndex = self._textField.index("@0,0")
            
            # Reset result lists            
            self._results = list()
            self._lineNumberDeleteOffset = 0

            self._bottomLinesSearched = False

            if string:

                self._nocase = self._caseVar.get() == self.STRING_TRUE
                self._regexp = self._regexVar.get() == self.STRING_TRUE

                # self._startTime = time.time()

                # Stop GUI worker to prevent lines being added during search (A large search can take up to 900 ms)
                self._guiWorker.stopWorker()

                self._searchJob = self._textField.after(0,self._searchProcess,string,self._searchStartIndex)

            self._updateResultInfo()

    def _searchProcess(self,string,start):

        countVar = tk.StringVar()
        loopMax = 500

        loopStoppedAtBottom = False
        searchCompleted = False
        tempResults = list()

        # If lines below start index has been search (first part of search) then set stopIndex to line above start index
        if not self._bottomLinesSearched:
            stopIndex = tk.END
        else:
            stopIndex = self._searchStartIndex + "-1l"

        for _ in range(loopMax):            
            pos = self._textField.search(string,start,stopindex=stopIndex,count=countVar,nocase=self._nocase,regexp=self._regexp)
            if not pos:
                if not self._bottomLinesSearched:
                    self._bottomLinesSearched = True
                    loopStoppedAtBottom = True
                    start = "1.0"                    
                else:
                    searchCompleted = True
                break
            else:
                posSplit = pos.split(".")
                tempResults.append(self.Result(int(posSplit[0]),int(posSplit[1]),int(countVar.get())))
                start = pos + "+1c"

        for result in tempResults:
            self._addTag(self.TAG_SEARCH, result)

        # Add temp results to result list and keep result list sorted by line number
        if (not self._bottomLinesSearched) or loopStoppedAtBottom:
            self._results.extend(tempResults)
            self._selectedResultIndex = -1
        else:
            tempResultCount = len(tempResults)
            self._results[self._selectedResultIndex:self._selectedResultIndex] = tempResults
            self._selectedResultIndex = self._selectedResultIndex + tempResultCount - 1

        self._selectNextResult()

        self._updateResultInfo()

        if searchCompleted:
            # self._searchTime = time.time()

            self._searchJob = None
            self._guiWorker.startWorker()

            # print("Search time: " + str(self._searchTime-self._startTime))

        else:
            self._searchJob = self._textField.after(1,self._searchProcess,string,start)

    def _addTag(self,tag,searchResult:Result):
        (pos,endPos) = searchResult.getStartAndEndIndex(self._lineNumberDeleteOffset)
        self._textField.tag_add(tag, pos, endPos)

    def _updateSelectedResultTags(self,*args):

        if self._selectedResultIndex > -1 and self._selectedResultIndex < len(self._results):

            # Selected result tag
            selected = self._textField.tag_ranges(self.TAG_SEARCH_SELECT)
            if selected:
                self._textField.tag_remove(self.TAG_SEARCH_SELECT,selected[0],selected[1])
            self._addTag(self.TAG_SEARCH_SELECT,self._results[self._selectedResultIndex])

            # Background of selected line
            selectedBg = self._textField.tag_ranges(self.TAG_SEARCH_SELECT_BG)
            if selectedBg:
                self._textField.tag_remove(self.TAG_SEARCH_SELECT_BG,selectedBg[0],selectedBg[1])
            selectLine = self._results[self._selectedResultIndex].originalLineNumber - self._lineNumberDeleteOffset
            self._textField.tag_add(self.TAG_SEARCH_SELECT_BG, str(selectLine) + ".0", str(selectLine) + ".0+1l")

            # Focus window on selected result
            self._textField.see(self._results[self._selectedResultIndex].getStartAndEndIndex(self._lineNumberDeleteOffset)[0])


    def _selectPriorResult(self,*args):
        self._decrementResultIndex()

        self._updateSelectedResultTags()

        self._updateResultInfo()

    def _selectNextResult(self,*args):
        self._incrementResultIndex()

        self._updateSelectedResultTags()

        self._updateResultInfo()

    def _decrementResultIndex(self):
        if self._results:
            self._selectedResultIndex -= 1
            if self._selectedResultIndex == 0:
                self._selectedResultIndex = len(self._results) - 1

    def _incrementResultIndex(self):
        if self._results:
            self._selectedResultIndex += 1
            if self._selectedResultIndex >= len(self._results):
                self._selectedResultIndex = 0

    def _updateResultInfo(self):
        if not self._results:
            self._label.config(text=self.NO_RESULT_STRING)
        else:
            self._label.config(text=str(self._selectedResultIndex+1) + " of " + str(len(self._results)))
