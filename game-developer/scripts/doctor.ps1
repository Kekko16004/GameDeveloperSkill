param(
  [string]$ProjectPath = "",
  [string]$ConfigPath = ""
)

$ErrorActionPreference = "Continue"
$SkillRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not $ConfigPath) {
  $cfg = Join-Path $SkillRoot "config.json"
  if (-not (Test-Path -LiteralPath $cfg)) { $cfg = Join-Path $SkillRoot "config\defaults.json" }
  $ConfigPath = $cfg
}

function Get-Cmd([string]$name) {
  $c = Get-Command $name -ErrorAction SilentlyContinue
  if ($c) { return $c.Source }
  return $null
}

function Row([string]$status, [string]$id, [string]$fix) {
  "{0} | {1} | {2}" -f $status, $id, $fix
}

$cfg = $null
if (Test-Path -LiteralPath $ConfigPath) {
  try { $cfg = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json } catch { }
}

$voxelDefault = Join-Path $env:USERPROFILE "Desktop\Dev Things\VoxelAIArtist"
if ($cfg -and $cfg.paths -and $cfg.paths.voxelai) { $voxelDefault = [string]$cfg.paths.voxelai }

$node = Get-Cmd "node"
if ($node) {
  $nv = & node -v 2>$null
  $nMajor = 0
  if ($nv -match 'v?(\d+)') { $nMajor = [int]$Matches[1] }
  if ($nMajor -ge 18) { Row "PASS" "node" $nv }
  else { Row "FAIL" "node" "Need Node >= 18 (got $nv). https://nodejs.org" }
} else { Row "FAIL" "node" "Install Node >= 18 from https://nodejs.org" }

$py = Get-Cmd "python"
if (-not $py) { $py = Get-Cmd "py" }
if ($py) {
  $pv = & python --version 2>$null
  if (-not $pv) { $pv = & py -3 --version 2>$null }
  Row "PASS" "python" "$pv"
} else { Row "FAIL" "python" "Install Python 3.10+ and tick Add to PATH" }

$uvx = Get-Cmd "uvx"
if (-not $uvx) {
  $cand = Join-Path $env:USERPROFILE ".local\bin\uvx.exe"
  if (Test-Path -LiteralPath $cand) { $uvx = $cand }
}
if ($uvx) { Row "PASS" "uvx" $uvx }
else { Row "FAIL" "uvx" 'powershell -c "irm https://astral.sh/uv/install.ps1 | iex"' }

$unity = Get-Cmd "unity"
if (-not $unity) {
  foreach ($cand in @("$env:LOCALAPPDATA\Unity\bin\unity.exe", "C:\Program Files\Unity Hub\resources\cli\unity.exe")) {
    if (Test-Path -LiteralPath $cand) { $unity = $cand; break }
  }
}
if ($unity) {
  $uv = & $unity --version 2>$null
  Row "PASS" "unity-cli" "$uv"
  try {
    $ed = & $unity editors --installed --format json --no-banner --non-interactive 2>$null
    if ($ed) {
      $edj = ($ed -join "`n") | ConvertFrom-Json
      $rows = if ($edj.data) { $edj.data } else { $edj }
      $vers = @($rows | ForEach-Object { $_.version })
      $lts = @($vers | Where-Object { $_ -match '^6000\.(0|3)\.' })
      $newer = @($vers | Where-Object { $_ -match '^6000\.([4-9]|\d{2,})\.' })
      if ($lts.Count -gt 0) { Row "PASS" "unity-editor" ("LTS " + ($lts -join ", ")) }
      elseif ($newer.Count -gt 0) { Row "WARN" "unity-editor" ("only " + ($newer -join ", ") + " (tech stream): needs ProBuilder >= 6.1.2 (install-gds-editor.ps1 sets it); prefer 6000.3 LTS for stability") }
      else { Row "WARN" "unity-editor" "no 6000.x found: unity install lts --yes --accept-eula" }
    }
    else { Row "WARN" "unity-editor" "unity install lts --yes --accept-eula" }
  } catch { Row "WARN" "unity-editor" "unity install lts --yes --accept-eula" }
  try {
    $au = (& $unity auth status --format json --no-banner --non-interactive 2>$null) -join "`n"
    $aj = $null; try { $aj = $au | ConvertFrom-Json } catch { }
    if (($aj -and $aj.data -and $aj.data.loggedIn) -or $au -match '"loggedIn"\s*:\s*true') {
      Row "PASS" "unity-auth" "signed in"
    } else { Row "WARN" "unity-auth" "unity auth login" }
  } catch { Row "WARN" "unity-auth" "unity auth login" }
} elseif ($cfg -and $cfg.modules -and $cfg.modules.unityCli -eq $false) { Row "SKIP" "unity-cli" "modules.unityCli = false" }
else { Row "FAIL" "unity-cli" "winget install Unity.CLI   OR   `$env:UNITY_CLI_CHANNEL='beta'; irm https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.ps1 | iex" }

