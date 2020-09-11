import os
import sys
import argparse
import psutil
# from datetime import datetime
import time


stdoutFile = "Testing"

parser = argparse.ArgumentParser()



parser.add_argument("-c","--enableConsole",help="send stdout and stderr to console, otherwise this is written to " + stdoutFile,action="store_true")
parser.add_argument("logFilePath",metavar="Path",nargs="?",help="(optional) path of logfile to open ",default="")
args = parser.parse_args()

if (args.logFilePath):
    print("File: " + args.logFilePath)

if (args.enableConsole):
    print("Console enabled!")

found = ""
pythonScript = list()
for proc in psutil.process_iter():
    # print(str(proc.name()))
    try:
        if "color" in proc.name().lower():
            found = proc.name()            
        if "python" in proc.name().lower():
            pythonScript.append([proc.name(), proc.cmdline(), proc.children(), proc.create_time()])
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass

if found:
    print("FOUND: " + str(found))

for name, cmdline, children, create_time in pythonScript:
    print(name)
    print(cmdline)
    # print(children)
    print(create_time)
    print("*********")

print(time.time())

# input("Press Enter to continue...")