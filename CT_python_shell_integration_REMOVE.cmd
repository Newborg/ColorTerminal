@echo off
echo *************************************
echo ColorTerminal shell integration removal
echo *****
echo Removing following folders in registry:
echo "HKEY_CLASSES_ROOT\*\shell\ColorTerminalPython" (contains 3 keys)
echo "HKEY_CLASSES_ROOT\*\shell\ColorTerminalPython\command" (contains 1 key)

reg delete "HKCR\*\shell\ColorTerminalPython" /f

echo *****
echo Remove environment variable CT_HOME_PYTHON:

reg delete "HKCU\Environment" /f /v CT_HOME_PYTHON

echo *************************************

pause