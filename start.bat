@echo off
rem 桌面玻璃小部件启动脚本
cd /d "%~dp0"
set "PYW="
rem 1) 优先找用户自己安装的 Python（常见位置）
for %%D in ("D:\Python313" "D:\Python312" "C:\Python313" "C:\Python312" "%LOCALAPPDATA%\Programs\Python\Python313" "%LOCALAPPDATA%\Programs\Python\Python312") do (
  if not defined PYW if exist "%%~D\pythonw.exe" set "PYW=%%~D\pythonw.exe"
)
rem 2) 找不到就按 PATH 探测
if not defined PYW for /f "delims=" %%i in ('where pythonw 2^>nul') do if not defined PYW set "PYW=%%i"
rem 3) 兜底
if not defined PYW set "PYW=pythonw"
start "" "%PYW%" "%~dp0main.py"