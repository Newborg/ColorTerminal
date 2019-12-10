@echo off
echo TESTING
IF "%1" NEQ "" (
	echo %1
) ELSE (
	echo No input
)

python %ColorTerminalPath%\_testing\PythonTesting\PythonTest.py

pause