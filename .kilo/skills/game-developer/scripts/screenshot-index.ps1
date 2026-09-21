param(
  [Parameter(Mandatory = $true)][string]$ProjectPath,
  [Parameter(Mandatory = $true)][string]$File,
  [Parameter(Mandatory = $true)][string]$Phase,
  [string]$Expected = "",
  [string]$Pass = "yes"
)

$ErrorActionPreference = "Stop"
$dir = Join-Path $ProjectPath "screenshots"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$index = Join-Path $dir "000-index.md"
if (-not (Test-Path -LiteralPath $index)) {
  @(
    "# Screenshots",
    "",
    "| file | phase | expected | pass |",
    "|---|---|---|---|"
  ) | Set-Content -LiteralPath $index -Encoding utf8
}
Add-Content -LiteralPath $index -Value "| $File | $Phase | $Expected | $Pass |" -Encoding utf8
Write-Host "indexed $File"
