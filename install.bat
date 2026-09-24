@echo off
rem 一键安装依赖：给朋友用的（需要网络，约 2-3 分钟）
cd /d "%~dp0"
echo ================================================
echo   正在安装依赖 PySide6，请稍候（需联网）...
echo ================================================
python -m pip install PySide6 --disable-pip-version-check
if %errorlevel%==0 (
    echo.
    echo  安装成功！双击 start.bat 即可启动小部件。
    echo  提示：小部件启动后没有窗口，只在桌面右上角显示。
) else (
    echo.
    echo  安装失败。请检查：
    echo   1. 是否已安装 Python（官网 python.org 下载，安装时勾选 Add to PATH）
    echo   2. 网络是否可用
    echo   装好 Python 后重新运行本脚本即可。
)
echo.
pause
