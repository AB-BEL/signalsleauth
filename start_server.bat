@echo off
cd /d "%~dp0"
title Signal Sleuth PC server
if not exist ".venv\Scripts\python.exe" (
  echo Run setup_windows.bat first.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
python pc_server.py
echo.
echo The server has stopped.
pause
