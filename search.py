import tkinter as tk


import settings as Sets

class Search:

    def __init__(self,settings):
        self._settings_ = settings
        self._textField_ = None
        self._showing_ = False

        self._results_ = list()
        self._selectedResult_ = -1

    def linkTextFrame(self,textFrame):
        self._textField_ = textFrame.textArea

    def close(self,*event):

        if self._showing_:

            self._textField_.tag_delete(self.TAG_SEARCH)
            self._textField_.tag_delete(self.TAG_SEARCH_SELECT)
            self._textField_.tag_delete(self.TAG_SEARCH_SELECT_BG)

            self._entry_.unbind("<Escape>")
            self._textField_.unbind("<Escape>")

            try:
                self._view_.destroy()
                self._showing_ = False
            except AttributeError:
                pass

    TAG_SEARCH = "tagSearch"
    TAG_SEARCH_SELECT = "tagSearchSelect"
    TAG_SEARCH_SELECT_BG = "tagSearchSelectBg"

    STRING_TRUE = "True"
    STRING_FALSE = "False"

    NO_RESULT_STRING = "No result"

    def show(self,*args):

        if not self._showing_:

            #####
            self._textField_.tag_configure("TESTING", background="red")
            self._textField_.tag_add("TESTING", 1.0, 1.5)
            ####

            self._showing_ = True

            self._view_ = tk.Frame(self._textField_,highlightthickness=2,highlightcolor=self._settings_.get(Sets.THEME_COLOR))
            self._view_.place(relx=1,x=-5,y=5,anchor=tk.NE)

            self._textField_.tag_configure(self.TAG_SEARCH_SELECT_BG, background=self._settings_.get(Sets.SEARCH_SELECTED_LINE_COLOR))
            self._textField_.tag_configure(self.TAG_SEARCH, background=self._settings_.get(Sets.SEARCH_MATCH_COLOR))
            self._textField_.tag_configure(self.TAG_SEARCH_SELECT, background=self._settings_.get(Sets.SEARCH_SELECTED_COLOR))

            self._var_ = tk.StringVar(self._view_)
            self._var_.set("")
            self._var_.trace("w",self.reloadSearch)

            self._entry_ = tk.Entry(self._view_,textvariable=self._var_)
            self._entry_.pack(side=tk.LEFT,padx=(4,2))
            self._entry_.bind("<Return>",self._selectNextResult_)

            self._entry_.focus_set()

            self._label_ = tk.Label(self._view_,text=self.NO_RESULT_STRING,width=10,anchor=tk.W)
            self._label_.pack(side=tk.LEFT,anchor=tk.E)

            self._caseVar_ = tk.StringVar(self._view_)
            self._caseVar_.trace("w",self.reloadSearch)
            self._caseButton_ = tk.Checkbutton(self._view_,text="Aa",variable=self._caseVar_,cursor="arrow",onvalue=self.STRING_FALSE,offvalue=self.STRING_TRUE)
            self._caseButton_.pack(side=tk.LEFT)
            self._caseButton_.deselect()

            self._regexVar_ = tk.StringVar(self._view_)
            self._regexVar_.trace("w",self.reloadSearch)
            self._regexButton_ = tk.Checkbutton(self._view_,text=".*",variable=self._regexVar_,cursor="arrow",onvalue=self.STRING_TRUE,offvalue=self.STRING_FALSE)
            self._regexButton_.pack(side=tk.LEFT)
            self._regexButton_.deselect()

            self._closeButton_ = tk.Button(self._view_,text="X",command=self.close,cursor="arrow",relief=tk.FLAT)
            self._closeButton_.pack(side=tk.LEFT)

            # Bind escape to close view
            self._textField_.bind("<Escape>",self.close)
            self._entry_.bind("<Escape>",self.close)

        else:

            self._entry_.focus_set()


    def reloadSearch(self,*args):

        if self._showing_:

            string = self._var_.get()

            self._textField_.tag_remove(self.TAG_SEARCH,1.0,tk.END)
            self._textField_.tag_remove(self.TAG_SEARCH_SELECT,1.0,tk.END)
            self._textField_.tag_remove(self.TAG_SEARCH_SELECT_BG,1.0,tk.END)
            self._start_ = "1.0"
            self._results_ = list()

            self.searchNew(string)

            self._selectedResult_ = -1
            self._selectNextResult_()

            self._updateResultInfo_()

    def searchNewLine(self,lineNumber):
        
        if self._showing_:

            string = self._var_.get()

            # print("Start: " + str(int(self._start_.split(".")[0])))
            # print("Max -1: " + str(self._settings_.get(Sets.MAX_LINE_BUFFER) - 1))


            if int(lineNumber) >= self._settings_.get(Sets.MAX_LINE_BUFFER):
                print("End line reached, " + string)

            # Check compare/check tk.END. Search will always be on lsat line when using this setup

            if self._start_:
                print("Prestart: " + self._start_)

            self._start_ = lineNumber + ".0"

            print("Poststart: " + self._start_)

            # We must delete old results when max has been reached
            print("Number of results: " + str(len(self._results_)))

            self.searchNew(string)

            # lastline = self._textField_.index("end-2c").split(".")[0]
            # self._textField_.delete(lastline + ".0",lastline +".0+1l")
            # self._textField_.insert(lastline + ".0", newLine)




    def searchNew(self,string):

        if string:
            
            print("Start: " + str(self._start_))

            nocase = True if self._caseVar_.get() == self.STRING_TRUE else False
            regexp = True if self._regexVar_.get() == self.STRING_TRUE else False

            countVar = tk.StringVar()
            while True:
                pos = self._textField_.search(string,self._start_,stopindex=tk.END,count=countVar,nocase=nocase,regexp=regexp)
                if not pos:
                    break
                else:
                    split = pos.split(".")
                    line = int(split[0])
                    start = int(split[1])
                    self._results_.append((line,start,int(countVar.get())))
                    self._start_ = pos + "+1c"

            for result in self._results_:
                    # startIndex = result
                    # Either edit all indexes when buffer is full or create variable with index modifier
                    # If a line with a search tag is deleted, rerun search
                    # Keep a record of lowest line number with search tag
                    self._textField_.tag_add(self.TAG_SEARCH, result[0], result[1])

        


    def searchxxx(self,searchStringUpdated=True,*args):

        if self._showing_:

            string = self._var_.get()

            # If the search string has not been updated,
            # no need to reload the tags, just search additional lines.
            # Used from the guiWorker, whenever new lines are added.
            if searchStringUpdated:
                self._textField_.tag_remove(self.TAG_SEARCH,1.0,tk.END)
                self._textField_.tag_remove(self.TAG_SEARCH_SELECT,1.0,tk.END)
                self._textField_.tag_remove(self.TAG_SEARCH_SELECT_BG,1.0,tk.END)
                self._start_ = "1.0"
                self._results_ = list()

            if string:
                
                print("Start: " + str(self._start_))

                nocase = True if self._caseVar_.get() == self.STRING_TRUE else False
                regexp = True if self._regexVar_.get() == self.STRING_TRUE else False

                countVar = tk.StringVar()
                while True:
                    pos = self._textField_.search(string,self._start_,stopindex=tk.END,count=countVar,nocase=nocase,regexp=regexp)
                    if not pos:
                        break
                    else:
                        self._results_.append((pos,pos + "+" + countVar.get() + "c"))
                        self._start_ = pos + "+1c"

                for result in self._results_:
                        self._textField_.tag_add(self.TAG_SEARCH, result[0], result[1])

                if searchStringUpdated:
                    self._selectedResult_ = -1
                    self._selectNextResult_()

            self._updateResultInfo_()

    def _selectNextResult_(self,*args):
        self._incrementResultIndex_()
        if self._selectedResult_ > -1:

            # Selected result tag
            selected = self._textField_.tag_ranges(self.TAG_SEARCH_SELECT)
            if selected:
                self._textField_.tag_remove(self.TAG_SEARCH_SELECT,selected[0],selected[1])
            self._textField_.tag_add(self.TAG_SEARCH_SELECT, self._results_[self._selectedResult_][0], self._results_[self._selectedResult_][1])

            # Background of selected line
            selectedBg = self._textField_.tag_ranges(self.TAG_SEARCH_SELECT_BG)
            if selectedBg:
                self._textField_.tag_remove(self.TAG_SEARCH_SELECT_BG,selectedBg[0],selectedBg[1])
            selectLine = self._results_[self._selectedResult_][0].split(".")[0]
            self._textField_.tag_add(self.TAG_SEARCH_SELECT_BG, selectLine + ".0", selectLine + ".0+1l")

            self._textField_.see(self._results_[self._selectedResult_][0])

            self._updateResultInfo_()

    def _incrementResultIndex_(self):
        if self._results_:
            self._selectedResult_ += 1
            if self._selectedResult_ >= len(self._results_):
                self._selectedResult_ = 0

    def _updateResultInfo_(self):

        if not self._results_:
            self._label_.config(text=self.NO_RESULT_STRING)
        else:
            self._label_.config(text=str(self._selectedResult_+1) + " of " + str(len(self._results_)))