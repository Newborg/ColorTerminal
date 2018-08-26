import tkinter as tk
from tkinter import messagebox
from tkinter.font import Font

# tFont = Font(family="DejaVu Sans Mono", size=10)
root = tk.Tk()
tFont2 = Font(family="DejaVu Sans Mono", size=10)
tFont1 = Font(family="courier", size=10)


fontList = tk.font.families()

for font in fontList:
    if font.find("Consolas") > -1:
        print(font)

#####################################

# import os

# filename = "Test2.txt"
# logFilePath = "LogsTest"

# fullFilename = os.path.join(logFilePath,filename)

# os.makedirs(os.path.dirname(fullFilename), exist_ok=True)

# with open(fullFilename,"a") as file:
#     file.write("HELLO\n")

# filesize = os.path.getsize(fullFilename)
# print(filesize)

#####################################

first = 5
second = 2
mod = 5 % 2

print(mod)