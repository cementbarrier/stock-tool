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
    echo [√] 独立 Python 已存在，跳过安装
    goto :install_deps
)

echo [1/3] 下载 Python 3.11.9...
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\python-3.11.9-amd64.exe' -UseBasicParsing"
if %ERRORLEVEL% neq 0 (
    echo [×] 下载失败，请检查网络连接
    pause
    exit /b 1
)

echo [2/3] 安装到项目 runtime 目录（静默安装）...
"%TEMP%\python-3.11.9-amd64.exe" /quiet InstallAllUsers=0 TargetDir="%RUNTIME_DIR%" Include_launcher=0 Include_test=0 Include_tcltk=1 Shortcuts=0
if %ERRORLEVEL% neq 0 (
    echo [×] 安装失败
    del "%TEMP%\python-3.11.9-amd64.exe"
    pause
    exit /b 1
)
del "%TEMP%\python-3.11.9-amd64.exe"
echo [√] Python 3.11.9 已安装到 runtime\

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
echo 打包: runtime\python.exe -m PyInstaller --onefile --windowed --name gui --add-data "backend;backend" --add-data "scripts;scripts" --hidden-import step1_fetch_videos --hidden-import step2_download_audio --hidden-import step3_transcribe --hidden-import step4_extract_stocks --hidden-import step5_analyze --hidden-import backend.config_manager --hidden-import backend.llm_client --hidden-import backend.single_parser --hidden-import backend.batch_parser --hidden-import backend.up_manager --hidden-import backend.single_summary_client --hidden-import backend.task_queue_manager --hidden-import backend.time_price_judge --hidden-import backend.valley_scheduler gui\build\gui.py
echo.
pause
