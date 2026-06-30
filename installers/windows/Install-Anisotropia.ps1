#Requires -Version 5.1
# Directional_Anisotropy - Windows one-click installer (PowerShell)

$ErrorActionPreference = 'Stop'
$InstallerRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$ProjectRoot = (Resolve-Path (Join-Path $InstallerRoot '..\..')).Path

. (Join-Path $InstallerRoot 'config.ps1')
. (Join-Path $InstallerRoot 'lib\InstallerHelpers.ps1')

$cfg = $script:AnisotropiaConfig
$VenvDir = Join-Path $ProjectRoot $cfg.VenvFolder
$script:InstallLogPath = Join-Path $ProjectRoot 'install.log'

Set-Location $ProjectRoot
$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = 'false'

Write-Host ''
Write-Host '========================================' -ForegroundColor Cyan
Write-Host "  $($cfg.AppName) - Installer" -ForegroundColor Cyan
Write-Host "  $($cfg.GitHubRepoUrl)" -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan
Write-Host "  Project: $ProjectRoot"
Write-Host ''

try {
    Write-InstallLog 'Checking for Python 3.10-3.12...'
    $py = Find-ExistingPython
    if (-not $py) {
        $py = Install-PythonIfNeeded
    }
    if (-not $py) {
        throw 'Python 3.10 or newer is required and was not found.'
    }
    Write-InstallLog "Using Python: $($py.Exe)$(if ($py.Arg) { ' ' + $py.Arg })"

    $venvPython = Initialize-ProjectVenv -Py $py -ProjectRoot $ProjectRoot -VenvDir $VenvDir
    Write-StartLauncherBat -ProjectRoot $ProjectRoot

    Write-Host ''
    Write-Host 'SUCCESS - Installation complete.' -ForegroundColor Green
    Write-Host "  Log: $script:InstallLogPath"
    Write-Host "  Run again later: $($cfg.StartBatName)"
    Write-Host ''

    START-Directional-AnisotropyApp -VenvPython $venvPython -ProjectRoot $ProjectRoot
}
catch {
    Write-InstallLog $_.Exception.Message 'ERROR'
    if ($_.ScriptStackTrace) { Write-InstallLog $_.ScriptStackTrace 'ERROR' }
    Write-Host ''
    Write-Host 'INSTALLATION FAILED.' -ForegroundColor Red
    Write-Host $_.Exception.Message
    Write-Host "Log: $script:InstallLogPath"
    exit 1
}
