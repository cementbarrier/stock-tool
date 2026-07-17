@echo off
cd /d E:\stock-tool
python fixed_generator.py sidebar.json firstFrame.json secondFrame.json
echo.
echo Build complete. Run: python gui\build\gui.py
pause
