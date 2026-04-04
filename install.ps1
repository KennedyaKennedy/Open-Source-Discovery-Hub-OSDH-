#Requires -Version 5.1

Write-Host "Open-Source Discovery Hub - Installer (PowerShell)" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

function Check-Command {
    param([string]$Name)
    return Get-Command $Name -ErrorAction SilentlyContinue
}

function Check-Python {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        $python = Get-Command python3 -ErrorAction SilentlyContinue
    }

    if (-not $python) {
        Write-Host "Error: Python 3.10+ is not installed." -ForegroundColor Red
        Write-Host "Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
        exit 1
    }

    $version = & $python.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    $major = [int]$version.Split('.')[0]
    $minor = [int]$version.Split('.')[1]

    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
        Write-Host "Error: Python 3.10+ is required (found $version)." -ForegroundColor Red
        exit 1
    }

    Write-Host "Python $version found." -ForegroundColor Green
    return $python.Source
}

function Check-Ollama {
    if (Check-Command ollama) {
        Write-Host "Ollama found." -ForegroundColor Green
        $models = & ollama list 2>$null
        if (-not ($models -match "phi3")) {
            Write-Host "Pulling phi3 model..." -ForegroundColor Yellow
            & ollama pull phi3
        }
    } else {
        Write-Host "Warning: Ollama not found. AI features will not work." -ForegroundColor Yellow
        Write-Host "Install Ollama: https://ollama.ai" -ForegroundColor Yellow
    }
}

$pythonPath = Check-Python
Check-Ollama

Write-Host ""
Write-Host "Setting up virtual environment..." -ForegroundColor Cyan
& $pythonPath -m venv .venv
& .\.venv\Scripts\Activate.ps1

Write-Host "Installing dependencies..." -ForegroundColor Cyan
& pip install -r requirements.txt

Write-Host "Creating directories..." -ForegroundColor Cyan
if (-not (Test-Path "data")) { New-Item -ItemType Directory -Path "data" }
if (-not (Test-Path "data\snapshots")) { New-Item -ItemType Directory -Path "data\snapshots" }
if (-not (Test-Path "data\cache")) { New-Item -ItemType Directory -Path "data\cache" }

if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from template..." -ForegroundColor Cyan
    Copy-Item .env.example .env
}

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To start the server:" -ForegroundColor Cyan
Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  python main.py" -ForegroundColor White
Write-Host ""
Write-Host "Or use Docker:" -ForegroundColor Cyan
Write-Host "  docker compose up -d" -ForegroundColor White
Write-Host ""
Write-Host "CLI usage:" -ForegroundColor Cyan
Write-Host "  python cli.py --help" -ForegroundColor White
