@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================
echo   Stock Tool - 环境初始化
echo ============================================
echo.

set "PROJECT_DIR=%~dp0"
set "RUNTIME_DIR=%PROJECT_DIR%runtime"

:: 检查 runtime 目录是否已存在
if exist "%RUNTIME_DIR%\python.exe" (
    echo [√] 独立 Python 已存在，跳过下载
    goto :install_deps
)

echo [1/3] 下载 Python 3.11.9 独立运行环境...
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip' -OutFile '%RUNTIME_DIR%.zip' -UseBasicParsing"
if %ERRORLEVEL% neq 0 (
    echo [×] 下载失败，请检查网络连接
    pause
    exit /b 1
)

echo [2/3] 解压...
powershell -Command "Expand-Archive -Force '%RUNTIME_DIR%.zip' -DestinationPath '%RUNTIME_DIR%'"
del "%RUNTIME_DIR%.zip"

:: 配置 site-packages 和 pip
echo import site >> "%RUNTIME_DIR%\python311._pth"
echo Lib\site-packages >> "%RUNTIME_DIR%\python311._pth"

:: 下载并安装 pip
powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%RUNTIME_DIR%\get-pip.py' -UseBasicParsing"
"%RUNTIME_DIR%\python.exe" "%RUNTIME_DIR%\get-pip.py" -q
del "%RUNTIME_DIR%\get-pip.py"

echo [√] Python 独立环境就绪

:install_deps
echo [3/3] 安装项目依赖...
"%RUNTIME_DIR%\python.exe" -m pip install -r "%PROJECT_DIR%requirements.txt" -q
if %ERRORLEVEL% neq 0 (
    echo [×] 依赖安装失败
    pause
    exit /b 1
)

echo.
echo [√] 环境初始化完成！
echo.
echo 打包命令: runtime\python.exe -m PyInstaller --onefile --windowed --name gui --add-data "backend;backend" gui\build\gui.py
echo.
pause
