echo OFF

pyinstaller --distpath build\dist --specpath build --workpath build\build --onedir --noconsole --add-data ..\icons;icons --icon "..\icons\Icon03.ico" --clean ColorTerminal.py

REM Copy shell setup script
xcopy CT_exe_shell_integration.cmd build\dist\ColorTerminal

pause