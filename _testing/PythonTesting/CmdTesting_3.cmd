@echo off
echo TESTING

REM set pythonpath=<'where python'
set pythonpath=
for /f %%i in ('where python') do if not defined pythonpath set pythonpath=%%i

echo %pythonpath%

set pythonpath2=
for /f %%i in ('where python') do (
	set pythonpath2=%%i
	echo %%i
)

echo %pythonpath2%