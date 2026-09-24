@echo off
rem 开启开机自启：把小部件快捷方式放进 Windows 启动文件夹
cd /d "%~dp0"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
powershell -NoProfile -Command "=New-Object -ComObject WScript.Shell; =.CreateShortcut('%STARTUP%\桌面最近打开小部件.lnk'); .TargetPath='%~dp0start.bat'; .WorkingDirectory='%~dp0'; .IconLocation='%~dp0widget_icon.ico'; .Description='桌面最近打开小部件（开机自启）'; .Save()"
echo.
echo 已开启开机自启：以后每次开机，小部件会自动出现在桌面。
echo 想取消的话，双击「取消开机自启.bat」即可。
echo.
pause