$blender = if ($cfg -and $cfg.paths -and $cfg.paths.blender -and (Test-Path -LiteralPath $cfg.paths.blender)) { [string]$cfg.paths.blender } else { Get-Cmd "blender" }
if (-not $blender) {
  $bf = Get-ChildItem -LiteralPath "C:\Program Files\Blender Foundation" -Filter "blender.exe" -Recurse -ErrorAction SilentlyContinue |
    Sort-Object { $m = [regex]::Match($_.Directory.Name, '\d+(\.\d+)+'); if ($m.Success) { [version]$m.Value } else { [version]"0.0" } } -Descending | Select-Object -First 1
  if ($bf) { $blender = $bf.FullName }
}
if ($blender) { Row "PASS" "blender-exe" $blender }
else { Row "FAIL" "blender-exe" "Install Blender 4.2+ then uvx mcp-for-blender install-addon" }

$tcp = $false
try {
  $c = Test-NetConnection -ComputerName 127.0.0.1 -Port 9876 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
  if ($c -and $c.TcpTestSucceeded) { $tcp = $true }
} catch { }
if ($tcp) { Row "PASS" "blender-socket" "127.0.0.1:9876" }
else { Row "WARN" "blender-socket" "Open Blender -> N -> MCP for Blender -> Start MCP Server" }

if (Test-Path -LiteralPath (Join-Path $voxelDefault "mcp_server")) {
  Row "PASS" "voxelai" $voxelDefault
} elseif ($cfg -and $cfg.modules -and $cfg.modules.voxelMcp -eq $false) { Row "SKIP" "voxelai" "modules.voxelMcp = false" }
else { Row "FAIL" "voxelai" "Set paths.voxelai in config.json (folder with mcp_server)" }

$designCandidates = @(
  (Join-Path $env:USERPROFILE ".claude\skills\real-world-design\SKILL.md"),
  (Join-Path $env:USERPROFILE ".gemini\config\skills\real-world-design\SKILL.md"),
  (Join-Path $env:USERPROFILE ".config\kilo\skills\real-world-design\SKILL.md"),
  (Join-Path $env:USERPROFILE ".agents\skills\real-world-design\SKILL.md")
)
$foundDesign = $null
foreach ($dc in $designCandidates) {
  if (Test-Path -LiteralPath $dc) { $foundDesign = $dc; break }
}
if ($foundDesign) { Row "PASS" "design-skill" $foundDesign }
else { Row "WARN" "design-skill" "Install DesignerSkill (real-world-design) before HUD work" }

if ($ProjectPath -and (Test-Path -LiteralPath $ProjectPath)) {
  $shots = Join-Path $ProjectPath "screenshots"
  if (-not (Test-Path -LiteralPath $shots)) {
    New-Item -ItemType Directory -Force -Path $shots | Out-Null
  }
  Row "PASS" "screenshots-dir" $shots
  $gdd = Join-Path $ProjectPath "GDD.md"
  if (Test-Path -LiteralPath $gdd) {
    $raw = Get-Content -LiteralPath $gdd -Raw
    if ($raw -match 'status:\s*locked') { Row "PASS" "gdd" "locked" }
    elseif ($raw -match 'status:\s*draft') { Row "WARN" "gdd" "draft - finish /gdd" }
    else { Row "WARN" "gdd" "GDD.md present, status unknown" }
  } else { Row "WARN" "gdd" "No GDD.md yet - run /game or /gdd" }
} else {
  Row "WARN" "screenshots-dir" "Pass -ProjectPath after attach"
  Row "WARN" "gdd" "No project attached"
}

