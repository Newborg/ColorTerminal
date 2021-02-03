echo OFF

pyinstaller --distpath build\dist --specpath build --workpath build\build --onedir --noconsole --add-data "..\resources;resources" --icon "..\resources\Icon03.ico" --name "ColorTerminal" --clean "colorterminal\__main__.py"

REM Copy shell setup script
xcopy CT_exe_shell_integration_ADD.cmd build\dist\ColorTerminal
xcopy CT_exe_shell_integration_REMOVE.cmd build\dist\ColorTerminal

REM Copy appdata folder content
xcopy appdata build\dist\ColorTerminal\appdata /I

pause