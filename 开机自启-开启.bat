@echo off
rem 开启开机自启：把快捷方式放进 Windows 启动文件夹
cd /d "%~dp0"
set "PYW="
rem 1) 优先找用户自己安装的 Python（常见位置）
for %%D in ("D:\Python313" "D:\Python312" "C:\Python313" "C:\Python312" "%LOCALAPPDATA%\Programs\Python\Python313" "%LOCALAPPDATA%\Programs\Python\Python312") do (
  if not defined PYW if exist "%%~D\pythonw.exe" set "PYW=%%~D\pythonw.exe"
)
rem 2) 找不到就按 PATH 探测
if not defined PYW for /f "delims=" %%i in ('where pythonw 2^>nul') do if not defined PYW set "PYW=%%i"
if not defined PYW set "PYW=pythonw"
powershell -NoProfile -Command "=New-Object -ComObject WScript.Shell; =.CreateShortcut('%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\桌面最近打开小部件.lnk'); .TargetPath='%PYW%'; .Arguments='main.py'; .WorkingDirectory='%~dp0'; .IconLocation='%~dp0widget_icon.ico'; .Description='桌面最近打开小部件（开机自启）'; .Save()"
echo.
echo 已开启开机自启（使用 Python: %PYW%）
echo 以后每次开机，小部件会自动出现在桌面。
echo 想取消就双击「取消开机自启.bat」。
echo.
pause