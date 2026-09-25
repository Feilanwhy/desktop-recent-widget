@echo off
rem 待办便签：开启开机自启
cd /d "%~dp0"
set "PYW="
for %%D in ("D:\Python313" "D:\Python312" "C:\Python313" "C:\Python312" "%LOCALAPPDATA%\Programs\Python\Python313" "%LOCALAPPDATA%\Programs\Python\Python312") do (
  if not defined PYW if exist "%%~D\pythonw.exe" set "PYW=%%~D\pythonw.exe"
)
if not defined PYW for /f "delims=" %%i in ('where pythonw 2^>nul') do if not defined PYW set "PYW=%%i"
if not defined PYW set "PYW=pythonw"
powershell -NoProfile -Command "=New-Object -ComObject WScript.Shell; =.CreateShortcut('%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\待办便签.lnk'); .TargetPath='%PYW%'; .Arguments='todo_widget.py'; .WorkingDirectory='%~dp0'; .IconLocation='%~dp0widget_icon.ico'; .Description='待办便签（开机自启）'; .Save()"
echo.
echo 已开启开机自启（使用 Python: %PYW%）
echo 想取消就双击「待办便签-取消开机自启.bat」。
echo.
pause