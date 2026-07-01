@echo off
echo ==============================
echo   Remote Terminal Server
echo   Windows Build Script
echo ==============================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found
    pause
    exit /b 1
)

REM 安装依赖
echo Installing dependencies...
pip install flet flask flask-cors psutil Pillow pyinstaller -q

REM 获取flet路径
for /f "tokens=*" %%i in ('python -c "import flet; import os; print(os.path.dirname(flet.__file__))"') do set FLET_PATH=%%i

echo Building...
pyinstaller --onefile --name remote-terminal-server --add-data "%FLET_PATH%;flet" main.py

echo.
echo Build complete: dist\remote-terminal-server.exe
pause
