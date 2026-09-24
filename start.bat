@echo off
rem 桌面玻璃小部件启动脚本
cd /d "%~dp0"

set "PY=pythonw"
where pythonw >nul 2>nul || set "PY=pyw"
where %PY% >nul 2>nul || set "PY=python"

start "" %PY% "%~dp0main.py"
