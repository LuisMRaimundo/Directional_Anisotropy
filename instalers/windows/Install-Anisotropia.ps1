# Anisotropia Direcional — Windows one-click installer (PowerShell)
# Installs Python if needed, creates .venv, installs deps, launches Streamlit.

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$VenvDir = Join-Path $ProjectRoot ".venv"
$ReqFile = Join-Path $ProjectRoot "requirements-app.txt"
$AppFile = Join-Path $ProjectRoot "Anisotropia.py"
$MinVersion = [version]"3.10.0"

Set-Location $ProjectRoot
$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"

function Write-Step([string]$Msg) {
    Write-Host ""
    Write-Host "==> $Msg" -ForegroundColor Cyan
}

function Test-PythonVersion([string]$Exe) {
    try {
        $out = & $Exe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null
        if (-not $out) { return $null }
        return [version]$out.Trim()
    } catch {
        return $null
    }
}

function Find-Python {
    $candidates = @(
        "py -3.12", "py -3.11", "py -3.10",
        "python3.12", "python3.11", "python3.10",
        "python3", "python"
    )
    foreach ($cmd in $candidates) {
        $parts = $cmd -split " ", 2
        $base = $parts[0]
        $arg = if ($parts.Count -gt 1) { $parts[1] } else { $null }
        if (-not (Get-Command $base -ErrorAction SilentlyContinue)) { continue }
        try {
            if ($arg) {
                $ver = & $base $arg -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null
                if ($ver -and ([version]$ver.Trim() -ge $MinVersion)) {
                    return @{ Exe = $base; Arg = $arg; Version = [version]$ver.Trim() }
                }
            } else {
                $ver = Test-PythonVersion $base
                if ($ver -and ($ver -ge $MinVersion)) {
                    return @{ Exe = $base; Arg = $null; Version = $ver }
                }
            }
        } catch { }
    }
    return $null
}

function Install-PythonWinget {
    Write-Step "Python 3.10+ not found. Installing via winget (may take a few minutes)..."
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget is not available. Install Python 3.10+ from https://www.python.org/downloads/ then run this installer again."
    }
    $ids = @("Python.Python.3.12", "Python.Python.3.11", "Python.Python.3.10")
    foreach ($id in $ids) {
        Write-Host "Trying $id ..."
        winget install -e --id $id --accept-package-agreements --accept-source-agreements --silent 2>&1 | Out-Host
        if ($LASTEXITCODE -eq 0) { return }
    }
    throw "winget could not install Python. Install manually from https://www.python.org/downloads/"
}

function Invoke-Python([hashtable]$Py, [string[]]$PythonArgs) {
    if ($Py.Arg) {
        & $Py.Exe $Py.Arg @PythonArgs
    } else {
        & $Py.Exe @PythonArgs
    }
}

Write-Host ""
Write-Host "  Anisotropia Direcional — Windows installer" -ForegroundColor Green
Write-Host "  Project: $ProjectRoot"
Write-Host ""

Write-Step "Checking for Python 3.10+..."
$py = Find-Python
if (-not $py) {
    Install-PythonWinget
    # Refresh PATH for current session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
    $py = Find-Python
    if (-not $py) {
        throw "Python was installed but is not on PATH. Close this window, open a new one, and run INSTALL-WINDOWS.bat again."
    }
}
Write-Host "Using Python $($py.Version) ($($py.Exe)$(if ($py.Arg) { ' ' + $py.Arg }))"

Write-Step "Creating virtual environment (.venv)..."
if (-not (Test-Path $VenvDir)) {
    Invoke-Python $py @("-m", "venv", $VenvDir)
}

$venvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Virtual environment failed at $VenvDir"
}

Write-Step "Installing dependencies (first time may take 5–15 minutes)..."
& $venvPython -m pip install --upgrade pip wheel setuptools 2>&1 | Out-Host
& $venvPython -m pip install -r $ReqFile 2>&1 | Out-Host

Write-Step "Writing START-Anisotropia.bat launcher..."
$startBat = @"
@echo off
cd /d "%~dp0"
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
if not exist ".venv\Scripts\python.exe" (
    echo Run INSTALL-WINDOWS.bat first.
    pause
    exit /b 1
)
echo Starting Anisotropia Direcional...
echo Close this window to stop the app.
".venv\Scripts\python.exe" -m streamlit run Anisotropia.py
pause
"@
Set-Content -Path (Join-Path $ProjectRoot "START-Anisotropia.bat") -Value $startBat -Encoding ASCII

Write-Step "Starting Anisotropia (browser should open)..."
Write-Host "To run again later, double-click START-Anisotropia.bat"
Write-Host ""
& $venvPython -m streamlit run $AppFile