$tmPath = ""
if ($cfg -and $cfg.paths -and $cfg.paths.terminalmcp) { $tmPath = [string]$cfg.paths.terminalmcp }
if (-not $tmPath) { $tmPath = Join-Path $env:USERPROFILE "Desktop\Dev Things\TerminalMCP" }
if (Test-Path -LiteralPath (Join-Path $tmPath "bin\terminalmcp.js")) {
  Row "PASS" "terminalmcp" $tmPath
} else {
  Row "WARN" "terminalmcp" "git clone https://github.com/Fonlogen/TerminalMCP `"$tmPath`""
}

$kitFetch = Join-Path $SkillRoot "scripts\fetch-cc0-kits.ps1"
if (Test-Path -LiteralPath $kitFetch) { Row "PASS" "cc0-kits" $kitFetch }
else { Row "WARN" "cc0-kits" "scripts/fetch-cc0-kits.ps1 missing" }

Row "PASS" "playwright" "Use existing Kilo MCP playwright if configured"

$gds = Join-Path $SkillRoot "templates\Editor\GDS\GDS.Editor.asmdef"
if (Test-Path -LiteralPath $gds) { Row "PASS" "gds-editor" "templates/Editor/GDS present (install-gds-editor.ps1 -ProjectPath <project>)" }
else { Row "FAIL" "gds-editor" "templates/Editor/GDS missing: re-run install.ps1" }
if ($ProjectPath -and (Test-Path -LiteralPath (Join-Path $ProjectPath "Assets\_Game\Editor\GDS\GDS.Editor.asmdef"))) { Row "PASS" "gds-project" "GDS scripts installed in project" }
elseif ($ProjectPath) { Row "WARN" "gds-project" "powershell -File scripts/install-gds-editor.ps1 -ProjectPath $ProjectPath" }


# Unity official skills (unity-cli skill documents the live-Editor commands)
if (Test-Path -LiteralPath (Join-Path $env:USERPROFILE ".agents\skills\unity-cli\SKILL.md")) { Row "PASS" "unity-skills" "Unity-Technologies/skills installed" }
else { Row "WARN" "unity-skills" "npx skills add Unity-Technologies/skills -g -y" }

# Unity CLI pipeline package in the project (live eval + gds_* commands)
if ($ProjectPath -and (Test-Path -LiteralPath (Join-Path $ProjectPath "Packages\manifest.json"))) {
  if ((Get-Content -LiteralPath (Join-Path $ProjectPath "Packages\manifest.json") -Raw) -match '"com\.unity\.pipeline"') { Row "PASS" "unity-pipeline" "com.unity.pipeline in manifest" }
  else { Row "WARN" "unity-pipeline" "unity pipeline install --project-path `"$ProjectPath`"" }
}

# Unreal (style realistic only): the official MCP needs 5.8+
$ue = @()
foreach ($root in @("$env:ProgramFiles\Epic Games", "C:\Games", "D:\Games")) {
  if (Test-Path -LiteralPath $root) { $ue += Get-ChildItem -LiteralPath $root -Directory -Filter "UE_*" -ErrorAction SilentlyContinue | ForEach-Object { $_.Name } }
}
if ($ue | Where-Object { $_ -match '^UE_(5\.(8|9|\d{2})|[6-9]\.)' }) { Row "PASS" "unreal" ($ue -join ", ") }
elseif ($ue.Count -gt 0) { Row "WARN" "unreal" (($ue -join ", ") + " found; style realistic needs UE 5.8+ (Epic Launcher)") }
else { Row "WARN" "unreal" "not installed (only needed for style realistic)" }
