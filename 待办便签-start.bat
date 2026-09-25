@echo off
rem ´ý°ì±ãÇ©Æô¶¯½Å±¾
cd /d "%~dp0"
set "PYW="
for %%D in ("D:\Python313" "D:\Python312" "C:\Python313" "C:\Python312" "%LOCALAPPDATA%\Programs\Python\Python313" "%LOCALAPPDATA%\Programs\Python\Python312") do (
  if not defined PYW if exist "%%~D\pythonw.exe" set "PYW=%%~D\pythonw.exe"
)
if not defined PYW for /f "delims=" %%i in ('where pythonw 2^>nul') do if not defined PYW set "PYW=%%i"
if not defined PYW set "PYW=pythonw"
start "" "%PYW%" "%~dp0todo_widget.py"