@echo off
echo *************************************
echo ColorTerminal shell integration setup
echo *****
echo Adding following folders in registry:
echo "HKEY_CLASSES_ROOT\*\shell\ColorTerminalPython" (contains 3 keys)
echo "HKEY_CLASSES_ROOT\*\shell\ColorTerminalPython\command" (contains 1 key)

reg add "HKCR\*\shell\ColorTerminalPython" /t REG_SZ /d "View in ColorTerminal (Python)" /f
reg add "HKCR\*\shell\ColorTerminalPython" /v "Icon" /t REG_SZ /d "%~dp0resources\Icon03.ico" /f
reg add "HKCR\*\shell\ColorTerminalPython" /v "AppliesTo" /t REG_SZ /d "System.FileName:\"*.txt\" OR System.FileName:\"*.log\"" /f

REM Get python path
set pythonpath=
for /f %%i in ('where python') do if not defined pythonpath set pythonpath=%%i

reg add "HKCR\*\shell\ColorTerminalPython\command" /t REG_SZ /d "\"%pythonpath%\" \"%~dp0colorterminal\" \"-c\" \"%%1\"" /f

echo *****
echo Adding environment variable CT_HOME_PYTHON:

REM TODO: Check if application exists in path

setx CT_HOME_PYTHON %~dp0

echo *************************************

pause