# BotFatir launcher for Windows (when `python` is not in PATH)
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Find-Python {
    $candidates = @(
        "python",
        "py",
        "$env:LOCALAPPDATA\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.10_qbz5n2kfra8p0\python.exe",
        "$env:LOCALAPPDATA\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"
    )
    foreach ($c in $candidates) {
        if ($c -eq "python" -or $c -eq "py") {
            $cmd = Get-Command $c -ErrorAction SilentlyContinue
            if ($cmd) { return $cmd.Source }
        } elseif (Test-Path $c) {
            return $c
        }
    }
    throw "Python not found. Install from https://www.python.org/downloads/ (check Add to PATH)."
}

$Python = Find-Python
Write-Host "Python: $Python" -ForegroundColor Green

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    & $Python -m venv .venv
    & ".venv\Scripts\python.exe" -m pip install --upgrade pip
    & ".venv\Scripts\pip.exe" install -r requirements.txt
    & ".venv\Scripts\pip.exe" install -e .
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env - fill TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID" -ForegroundColor Yellow
    notepad .env
    exit 0
}

Write-Host "Starting bot..." -ForegroundColor Green
& ".venv\Scripts\python.exe" -m botfatir
