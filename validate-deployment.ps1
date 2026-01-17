# WildPass Deployment Validation Script
# Run this after deployment to verify the API is working

param(
    [string]$ApiUrl = "https://wildpass-api.onrender.com"
)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  WildPass API Deployment Validation" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Health Check
Write-Host "1. Testing Health Endpoint..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$ApiUrl/api/health" -Method GET
    Write-Host "   Status: $($health.status)" -ForegroundColor Green
    Write-Host "   Amadeus Enabled: $($health.amadeus_enabled)"
    Write-Host "   Dev Mode: $($health.dev_mode)"
    if ($health.amadeus_api_key_set -ne $null) {
        Write-Host "   API Key Set: $($health.amadeus_api_key_set)"
        Write-Host "   API Secret Set: $($health.amadeus_api_secret_set)"
    }
} catch {
    Write-Host "   FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test 2: Amadeus API Connection (if debug endpoint exists)
Write-Host "2. Testing Amadeus API Connection..." -ForegroundColor Yellow
try {
    $amadeusTest = Invoke-RestMethod -Uri "$ApiUrl/api/debug/amadeus-test" -Method GET
    Write-Host "   Status: $($amadeusTest.status)" -ForegroundColor $(if($amadeusTest.status -eq 'ok'){'Green'}else{'Red'})
    Write-Host "   Test Route: $($amadeusTest.route)"
    Write-Host "   Offers Found: $($amadeusTest.offers_found)"
    Write-Host "   Airlines Found: $($amadeusTest.airlines_found -join ', ')"
    if ($amadeusTest.sample_price) {
        Write-Host "   Sample Price: `$$($amadeusTest.sample_price)"
    }
    if ($amadeusTest.message -and $amadeusTest.status -ne 'ok') {
        Write-Host "   Error: $($amadeusTest.message)" -ForegroundColor Red
    }
} catch {
    Write-Host "   Endpoint not available or error: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""

# Test 3: Flight Search
Write-Host "3. Testing Flight Search..." -ForegroundColor Yellow
$searchBody = @{
    origins = @("DEN")
    destinations = @("PHX")
    tripType = "one-way"
    departureDate = (Get-Date).AddDays(30).ToString("yyyy-MM-dd")
} | ConvertTo-Json

try {
    $searchResult = Invoke-RestMethod -Uri "$ApiUrl/api/search" -Method POST -Body $searchBody -ContentType "application/json"
    Write-Host "   Flights Found: $($searchResult.count)" -ForegroundColor $(if($searchResult.count -gt 0){'Green'}else{'Yellow'})
    Write-Host "   Dev Mode: $($searchResult.devMode)"
    Write-Host "   Cached: $($searchResult.cached)"
    
    if ($searchResult.count -eq 0) {
        Write-Host ""
        Write-Host "   ⚠️  No flights returned!" -ForegroundColor Yellow
        Write-Host "   Possible causes:" -ForegroundColor Yellow
        Write-Host "   - Amadeus test credentials only return limited data"
        Write-Host "   - No Frontier flights available for this route/date"
        Write-Host "   - Try the debug endpoint for more info"
    } else {
        $firstFlight = $searchResult.flights[0]
        Write-Host "   Sample Flight: $($firstFlight.origin) -> $($firstFlight.destination)"
        Write-Host "   Price: $($firstFlight.currency)$($firstFlight.price)"
        Write-Host "   Airline: $($firstFlight.airline)"
    }
} catch {
    Write-Host "   FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test 4: Debug Search (if available)
Write-Host "4. Running Debug Search..." -ForegroundColor Yellow
$debugBody = @{
    origins = @("DEN")
    destinations = @("LAX")
    departureDate = (Get-Date).AddDays(30).ToString("yyyy-MM-dd")
} | ConvertTo-Json

try {
    $debugResult = Invoke-RestMethod -Uri "$ApiUrl/api/debug/search" -Method POST -Body $debugBody -ContentType "application/json"
    Write-Host "   Airlines Available (any carrier): $($debugResult.airlines_available -join ', ')" -ForegroundColor $(if($debugResult.airlines_available -contains 'F9'){'Green'}else{'Yellow'})
    Write-Host "   Steps:" -ForegroundColor White
    foreach ($step in $debugResult.steps) {
        Write-Host "     - $step"
    }
    if ($debugResult.errors.Count -gt 0) {
        Write-Host "   Errors:" -ForegroundColor Red
        foreach ($err in $debugResult.errors) {
            Write-Host "     - $err" -ForegroundColor Red
        }
    }
    
    if (-not ($debugResult.airlines_available -contains 'F9')) {
        Write-Host ""
        Write-Host "   ⚠️  Frontier (F9) NOT found in available airlines!" -ForegroundColor Yellow
        Write-Host "   This is likely why no flights are showing." -ForegroundColor Yellow
        Write-Host "   The Amadeus API may not have Frontier data for this route." -ForegroundColor Yellow
    }
} catch {
    Write-Host "   Debug endpoint not available: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Validation Complete" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps if no flights showing:" -ForegroundColor White
Write-Host "1. Check if Amadeus credentials are production (not test)"
Write-Host "2. Try enabling DEV_MODE=true for mock data"
Write-Host "3. Remove Frontier filter to see all airlines"
Write-Host "4. Check browser console (F12) for frontend errors"
