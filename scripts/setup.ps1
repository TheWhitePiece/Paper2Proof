$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed" }
    }
    & .\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
    if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed" }
    & .\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
    if ($LASTEXITCODE -ne 0) { throw "Editable project installation failed" }
    if (-not (Test-Path -LiteralPath ".env")) {
        Copy-Item -LiteralPath ".env.example" -Destination ".env"
    }
    Push-Location apps/web
    try {
        npm.cmd ci --no-fund
        if ($LASTEXITCODE -ne 0) { throw "Frontend dependency installation failed" }
    } finally { Pop-Location }
    Write-Host "Development dependencies installed. No provider calls were made."
} finally { Pop-Location }
