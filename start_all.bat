@echo off
cd /d "%~dp0"
rem Starts the server and the internet tunnel, each in its own window.
start "Signal Sleuth server" cmd /k start_server.bat
timeout /t 6 /nobreak >nul
start "Signal Sleuth tunnel" cmd /k start_tunnel.bat
