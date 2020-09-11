echo OFF

pyinstaller --distpath build\dist --specpath build --workpath build\build --onedir --noconsole --add-data icons;icons --icon "resources\Icon03.ico" --clean colorterminal

REM Copy shell setup script
xcopy CT_exe_shell_integration_ADD.cmd build\dist\colorterminal
xcopy CT_exe_shell_integration_REMOVE.cmd build\dist\colorterminal

pause