import tkinter as tk
from tkinter.font import Font
import time
from tracemalloc import start
import util
import math

import settings as Sets

import win32api
#import win32.lib.win32con as win32con


class Search:

    def __init__(self, root, settings, scrollbarWidth):
        self._root = root
        self._settings = settings
        self._scrollbarWidth = int(scrollbarWidth)
        self._textField: tk.Text = None
        self._guiWorker = None
        self._showing = False

        self._resultMarkerMinHeightPx = 4
        self._resultMarkerWidthPx = 10
        self._resultMarkerLimit = 1000

        self._lastWindowHeightPx = 0
        self._lastWindowWidthPx = 0

        self._searchJob = None

        self._results = list()

        self._selectedResultListIndex = -1
        self._lineNumberDeleteOffset = 0

        # The index in the result list of the first search result found during the search job
        self._searchJobFirstResultListIndex = 0

        self._searchJobResultSelected = False
        self._bottomLinesSearched = False

        self._searchSelectTextIndexRange = None

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
            self._root.unbind("<Configure>")

            try:
                self._view.destroy()
                self._resultMarkerCanvas.destroy()
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

            # # Result markers
            self._resultMarkerCanvas = tk.Canvas(self._textField, width=self._resultMarkerWidthPx, bg="green", highlightthickness=0)
            self._resultMarkerCanvas.pack(side=tk.RIGHT, fill=tk.Y, pady=(self._scrollbarWidth, 0))

            self._root.bind("<Configure>", self._onWindowSizeChange)  # Called very often as it binds to all widgets

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

            self._entry = tk.Entry(self._view, textvariable=self._var, width=30, font=tFont)
            self._entry.pack(side=tk.LEFT, padx=(4, 2))
            self._entry.bind("<Return>", self._selectNextResultButton)  # Enter key
            self._entry.bind("<Next>", self._selectNextResultButton)  # Page down
            self._entry.bind("<Prior>", self._selectPriorResultButton)  # Page up

            self._entry.bind("<FocusIn>", self._focusIn)
            self._entry.bind("<FocusOut>", self._focusOut)

            self._entry.focus_set()
            self._var.trace("w", self._searchStringUpdated)

            self._label = tk.Label(self._view, text=self.NO_RESULT_STRING, width=10, anchor=tk.W, font=tFont)
            self._label.pack(side=tk.LEFT, anchor=tk.E)

            self._caseVar = tk.StringVar(self._view)
            caseButton = tk.Checkbutton(self._view, text="Aa", variable=self._caseVar, cursor="arrow",
                                        onvalue=self.STRING_FALSE, offvalue=self.STRING_TRUE, font=tFont)
            caseButton.pack(side=tk.LEFT)
            caseButton.deselect()
            self._caseVar.trace("w", self._searchStringUpdated)

            self._regexVar = tk.StringVar(self._view)
            regexButton = tk.Checkbutton(self._view, text=".*", variable=self._regexVar, cursor="arrow",
                                         onvalue=self.STRING_TRUE, offvalue=self.STRING_FALSE, font=tFont)
            regexButton.pack(side=tk.LEFT)
            regexButton.deselect()
            self._regexVar.trace("w", self._searchStringUpdated)

            closeButton = tk.Button(self._view, text="X", command=self.close, cursor="arrow", relief=tk.FLAT, font=tFont)
            closeButton.pack(side=tk.LEFT)

            # Bind escape to close view
            self._textField.bind("<Escape>", self.close)
            self._entry.bind("<Escape>", self.close)

            # Init search settings
            self._nocase = self._caseVar.get() == self.STRING_TRUE
            self._regexp = self._regexVar.get() == self.STRING_TRUE

            # Init search field
            self._textField.after_idle(self._initiateSearchField)  # As not all elements are ready for search as this point, after_idle is used.

        else:

            self._entry.focus_set()

            # Copy select text to field
            if self._textField.tag_ranges(tk.SEL):
                self._var.set(self._textField.get(tk.SEL_FIRST, tk.SEL_LAST))

            # Select all text
            self._entry.select_range(0, tk.END)

    def _initiateSearchField(self):
        if self._textField.tag_ranges(tk.SEL):
            self._var.set(self._textField.get(tk.SEL_FIRST, tk.SEL_LAST))
        else:
            self._var.set("")

        self._entry.icursor(tk.END)

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
                    self._selectedResultListIndex = self._selectedResultListIndex - resultsDeleted

                    if self._results:
                        # If new selected result is no longer pointing to a valid result, selected first result in list (line with selected result has been deleted)
                        if self._selectedResultListIndex < 0 or self._selectedResultListIndex >= len(self._results):
                            self._selectedResultListIndex = 0

                    else:
                        self._selectedResultListIndex = -1

                    self._updateSelectedResultTags()

                if not self._resultMarkerUpdateJob:
                    self._resultMarkerUpdateJob = self._textField.after_idle(self._updateResultMarkers)

            self._updateResultInfo()

    def _focusIn(self, *args):
        self._searchHasFocus = True
        # Remove cursor based text selection
        self._textField.tag_remove(tk.SEL, 1.0, tk.END)
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

            # Start search at selection or first visible line
            if self._textField.tag_ranges(tk.SEL):
                self._searchJobStartTextIndex = self._textField.index(tk.SEL_FIRST)
            else:
                self._searchJobStartTextIndex = self._textField.index("@0,0")

            # Remove all result marker at scroll bar
            self._removeResultMarkers()

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

                self._searchJob = self._textField.after_idle(self._searchProcess, string, self._searchJobStartTextIndex)

            self._updateResultInfo()

    def _searchProcess(self, string, startTextIndex):

        countVar = tk.StringVar()
        loopMax = 500

        loopStoppedAtBottom = False
        searchCompleted = False
        tempResults = list()

        # If all lines below initial start index (_searchJobStartTextIndex) has been searched (first part of search)
        # then set stopIndex to line above _searchJobStartTextIndex to search all lines above _searchJobStartTextIndex.
        if not self._bottomLinesSearched:
            stopTextIndex = tk.END
        else:
            stopTextIndex = self._searchJobStartTextIndex

        for _ in range(loopMax):
            pos = self._textField.search(string, startTextIndex, stopindex=stopTextIndex, count=countVar, nocase=self._nocase, regexp=self._regexp)
            if not pos:
                if not self._bottomLinesSearched:
                    self._bottomLinesSearched = True
                    loopStoppedAtBottom = True
                    startTextIndex = "1.0"
                else:
                    searchCompleted = True
                break
            else:
                posSplit = pos.split(".")
                tempResults.append(self.Result(int(posSplit[0]), int(posSplit[1]), int(countVar.get())))
                startTextIndex = pos + "+1c"

        for result in tempResults:
            self._addTag(self.TAG_SEARCH, result)

        # Add temp results to result list and keep result list sorted by line number
        if (not self._bottomLinesSearched) or loopStoppedAtBottom:
            self._results.extend(tempResults)
        else:
            tempResultCount = len(tempResults)
            self._results[self._searchJobFirstResultListIndex:self._searchJobFirstResultListIndex] = tempResults
            self._searchJobFirstResultListIndex = self._searchJobFirstResultListIndex + tempResultCount
            self._selectedResultListIndex = self._selectedResultListIndex + tempResultCount

        if tempResults and not self._searchJobResultSelected:
            self._selectedResultListIndex = self._searchJobFirstResultListIndex
            self._updateSelectedResultTags()
            self._searchJobResultSelected = True

        self._updateResultInfo()

        if searchCompleted:
            # self._searchTime = time.time()

            # Reset search variables
            self._searchJobFirstResultListIndex = 0
            self._searchJobResultSelected = False

            self._drawResultMarkerLines()

            if self._results:
                # Disable scrolling of window if a result has been found. Otherwise we will quickly move past the selected result.
                self._disableGuiScrolling()
                # self._guiWorker.disableScrolling()

            self._searchJob = None
            if self._guiWorker:
                self._guiWorker.startWorker()

            # print("Search time: " + str(self._searchTime-self._startTime))

        else:
            self._searchJob = self._textField.after(1, self._searchProcess, string, startTextIndex)

    def _addTag(self, tag, searchResult: Result):
        (pos, endPos) = searchResult.getStartAndEndIndex(self._lineNumberDeleteOffset)
        self._textField.tag_add(tag, pos, endPos)

    def _updateSelectedResultTags(self, *args):

        if self._searchHasFocus:
            if self._selectedResultListIndex > -1 and self._selectedResultListIndex < len(self._results):

                # Selected result tag
                selected = self._textField.tag_ranges(self.TAG_SEARCH_SELECT)
                if selected:
                    self._textField.tag_remove(self.TAG_SEARCH_SELECT, selected[0], selected[1])
                self._addTag(self.TAG_SEARCH_SELECT, self._results[self._selectedResultListIndex])

                # Background of selected line
                selectedBg = self._textField.tag_ranges(self.TAG_SEARCH_SELECT_BG)
                if selectedBg:
                    self._textField.tag_remove(self.TAG_SEARCH_SELECT_BG, selectedBg[0], selectedBg[1])
                selectLine = self._results[self._selectedResultListIndex].originalLineNumber - self._lineNumberDeleteOffset
                self._textField.tag_add(self.TAG_SEARCH_SELECT_BG, str(selectLine) + ".0", str(selectLine) + ".0+1l")

                # Focus window on selected result
                self._textField.see(self._results[self._selectedResultListIndex].getStartAndEndIndex(self._lineNumberDeleteOffset)[0])

    def _selectPriorResultButton(self, *args):
        self._disableGuiScrolling()
        self._selectPriorResult()

    def _selectNextResultButton(self, *args):
        self._disableGuiScrolling()
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
            self._selectedResultListIndex -= 1
            if self._selectedResultListIndex < 0:
                self._selectedResultListIndex = len(self._results) - 1

    def _incrementResultIndex(self):
        if self._results:
            self._selectedResultListIndex += 1
            if self._selectedResultListIndex >= len(self._results):
                self._selectedResultListIndex = 0

    def _updateResultInfo(self):
        if not self._results:
            self._label.config(text=self.NO_RESULT_STRING)
        else:
            self._label.config(text=str(self._selectedResultListIndex+1) + " of " + str(len(self._results)))

    def _enableGuiScrolling(self):
        if self._guiWorker:
            self._guiWorker.enableScrolling()

    def _disableGuiScrolling(self):
        if self._guiWorker:
            self._guiWorker.disableScrolling()

    ####################################
    # Result Markers

    def _onWindowSizeChange(self, event):

        # Check if event is from root widget
        if isinstance(event.widget, tk.Tk):

            # Resize event (no need to update markers on a move event, but we do it anyway for now)
            if event.width != self._lastWindowWidthPx or event.height != self._lastWindowHeightPx:
                self._lastWindowWidthPx = event.width
                self._lastWindowHeightPx = event.height
                # print("**** Window Resize")
            else:
                # print("**** Window Move")
                pass

            if self._resultMarkerUpdateJob:
                self._textField.after_cancel(self._resultMarkerUpdateJob)
                # print("**** Cancel update job")
            self._resultMarkerUpdateJob = self._textField.after(100, self._updateResultMarkers)

    def _updateResultMarkers(self):
        # check if left mouse button is still pressed (during a resize or move)
        if (win32api.GetAsyncKeyState(0x01) == 0):
            self._resultMarkerUpdateJob = None
            self._removeResultMarkers()
            self._drawResultMarkerLines()
        else:
            self._resultMarkerUpdateJob = self._textField.after(100, self._updateResultMarkers)

    def _removeResultMarkers(self):
        if not self._resultMarkerUpdateJob:
            self._resultMarkerCanvas.delete("all")
            # print("Remove result markers")

    def _drawResultMarkerLines(self):

        if self._showing:

            # If windows resize or move is ongoing we should not update result markers, as it will block the resize.
            if not self._resultMarkerUpdateJob:
                if len(self._results) < self._resultMarkerLimit:

                    # print("Redraw result markers")

                    canvasHeightPx = self._resultMarkerCanvas.winfo_height()
                    # print(f"result marker canvas H {canvasHeightPx}")

                    canvasYPadding = self._calcCanvasYPadding(canvasHeightPx)

                    # Height of area where marker are allowed to be placed
                    resultMarkerAreaHeightPx = canvasHeightPx - (2 * canvasYPadding)

                    # Get total number of lines
                    lastline = int(self._textField.index("end-2c").split(".")[0])

                    # Calculate height of each result marker, based on total number of lines
                    markerHeightPx = round(resultMarkerAreaHeightPx/lastline)
                    if markerHeightPx < self._resultMarkerMinHeightPx:
                        markerHeightMinLimitPx = self._resultMarkerMinHeightPx
                    else:
                        markerHeightMinLimitPx = markerHeightPx

                    # markerColor = util.lightOrDarkenColor(self._settings.get(Sets.SEARCH_MATCH_COLOR), Sets.SELECTED_LINE_DARKEN_COLOR)
                    markerColor = self._settings.get(Sets.SEARCH_MATCH_COLOR)

                    minYPos = math.ceil(markerHeightMinLimitPx/2)
                    maxYPos = canvasHeightPx - minYPos

                    for result in self._results:

                        yPosition = round(((result.originalLineNumber - self._lineNumberDeleteOffset)/lastline) * resultMarkerAreaHeightPx)

                        # Center result marker line in "text line group"
                        yPosition = yPosition - round(markerHeightPx/2)

                        # Add Ypadding
                        yPosition = yPosition + canvasYPadding

                        if yPosition < minYPos:
                            yPosition = minYPos
                        elif yPosition > maxYPos:
                            yPosition = maxYPos

                        self._resultMarkerCanvas.create_line(0, yPosition, self._resultMarkerWidthPx, yPosition,
                                                             fill=markerColor, width=markerHeightMinLimitPx)

    def _calcCanvasYPadding(self, resultMarkerCanvasHeightPx):

        # Get total number of lines
        lastline = int(self._textField.index("end-2c").split(".")[0])

        # Calculate "real" scrollbar slider size (actual scrollbar has a minimum size)
        topVisibleLine = int(self._textField.index("@0,0").split(".")[0])
        bottomVisibleLine = int(self._textField.index("@0,%d" % self._textField.winfo_height()).split(".")[0])
        visibleLines = bottomVisibleLine - topVisibleLine
        # print("Visible lines: " + str(visibleLines))

        sliderRealSizePx = round((visibleLines/lastline) * resultMarkerCanvasHeightPx)
        # print("Slider real size: " + str(sliderRealSizePx))

        # If "real" scrollbar is smaller than actual scrollbar, add padding
        if sliderRealSizePx < self._scrollbarWidth:
            canvasYPadding = round((self._scrollbarWidth - sliderRealSizePx)/2) - 1
            # For some reason, 1/2 can round to 0.
            if canvasYPadding < 0:
                canvasYPadding = 0
        else:
            canvasYPadding = 0

        # print(f"Canvas Y padding: {canvasYPadding}")

        return canvasYPadding
