# GuessTheCountry - Local Development Runner
# Run this script to start both backend and frontend

Write-Host "================================" -ForegroundColor Green
Write-Host "Guess the Country - Local Dev Setup" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""

# Check if terminals are available
Write-Host "This script will start the backend and frontend." -ForegroundColor Yellow
Write-Host "You need TWO terminal windows open:" -ForegroundColor Yellow
Write-Host ""

Write-Host "STEP 1: Backend Setup" -ForegroundColor Cyan
Write-Host "=====================" -ForegroundColor Cyan
Write-Host "Run this in Terminal 1:" -ForegroundColor White
Write-Host "cd c:\Users\JosepNoguer\Desktop\guess_the_country\backend" -ForegroundColor Gray
Write-Host ".\venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "python -m uvicorn app.main:app --reload" -ForegroundColor Gray
Write-Host ""

Write-Host "STEP 2: Frontend Setup" -ForegroundColor Cyan
Write-Host "=====================" -ForegroundColor Cyan
Write-Host "Run this in Terminal 2:" -ForegroundColor White
Write-Host "cd c:\Users\JosepNoguer\Desktop\guess_the_country\frontend" -ForegroundColor Gray
Write-Host "npm run dev" -ForegroundColor Gray
Write-Host ""

Write-Host "STEP 3: Open Browser" -ForegroundColor Cyan
Write-Host "===================" -ForegroundColor Cyan
Write-Host "Once both are running, open:" -ForegroundColor White
Write-Host "http://localhost:5173" -ForegroundColor Cyan
Write-Host ""

Write-Host "OPTIONAL: Generate Full Game Data" -ForegroundColor Magenta
Write-Host "=================================" -ForegroundColor Magenta
Write-Host "To generate all ~195 countries (takes ~5 minutes):" -ForegroundColor White
Write-Host "cd c:\Users\JosepNoguer\Desktop\guess_the_country\backend" -ForegroundColor Gray
Write-Host ".\venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "python -m pipeline.build" -ForegroundColor Gray
Write-Host ""

Write-Host "Press any key to continue..." -ForegroundColor Yellow
Read-Host
