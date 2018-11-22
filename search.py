import tkinter as tk


import settings as Sets

class Search:

    def __init__(self,settings):
        self._settings = settings
        self._textField = None
        self._showing = False

        self._results = list()
        self._selectedResultIndex = -1

    def linkTextFrame(self,textFrame):
        self._textField = textFrame.textArea

    def close(self,*event):

        if self._showing:

            self._textField.tag_delete(self.TAG_SEARCH)
            self._textField.tag_delete(self.TAG_SEARCH_SELECT)
            self._textField.tag_delete(self.TAG_SEARCH_SELECT_BG)

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
            self._var.trace("w",self._search)

            self._entry = tk.Entry(self._view,textvariable=self._var)
            self._entry.pack(side=tk.LEFT,padx=(4,2))
            self._entry.bind("<Return>",self._selectNextResult)

            self._entry.focus_set()

            self._label = tk.Label(self._view,text=self.NO_RESULT_STRING,width=10,anchor=tk.W)
            self._label.pack(side=tk.LEFT,anchor=tk.E)

            self._caseVar = tk.StringVar(self._view)
            self._caseVar.trace("w",self._search)
            self._caseButton = tk.Checkbutton(self._view,text="Aa",variable=self._caseVar,cursor="arrow",onvalue=self.STRING_FALSE,offvalue=self.STRING_TRUE)
            self._caseButton.pack(side=tk.LEFT)
            self._caseButton.deselect()

            self._regexVar = tk.StringVar(self._view)
            self._regexVar.trace("w",self._search)
            self._regexButton = tk.Checkbutton(self._view,text=".*",variable=self._regexVar,cursor="arrow",onvalue=self.STRING_TRUE,offvalue=self.STRING_FALSE)
            self._regexButton.pack(side=tk.LEFT)
            self._regexButton.deselect()

            self._closeButton = tk.Button(self._view,text="X",command=self.close,cursor="arrow",relief=tk.FLAT)
            self._closeButton.pack(side=tk.LEFT)

            # Bind escape to close view
            self._textField.bind("<Escape>",self.close)
            self._entry.bind("<Escape>",self.close)

        else:

            self._entry.focus_set()

    def searchLinesAdded(self,numberOfLinesDeleted):

        if self._showing:

            reloadSelectedResult = False

            # If lines have been deleted from the window line buffer, search must be updated
            if numberOfLinesDeleted > 0:

                # Check if selectedResultIndex is currently pointing to a valid search result
                if self._selectedResultIndex > -1 and self._selectedResultIndex < len(self._results):

                    # Get current (old, as lines have been deleted) line number of selected search result
                    selectedResultLineNumber = self._results[self._selectedResultIndex][2]

                    # Check if line with selected result has been deleted.
                    # In that case, select the next result in the window
                    if selectedResultLineNumber <= numberOfLinesDeleted:
                        reloadSelectedResult = True

                    else:
                        # Check if a line with a result has been deleted.
                        # In that case, update index of selected result accordingly.
                        # No need to update results list, as this is reloaded on every call                       
                        
                        resultsDeleted = 0                        
                        for result in self._results:
                            if result[2] <= numberOfLinesDeleted:
                                resultsDeleted += 1
                            else:                         
                                break
                        
                        self._selectedResultIndex = self._selectedResultIndex - resultsDeleted


            # We are currently searching through all lines every time a new line is added.
            # This can likely be updated to just search the new line added,
            # but will require some rework of the result list, including updating all line numbers
            self._search(searchStringUpdated=reloadSelectedResult)


    def _search(self,searchStringUpdated=True,*args):

        if self._showing:

            string = self._var.get()

            if searchStringUpdated:
                self._textField.tag_remove(self.TAG_SEARCH_SELECT,1.0,tk.END)
                self._textField.tag_remove(self.TAG_SEARCH_SELECT_BG,1.0,tk.END)

            self._textField.tag_remove(self.TAG_SEARCH,1.0,tk.END)
            self._start = "1.0"
            self._results = list()

            if string:

                nocase = self._caseVar.get() == self.STRING_TRUE
                regexp = self._regexVar.get() == self.STRING_TRUE

                countVar = tk.StringVar()
                while True:
                    pos = self._textField.search(string,self._start,stopindex=tk.END,count=countVar,nocase=nocase,regexp=regexp)
                    if not pos:
                        break
                    else:
                        line = int(pos.split(".")[0])                        
                        self._results.append((pos,pos + "+" + countVar.get() + "c",line))
                        self._start = pos + "+1c"

                for result in self._results:
                    self._textField.tag_add(self.TAG_SEARCH, result[0], result[1])

                if searchStringUpdated:
                    self._selectedResultIndex = -1
                    self._selectNextResult()

            self._updateResultInfo()

    def _selectNextResult(self,*args):
        self._incrementResultIndex()
        if self._selectedResultIndex > -1 and self._selectedResultIndex < len(self._results):

            # Selected result tag
            selected = self._textField.tag_ranges(self.TAG_SEARCH_SELECT)
            if selected:
                self._textField.tag_remove(self.TAG_SEARCH_SELECT,selected[0],selected[1])
            self._textField.tag_add(self.TAG_SEARCH_SELECT, self._results[self._selectedResultIndex][0], self._results[self._selectedResultIndex][1])

            # Background of selected line
            selectedBg = self._textField.tag_ranges(self.TAG_SEARCH_SELECT_BG)
            if selectedBg:
                self._textField.tag_remove(self.TAG_SEARCH_SELECT_BG,selectedBg[0],selectedBg[1])
            selectLine = self._results[self._selectedResultIndex][0].split(".")[0]
            self._textField.tag_add(self.TAG_SEARCH_SELECT_BG, selectLine + ".0", selectLine + ".0+1l")

            self._textField.see(self._results[self._selectedResultIndex][0])

            self._updateResultInfo()

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
