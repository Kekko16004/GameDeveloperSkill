param(
  [switch]$All,
  [switch]$Quiet,
  [string[]]$Hosts,
  [string[]]$SkipModules
)

$ErrorActionPreference = "Stop"
$SkillSrc = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $SkillSrc
$User = $env:USERPROFILE
$McpScript = Join-Path $SkillSrc "install-mcp.ps1"
$DefaultsPath = Join-Path $SkillSrc "config\defaults.json"

if (-not (Test-Path -LiteralPath (Join-Path $SkillSrc "SKILL.md"))) {
  Write-Host "FAIL: SKILL.md missing in $SkillSrc"
  exit 1
}

$defaults = Get-Content -LiteralPath $DefaultsPath -Raw | ConvertFrom-Json
$voxelDefault = [string]$defaults.paths.voxelai
$terminalDefault = [string]$defaults.paths.terminalmcp
if (-not $terminalDefault) { $terminalDefault = "$User\Desktop\Dev Things\TerminalMCP" }

$hostCatalog = [ordered]@{
  kilo         = @{ Label = "Kilo Code";           Recommended = $true;  Paths = @("$User\.config\kilo\skills\game-developer", "$User\.kilo\skills\game-developer", "$User\.kilocode\skills\game-developer"); Cmd = @("$User\.config\kilo\command", "$User\.config\kilo\commands", "$User\.kilo\command", "$User\.kilo\commands"); Mcp = "kilo" }
  claude       = @{ Label = "Claude Code";         Recommended = $true;  Paths = @("$User\.claude\skills\game-developer"); Cmd = @("$User\.claude\commands"); Mcp = "claude" }
  codex        = @{ Label = "Codex / agents";      Recommended = $true;  Paths = @("$User\.codex\skills\game-developer", "$User\.agents\skills\game-developer"); Cmd = $null; Mcp = "codex" }
  antigravity  = @{ Label = "Antigravity IDE";     Recommended = $true;  Paths = @("$User\.gemini\config\skills\game-developer", "$User\.gemini\antigravity\skills\game-developer", "$User\.antigravity\skills\game-developer"); Cmd = @("$User\.gemini\config\global_workflows"); Mcp = "antigravity" }
  cursor       = @{ Label = "Cursor";              Recommended = $false; Paths = @("$User\.cursor\skills\game-developer"); Cmd = $null; Mcp = "cursor" }
  opencode     = @{ Label = "OpenCode";            Recommended = $false; Paths = @("$User\.config\opencode\skills\game-developer"); Cmd = $null; Mcp = $null }
  github       = @{ Label = "GitHub Copilot";      Recommended = $false; Paths = @("$User\.github\skills\game-developer"); Cmd = $null; Mcp = $null }
  windsurf     = @{ Label = "Windsurf";            Recommended = $false; Paths = @("$User\.codeium\windsurf\skills\game-developer"); Cmd = $null; Mcp = $null }
}

$moduleCatalog = [ordered]@{
  skillFiles           = @{ Label = "Skill files"; Recommended = $true }
  gameCommand          = @{ Label = "/game command"; Recommended = $true }
  resumegameCommand    = @{ Label = "/resumegame command (context resume)"; Recommended = $true }
  gddCommand           = @{ Label = "/gdd command"; Recommended = $true }
  playtestCommand      = @{ Label = "/playtest command"; Recommended = $true }
  unityCli             = @{ Label = "Unity CLI (create/open/auth)"; Recommended = $true }
  unityMcp             = @{ Label = "CoplayDev Unity MCP notes + kilo inject skip (per-project)"; Recommended = $true }
  blenderMcp           = @{ Label = "Blender MCP (uvx blender-mcp)"; Recommended = $true }
  voxelMcp             = @{ Label = "VoxelAI MCP"; Recommended = $true }
  cc0Fetch             = @{ Label = "CC0 Kenney / Poly Haven scripts"; Recommended = $true }
  designSkillCheck     = @{ Label = "Check real-world-design is installed"; Recommended = $true }
  godotMcp             = @{ Label = "Godot AI MCP (optional)"; Recommended = $false }
  terminalMcp          = @{ Label = "TerminalMCP - full PC control (screen/input/browser, stdio local)"; Recommended = $true }
  unityOfficialSkills  = @{ Label = "npx skills add Unity-Technologies/skills"; Recommended = $true }
}

