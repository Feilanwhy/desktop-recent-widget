@echo off
rem 取消开机自启：删除启动文件夹里的快捷方式
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
if exist "%STARTUP%\桌面最近打开小部件.lnk" (
  del "%STARTUP%\桌面最近打开小部件.lnk"
  echo 已取消开机自启。
) else (
  echo 之前没有开启开机自启。
)
echo.
pause