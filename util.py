import tkinter as tk

class AutoScrollbar(tk.Scrollbar):
    # a scrollbar that hides itself if it's not needed.
    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:                
            self.pack_forget()
        else:
            super().pack(self.packInput)
        tk.Scrollbar.set(self, lo, hi)
    def pack(self, **kw):
        self.packInput = kw
        super().pack(kw)             
    def grid(self, **kw):
        raise tk.TclError("cannot use grid with this widget")
    def place(self, **kw):
        raise tk.TclError("cannot use place with this widget")