function Read-Pick {
  param(
    [string]$Title,
    [System.Collections.Specialized.OrderedDictionary]$Catalog,
    [string[]]$DefaultIds,
    [switch]$AllowEmpty
  )
  $ids = @($Catalog.Keys)
  Write-Host ""
  Write-Host $Title
  Write-Host "  numbers + Enter  |  all  |  none  |  Enter = recommended"
  for ($i = 0; $i -lt $ids.Count; $i++) {
    $id = $ids[$i]
    $mark = if ($Catalog[$id].Recommended) { "*" } else { " " }
    Write-Host ("  [{0}]{1} {2}" -f ($i + 1), $mark, $Catalog[$id].Label)
  }
  $raw = Read-Host "Select"
  if ([string]::IsNullOrWhiteSpace($raw)) { return @($DefaultIds) }
  $t = $raw.Trim().ToLowerInvariant()
  if ($t -eq "all") { return @($ids) }
  if ($t -eq "none") {
    if ($AllowEmpty) { return @() }
    Write-Host "Need at least one. Using recommended."
    return @($DefaultIds)
  }
  $picked = New-Object System.Collections.Generic.List[string]
  foreach ($tok in ($raw -split '[,\s]+' | Where-Object { $_ })) {
    $n = 0
    if ([int]::TryParse($tok, [ref]$n) -and $n -ge 1 -and $n -le $ids.Count) {
      $picked.Add($ids[$n - 1]) | Out-Null
    } elseif ($Catalog.Contains($tok)) {
      $picked.Add($tok) | Out-Null
    }
  }
  $uniq = @($picked | Select-Object -Unique)
  if ($uniq.Count -eq 0) {
    Write-Host "Nothing matched. Using recommended."
    return @($DefaultIds)
  }
  return $uniq
}

function Copy-SkillTo([string]$Dest) {
  New-Item -ItemType Directory -Force -Path $Dest | Out-Null
  Copy-Item -Path (Join-Path $SkillSrc "*") -Destination $Dest -Recurse -Force
  Write-Host "OK skill  $Dest"
}

function Copy-Cmd([string]$Dest, [string]$Name) {
  $src = Join-Path $SkillSrc "command\$Name.md"
  if (-not (Test-Path -LiteralPath $src)) { $src = Join-Path $Root "command\$Name.md" }
  if (-not (Test-Path -LiteralPath $src)) { return }
  New-Item -ItemType Directory -Force -Path $Dest | Out-Null
  Copy-Item -LiteralPath $src -Destination (Join-Path $Dest "$Name.md") -Force
  Write-Host "OK cmd    $(Join-Path $Dest "$Name.md")"
}

function Write-Config([string]$Dest, $cfg) {
  $json = $cfg | ConvertTo-Json -Depth 8
  $utf8 = New-Object System.Text.UTF8Encoding $false
  [System.IO.File]::WriteAllText((Join-Path $Dest "config.json"), $json.TrimEnd() + "`n", $utf8)
}

function Invoke-GameMcp {
  param([string]$Target, [string]$Mode, [switch]$Create, [bool]$DoBlender, [bool]$DoVoxel, [string]$VoxelPath, [string]$TerminalPath)
  $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $McpScript, "-Target", $Target, "-VoxelPath", $VoxelPath)
  if ($Create) { $args += "-Create" }
  if ($Mode -eq "claude") { $args += "-Claude" }
  if ($Mode -eq "generic") { $args += "-Generic" }
  if ($Mode -eq "codex") { $args += "-Codex" }
  if (-not $DoBlender) { $args += "-SkipBlender" }
  if (-not $DoVoxel) { $args += "-SkipVoxel" }
  if ($TerminalPath) { $args += "-TerminalPath"; $args += $TerminalPath }
  & powershell @args
}

$recommendedHosts = @($hostCatalog.Keys | Where-Object { $hostCatalog[$_].Recommended })
$recommendedModules = @($moduleCatalog.Keys | Where-Object { $moduleCatalog[$_].Recommended })

Write-Host ""
Write-Host "=== Game Developer installer ==="
Write-Host "Source: $SkillSrc"

