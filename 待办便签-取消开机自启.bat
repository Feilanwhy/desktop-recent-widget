@echo off
rem 待办便签：取消开机自启
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
if exist "%STARTUP%\待办便签.lnk" (
  del "%STARTUP%\待办便签.lnk"
  echo 已取消开机自启。
) else (
  echo 之前没有开启开机自启。
)
echo.
pause