# WildPass Launcher
# Starts backend and opens web app in default browser

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "WildPass Launcher"

Write-Host "🚀 Starting WildPass..." -ForegroundColor Cyan
Write-Host ""

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Check if dependencies exist
if (-not (Test-Path "backend\venv\Scripts\python.exe")) {
    Write-Host "Error: Python virtual environment not found!" -ForegroundColor Red
    Write-Host "Run: cd backend; python -m venv venv; .\venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
    pause
    exit 1
}

if (-not (Test-Path "build\index.html")) {
    Write-Host "Building React frontend..." -ForegroundColor Yellow
    npm run build
}

# Start backend
Write-Host "Starting Python backend..." -ForegroundColor Green
$backendProcess = Start-Process -FilePath "backend\venv\Scripts\python.exe" -ArgumentList "app.py" -WorkingDirectory "backend" -WindowStyle Hidden -PassThru

Start-Sleep -Seconds 3

# Check if backend started
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5001/api/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "Backend running on http://localhost:5001" -ForegroundColor Green
} catch {
    Write-Host "Backend failed to start" -ForegroundColor Red
    Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
    pause
    exit 1
}

# Start simple HTTP server for frontend
Write-Host "Starting web server..." -ForegroundColor Green
$serverProcess = Start-Process -FilePath "python" -ArgumentList "-m", "http.server", "3000", "--directory", "build" -WindowStyle Hidden -PassThru

Start-Sleep -Seconds 2

# Open browser
Write-Host "Opening WildPass in your browser..." -ForegroundColor Cyan
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "WildPass is running!" -ForegroundColor Green
Write-Host "   Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "   Backend:  http://localhost:5001" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop all services..." -ForegroundColor Yellow

# Wait for Ctrl+C
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host ""
    Write-Host "Stopping WildPass..." -ForegroundColor Yellow
    Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped" -ForegroundColor Green
}