if ($All) {
  $pickedHosts = @($hostCatalog.Keys)
  $pickedModules = @($moduleCatalog.Keys)
} elseif ($Quiet -or $Hosts) {
  $split = { param($arr) @($arr | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ }) }
  $pickedHosts = if ($Hosts) { & $split $Hosts } else { @($recommendedHosts) }
  $pickedModules = @($recommendedModules)
  if ($SkipModules) {
    $skipM = & $split $SkipModules
    $pickedModules = @($pickedModules | Where-Object { $skipM -notcontains $_ })
  }
} else {
  $pickedHosts = Read-Pick "Hosts (where to install the skill)" $hostCatalog $recommendedHosts
  $pickedModules = Read-Pick "Modules" $moduleCatalog $recommendedModules -AllowEmpty
}

$pickedHosts = @($pickedHosts | Where-Object { $hostCatalog.Contains($_) } | Select-Object -Unique)
if ($pickedHosts.Count -eq 0) {
  Write-Host "No hosts selected. Abort."
  exit 1
}

$mod = @{}
foreach ($k in $moduleCatalog.Keys) { $mod[$k] = $pickedModules -contains $k }

$voxelPath = $voxelDefault
if ($mod["voxelMcp"] -and -not $Quiet -and -not $All -and -not $Hosts) {
  $ask = Read-Host "VoxelAI path [$voxelDefault]"
  if (-not [string]::IsNullOrWhiteSpace($ask)) { $voxelPath = $ask.Trim() }
}

$terminalPath = ""
if ($mod["terminalMcp"]) {
  $terminalPath = $terminalDefault
  if (-not (Test-Path -LiteralPath (Join-Path $terminalPath "bin\terminalmcp.js"))) {
    if (-not $Quiet -and -not $All) {
      $ask = Read-Host "TerminalMCP not found at [$terminalDefault]. Clone from GitHub into this path? (Enter = yes, other path, or 'skip')"
      if ($ask -match '^\s*skip\s*$') { $terminalPath = "" }
      elseif (-not [string]::IsNullOrWhiteSpace($ask)) { $terminalPath = $ask.Trim() }
    }
    if ($terminalPath -and -not (Test-Path -LiteralPath $terminalPath)) {
      Write-Host "Cloning TerminalMCP -> $terminalPath"
      try {
        git clone --depth 1 https://github.com/Fonlogen/TerminalMCP $terminalPath 2>&1 | Out-Null
      } catch { Write-Host "WARN git clone failed: $_" }
    }
    if ($terminalPath -and -not (Test-Path -LiteralPath (Join-Path $terminalPath "bin\terminalmcp.js"))) {
      Write-Host "WARN TerminalMCP incomplete at $terminalPath (bin\terminalmcp.js missing). MCP inject skipped."
      $terminalPath = ""
    }
  }
}

$cfg = [ordered]@{
  version = 1
  hosts   = @($pickedHosts)
  paths   = [ordered]@{
    voxelai     = $voxelPath
    blender     = ""
    terminalmcp = $terminalPath
    unityCli    = ""
    godot       = ""
  }
  engines = [ordered]@{
    default       = "unity"
    godotEnabled  = [bool]$mod["godotMcp"]
  }
  modules = [ordered]@{
    skillFiles          = [bool]$mod["skillFiles"]
    gameCommand         = [bool]$mod["gameCommand"]
    resumegameCommand   = [bool]$mod["resumegameCommand"]
    gddCommand          = [bool]$mod["gddCommand"]
    playtestCommand     = [bool]$mod["playtestCommand"]
    unityCli            = [bool]$mod["unityCli"]
    unityMcp            = [bool]$mod["unityMcp"]
    blenderMcp          = [bool]$mod["blenderMcp"]
    voxelMcp            = [bool]$mod["voxelMcp"]
    cc0Fetch            = [bool]$mod["cc0Fetch"]
    designSkillCheck    = [bool]$mod["designSkillCheck"]
    godotMcp            = [bool]$mod["godotMcp"]
    terminalMcp         = [bool]$mod["terminalMcp"]
    unityOfficialSkills = [bool]$mod["unityOfficialSkills"]
  }
  mcp = [ordered]@{
    blenderCommand      = @("cmd", "/c", "uvx", "blender-mcp")
    voxelaiWorkdirMode  = "per-project"
    terminalHttp        = $false
  }
  unity = [ordered]@{
    templatePreference = @("urp-3d", "com.unity.template.3d-urp", "com.unity.template.3d")
    coplayGitUrl       = "https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity"
  }
  art = [ordered]@{
    scale                   = "1u=1m"
    forbidPaid3dApis        = $true
    forbidHdriOnGameAssets  = $true
    polyhavenUserAgent      = "GameDeveloperSkill/1.0"
  }
}

