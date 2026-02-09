# KSP RAG System - Windows setup script
# Run in PowerShell: .\setup.ps1
# (English messages to avoid console encoding issues on Windows)

$ErrorActionPreference = "Stop"

Write-Host "KSP RAG System - Setup" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path ".env.local")) {
    Write-Host "Creating .env.local ..." -ForegroundColor Yellow
    Copy-Item ".env.local.example" ".env.local"
    Write-Host ".env.local created." -ForegroundColor Green
    Write-Host ""
    Write-Host "Important: Edit .env.local and set LLM_API_KEY (OpenAI API key)." -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host ".env.local already exists." -ForegroundColor Green
}

if (-not (Test-Path ".env.server")) {
    Write-Host "Creating .env.server ..." -ForegroundColor Yellow
    Copy-Item ".env.server.example" ".env.server"
    Write-Host ".env.server created." -ForegroundColor Green
} else {
    Write-Host ".env.server already exists." -ForegroundColor Green
}

Write-Host ""
Write-Host "Setup done!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Set LLM_API_KEY in .env.local"
Write-Host "2. docker compose build app"
Write-Host "3. See docs/WINDOWS.md for run commands"
Write-Host ""
