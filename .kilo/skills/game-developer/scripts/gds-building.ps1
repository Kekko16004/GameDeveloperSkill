param(
  [Parameter(Mandatory = $true)][string]$Spec,          # JSON spec (see references/blender-building.md)
  [string]$ProjectPath = "",                            # if set: relative export/preview paths resolve here and FBX/GLB are copied to Assets/_Game/Art/Exports/
  [string]$Blender = ""
)
# Headless Blender building generator: deterministic, no MCP, no GUI. Prints GDS_RESULT {json}.
$ErrorActionPreference = "Stop"
$SkillRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$script = Join-Path $SkillRoot "templates\blender\gds_building.py"
if (-not $Blender) {
  $cfgPath = Join-Path $SkillRoot "config.json"; if (-not (Test-Path $cfgPath)) { $cfgPath = Join-Path $SkillRoot "config\defaults.json" }
  try { $cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json; if ($cfg.paths.blender) { $Blender = [string]$cfg.paths.blender } } catch {}
}
if (-not $Blender -or -not (Test-Path $Blender)) {
  $cands = Get-ChildItem "C:\Program Files\Blender Foundation" -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | ForEach-Object { Join-Path $_.FullName "blender.exe" }
  $Blender = $cands | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $Blender) { Write-Host "FAIL: blender.exe not found (set paths.blender in config.json)"; exit 1 }
$specPath = (Resolve-Path $Spec).Path
if ($ProjectPath) {
  $env:GDS_PROJECT = (Resolve-Path $ProjectPath).Path
  foreach ($d in @("art\exports", "screenshots", "Assets\_Game\Art\Exports")) { New-Item -ItemType Directory -Force -Path (Join-Path $ProjectPath $d) | Out-Null }
}
$ErrorActionPreference = "Continue"   # Blender prints warnings on stderr; do not treat them as failures
$out = & $Blender -b --python $script -- $specPath 2>&1 | ForEach-Object { "$_" }
$ErrorActionPreference = "Stop"
$line = $out | Where-Object { $_ -match '^GDS_RESULT ' } | Select-Object -Last 1
if (-not $line) { Write-Host ($out | Select-String -Pattern "Error|Traceback" -Context 0,6 | Out-String); Write-Host "FAIL: no GDS_RESULT"; exit 1 }
$json = $line -replace '^GDS_RESULT ', ''
if ($ProjectPath) {
  $r = $json | ConvertFrom-Json
  foreach ($f in @($r.fbx, $r.glb)) { if ($f -and (Test-Path $f)) { Copy-Item $f (Join-Path $ProjectPath "Assets\_Game\Art\Exports\") -Force } }
}
Write-Host "GDS_RESULT $json"
