@echo off
echo *************************************
echo ColorTerminal shell integration setup
echo *****
echo Adding following folders in registry:
echo "HKEY_CLASSES_ROOT\*\shell\ColorTerminal" (contains 3 keys)
echo "HKEY_CLASSES_ROOT\*\shell\ColorTerminal\command" (contains 1 key)

reg add "HKCR\*\shell\ColorTerminal" /t REG_SZ /d "View in ColorTerminal" /f
reg add "HKCR\*\shell\ColorTerminal" /v "Icon" /t REG_SZ /d "%~dp0ColorTerminal.exe,0" /f
reg add "HKCR\*\shell\ColorTerminal" /v "AppliesTo" /t REG_SZ /d "System.FileName:\"*.txt\" OR System.FileName:\"*.log\"" /f

reg add "HKCR\*\shell\ColorTerminal\command" /t REG_SZ /d "\"%~dp0ColorTerminal.exe\" \"%%1\"" /f

echo *****
echo Adding environment variable CT_HOME:

REM TODO: Check if application exists in path

setx CT_HOME %~dp0

echo *************************************

pause