import tkinter as tk
from tkinter.font import Font
import time
import util

import settings as Sets

import win32api
#import win32.lib.win32con as win32con


class Search:

    def __init__(self, root, settings, scrollbarWidth):
        self._root = root
        self._settings = settings
        self._scrollbarWidth = int(scrollbarWidth)
        self._textField = None
        self._guiWorker = None
        self._showing = False

        self._resultMarkerHighPx = 4
        self._resultMarkerWidthPx = 10
        self._resultMarkerLimit = 200

        self._searchJob = None

        self._results = list()

        self._selectedResultIndex = -1
        self._lineNumberDeleteOffset = 0

        self._bottomLinesSearched = False
        self._searchStartIndex = 0

        self._searchHasFocus = False

    def linkTextArea(self, textArea):
        self._textField = textArea

    def linkWorkers(self, workers):
        self._guiWorker = workers.guiWorker

    def close(self, *event):

        if self._showing:

            self._textField.tag_delete(self.TAG_SEARCH)
            self._textField.tag_delete(self.TAG_SEARCH_SELECT)
            self._textField.tag_delete(self.TAG_SEARCH_SELECT_BG)

            self._focusOut()

            self._entry.unbind("<Escape>")
            self._textField.unbind("<Escape>")
            # self._textField.unbind("<Configure>")
            self._root.unbind("<Configure>")

            # self._root.unbind("<Button-1>")
            # self._root.unbind("<ButtonRelease-1>")
            # self._root.unbind("<B1-Motion>")

            try:
                self._view.destroy()
                self._resultMarkerFrame.destroy()
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
        def __init__(self, line, startColumn, length):
            self.originalLineNumber = line
            self.startColumn = startColumn
            self.length = length

        def getStartAndEndIndex(self, deletedLines):
            pos = str(self.originalLineNumber - deletedLines) + "." + str(self.startColumn)
            endPos = pos + "+" + str(self.length) + "c"
            return (pos, endPos)

    def show(self, *args):

        if not self._showing:

            self._showing = True

            # Result markers
            # self._resultMarkerFrame = tk.Frame(self._textField,width=self._resultMarkerWidthPx,bg=self._settings.get(Sets.TEXTAREA_BACKGROUND_COLOR))
            self._resultMarkerFrame = tk.Frame(self._textField, width=self._resultMarkerWidthPx, bg="green")
            self._resultMarkerFrame.pack(side=tk.RIGHT, fill=tk.Y, pady=(self._scrollbarWidth, 0))
            self._resultMarkerList = list()

            self._root.bind("<Configure>", self._onWindowSizeChange) # Called very often (no it is bund to too many things! :O)
            # self._textField.bind("<Configure>", self._onWindowSizeChange) # Not able to move window with this
            # self._textField.bind_all("<Configure>", self._onWindowSizeChange) # Same as bind to root

            # self._root.bind("<Button-1>", self._onButtonPressed) # Does not catch button press on the window frame :(
            # self._root.bind("<ButtonRelease-1>", self._onButtonReleased) # Does not catch button press on the window frame :(
            # self._root.bind("<B1-Motion>", self._onButtonDownMove) # Does not catch button press on the window frame :(

            ## self._root.protocol("WM_EXITSIZEMOVE", self._onButtonReleased) # Not working it seems.

            self._lastResultFramePadding = 0
            self._resultMarkerUpdateJob = None
            
            # Input view
            self._view = tk.Frame(self._textField, highlightthickness=2, highlightcolor=self._settings.get(Sets.THEME_COLOR))
            self._view.place(relx=1, x=(-5-self._resultMarkerWidthPx), y=5, anchor=tk.NE)

            self._textField.tag_configure(self.TAG_SEARCH_SELECT_BG,
                                          background=self._settings.get(Sets.SEARCH_SELECTED_LINE_COLOR),
                                          selectbackground=util.lightOrDarkenColor(self._settings.get(Sets.SEARCH_SELECTED_LINE_COLOR), Sets.SELECTED_LINE_DARKEN_COLOR))
            self._textField.tag_configure(self.TAG_SEARCH,
                                          background=self._settings.get(Sets.SEARCH_MATCH_COLOR),
                                          selectbackground=util.lightOrDarkenColor(self._settings.get(Sets.SEARCH_MATCH_COLOR), Sets.SELECTED_LINE_DARKEN_COLOR))
            self._textField.tag_configure(self.TAG_SEARCH_SELECT,
                                          background=self._settings.get(Sets.SEARCH_SELECTED_COLOR),
                                          selectbackground=util.lightOrDarkenColor(self._settings.get(Sets.SEARCH_SELECTED_COLOR), Sets.SELECTED_LINE_DARKEN_COLOR))

            # Due to focusIn, focusOut and opening and closing of search view, tags are sometimes not created in the right order.
            self._textField.tag_raise(self.TAG_SEARCH_SELECT, aboveThis=self.TAG_SEARCH)

            tFont = Font(size=self._settings.get(Sets.TEXTAREA_FONT_SIZE))

            self._var = tk.StringVar(self._view)
            self._var.set("")
            self._var.trace("w", self._searchStringUpdated)

            self._entry = tk.Entry(self._view, textvariable=self._var, width=30, font=tFont)
            self._entry.pack(side=tk.LEFT, padx=(4, 2))
            self._entry.bind("<Return>", self._selectNextResultButton)  # Enter key
            self._entry.bind("<Next>", self._selectNextResultButton)  # Page down
            self._entry.bind("<Prior>", self._selectPriorResultButton)  # Page up

            self._entry.bind("<FocusIn>", self._focusIn)
            self._entry.bind("<FocusOut>", self._focusOut)

            self._entry.focus_set()

            self._label = tk.Label(self._view, text=self.NO_RESULT_STRING, width=10, anchor=tk.W, font=tFont)
            self._label.pack(side=tk.LEFT, anchor=tk.E)

            self._caseVar = tk.StringVar(self._view)
            self._caseVar.trace("w", self._searchStringUpdated)
            caseButton = tk.Checkbutton(self._view, text="Aa", variable=self._caseVar, cursor="arrow",
                                        onvalue=self.STRING_FALSE, offvalue=self.STRING_TRUE, font=tFont)
            caseButton.pack(side=tk.LEFT)
            caseButton.deselect()

            self._regexVar = tk.StringVar(self._view)
            self._regexVar.trace("w", self._searchStringUpdated)
            regexButton = tk.Checkbutton(self._view, text=".*", variable=self._regexVar, cursor="arrow",
                                         onvalue=self.STRING_TRUE, offvalue=self.STRING_FALSE, font=tFont)
            regexButton.pack(side=tk.LEFT)
            regexButton.deselect()

            closeButton = tk.Button(self._view, text="X", command=self.close, cursor="arrow", relief=tk.FLAT, font=tFont)
            closeButton.pack(side=tk.LEFT)

            # Bind escape to close view
            self._textField.bind("<Escape>", self.close)
            self._entry.bind("<Escape>", self.close)

            # Init search settings
            self._nocase = self._caseVar.get() == self.STRING_TRUE
            self._regexp = self._regexVar.get() == self.STRING_TRUE

        else:

            self._entry.focus_set()

    def searchLinesAdded(self, numberOfLinesAdded, numberOfLinesDeleted, lastLine):

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
                    pos = self._textField.search(string, searchStartIndex, stopindex=tk.END, count=countVar, nocase=self._nocase, regexp=self._regexp)
                    if not pos:
                        break
                    else:
                        posSplit = pos.split(".")
                        # Add number of deleted line to line number to match existing results in result list
                        newLine = int(posSplit[0]) + self._lineNumberDeleteOffset
                        column = int(posSplit[1])

                        result = self.Result(newLine, column, int(countVar.get()))
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

                # Update result markers (might be slow?)
                if self._resultMarkerVisible:
                    self._removeResultMarkers()
                    self._drawResultMarkers()
                elif len(self._results) < self._resultMarkerLimit:
                    self._drawResultMarkers()

            self._updateResultInfo()

    def _focusIn(self, *args):
        self._searchHasFocus = True
        # Remove cursor based text selection
        self._textField.tag_remove("sel", 1.0, tk.END)
        # Show tag of selected result when search gets focus again
        self._updateSelectedResultTags()

    def _focusOut(self, *args):
        self._searchHasFocus = False

        self._textField.tag_remove(self.TAG_SEARCH_SELECT, 1.0, tk.END)
        self._textField.tag_remove(self.TAG_SEARCH_SELECT_BG, 1.0, tk.END)

        self._enableGuiScrolling()

    def _searchStringUpdated(self, *args):

        if self._showing:

            string = self._var.get()

            if self._searchJob:
                self._textField.after_cancel(self._searchJob)
                self._searchJob = None
                if not string:
                    # If search field is empty, the guiWorker has to be started again
                    if self._guiWorker:
                        self._guiWorker.startWorker()

            self._textField.tag_remove(self.TAG_SEARCH_SELECT, 1.0, tk.END)
            self._textField.tag_remove(self.TAG_SEARCH_SELECT_BG, 1.0, tk.END)
            self._textField.tag_remove(self.TAG_SEARCH, 1.0, tk.END)

            # Remove all result marker on scroll bar
            self._removeResultMarkers()

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
                if self._guiWorker:
                    self._guiWorker.stopWorker()

                self._searchJob = self._textField.after(0, self._searchProcess, string, self._searchStartIndex)

            self._updateResultInfo()

    def _searchProcess(self, string, start):

        countVar = tk.StringVar()
        loopMax = 500

        loopStoppedAtBottom = False
        searchCompleted = False
        tempResults = list()

        # If lines below start index has been searched (first part of search) then set stopIndex to line above start index
        if not self._bottomLinesSearched:
            stopIndex = tk.END
        else:
            stopIndex = self._searchStartIndex + "-1l"

        for _ in range(loopMax):
            pos = self._textField.search(string, start, stopindex=stopIndex, count=countVar, nocase=self._nocase, regexp=self._regexp)
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
                tempResults.append(self.Result(int(posSplit[0]), int(posSplit[1]), int(countVar.get())))
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

            self._drawResultMarkers()

            if self._results:
                # Disable scrolling of window if a result has been found. Otherwise we will quickly move past the selected result.
                self._disableGuiScrolling()
                # self._guiWorker.disableScrolling()

            self._searchJob = None
            if self._guiWorker:
                self._guiWorker.startWorker()

            # print("Search time: " + str(self._searchTime-self._startTime))

        else:
            self._searchJob = self._textField.after(1, self._searchProcess, string, start)

    def _addTag(self, tag, searchResult: Result):
        (pos, endPos) = searchResult.getStartAndEndIndex(self._lineNumberDeleteOffset)
        self._textField.tag_add(tag, pos, endPos)

    def _updateSelectedResultTags(self, *args):

        if self._searchHasFocus:
            if self._selectedResultIndex > -1 and self._selectedResultIndex < len(self._results):

                # Selected result tag
                selected = self._textField.tag_ranges(self.TAG_SEARCH_SELECT)
                if selected:
                    self._textField.tag_remove(self.TAG_SEARCH_SELECT, selected[0], selected[1])
                self._addTag(self.TAG_SEARCH_SELECT, self._results[self._selectedResultIndex])

                # Background of selected line
                selectedBg = self._textField.tag_ranges(self.TAG_SEARCH_SELECT_BG)
                if selectedBg:
                    self._textField.tag_remove(self.TAG_SEARCH_SELECT_BG, selectedBg[0], selectedBg[1])
                selectLine = self._results[self._selectedResultIndex].originalLineNumber - self._lineNumberDeleteOffset
                self._textField.tag_add(self.TAG_SEARCH_SELECT_BG, str(selectLine) + ".0", str(selectLine) + ".0+1l")

                # Focus window on selected result
                self._textField.see(self._results[self._selectedResultIndex].getStartAndEndIndex(self._lineNumberDeleteOffset)[0])

    def _selectPriorResultButton(self, *args):
        self._disableGuiScrolling()
        # self._guiWorker.disableScrolling()
        self._selectPriorResult()

    def _selectNextResultButton(self, *args):
        self._disableGuiScrolling()
        # self._guiWorker.disableScrolling()
        self._selectNextResult()

    def _selectPriorResult(self, *args):
        self._decrementResultIndex()

        self._updateSelectedResultTags()

        self._updateResultInfo()

    def _selectNextResult(self, *args):
        self._incrementResultIndex()

        self._updateSelectedResultTags()

        self._updateResultInfo()

    def _decrementResultIndex(self):
        if self._results:
            self._selectedResultIndex -= 1
            if self._selectedResultIndex < 0:
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

    def _enableGuiScrolling(self):
        if self._guiWorker:
            self._guiWorker.enableScrolling()

    def _disableGuiScrolling(self):
        if self._guiWorker:
            self._guiWorker.disableScrolling()

    ####################################
    # Result Markers

    def _onWindowSizeChange(self, event):
        
        
        if isinstance(event.widget,tk.Tk):
            print("**** Window Size Change")
            print(event)
            if self._resultMarkerUpdateJob:
                self._textField.after_cancel(self._resultMarkerUpdateJob)
                print("**** Cancel update job")
            self._resultMarkerUpdateJob = self._textField.after(1000, self._updateResultMarkersOnResize)
        # self._resultMarkerUpdateJob = self._textField.after_idle(self._updateResultMarkersOnResize) # not the solution

    # def _onButtonPressed(self, event):
    #     print("## Button down ##")
    #     print(win32api.GetKeyState(0x01))
    #     print(win32api.GetAsyncKeyState(0x01))
    #     print(win32api.GetAsyncKeyState(0x02))
        

    # def _onButtonReleased(self, event):
    #     print("## Button released ##")
    #     print(win32api.GetKeyState(0x01))
    #     print(win32api.GetAsyncKeyState(0x01))
    #     print(win32api.GetAsyncKeyState(0x02))

    # def _onButtonDownMove(self, event):
    #     print("## Button dowm move ##")

    def _updateResultMarkersOnResize(self):
        self._resultMarkerUpdateJob = None
        
        # check if left mouse button is still pressed (during a resize or move)
        if (win32api.GetAsyncKeyState(0x01) == 0):            
            self._removeResultMarkers()
            self._drawResultMarkers()
        else:
            self._resultMarkerUpdateJob = self._textField.after(1000, self._updateResultMarkersOnResize)


    def _removeResultMarkers(self):
        if not self._resultMarkerUpdateJob:
            for label in self._resultMarkerList:
                label.destroy()
            self._resultMarkerList.clear()
            self._resultMarkerVisible = False

            print("Remove result markers")

    def _drawResultMarkers(self):
        
        # TODO Problem. Not able to resize window as we redraw a lot

        if self._showing:

            # If windows resize is ongoing we should not try to update result markers, as it will block the resize.
            # TODO not a good solution :( Update <Configure> called way too often when bound to root. IF not bound to root, it is not possible to move the window 
            if not self._resultMarkerUpdateJob:
                if len(self._results) < self._resultMarkerLimit:

                    print("Redraw result markers")

                    # Add result label to scrollbar
                    # Get total number of lines
                    lastline = int(self._textField.index("end-2c").split(".")[0])

                    resultMarkerFrameHeight = self._resultMarkerFrame.winfo_height()

                    self._repackResultMarkerFrame()

                    # markerColor = util.lightOrDarkenColor(self._settings.get(Sets.SEARCH_MATCH_COLOR), Sets.SELECTED_LINE_DARKEN_COLOR)
                    markerColor = self._settings.get(Sets.SEARCH_MATCH_COLOR)

                    # markerYOffset = self._resultMarkerHighPx/2 # Not used for now.
                    markerYOffset = 0
                    # print("Line offset: " + str(self._lineNumberDeleteOffset))

                    # resultMarker = tk.Label(self._resultMarkerFrame, bg="red")
                    # resultMarker.place(relx=1, rely=0, x=2, y=markerYOffset, width=self._resultMarkerWidthPx, height=self._resultMarkerHighPx, anchor=tk.SE)
                    # print("Marker y pos: " + str(resultMarker.winfo_y()))

                    #     width = widget.winfo_width()
                    #     height = widget.winfo_height()
                    #     posx = widget.winfo_x()
                    #     posy = widget.winfo_y()

                    minimumRatio = (self._resultMarkerHighPx-markerYOffset)/resultMarkerFrameHeight

                    for result in self._results:

                        resultMarker = tk.Label(self._resultMarkerFrame, bg=markerColor)

                        location = (result.originalLineNumber - self._lineNumberDeleteOffset)/lastline
                        if location < minimumRatio:
                            location = minimumRatio

                        # If window has been resized during draw, cancel draw.
                        if self._resultMarkerUpdateJob:
                            print("Break draw ****") # Is this needed?
                            break

                        resultMarker.place(relx=1, rely=location, x=0, y=markerYOffset, width=self._resultMarkerWidthPx,
                                        height=self._resultMarkerHighPx, anchor=tk.SE)
                        self._resultMarkerList.append(resultMarker)

                        self._resultMarkerVisible = True

    def _repackResultMarkerFrame(self):

        if self._showing:
            # Get total number of lines
            lastline = int(self._textField.index("end-2c").split(".")[0])

            resultMarkerFrameHeight = self._resultMarkerFrame.winfo_height()

            # Calculate "real" scrollbar slider size
            topVisibleLine = int(self._textField.index("@0,0").split(".")[0])
            bottomVisibleLine = int(self._textField.index("@0,%d" % self._textField.winfo_height()).split(".")[0])
            visibleLines = bottomVisibleLine - topVisibleLine
            print("Visible lines: " + str(visibleLines))

            sliderRealSizePx = round((visibleLines/lastline) * resultMarkerFrameHeight)
            print("Slider real size: " + str(sliderRealSizePx))

            
            if sliderRealSizePx < self._scrollbarWidth:
                resultFramePadding = round((self._scrollbarWidth - sliderRealSizePx)/2) - 1  # TODO The 1 could be adjusted later maybe?
            else:
                resultFramePadding = 0

            if self._lastResultFramePadding != resultFramePadding:
                self._lastResultFramePadding = resultFramePadding  

                self._resultMarkerFrame.pack(side=tk.RIGHT, fill=tk.Y, pady=((self._scrollbarWidth+int(resultFramePadding)), resultFramePadding))

                print("Repack result marker frame")




#                 Traceback (most recent call last):
#   File "C:\Users\knn\AppData\Local\Programs\Python\Python39\lib\tkinter\__init__.py", line 1892, in __call__
#     return self.func(*args)
#   File "C:\Users\knn\AppData\Local\Programs\Python\Python39\lib\tkinter\__init__.py", line 814, in callit
#     func(*args)
#   File "C:\tools\ColorTerminal/colorterminal\search.py", line 483, in _updateResultMarkersOnResize
#     self._drawResultMarkers()
#   File "C:\tools\ColorTerminal/colorterminal\search.py", line 516, in _drawResultMarkers
#     self._repackResultMarkerFrame()
#   File "C:\tools\ColorTerminal/colorterminal\search.py", line 581, in _repackResultMarkerFrame
#     self._resultMarkerFrame.pack(side=tk.RIGHT, fill=tk.Y, pady=((self._scrollbarWidth+int(resultFramePadding)), resultFramePadding))
#   File "C:\Users\knn\AppData\Local\Programs\Python\Python39\lib\tkinter\__init__.py", line 2396, in pack_configure
#     self.tk.call(
# _tkinter.TclError: bad 2nd pad value "-1": must be positive screen distance