Write-Host ""
Write-Host "Installing to: $($pickedHosts -join ', ')"
Write-Host "Modules:      $($pickedModules -join ', ')"
Write-Host ""

foreach ($h in $pickedHosts) {
  $info = $hostCatalog[$h]
  foreach ($p in $info.Paths) {
    Copy-SkillTo $p
    Write-Config $p $cfg
  }
  if ($info.Cmd) {
    foreach ($c in @($info.Cmd)) {
      if ($mod["gameCommand"]) { Copy-Cmd $c "game" }
      if ($mod["resumegameCommand"]) { Copy-Cmd $c "resumegame" }
      if ($mod["gddCommand"]) { Copy-Cmd $c "gdd" }
      if ($mod["playtestCommand"]) { Copy-Cmd $c "playtest" }
    }
  }
}

$doBlender = [bool]$mod["blenderMcp"]
$doVoxel = [bool]$mod["voxelMcp"]
if ($doBlender -or $doVoxel -or $terminalPath) {
  Write-Host ""
  Write-Host "--- MCP (blender / voxelai; will not remove playwright/21st/originkit) ---"
  foreach ($h in $pickedHosts) {
    switch ($hostCatalog[$h].Mcp) {
      "kilo" {
        $kj = "$User\.config\kilo\kilo.json"
        $kjc = "$User\.config\kilo\kilo.jsonc"
        if (Test-Path -LiteralPath $kj) { Invoke-GameMcp -Target $kj -Mode "kilo" -DoBlender $doBlender -DoVoxel $doVoxel -VoxelPath $voxelPath -TerminalPath $terminalPath }
        if (Test-Path -LiteralPath $kjc) { Invoke-GameMcp -Target $kjc -Mode "kilo" -DoBlender $doBlender -DoVoxel $doVoxel -VoxelPath $voxelPath -TerminalPath $terminalPath }
        if (-not (Test-Path -LiteralPath $kj) -and -not (Test-Path -LiteralPath $kjc)) {
          New-Item -ItemType Directory -Force -Path "$User\.config\kilo" | Out-Null
          Invoke-GameMcp -Target $kj -Mode "kilo" -Create -DoBlender $doBlender -DoVoxel $doVoxel -VoxelPath $voxelPath -TerminalPath $terminalPath
        }
        Write-Host "OK MCP    Kilo"
      }
      "claude" {
        Invoke-GameMcp -Target "$User\.claude.json" -Mode "claude" -DoBlender $doBlender -DoVoxel $doVoxel -VoxelPath $voxelPath -TerminalPath $terminalPath
        Write-Host "OK MCP    Claude ~/.claude.json"
      }
      "cursor" {
        New-Item -ItemType Directory -Force -Path "$User\.cursor" | Out-Null
        Invoke-GameMcp -Target "$User\.cursor\mcp.json" -Mode "generic" -DoBlender $doBlender -DoVoxel $doVoxel -VoxelPath $voxelPath -TerminalPath $terminalPath
        Write-Host "OK MCP    Cursor"
      }
      "antigravity" {
        New-Item -ItemType Directory -Force -Path "$User\.gemini\config" | Out-Null
        Invoke-GameMcp -Target "$User\.gemini\config\mcp_config.json" -Mode "generic" -DoBlender $doBlender -DoVoxel $doVoxel -VoxelPath $voxelPath -TerminalPath $terminalPath
        New-Item -ItemType Directory -Force -Path "$User\.gemini\antigravity" | Out-Null
        Invoke-GameMcp -Target "$User\.gemini\antigravity\mcp.json" -Mode "generic" -DoBlender $doBlender -DoVoxel $doVoxel -VoxelPath $voxelPath -TerminalPath $terminalPath
        New-Item -ItemType Directory -Force -Path "$User\.antigravity" | Out-Null
        Invoke-GameMcp -Target "$User\.antigravity\mcp_config.json" -Mode "generic" -DoBlender $doBlender -DoVoxel $doVoxel -VoxelPath $voxelPath -TerminalPath $terminalPath
        Write-Host "OK MCP    Antigravity"
      }
      "codex" {
        $ct = "$User\.codex\config.toml"
        if (Test-Path -LiteralPath $ct) {
          Invoke-GameMcp -Target $ct -Mode "codex" -DoBlender $doBlender -DoVoxel $doVoxel -VoxelPath $voxelPath -TerminalPath $terminalPath
          Write-Host "OK MCP    Codex config.toml"
        } else {
          Write-Host "SKIP MCP  Codex (no $ct)"
        }
      }
    }
  }
}

