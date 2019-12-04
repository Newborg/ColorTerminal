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


def lightOrDarkenColor(hex_color, brightness_offset=1):
    """ takes a color like #87c95f and produces a lighter or darker variant """
    if len(hex_color) != 7:
        raise Exception("Passed %s into _lightOrDarkenColor(), needs to be in #87c95f format." % hex_color)
    rgb_hex = [hex_color[x:x+2] for x in [1, 3, 5]]
    new_rgb_int = [int(hex_value, 16) + brightness_offset for hex_value in rgb_hex]
    new_rgb_int = [min([255, max([0, i])]) for i in new_rgb_int] # make sure new values are between 0 and 255        
    return "#" + "".join('%02x'%i for i in new_rgb_int)