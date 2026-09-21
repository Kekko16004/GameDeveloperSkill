param(
  [Parameter(Mandatory = $true)][string]$ProjectPath,
  [switch]$IncludeDungeon,
  [switch]$IncludeAudio
)

$ErrorActionPreference = "Stop"
$SkillRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$kitScript = Join-Path $SkillRoot "scripts\fetch-cc0-kits.ps1"

if (Test-Path -LiteralPath $kitScript) {
  $genre = if ($IncludeDungeon) { "dungeon" } else { "medieval" }
  & powershell -NoProfile -ExecutionPolicy Bypass -File $kitScript -ProjectPath $ProjectPath -Genre $genre
  Write-Host "CC0 fetch completed via fetch-cc0-kits.ps1 ($genre)."
  exit 0
}

$artDir = Join-Path $ProjectPath "art\cc0"
$engineArt = Join-Path $ProjectPath "Assets\_Game\Art\Modular"
New-Item -ItemType Directory -Force -Path $artDir | Out-Null
New-Item -ItemType Directory -Force -Path $engineArt | Out-Null

$kaykitDest = Join-Path $artDir "KayKit-Medieval-Hexagon-Pack-1.0"
if (-not (Test-Path -LiteralPath $kaykitDest)) {
  git clone --depth 1 https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0.git $kaykitDest
}
if ($IncludeDungeon) {
  $dungeonDest = Join-Path $artDir "KayKit-Dungeon-Remastered-1.0"
  if (-not (Test-Path -LiteralPath $dungeonDest)) {
    git clone --depth 1 https://github.com/KayKit-Game-Assets/KayKit-Dungeon-Remastered-1.0.git $dungeonDest
  }
}
Write-Host "CC0 asset fetch completed successfully."
