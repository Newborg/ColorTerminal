#####################################
# Dict stuff

DictA = {"A":"AAAA"}

try:
    print(DictA["B"])
except KeyError:
    print("No key man")



exit()

#####################################
# List stuff

ListA = ["A","B"]
ListB = ["D","C"]
Element = "E"

print(ListA + ListB)
print(ListA)

ListA.extend(ListB)
print(ListA)

ListA = ["A","B"]
ListA += ListB
print(ListA)

ListA.append(Element)
print(ListA)

ListA = ["A","B"]
ListA += Element
print(ListA)

ListA = ["A","B"]
ListA.extend(Element)
print(ListA)

exit()

#####################################
# Tk version

import tkinter

print(tkinter.TkVersion)
exit()

#####################################
# String format

testINt = 100
newstring = "Hello" + "{:05d}".format(testINt)
print(newstring)

newint = int(newstring.replace("Hello",""))

print(str(newint))

print(str(int("10000125")))

exit()


#####################################
# Json settings file v2

# import json
# import datetime
# # import collections 



# config = dict()
# config["Default"] = "testing"
# config["Empty"] = ""
# config["HEY"] = r"%Y.%m.%d_%H.%M.%S"

# with open ("SuperConfig_v2.json","w") as configfile:
#     json.dump(config,configfile,indent=4)



# with open("SuperConfig_v2.json","r") as readfile:
#     data = json.load(readfile)
#     print(json.dumps(data,indent=2))

# print(data["HEY"])


# timestamp = datetime.datetime.now().strftime(data["HEY"])
# print(timestamp)

# with open ("SuperConfig_v2.json","w") as configfile:
#     config["Empty"] = "Not empty!!"
#     config["HEY"] = "A new value!"
#     json.dump(config,configfile,indent=4)

#     # config["HEY"] = {"T123":"Hello"}
#     # json.dump(config,configfile,indent=4)

# exit()

#####################################
# Json settings file

import json
import datetime
# import collections 



config = dict()
config["Default"] = {"testing1" : "MoreBAM", "testing2" : 1234}
config["Empty"] = {}
config["HEY"] = {"AHHHHH": r"%Y.%m.%d_%H.%M.%S", "T123": r"\Logs\logsdf", "T456": r"\Logs\logsdf"}

with open ("SuperConfig.json","w") as configfile:
    json.dump(config,configfile,indent=4)



with open("SuperConfig.json","r") as readfile:
    data = json.load(readfile)
    print(json.dumps(data,indent=2))

print(data["HEY"]["AHHHHH"])


timestamp = datetime.datetime.now().strftime(data["HEY"]["AHHHHH"])
print(timestamp)


# print(data["DAMN"]["AHHHHH"])
print(data.get("HEY")["AHHHHH"])
print(data.get("DAMN",{}).get("AHHHHH","Default Value"))
# print(data["DAMN"].get("AHHHHH","Default Value"))
print(data.get("HEY",{}).get("13245","Default Value"))

with open ("SuperConfig.json","w") as configfile:
    config["Empty"] = {"NOT":"Hello"}
    config["HEY"]["T123"] = "Hello"
    json.dump(config,configfile,indent=4)

    # config["HEY"] = {"T123":"Hello"}
    # json.dump(config,configfile,indent=4)

exit()


#####################################
# String split

teststring = "Hello_there"

print(teststring.split("_"))


exit()
#####################################
# tkinter window focus

# self.view.lift()
# self.view.focus_force()
# self.view.attributes('-topmost', 1)
# self.view.attributes('-topmost', 0)


#####################################
# tkinter color chooser

from tkinter import *
from tkinter.colorchooser import askcolor

def getColor():
    color = askcolor("red") 
    print(color)

Button(text='Select Color', command=getColor).pack()
mainloop()

exit()

#####################################
# Dict index

testing = dict()

testing["BAM"] = "HELLO"

key = "BAM"

if key in testing.keys():
    print(testing[key])
else:
    print("WROng key")

exit()

#####################################
# List delete

testlist = [1,2,3,4,5,6,7,8]

del testlist[0]

print(testlist[0])
print(len(testlist))

testlist.append(9)
print(testlist[0])
print(len(testlist))

exit()
#####################################
# Empty String

stringtest = ""

if stringtest:
    print("Hello")

exit()

#####################################
# Lists

alist = ("test",)

for stuff in alist:
    print(stuff)


exit()

#####################################
# Regex

import re

# testString = "11 GUI::GUIMasterStateMachine=>Completed transition onFOSS::Bifrost::T123::MeasureProgress to nil"
testString = "[12:36:33.240] ( 0.107) 11 GUI::GUIMasterStateMachine=>Completed transition onFOSS::Bifrost::T123::MeasureProgress to nil"

regexString = r"\[.{12}\] \(.{6,12}\)"

match = re.search(regexString,testString)
if match:    
    print(match)
    print("HERE: " + str(match))
    print(match.group(0))

exit()


#####################################
# Ini settings file

import configparser
import datetime

config = configparser.ConfigParser(delimiters=("=",))
config["Default"] = {"testing1" : "BAM", "testing2" : 1234}
config["Empty"] = {}
config["HEY"] = {"AHHHHH": r"%%Y.%%m.%%d_%%H.%%M.%%S", "T123": r"\Logs\logsdf", "T456": r"\Logs\logsdf"}


with open ("SuperComfig.ini","w") as configfile:
    config.write(configfile)

configRead = configparser.ConfigParser()

configRead.read("SuperComfig.ini")

print(configRead.sections())

print(configRead["HEY"]["AHHHHH"])
print(configRead["HEY"]["T123"])
print(configRead["HEY"]["T456"])

testing = configRead["HEY"]["AHHHHH"]

timestamp = datetime.datetime.now().strftime(testing)
print(timestamp)

print(configRead.getint("Default","testing4",fallback=123))

print(type(configRead["Default"]["testing1"]))
print(type(configRead.getint("Default","testing4",fallback=123)))

# structure = configRead["Default"]
# print(configRead.items("Default"))

# print("Sections " + str(configRead._sections["Default"]))

# print(configRead._sections["Default"].keys())

testdict = dict(configRead.items("Default"))
print("Dict test keys: " + str(testdict.keys()))

if "Default" in configRead.sections():
    print("HELLLO")

textColorMap = {
        "Main::.*":"#EFC090",
        ".*TM::.*":"#00D0D0",
        "TM::LevelSensorsI2C=>":"#FF8080",
        "GUI::.*":"#79ABFF",
        }

print(textColorMap.keys())


#####################################

# import tkinter as tk
# from tkinter import messagebox
# from tkinter.font import Font

# # tFont = Font(family="DejaVu Sans Mono", size=10)
# root = tk.Tk()
# tFont2 = Font(family="DejaVu Sans Mono", size=10)
# tFont1 = Font(family="courier", size=10)


# fontList = tk.font.families()

# for font in fontList:
#     if font.find("Consolas") > -1:
#         print(font)

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

# first = 5
# second = 2
# mod = 5 % 2

# print(mod)

#####################################

# listTest = 999

# listlist = [listTest]

# for test in listlist:
#     print(test)

#####################################

# import msvcrt

# while True:
#     pressedKey = msvcrt.getwch()
#     if pressedKey == 'q':    
#        print("Q was pressed")
#     elif pressedKey == 'x':    
#        break
#     else:
#        print("Key Pressed:" + str(pressedKey))

#####################################

       
# import time

# while True:
#     try:
#         while True:
#             print("HELOOOOO")     
#             time.sleep(1)
#     except KeyboardInterrupt:
#         pass