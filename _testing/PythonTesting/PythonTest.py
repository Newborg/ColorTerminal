import os
import sys
import argparse
import psutil

stdoutFile = "Testing"

parser = argparse.ArgumentParser()



parser.add_argument("-c","--enableConsole",help="send stdout and stderr to console, otherwise this is written to " + stdoutFile,action="store_true")
parser.add_argument("logFilePath",metavar="Path",nargs="?",help="(optional) path of logfile to open ",default="")
args = parser.parse_args()

if (args.logFilePath):
    print("File: " + args.logFilePath)

if (args.enableConsole):
    print("Console enabled!")

# found = ""
# pythonScript = list()
# for proc in psutil.process_iter():
#     # print(str(proc.name()))
#     try:
#         if "color" in proc.name().lower():
#             found = proc.name()
#         if "python" in proc.name().lower():
#             pythonScript.append(proc.cmdline())
#     except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
#         pass

# if found:
#     print("FOUND: " + str(found))

# for cmdline in pythonScript:
#     print(cmdline)


input("Press Enter to continue...")