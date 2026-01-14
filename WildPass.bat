@echo off
title WildPass
echo Starting WildPass...
echo.

REM Run the PowerShell launcher
powershell.exe -ExecutionPolicy Bypass -File "%~dp0launch-wildpass.ps1"

pause
