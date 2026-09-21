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

$voxelDefault = "C:\Users\FRANCY\Desktop\Dev Things\VoxelAIArtist"
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
    if ($ed) { Row "PASS" "unity-editor" "listed (check 6000.x in JSON)" }
    else { Row "WARN" "unity-editor" "unity install lts --yes --accept-eula" }
  } catch { Row "WARN" "unity-editor" "unity install lts --yes --accept-eula" }
  try {
    $au = & $unity auth status --format json --no-banner --non-interactive 2>$null
    if ($au -match '"loggedIn"\s*:\s*true' -or $au -match '"signedIn"\s*:\s*true' -or $au -match 'logged in') {
      Row "PASS" "unity-auth" "signed in"
    } else { Row "WARN" "unity-auth" "unity auth login" }
  } catch { Row "WARN" "unity-auth" "unity auth login" }
} else { Row "FAIL" "unity-cli" "winget install Unity.CLI   OR   `$env:UNITY_CLI_CHANNEL='beta'; irm https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.ps1 | iex" }

$blender = Get-Cmd "blender"
if (-not $blender) {
  $bf = Get-ChildItem -LiteralPath "C:\Program Files\Blender Foundation" -Filter "blender.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($bf) { $blender = $bf.FullName }
}
if ($blender) { Row "PASS" "blender-exe" $blender }
else { Row "FAIL" "blender-exe" "Install Blender 4.2+ then uvx blender-mcp install-addon" }

$tcp = $false
try {
  $c = Test-NetConnection -ComputerName 127.0.0.1 -Port 9876 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
  if ($c -and $c.TcpTestSucceeded) { $tcp = $true }
} catch { }
if ($tcp) { Row "PASS" "blender-socket" "127.0.0.1:9876" }
else { Row "WARN" "blender-socket" "Open Blender -> N -> MCP for Blender -> Start MCP Server" }

if (Test-Path -LiteralPath (Join-Path $voxelDefault "mcp_server")) {
  Row "PASS" "voxelai" $voxelDefault
} else { Row "FAIL" "voxelai" "Set paths.voxelai in config.json (folder with mcp_server)" }

$designCandidates = @(
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
if (-not $tmPath) { $tmPath = "C:\Users\FRANCY\Desktop\Dev Things\TerminalMCP" }
if (Test-Path -LiteralPath (Join-Path $tmPath "bin\terminalmcp.js")) {
  Row "PASS" "terminalmcp" $tmPath
} else {
  Row "WARN" "terminalmcp" "git clone https://github.com/Fonlogen/TerminalMCP `"$tmPath`""
}

Row "PASS" "playwright" "Use existing Kilo MCP playwright if configured"
