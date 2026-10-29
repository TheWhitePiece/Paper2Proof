$ErrorActionPreference = "Stop"
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    & .\.venv\Scripts\python.exe -m ruff check .
    if ($LASTEXITCODE -ne 0) { throw "Python lint failed" }
    & .\.venv\Scripts\python.exe -m ruff format --check .
    if ($LASTEXITCODE -ne 0) { throw "Python formatting failed" }
    & .\.venv\Scripts\python.exe -m pytest
    if ($LASTEXITCODE -ne 0) { throw "Python tests failed" }
    Push-Location apps/web
    try {
        npm.cmd run typecheck
        if ($LASTEXITCODE -ne 0) { throw "TypeScript check failed" }
        npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend production build failed" }
    } finally { Pop-Location }
} finally { Pop-Location }
