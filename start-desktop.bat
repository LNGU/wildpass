@echo off
echo Starting WildPass Desktop App...
echo.

REM Check if Node modules exist
if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
)

REM Kill any existing processes
echo Cleaning up existing processes...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq WildPass Backend*" >nul 2>&1
taskkill /F /IM node.exe /FI "WINDOWTITLE eq WildPass Frontend*" >nul 2>&1

REM Start backend in new window
echo Starting backend server...
start "WildPass Backend" cmd /k "cd backend && venv\Scripts\python.exe app.py"

REM Wait for backend to start
timeout /t 5 /nobreak > nul

REM Start React dev server and Electron together
echo Starting frontend and desktop app...
call npm run electron-dev

echo.
echo Desktop app closed.
pause
