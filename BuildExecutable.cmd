pyinstaller --distpath build\dist --specpath build --workpath build\build --onefile --noconsole --add-data "..\resources;resources" --icon "..\resources\Icon03.ico" --name "ColorTerminal" --clean "colorterminal\__main__.py"

REM Copy appdata folder content
xcopy appdata build\dist\appdata /I

@pause