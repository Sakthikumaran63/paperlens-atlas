# PaperLens Offline Runner
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Starting PaperLens Application Locally " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$RepoRoot = Get-Location

# 1. Start Frontend Dev Server
Write-Host "`n[1/2] Starting Frontend (Vite) on http://localhost:5173 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\frontend'; npm run dev"

# 2. Start Backend FastAPI Server
Write-Host "[2/2] Starting Backend (FastAPI) on http://localhost:8000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot\backend'; $env:VITE_API_URL='http://localhost:8000/api/v1'; uvicorn app.main:app --reload --port 8000"

Write-Host "`n✓ PaperLens Offline Application Started!" -ForegroundColor Yellow
Write-Host "  Frontend:  http://localhost:5173" -ForegroundColor White
Write-Host "  Backend:   http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs:  http://localhost:8000/docs" -ForegroundColor White
