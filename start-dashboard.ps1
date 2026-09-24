# GameDeveloperSkill console. No web server.
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python non trovato. Serve Python 3.10 o successivo."
    exit 1
}

python (Join-Path $PSScriptRoot "game-developer\tools\tui\gds_tui.py")
