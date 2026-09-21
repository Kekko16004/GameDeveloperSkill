param(
  [Parameter(Mandatory = $true)][string]$ProjectPath
)

$ErrorActionPreference = "Stop"
$src = Join-Path $ProjectPath "art\exports"
$unity = Join-Path $ProjectPath "Assets\_Game\Art"
$godot = Join-Path $ProjectPath "_game\art"
if (-not (Test-Path -LiteralPath $src)) {
  Write-Host "No art/exports"
  exit 0
}
$dest = $null
if (Test-Path -LiteralPath (Join-Path $ProjectPath "ProjectSettings")) {
  $dest = $unity
} elseif (Test-Path -LiteralPath (Join-Path $ProjectPath "project.godot")) {
  $dest = $godot
} else {
  Write-Host "Not a Unity/Godot project: $ProjectPath"
  exit 1
}
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Path (Join-Path $src "*") -Destination $dest -Recurse -Force
Write-Host "copied exports -> $dest"
