param(
  [Parameter(Mandatory = $true)][string]$ProjectPath,
  [switch]$WithToonShader,
  [switch]$WithOutline,
  [switch]$WithVolumetric,
  [switch]$NoPipeline
)
# Copies the GDS layer into a Unity project:
#   Assets/_Game/Editor/GDS   (LevelBuilder, Village, World, SceneLint, LookDev, Shots, KitCatalog, VFX, Characters, PB, CLI commands)
#   Assets/_Game/Scripts/GDS  (runtime: Noise, VoxelWorld, VoxelInteractor)
# Adds ProBuilder + glTFast (+ optional toon/outline/volumetric) to the manifest and the Unity CLI Pipeline package,
# so `unity command eval` and the gds_* commands work against the open Editor.
$ErrorActionPreference = "Stop"
$SkillRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not (Test-Path -LiteralPath (Join-Path $ProjectPath "ProjectSettings"))) { Write-Host "FAIL: not a Unity project: $ProjectPath"; exit 1 }

$pairs = @(
  @{ Src = "templates\Editor\GDS";  Dst = "Assets\_Game\Editor\GDS" },
  @{ Src = "templates\Runtime\GDS"; Dst = "Assets\_Game\Scripts\GDS" }
)
foreach ($p in $pairs) {
  $dst = Join-Path $ProjectPath $p.Dst
  New-Item -ItemType Directory -Force -Path $dst | Out-Null
  Copy-Item -Path (Join-Path $SkillRoot "$($p.Src)\*") -Destination $dst -Recurse -Force
  Write-Host "OK $($p.Src) -> $dst"
}
foreach ($d in @("art\blueprints", "art\world", "art\specs", "docs\lint", "docs\gates", "screenshots\review", "Assets\_Game\Settings", "Assets\_Game\Art\Materials", "Assets\_Game\Prefabs\VFX", "Assets\_Game\Animation")) {
  New-Item -ItemType Directory -Force -Path (Join-Path $ProjectPath $d) | Out-Null
}
# world spec examples next to the blueprints, so a worker edits a copy instead of inventing the schema
$worldTpl = Join-Path $SkillRoot "templates\world"
if (Test-Path -LiteralPath $worldTpl) {
  Get-ChildItem -LiteralPath $worldTpl -Filter *.json | ForEach-Object {
    $t = Join-Path $ProjectPath "art\world\example_$($_.Name)"
    if (-not (Test-Path -LiteralPath $t)) { Copy-Item -LiteralPath $_.FullName -Destination $t }
  }
}

$manifestPath = Join-Path $ProjectPath "Packages\manifest.json"
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$deps = $manifest.dependencies
function Add-Dep([string]$name, [string]$value) {
  if ($deps.PSObject.Properties.Name -contains $name) { Write-Host "SKIP $name (present)"; return }
  $deps | Add-Member -NotePropertyName $name -NotePropertyValue $value
  Write-Host "ADD  $name = $value"
}
# Versions: ask the project's own Editor which versions it recommends (a pinned number breaks on the next Unity release)
$editorPkgs = $null
try {
  $pv = (Get-Content -LiteralPath (Join-Path $ProjectPath "ProjectSettings\ProjectVersion.txt") | Select-String "m_EditorVersion:").ToString().Split(":")[1].Trim()
  $eds = (& unity editors --installed --format json 2>$null | ConvertFrom-Json).data
  $ed = $eds | Where-Object { $_.version -eq $pv } | Select-Object -First 1
  if ($ed) {
    $mf = Join-Path (Split-Path -Parent $ed.location) "Data\Resources\PackageManager\Editor\manifest.json"
    if (Test-Path -LiteralPath $mf) { $editorPkgs = Get-Content -LiteralPath $mf -Raw | ConvertFrom-Json }
  }
} catch { }
function Ver([string]$name, [string]$fallback) {
  if ($editorPkgs) {
    $e = $editorPkgs.$name; if (-not $e -and $editorPkgs.packages) { $e = $editorPkgs.packages.$name }
    if ($e -and $e.version) { return [string]$e.version }
  }
  return $fallback
}
Add-Dep "com.unity.probuilder" (Ver "com.unity.probuilder" "6.1.2")
Add-Dep "com.unity.cloud.gltfast" (Ver "com.unity.cloud.gltfast" "6.14.1")
Add-Dep "com.unity.inputsystem" (Ver "com.unity.inputsystem" "1.14.2")
Add-Dep "com.unity.ai.navigation" (Ver "com.unity.ai.navigation" "2.0.9")
if ($WithToonShader) { Add-Dep "com.deltation.toon-shader" "https://github.com/Delt06/urp-toon-shader.git?path=Packages/com.deltation.toon-shader" }
if ($WithOutline)    { Add-Dep "com.cqf.outline" "https://github.com/CristianQiu/Unity-URP-Outline.git" }
if ($WithVolumetric) { Add-Dep "com.cristianqiu.urp-volumetric-light" "https://github.com/CristianQiu/Unity-URP-Volumetric-Light.git" }
$json = $manifest | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText($manifestPath, $json.TrimEnd() + "`n", (New-Object System.Text.UTF8Encoding $false))
Write-Host "OK manifest updated"

# Unity CLI Pipeline package: live Editor control (eval, screenshot, editor_play, gds_* commands)
if (-not $NoPipeline) {
  $unity = Get-Command unity -ErrorAction SilentlyContinue
  if ($unity) {
    & unity pipeline install --project-path $ProjectPath --non-interactive --no-banner 2>&1 | ForEach-Object { Write-Host "  $_" }
    if ($LASTEXITCODE -eq 0) { Write-Host "OK com.unity.pipeline" } else { Write-Host "WARN unity pipeline install failed (exit $LASTEXITCODE): CoplayDev execute_code still works" }
  } else {
    Write-Host "WARN Unity CLI not on PATH: skipped com.unity.pipeline (install the CLI, then: unity pipeline install --project-path `"$ProjectPath`")"
  }
}
Write-Host "Next: open the project (or let the Editor reimport), wait for compile, then:"
Write-Host "  unity command gds_ping --project-path `"$ProjectPath`""
Write-Host "  (fallback) unity command eval `"return GDS.SceneLint.RunJson();`"   or CoplayDev execute_code"
