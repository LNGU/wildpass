@echo off
echo Starting WildPass Desktop App...
echo.

REM Check if Node modules exist
if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
)

REM Start backend in new window
echo Starting backend server...
start "WildPass Backend" cmd /k "cd backend && venv\Scripts\python.exe app.py"

REM Wait a bit for backend to start
timeout /t 3 /nobreak > nul

REM Start React dev server in new window
echo Starting frontend server...
start "WildPass Frontend" cmd /k "set BROWSER=none && npm start"

REM Wait for frontend to compile
timeout /t 10 /nobreak > nul

REM Launch Electron
echo Launching desktop app...
call npx electron .

echo.
echo Desktop app closed.
pause
