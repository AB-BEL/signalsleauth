@echo off
setlocal
cd /d "%~dp0"
echo ==============================================
echo  Signal Sleuth - PC server setup (run once)
echo ==============================================
echo.

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo Python 3.10 or newer was not found.
  echo Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  %PY% -m venv .venv
  if errorlevel 1 ( echo Could not create the virtual environment. & pause & exit /b 1 )
)
call ".venv\Scripts\activate.bat"

echo Installing packages (needs internet, one time)...
python -m pip install --upgrade pip >nul
pip install -r requirements-pc.txt
if errorlevel 1 ( echo Package installation failed. & pause & exit /b 1 )

echo.
echo Make sure MariaDB or MySQL is installed and running (see docs\PC_SERVER.md, step 1).
echo.
set "SEED="
set /p "SEED=Load the sample student ID list from database\seed? (y/N): "
if /i "%SEED%"=="y" (
  python scripts\pc_setup.py --seed-ids
) else (
  python scripts\pc_setup.py
)
if errorlevel 1 ( echo. & echo Setup did not finish. Fix the message above and run this file again. & pause & exit /b 1 )

echo.
echo Next: double-click open_firewall.bat once (as Administrator), then start_server.bat
pause