if ($mod["unityCli"] -and -not (Get-Command unity -ErrorAction SilentlyContinue)) {
  Write-Host ""
  Write-Host "--- Unity CLI missing ---"
  if ($All) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $SkillSrc "scripts\install-unity-cli.ps1")
  } else {
    Write-Host "Install when ready:"
    Write-Host '  winget install Unity.CLI'
    Write-Host "  or  game-developer\scripts\install-unity-cli.ps1"
  }
}

if ($mod["blenderMcp"] -and (Get-Command uvx -ErrorAction SilentlyContinue)) {
  Write-Host ""
  Write-Host "--- Blender addon (best-effort) ---"
  try { & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $SkillSrc "scripts\install-blender-mcp.ps1") }
  catch { Write-Host "WARN blender addon: $_" }
}

if ($mod["unityOfficialSkills"]) {
  Write-Host ""
  Write-Host "--- Unity-Technologies/skills ---"
  $npx = Get-Command npx -ErrorAction SilentlyContinue
  if (-not $npx) {
    Write-Host "npx not found. Later: npx skills add Unity-Technologies/skills -g -y"
  } else {
    try { & npx --yes skills add Unity-Technologies/skills -g -y }
    catch { Write-Host "WARN official unity skills: $_" }
  }
}

if ($mod["designSkillCheck"]) {
  $dsSrc = Join-Path $User "Desktop\DesignerSkill\real-world-design"
  if (Test-Path -LiteralPath (Join-Path $dsSrc "SKILL.md")) {
    $dsTargets = @(
      "$User\.gemini\config\skills\real-world-design",
      "$User\.config\kilo\skills\real-world-design",
      "$User\.agents\skills\real-world-design",
      "$User\.claude\skills\real-world-design"
    )
    foreach ($dst in $dsTargets) {
      if (-not (Test-Path -LiteralPath (Join-Path $dst "SKILL.md"))) {
        New-Item -ItemType Directory -Force -Path $dst | Out-Null
        Copy-Item -Path (Join-Path $dsSrc "*") -Destination $dst -Recurse -Force
      }
    }
    Write-Host "OK design-skill  installed from $dsSrc to all hosts"
  } else {
    $ds = Join-Path $User ".config\kilo\skills\real-world-design\SKILL.md"
    if (Test-Path -LiteralPath $ds) { Write-Host "OK design-skill  $ds" }
    else { Write-Host "WARN DesignerSkill (real-world-design) not found on Desktop - HUD phase will skip" }
  }
}

Write-Host ""
Write-Host "--- doctor ---"
$doctor = Join-Path $SkillSrc "scripts\doctor.ps1"
$report = & powershell -NoProfile -ExecutionPolicy Bypass -File $doctor
$report | ForEach-Object { Write-Host $_ }
$destDoctor = Join-Path $User ".config\kilo\skills\game-developer\last-doctor.txt"
if (Test-Path -LiteralPath (Split-Path $destDoctor)) {
  $report | Set-Content -LiteralPath $destDoctor -Encoding utf8
}

Write-Host ""
Write-Host "=== Next (human clicks) ==="
Write-Host "1. Restart Kilo / Claude / Cursor"
Write-Host "2. unity auth login   then   unity license activate"
Write-Host "3. If no Editor:  unity install lts --yes --accept-eula"
Write-Host "4. Blender: enable MCP addon, N-panel -> Start MCP Server"
Write-Host "5. After you create/open a Unity project: Package Manager git"
Write-Host "   https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity"
Write-Host "   Window -> MCP for Unity -> Configure All Detected Clients"
Write-Host "6. Voxel workdir is PER GAME: art/voxel  (do not pin a global folder)"
Write-Host "Then: /game your-idea"
