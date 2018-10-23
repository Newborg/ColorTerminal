import tkinter as tk

class Spinner:

    def __init__(self,root):
        self.root = root
        self.runFlag = True

    def close(self):

        self.runFlag = False

        try:
            self.view.after_cancel(self.updateJob)
        except AttributeError:
            # print("No job to cancel")
            pass

        try:
            self.view.destroy()
        except AttributeError:
            # print("No view")
            pass


    def show(self,indicators=True,animate=False,message=""):

        self.animate = animate

        bgColor = "black"
        borderColor = "#777"
        padding = 20

        self.view = tk.Frame(self.root,bg=bgColor,highlightthickness=2,highlightbackground=borderColor)
        self.view.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        ########################
        # Indicators

        if indicators:

            indicatorBaseFrame = tk.Frame(self.view,bg=bgColor)
            indicatorBaseFrame.pack(padx=padding,pady=padding)

            # Setup
            colors = [bgColor,"#222","#444","#777"]
            colorSequenceIndexList = [0,0,0,0,0,0,1,2,3,2,1]

            self.updatePeriod_ms = 100
            indicatorX = 20
            indicatorY = 20
            indicatorSpacing = 10
            indicatorCount = 5

            # Create color list
            self.colorSequence = list()
            for i in range(len(colorSequenceIndexList)):
                self.colorSequence.append(colors[colorSequenceIndexList[i]])

            self.colorSequenceIndex = 0

            self.indicators = list()
            for i in range(indicatorCount):
                indicator = tk.Frame(indicatorBaseFrame,bg=bgColor,width=indicatorX,height=indicatorY)
                if i > 0:
                    padx = (0,indicatorSpacing)
                else:
                    padx = 0
                # Add indicators right to left, to get movement correct
                indicator.pack(side=tk.RIGHT,padx=padx)
                self.indicators.append(indicator)

            if self.animate:
                self.updateJob = self.view.after(self.updatePeriod_ms,self.updateIndicators)

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

            indicatorLabel = tk.Label(self.view,text=message,fg=textColor,bg=bgColor,font=font)
            indicatorLabel.pack(padx=padding, pady=(topPad,padding))

    def updateIndicators(self):

        colorLen = len(self.colorSequence)

        for index,indicator in enumerate(self.indicators):
            indicator.config(bg=self.colorSequence[self._nextIndex_(colorLen,self.colorSequenceIndex+index)])

        self.colorSequenceIndex = self._nextIndex_(colorLen,self.colorSequenceIndex)

        if self.animate and self.runFlag:
            self.updateJob = self.view.after(self.updatePeriod_ms,self.updateIndicators)

    def _nextIndex_(self,len,currentIndex):
        nextIndex = currentIndex + 1
        if nextIndex >= len:
            nextIndex = 0
        return nextIndex