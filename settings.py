from traceLog import traceLog,LogLevel
import json

DEFAULT_WINDOW_SIZE         = "MainWindow_defaultWindowSize"
THEME_COLOR                 = "MainWindow_themeColor"

BACKGROUND_COLOR            = "TextArea_backgroundColor"
SELECT_BACKGROUND_COLOR     = "TextArea_selectBackgroundColor"
TEXT_COLOR                  = "TextArea_textColor"
FONT_FAMILY                 = "TextArea_fontFamily"
FONT_SIZE                   = "TextArea_fontSize"
MAX_LINE_BUFFER             = "TextArea_maxLineBuffer"

SEARCH_MATCH_COLOR          = "Search_MatchColor"
SEARCH_SELECTED_COLOR       = "Search_SelectedColor"
SEARCH_SELECTED_LINE_COLOR  = "Search_SelectedLineColor"

LOG_FILE_PATH               = "LogFile_logFilePath"
LOG_FILE_BASE_NAME          = "LogFile_logFileBaseName"
LOG_FILE_TIMESTAMP          = "LogFile_logFileTimestamp"

LINE_COLOR_MAP              = "LineColorMap"


# Static for now

# Time Stamp
timeStampBracket = ["[","]"]
timeDeltaBracket = ["(",")"]
timeStampRegex = "\\" + timeStampBracket[0] + ".{12}\\" + timeStampBracket[1] + " \\" + timeDeltaBracket[0] + ".{6,12}\\" + timeDeltaBracket[1]

# Other Colors
STATUS_CONNECT_BACKGROUND_COLOR = "#008800"
STATUS_WORKING_BACKGROUND_COLOR = "gray"
STATUS_DISCONNECT_BACKGROUND_COLOR = "#CC0000"
STATUS_TEXT_COLOR = "white"

# Connect Status Lines
CONNECT_LINE_TEXT = " Connected to port\n"
connectLineRegex = "\\" + timeStampBracket[0] + ".{8}\\" + timeStampBracket[1] + CONNECT_LINE_TEXT
CONNECT_LINE_BACKGROUND_COLOR = "#008800"
CONNECT_LINE_SELECT_BACKGROUND_COLOR = "#084C08"

disconnectLineText = " Disconnected from port. Log file "
disconnectLineRegex = "\\" + timeStampBracket[0] + ".{8}\\" + timeStampBracket[1] + disconnectLineText
DISCONNECT_LINE_BACKGROUND_COLOR = "#880000"
DISCONNECT_LINE_SELECT_BACKGROUND_COLOR = "#4C0808"

CONNECT_COLOR_TAG = "CONNECT_COLOR_TAG"
DISCONNECT_COLOR_TAG = "DISCONNECT_COLOR_TAG"

# Hide line
HIDE_LINE_FONT_COLOR = "#808080"
HIDELINE_COLOR_TAG = "HIDELINE_COLOR_TAG"

class Settings:

    # DEFAULT_WINDOW_SIZE         = "MainWindow_defaultWindowSize"
    # THEME_COLOR                 = "MainWindow_themeColor"

    # BACKGROUND_COLOR            = "TextArea_backgroundColor"
    # SELECT_BACKGROUND_COLOR     = "TextArea_selectBackgroundColor"
    # TEXT_COLOR                  = "TextArea_textColor"
    # FONT_FAMILY                 = "TextArea_fontFamily"
    # FONT_SIZE                   = "TextArea_fontSize"
    # MAX_LINE_BUFFER             = "TextArea_maxLineBuffer"

    # SEARCH_MATCH_COLOR          = "Search_MatchColor"
    # SEARCH_SELECTED_COLOR       = "Search_SelectedColor"
    # SEARCH_SELECTED_LINE_COLOR  = "Search_SelectedLineColor"

    # LOG_FILE_PATH               = "LogFile_logFilePath"
    # LOG_FILE_BASE_NAME          = "LogFile_logFileBaseName"
    # LOG_FILE_TIMESTAMP          = "LogFile_logFileTimestamp"

    # LINE_COLOR_MAP              = "LineColorMap"

    def __init__(self,jsonFileName):
        self.jsonFileName = jsonFileName
        self.settings = dict()

    def reload(self):

        settingsJson = dict()

        try:
            with open(self.jsonFileName,"r") as jsonFile:
                settingsJson = json.load(jsonFile)
        except FileNotFoundError:
            traceLog(LogLevel.WARNING,"Settings file not found. Using default values")
            pass

        # Main Window
        self.settings[DEFAULT_WINDOW_SIZE]         = settingsJson.get(DEFAULT_WINDOW_SIZE,"1100x600")
        self.settings[THEME_COLOR]                 = settingsJson.get(THEME_COLOR,"#42bcf4")

        # Text Area
        self.settings[BACKGROUND_COLOR]            = settingsJson.get(BACKGROUND_COLOR,"#000000")
        self.settings[SELECT_BACKGROUND_COLOR]     = settingsJson.get(SELECT_BACKGROUND_COLOR,"#303030")
        self.settings[TEXT_COLOR]                  = settingsJson.get(TEXT_COLOR,"#FFFFFF")
        self.settings[FONT_FAMILY]                 = settingsJson.get(FONT_FAMILY,"Consolas")
        self.settings[FONT_SIZE]                   = settingsJson.get(FONT_SIZE,10)
        self.settings[MAX_LINE_BUFFER]             = settingsJson.get(MAX_LINE_BUFFER,4000)

        # Search
        self.settings[SEARCH_MATCH_COLOR]          = settingsJson.get(SEARCH_MATCH_COLOR,"#9e6209")
        self.settings[SEARCH_SELECTED_COLOR]       = settingsJson.get(SEARCH_SELECTED_COLOR,"#06487f")
        self.settings[SEARCH_SELECTED_LINE_COLOR]  = settingsJson.get(SEARCH_SELECTED_LINE_COLOR,"#303030")

        # Log File
        self.settings[LOG_FILE_PATH]               = settingsJson.get(LOG_FILE_PATH,"Logs")
        self.settings[LOG_FILE_BASE_NAME]          = settingsJson.get(LOG_FILE_BASE_NAME,"SerialLog_")
        self.settings[LOG_FILE_TIMESTAMP]          = settingsJson.get(LOG_FILE_TIMESTAMP,"%Y.%m.%d_%H.%M.%S")

        # Line Color Map
        self.settings[LINE_COLOR_MAP]              = settingsJson.get(LINE_COLOR_MAP,{})

        try:
            with open(self.jsonFileName,"w") as jsonFile:
                json.dump(self.settings,jsonFile,indent=4)
        except:
            traceLog(LogLevel.WARNING,"Error updating settings file")
            pass


    def get(self,option):
        # No keycheck, should fail if wrong key
        return self.settings[option]

    def setOption(self,option,value):

        self.settings[option] = value

        # print("Saving option " + str(option) + " with value " + str(value))

        try:
            with open(self.jsonFileName,"w") as jsonFile:
                json.dump(self.settings,jsonFile,indent=4)
        except FileNotFoundError:
            traceLog(LogLevel.WARNING,"Settings file not found. Not able to save setting")
            pass

    