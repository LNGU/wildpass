# WildPass Remote Access Startup Script
# This script starts the backend, frontend, and Cloudflare tunnels for remote access

Write-Host "🚀 Starting WildPass with Remote Access..." -ForegroundColor Cyan

# Configuration - Update these after creating your tunnel
$TUNNEL_NAME = "wildpass"  # Your Cloudflare tunnel name

# Start the Python backend
Write-Host "`n📡 Starting Backend API on port 5001..." -ForegroundColor Yellow
$backendJob = Start-Job -ScriptBlock {
    Set-Location $using:PSScriptRoot\backend
    if (Test-Path "venv\Scripts\Activate.ps1") {
        & .\venv\Scripts\Activate.ps1
    }
    python app.py
}

# Wait for backend to start
Start-Sleep -Seconds 3

# Start the React frontend
Write-Host "🌐 Starting React Frontend on port 3000..." -ForegroundColor Yellow
$frontendJob = Start-Job -ScriptBlock {
    Set-Location $using:PSScriptRoot
    npm start
}

# Wait for frontend to start
Start-Sleep -Seconds 5

# Start Cloudflare tunnel for backend API
Write-Host "`n☁️ Starting Cloudflare Tunnel for Backend (API)..." -ForegroundColor Magenta
$tunnelBackendJob = Start-Job -ScriptBlock {
    cloudflared tunnel --url http://localhost:5001
}

# Start Cloudflare tunnel for frontend
Write-Host "☁️ Starting Cloudflare Tunnel for Frontend (Web UI)..." -ForegroundColor Magenta
$tunnelFrontendJob = Start-Job -ScriptBlock {
    cloudflared tunnel --url http://localhost:3000
}

Write-Host "`n✅ WildPass is starting up!" -ForegroundColor Green
Write-Host "Please wait for the tunnel URLs to appear..." -ForegroundColor White
Write-Host "`nPress Ctrl+C to stop all services`n" -ForegroundColor Gray

# Display tunnel URLs as they become available
Start-Sleep -Seconds 10
Write-Host "`n📋 Check the terminal output above for your public URLs" -ForegroundColor Cyan
Write-Host "   They will look like: https://xxxxx.trycloudflare.com" -ForegroundColor White

# Keep script running and show output
try {
    while ($true) {
        Receive-Job $tunnelBackendJob -Keep 2>&1 | Where-Object { $_ -match "trycloudflare.com" } | ForEach-Object {
            Write-Host "🔗 Backend API URL: $_" -ForegroundColor Green
        }
        Receive-Job $tunnelFrontendJob -Keep 2>&1 | Where-Object { $_ -match "trycloudflare.com" } | ForEach-Object {
            Write-Host "🔗 Frontend URL: $_" -ForegroundColor Green
        }
        Start-Sleep -Seconds 5
    }
}
finally {
    # Cleanup on exit
    Write-Host "`n🛑 Stopping all services..." -ForegroundColor Red
    Stop-Job $backendJob, $frontendJob, $tunnelBackendJob, $tunnelFrontendJob -ErrorAction SilentlyContinue
    Remove-Job $backendJob, $frontendJob, $tunnelBackendJob, $tunnelFrontendJob -ErrorAction SilentlyContinue
}
