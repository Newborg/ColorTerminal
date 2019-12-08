import os
import sys
import argparse

stdoutFile = "Testing"

parser = argparse.ArgumentParser()



parser.add_argument("-c","--enableConsole",help="send stdout and stderr to console, otherwise this is written to " + stdoutFile,action="store_true")
parser.add_argument("logFilePath",metavar="Path",help="Path of logfile to open")
args = parser.parse_args()

if (args.logFilePath):
    print("File: " + args.logFilePath)

input("Press Enter to continue...")