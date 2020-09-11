@echo off
echo *************************************
echo ColorTerminal shell integration removal
echo *****
echo Removing following folders in registry:
echo "HKEY_CLASSES_ROOT\*\shell\ColorTerminal" (contains 3 keys)
echo "HKEY_CLASSES_ROOT\*\shell\ColorTerminal\command" (contains 1 key)

reg delete "HKCR\*\shell\ColorTerminal" /f

echo *****
echo Remove environment variable CT_HOME:

reg delete "HKCU\Environment" /f /v "CT_HOME"

echo *************************************

pause