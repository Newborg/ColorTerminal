from enum import Enum

class ConnectState(Enum):
    CONNECTING = 1
    CONNECTED = 2
    DISCONNECTING = 3   
    DISCONNECTED = 4

class SerialLine:
    def __init__(self, data, timestamp):
        self.data = data
        self.timestamp = timestamp

class PrintLine:
    def __init__(self, line, lineTags, updatePreviousLine = False):
        self.line = line
        self.lineTags = lineTags
        self.updatePreviousLine = updatePreviousLine