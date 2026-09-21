param(
  [Parameter(Mandatory = $true)][string]$ProjectPath,
  [switch]$IncludeDungeon,
  [switch]$IncludeAudio
)

$ErrorActionPreference = "Stop"

$artDir = Join-Path $ProjectPath "art\cc0"
$engineArt = Join-Path $ProjectPath "Assets\_Game\Art\Modular"
$engineAudio = Join-Path $ProjectPath "Assets\_Game\Audio"

New-Item -ItemType Directory -Force -Path $artDir | Out-Null
New-Item -ItemType Directory -Force -Path $engineArt | Out-Null
New-Item -ItemType Directory -Force -Path $engineAudio | Out-Null

$kaykitDest = Join-Path $artDir "kaykit_medieval"
if (-not (Test-Path -LiteralPath $kaykitDest)) {
  Write-Host "Cloning KayKit Medieval CC0 pack..."
  git clone --depth 1 https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0.git $kaykitDest
}

if (Test-Path -LiteralPath $kaykitDest) {
  $models = Get-ChildItem -LiteralPath $kaykitDest -Recurse -Include "*.gltf", "*.glb", "*.fbx", "*.obj"
  foreach ($m in $models) {
    Copy-Item -Path $m.FullName -Destination $engineArt -Force
  }
  Write-Host "Copied $($models.Count) medieval models to $engineArt"
}

if ($IncludeDungeon) {
  $dungeonDest = Join-Path $artDir "kaykit_dungeon"
  if (-not (Test-Path -LiteralPath $dungeonDest)) {
    Write-Host "Cloning KayKit Dungeon CC0 pack..."
    git clone --depth 1 https://github.com/KayKit-Game-Assets/KayKit-Dungeon-Pack-1.0.git $dungeonDest
  }
  if (Test-Path -LiteralPath $dungeonDest) {
    $dModels = Get-ChildItem -LiteralPath $dungeonDest -Recurse -Include "*.gltf", "*.glb", "*.fbx", "*.obj"
    foreach ($m in $dModels) {
      Copy-Item -Path $m.FullName -Destination $engineArt -Force
    }
  }
}

Write-Host "CC0 asset fetch completed successfully."
