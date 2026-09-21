param(
  [Parameter(Mandatory = $true)][string]$Url,
  [Parameter(Mandatory = $true)][string]$OutDir,
  [string]$Name = ""
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
if (-not $Name) { $Name = [IO.Path]::GetFileName(($Url -split '\?')[0]) }
$dest = Join-Path $OutDir $Name
Write-Host "GET $Url"
Invoke-WebRequest -Uri $Url -OutFile $dest -UseBasicParsing -UserAgent "GameDeveloperSkill/1.0"
if ($dest -match '\.zip$') {
  $extract = Join-Path $OutDir ([IO.Path]::GetFileNameWithoutExtension($Name))
  Expand-Archive -LiteralPath $dest -DestinationPath $extract -Force
  Write-Host "unzip $extract"
}
Write-Host "OK $dest"
Write-Host "ledger: $Name | kenney-or-cc0 | CC0 | $dest"
