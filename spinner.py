import tkinter as tk

class Spinner:

    def __init__(self,root):
        self._root = root
        self._runFlag = True

    def close(self):

        self._runFlag = False

        try:
            self._view.after_cancel(self._updateJob)
        except AttributeError:
            # print("No job to cancel")
            pass

        try:
            self._view.destroy()
        except AttributeError:
            # print("No view")
            pass


    def show(self,indicators=True,animate=False,message=""):

        self._animate = animate

        bgColor = "black"
        borderColor = "#777"
        padding = 20

        self._view = tk.Frame(self._root,bg=bgColor,highlightthickness=2,highlightbackground=borderColor)
        self._view.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        ########################
        # Indicators

        if indicators:

            indicatorBaseFrame = tk.Frame(self._view,bg=bgColor)
            indicatorBaseFrame.pack(padx=padding,pady=padding)

            # Setup
            colors = [bgColor,"#222","#444","#777"]
            colorSequenceIndexList = [0,0,0,0,0,0,1,2,3,2,1]

            self._updatePeriod_ms = 100
            indicatorX = 20
            indicatorY = 20
            indicatorSpacing = 10
            indicatorCount = 5

            # Create color list
            self.colorSequence = list()
            for i in range(len(colorSequenceIndexList)):
                self.colorSequence.append(colors[colorSequenceIndexList[i]])

            self._colorSequenceIndex = 0

            self._indicators = list()
            for i in range(indicatorCount):
                indicator = tk.Frame(indicatorBaseFrame,bg=bgColor,width=indicatorX,height=indicatorY)
                if i > 0:
                    padx = (0,indicatorSpacing)
                else:
                    padx = 0
                # Add indicators right to left, to get movement correct
                indicator.pack(side=tk.RIGHT,padx=padx)
                self._indicators.append(indicator)

            if self._animate:
                self._updateJob = self._view.after(self._updatePeriod_ms,self.updateIndicators)

        ########################
        # Text

        if indicators:
            topPad = 0
        else:
            topPad = padding

        if message:
            textColor = "white"
            font = ("arial",14)
            # font = ("courier new",12)

            indicatorLabel = tk.Label(self._view,text=message,fg=textColor,bg=bgColor,font=font)
            indicatorLabel.pack(padx=padding, pady=(topPad,padding))

    def updateIndicators(self):

        colorLen = len(self.colorSequence)

        for index,indicator in enumerate(self._indicators):
            indicator.config(bg=self.colorSequence[self._nextIndex(colorLen,self._colorSequenceIndex+index)])

        self._colorSequenceIndex = self._nextIndex(colorLen,self._colorSequenceIndex)

        if self._animate and self._runFlag:
            self._updateJob = self._view.after(self._updatePeriod_ms,self.updateIndicators)

    def _nextIndex(self,len,currentIndex):
        nextIndex = currentIndex + 1
        if nextIndex >= len:
            nextIndex = 0
        return nextIndex