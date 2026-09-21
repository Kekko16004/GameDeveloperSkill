param(
  [Parameter(Mandatory = $true)][string]$ProjectPath,
  [switch]$WithToonShader,
  [switch]$WithOutline,
  [switch]$WithVolumetric
)
# Copies the GDS editor scripts (LevelBuilder, SceneLint, LookDev, KitCatalog, VFX, Characters) into the Unity project
# and optionally adds free rendering packages to Packages/manifest.json. Unity must reimport afterwards (open the Editor or unity -batchmode -quit).
$ErrorActionPreference = "Stop"
$SkillRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$src = Join-Path $SkillRoot "templates\Editor\GDS"
$dst = Join-Path $ProjectPath "Assets\_Game\Editor\GDS"
if (-not (Test-Path -LiteralPath (Join-Path $ProjectPath "ProjectSettings"))) { Write-Host "FAIL: not a Unity project: $ProjectPath"; exit 1 }
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Copy-Item -Path (Join-Path $src "*") -Destination $dst -Recurse -Force
foreach ($d in @("art\blueprints", "docs\lint", "docs\gates", "screenshots", "Assets\_Game\Settings", "Assets\_Game\Art\Materials", "Assets\_Game\Prefabs\VFX", "Assets\_Game\Animation")) {
  New-Item -ItemType Directory -Force -Path (Join-Path $ProjectPath $d) | Out-Null
}
Write-Host "OK GDS editor scripts -> $dst"

$manifestPath = Join-Path $ProjectPath "Packages\manifest.json"
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$deps = $manifest.dependencies
function Add-Dep([string]$name, [string]$value) {
  if ($deps.PSObject.Properties.Name -contains $name) { Write-Host "SKIP $name (present)"; return }
  $deps | Add-Member -NotePropertyName $name -NotePropertyValue $value
  Write-Host "ADD  $name = $value"
}
Add-Dep "com.unity.probuilder" "6.1.2"
Add-Dep "com.unity.cloud.gltfast" "6.20.0"
if ($WithToonShader) { Add-Dep "com.deltation.toon-shader" "https://github.com/Delt06/urp-toon-shader.git?path=Packages/com.deltation.toon-shader" }
if ($WithOutline)    { Add-Dep "com.cristianqiu.urp-outline" "https://github.com/CristianQiu/Unity-URP-Outline.git" }
if ($WithVolumetric) { Add-Dep "com.cristianqiu.urp-volumetric-light" "https://github.com/CristianQiu/Unity-URP-Volumetric-Light.git" }
$json = $manifest | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText($manifestPath, $json.TrimEnd() + "`n", (New-Object System.Text.UTF8Encoding $false))
Write-Host "OK manifest updated. Next: open the project (or unity -batchmode -quit) and read_console for 0 errors. Then execute_code: return GDS.SceneLint.RunJson();"
