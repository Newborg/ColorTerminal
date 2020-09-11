from enum import Enum
import datetime

class LogLevel(Enum):
    ERROR = 0
    WARNING = 1
    INFO = 2
    DEBUG = 3

def traceLog(level,msg):
    timestamp = datetime.datetime.now()
    micros = int(timestamp.microsecond/1000)
    timeString = timestamp.strftime("%Y-%m-%d %H:%M:%S") + "." + '{:03d}'.format(micros)

    print(timeString + " [" + level.name + "] " + msg)