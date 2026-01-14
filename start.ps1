# WildPass Desktop Launcher
Write-Host "Starting WildPass Desktop App..." -ForegroundColor Green
Write-Host ""

# Navigate to project directory
Set-Location "C:\Users\lngu1\OneDrive\wildpass"

# Check if backend is already running
$backendRunning = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*wildpass\backend\venv*" }
if (-not $backendRunning) {
    Write-Host "Starting backend server..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd C:\Users\lngu1\OneDrive\wildpass\backend; .\venv\Scripts\python.exe app.py" -WindowStyle Minimized
    Start-Sleep -Seconds 3
} else {
    Write-Host "Backend already running" -ForegroundColor Green
}

# Check if frontend is already running
$port3000 = Test-NetConnection -ComputerName localhost -Port 3000 -InformationLevel Quiet -WarningAction SilentlyContinue
if (-not $port3000) {
    Write-Host "Starting frontend server..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd C:\Users\lngu1\OneDrive\wildpass; `$env:BROWSER='none'; npm start" -WindowStyle Minimized
    Write-Host "Waiting for frontend to compile..." -ForegroundColor Yellow
    Start-Sleep -Seconds 12
} else {
    Write-Host "Frontend already running" -ForegroundColor Green
}

# Launch Electron
Write-Host "Launching desktop window..." -ForegroundColor Cyan
& node_modules\.bin\electron.cmd .

Write-Host ""
Write-Host "Desktop app closed." -ForegroundColor Yellow
