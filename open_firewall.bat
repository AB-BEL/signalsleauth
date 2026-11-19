@echo off
rem Lets other computers on your network reach the server. Right-click -> Run as administrator.
net session >nul 2>&1
if errorlevel 1 (
  echo Please right-click this file and choose "Run as administrator".
  pause
  exit /b 1
)
set "PORT=%~1"
if "%PORT%"=="" set "PORT=8000"
netsh advfirewall firewall delete rule name="Signal Sleuth" >nul 2>&1
netsh advfirewall firewall add rule name="Signal Sleuth" dir=in action=allow protocol=TCP localport=%PORT% profile=private,domain
echo.
echo Port %PORT% is now open for Private/Domain networks.
echo If your Wi-Fi is set to "Public", change it to "Private" in Windows network settings.
pause
