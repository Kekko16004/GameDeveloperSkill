param(
  [switch]$All,          # every detected host + every module, no questions
  [switch]$Quiet,        # detected hosts + recommended modules, no questions
  [string[]]$Hosts,      # force a host list: kilo,claude,codex,antigravity,cursor,opencode,windsurf,copilot
  [string[]]$SkipModules,
  [switch]$Copy          # copy into every host instead of linking (for hosts that do not follow junctions)
)
# Game Developer installer.
# 1. Detects which agent hosts exist on this PC and which tools/skills are already installed (search, not hardcoded paths).
# 2. Installs the skill ONCE in the canonical folder %USERPROFILE%\.agents\skills\game-developer and links every host
#    folder to it with a directory junction (no admin, no drift: one update reaches every host).
# 3. Merges config.json: values the user already set win, detected paths fill the blanks, defaults fill the rest.
# 4. Injects MCP entries (Blender, VoxelAI, TerminalMCP), installs Unity's official skills, runs doctor.

$ErrorActionPreference = "Stop"
$SkillSrc = Split-Path -Parent $MyInvocation.MyCommand.Path
$User = $env:USERPROFILE
$McpScript = Join-Path $SkillSrc "install-mcp.ps1"
$Canon = Join-Path $User ".agents\skills\game-developer"

if (-not (Test-Path -LiteralPath (Join-Path $SkillSrc "SKILL.md"))) { Write-Host "FAIL: SKILL.md missing in $SkillSrc"; exit 1 }

# ------------------------------------------------------------------ hosts
$hostCatalog = [ordered]@{
  kilo        = @{ Label = "Kilo Code";      Detect = @("$User\.config\kilo", "$User\.kilocode", "$User\.kilo");   Paths = @("$User\.config\kilo\skills\game-developer", "$User\.kilo\skills\game-developer", "$User\.kilocode\skills\game-developer"); Cmd = @("$User\.config\kilo\command"); Mcp = "kilo" }
  claude      = @{ Label = "Claude Code";    Detect = @("$User\.claude");                                          Paths = @("$User\.claude\skills\game-developer"); Cmd = @("$User\.claude\commands"); Mcp = "claude" }
  codex       = @{ Label = "Codex";          Detect = @("$User\.codex");                                           Paths = @("$User\.codex\skills\game-developer"); Cmd = $null; Mcp = "codex" }
  antigravity = @{ Label = "Antigravity";    Detect = @("$User\.gemini", "$User\.antigravity");                    Paths = @("$User\.gemini\config\skills\game-developer", "$User\.gemini\antigravity\skills\game-developer", "$User\.antigravity\skills\game-developer"); Cmd = @("$User\.gemini\config\global_workflows"); Mcp = "antigravity" }
  cursor      = @{ Label = "Cursor";         Detect = @("$User\.cursor");                                          Paths = @("$User\.cursor\skills\game-developer"); Cmd = $null; Mcp = "cursor" }
  opencode    = @{ Label = "OpenCode";       Detect = @("$User\.config\opencode");                                 Paths = @("$User\.config\opencode\skills\game-developer"); Cmd = $null; Mcp = $null }
  windsurf    = @{ Label = "Windsurf";       Detect = @("$User\.codeium\windsurf");                                Paths = @("$User\.codeium\windsurf\skills\game-developer"); Cmd = $null; Mcp = $null }
  copilot     = @{ Label = "GitHub Copilot"; Detect = @("$User\.copilot");                                         Paths = @("$User\.copilot\skills\game-developer"); Cmd = $null; Mcp = $null }
}
foreach ($k in $hostCatalog.Keys) {
  $h = $hostCatalog[$k]
  $h.Found = [bool]($h.Detect | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1)
}

$moduleCatalog = [ordered]@{
  skillFiles          = @{ Label = "Skill files (canonical + host links)"; Recommended = $true }
  commands            = @{ Label = "/game /gdd /playtest /resumegame commands"; Recommended = $true }
  unityCli            = @{ Label = "Unity CLI check (+ install hint)"; Recommended = $true }
  unityOfficialSkills = @{ Label = "Unity official skills (npx skills add Unity-Technologies/skills)"; Recommended = $true }
  blenderMcp          = @{ Label = "Blender MCP (uvx mcp-for-blender)"; Recommended = $true }
  voxelMcp            = @{ Label = "VoxelAI MCP"; Recommended = $true }
  terminalMcp         = @{ Label = "TerminalMCP (screen/input/browser, stdio)"; Recommended = $true }
  designSkill         = @{ Label = "real-world-design (DesignerSkill) link"; Recommended = $true }
}

function Read-Pick([string]$Title, $Catalog, [string[]]$DefaultIds, [scriptblock]$Label) {
  $ids = @($Catalog.Keys)
  Write-Host ""; Write-Host $Title; Write-Host "  numbers + Enter  |  all  |  Enter = [*]"
  for ($i = 0; $i -lt $ids.Count; $i++) {
    $mark = if ($DefaultIds -contains $ids[$i]) { "*" } else { " " }
    Write-Host ("  [{0}]{1} {2}" -f ($i + 1), $mark, (& $Label $ids[$i]))
  }
  $raw = Read-Host "Select"
  if ([string]::IsNullOrWhiteSpace($raw)) { return @($DefaultIds) }
  if ($raw.Trim() -eq "all") { return $ids }
  $picked = @()
  foreach ($tok in ($raw -split '[,\s]+' | Where-Object { $_ })) {
    $n = 0
    if ([int]::TryParse($tok, [ref]$n) -and $n -ge 1 -and $n -le $ids.Count) { $picked += $ids[$n - 1] }
    elseif ($Catalog.Contains($tok)) { $picked += $tok }
  }
  if ($picked.Count -eq 0) { return @($DefaultIds) }
  return @($picked | Select-Object -Unique)
}

# ------------------------------------------------------------------ detection (search, not hardcoded)
function Find-First([string[]]$candidates) { foreach ($c in $candidates) { if ($c -and (Test-Path -LiteralPath $c)) { return (Resolve-Path -LiteralPath $c).Path } }; return "" }

function Find-SkillDir([string]$name) {
  # installed anywhere an agent looks, then a source checkout on Desktop/Documents (depth 3)
  $roots = @("$User\.agents\skills", "$User\.claude\skills", "$User\.config\kilo\skills", "$User\.codex\skills", "$User\.gemini\config\skills", "$User\.cursor\skills")
  foreach ($r in $roots) { $p = Join-Path $r "$name\SKILL.md"; if (Test-Path -LiteralPath $p) { return (Split-Path -Parent (Resolve-Path -LiteralPath $p).Path) } }
  foreach ($base in @("$User\Desktop", "$User\Documents", "$User\source", "$User\Projects")) {
    if (-not (Test-Path -LiteralPath $base)) { continue }
    $hit = Get-ChildItem -LiteralPath $base -Directory -Recurse -Depth 3 -Filter $name -ErrorAction SilentlyContinue |
      Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "SKILL.md") } | Select-Object -First 1
    if ($hit) { return $hit.FullName }
  }
  return ""
}

function Find-Blender {
  $cmd = Get-Command blender -ErrorAction SilentlyContinue; if ($cmd) { return $cmd.Source }
  $all = @()
  foreach ($root in @("$env:ProgramFiles\Blender Foundation", "${env:ProgramFiles(x86)}\Steam\steamapps\common\Blender", "$env:LOCALAPPDATA\Programs\Blender Foundation")) {
    if (Test-Path -LiteralPath $root) { $all += Get-ChildItem -LiteralPath $root -Recurse -Depth 2 -Filter blender.exe -ErrorAction SilentlyContinue }
  }
  # newest version folder wins (Blender 5.1 over 4.2)
  $best = $all | Sort-Object { $m = [regex]::Match($_.Directory.Name, '\d+(\.\d+)+'); if ($m.Success) { [version]$m.Value } else { [version]"0.0" } } -Descending | Select-Object -First 1
  if ($best) { return $best.FullName } ; return ""
}

function Find-Unreal {
  $found = @()
  $dat = "$env:ProgramData\Epic\UnrealEngineLauncher\LauncherInstalled.dat"
  if (Test-Path -LiteralPath $dat) {
    try { (Get-Content -LiteralPath $dat -Raw | ConvertFrom-Json).InstallationList | Where-Object { $_.AppName -match '^UE_\d' } | ForEach-Object { $found += $_.InstallLocation } } catch {}
  }
  foreach ($root in @("$env:ProgramFiles\Epic Games", "C:\Games", "D:\Games", "D:\Epic Games")) {
    if (Test-Path -LiteralPath $root) { Get-ChildItem -LiteralPath $root -Directory -Filter "UE_*" -ErrorAction SilentlyContinue | ForEach-Object { $found += $_.FullName } }
  }
  return @($found | Where-Object { Test-Path -LiteralPath (Join-Path $_ "Engine\Binaries\Win64\UnrealEditor.exe") } | Select-Object -Unique)
}

Write-Host ""
Write-Host "=== Game Developer installer ==="
Write-Host "Source:    $SkillSrc"
Write-Host "Canonical: $Canon"
Write-Host ""
Write-Host "--- detection ---"
$det = [ordered]@{}
$det.unityCli = (Get-Command unity -ErrorAction SilentlyContinue).Source
$det.unityEditors = @()
if ($det.unityCli) { try { $det.unityEditors = @((& unity editors --installed --format json --no-banner 2>$null | ConvertFrom-Json).data | ForEach-Object { $_.version }) } catch {} }
$det.unreal = Find-Unreal
$det.blender = Find-Blender
$det.fabcli = Find-First @((Get-Command fabcli -ErrorAction SilentlyContinue).Source, "$env:LOCALAPPDATA\fabcli\fabcli.exe", "$User\.local\bin\fabcli.exe", "$User\Tools\fabcli\fabcli.exe")
$det.uvx = Find-First @((Get-Command uvx -ErrorAction SilentlyContinue).Source, "$User\.local\bin\uvx.exe")
$det.designerSkill = Find-SkillDir "real-world-design"
$det.unitySkills = Find-SkillDir "unity-cli"
$det.voxelai = Find-First @("$User\Desktop\Dev Things\VoxelAIArtist", "$User\Desktop\VoxelAIArtist", "$User\Documents\VoxelAIArtist")
$det.terminalmcp = Find-First @("$User\Desktop\Dev Things\TerminalMCP", "$User\Desktop\TerminalMCP", "$User\Documents\TerminalMCP")
foreach ($k in $det.Keys) {
  $v = $det[$k]; $s = if ($v -is [array]) { ($v -join ", ") } else { [string]$v }
  Write-Host ("  {0,-14} {1}" -f $k, $(if ($s) { $s } else { "-" }))
}
foreach ($k in $hostCatalog.Keys) { if ($hostCatalog[$k].Found) { Write-Host ("  host           {0}" -f $hostCatalog[$k].Label) } }

# ------------------------------------------------------------------ choices
$detectedHosts = @($hostCatalog.Keys | Where-Object { $hostCatalog[$_].Found })
if ($detectedHosts.Count -eq 0) { $detectedHosts = @("claude") }
$recModules = @($moduleCatalog.Keys | Where-Object { $moduleCatalog[$_].Recommended })
$split = { param($arr) @($arr | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ }) }

if ($All) { $pickedHosts = $detectedHosts; $pickedModules = @($moduleCatalog.Keys) }
elseif ($Quiet -or $Hosts) { $pickedHosts = if ($Hosts) { & $split $Hosts } else { $detectedHosts }; $pickedModules = $recModules }
else {
  $pickedHosts = Read-Pick "Hosts (detected = *)" $hostCatalog $detectedHosts { param($id) $hostCatalog[$id].Label + $(if ($hostCatalog[$id].Found) { "" } else { "  (not found)" }) }
  $pickedModules = Read-Pick "Modules" $moduleCatalog $recModules { param($id) $moduleCatalog[$id].Label }
}
if ($SkipModules) { $skip = & $split $SkipModules; $pickedModules = @($pickedModules | Where-Object { $skip -notcontains $_ }) }
$pickedHosts = @($pickedHosts | Where-Object { $hostCatalog.Contains($_) } | Select-Object -Unique)
$mod = @{}; foreach ($k in $moduleCatalog.Keys) { $mod[$k] = $pickedModules -contains $k }

# ------------------------------------------------------------------ config merge (user values win)
function Merge-Obj($base, $over) {
  # returns base with every non-empty value from over applied, recursively (hashtables from ConvertFrom-Json objects)
  foreach ($p in $over.PSObject.Properties) {
    $b = $base.PSObject.Properties[$p.Name]
    if ($null -eq $b) { $base | Add-Member -NotePropertyName $p.Name -NotePropertyValue $p.Value; continue }
    if ($p.Value -is [System.Management.Automation.PSCustomObject] -and $b.Value -is [System.Management.Automation.PSCustomObject]) { Merge-Obj $b.Value $p.Value | Out-Null }
    elseif ($null -ne $p.Value -and "$($p.Value)" -ne "") { $base.$($p.Name) = $p.Value }
  }
  return $base
}
$cfg = Get-Content -LiteralPath (Join-Path $SkillSrc "config\defaults.json") -Raw | ConvertFrom-Json
# existing user configs: canonical first, then any old host copy, then the repo-local one
$existing = @((Join-Path $Canon "config.json")) + @($hostCatalog.Values | ForEach-Object { $_.Paths } | ForEach-Object { Join-Path $_ "config.json" }) + @((Join-Path $SkillSrc "config.json"))
$userCfg = $null
foreach ($c in ($existing | Select-Object -Unique)) {
  if (Test-Path -LiteralPath $c) { try { $userCfg = Get-Content -LiteralPath $c -Raw | ConvertFrom-Json; Write-Host "  config         keeping user values from $c"; break } catch {} }
}
# detected values fill blanks only
$detCfg = [pscustomobject]@{
  hosts = $pickedHosts
  paths = [pscustomobject]@{ blender = $det.blender; unityCli = $det.unityCli; designerSkill = $(if ($det.designerSkill) { Split-Path -Parent $det.designerSkill } else { "" }); voxelai = $det.voxelai; terminalmcp = $det.terminalmcp; unreal = $(if ($det.unreal) { @($det.unreal)[-1] } else { "" }) }
  fab = [pscustomobject]@{ cli = $det.fabcli }
}
$cfg = Merge-Obj $cfg $detCfg
if ($userCfg) {
  # saved paths that do not exist on this PC (e.g. copied from another machine) are dropped, so detection wins
  if ($userCfg.paths) {
    foreach ($pp in @($userCfg.paths.PSObject.Properties)) {
      $v = [string]$pp.Value
      if ($v -and -not (Test-Path -LiteralPath $v)) { $userCfg.paths.$($pp.Name) = "" }
    }
  }
  $cfg = Merge-Obj $cfg $userCfg
}
# modules skipped on the command line stay off in config.json, so doctor and the skill know they are not wanted
if ($SkipModules) {
  foreach ($k in (& $split $SkipModules)) {
    if ($cfg.modules.PSObject.Properties[$k]) { $cfg.modules.$k = $false } else { $cfg.modules | Add-Member -NotePropertyName $k -NotePropertyValue $false }
  }
}

# ------------------------------------------------------------------ install: canonical copy + junctions
function Remove-HostFolder([string]$p) {
  $it = Get-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
  if (-not $it) { return }
  if ($it.LinkType -in @("Junction", "SymbolicLink")) { cmd /c rmdir "$p" | Out-Null }   # removes the link, never the target
  else { Remove-Item -LiteralPath $p -Recurse -Force }
}
function Write-Config([string]$dest) {
  $json = $cfg | ConvertTo-Json -Depth 10
  [System.IO.File]::WriteAllText((Join-Path $dest "config.json"), $json.TrimEnd() + "`n", (New-Object System.Text.UTF8Encoding $false))
}

if ($mod.skillFiles) {
  Write-Host ""; Write-Host "--- skill ---"
  if ((Resolve-Path -LiteralPath $SkillSrc).Path -ne $Canon) {
    Remove-HostFolder $Canon
    New-Item -ItemType Directory -Force -Path $Canon | Out-Null
    Copy-Item -Path (Join-Path $SkillSrc "*") -Destination $Canon -Recurse -Force
  }
  Write-Config $Canon
  Write-Host "OK canonical  $Canon"
  foreach ($h in $pickedHosts) {
    foreach ($p in $hostCatalog[$h].Paths) {
      if ($p -eq $Canon) { continue }
      $parent = Split-Path -Parent $p
      # secondary paths (Kilo/Antigravity have several) only when their root folder already exists
      $rootDir = Join-Path $User (($p.Substring($User.Length + 1)).Split('')[0])
      if ($p -ne $hostCatalog[$h].Paths[0] -and -not (Test-Path -LiteralPath $rootDir)) { continue }
      New-Item -ItemType Directory -Force -Path $parent | Out-Null
      Remove-HostFolder $p
      if ($Copy) { New-Item -ItemType Directory -Force -Path $p | Out-Null; Copy-Item -Path (Join-Path $Canon "*") -Destination $p -Recurse -Force; Write-Host "OK copy      $p" }
      else { New-Item -ItemType Junction -Path $p -Target $Canon | Out-Null; Write-Host "OK link      $p -> canonical" }
    }
  }
}

if ($mod.commands) {
  foreach ($h in $pickedHosts) {
    foreach ($c in @($hostCatalog[$h].Cmd)) {
      if (-not $c) { continue }
      New-Item -ItemType Directory -Force -Path $c | Out-Null
      foreach ($n in @("game", "gdd", "playtest", "resumegame")) {
        $src = Join-Path $SkillSrc "command\$n.md"
        if (Test-Path -LiteralPath $src) { Copy-Item -LiteralPath $src -Destination (Join-Path $c "$n.md") -Force }
      }
      Write-Host "OK commands  $c"
    }
  }
}

# ------------------------------------------------------------------ DesignerSkill: link where missing
if ($mod.designSkill) {
  if ($det.designerSkill) {
    foreach ($root in @("$User\.agents\skills", "$User\.claude\skills", "$User\.config\kilo\skills", "$User\.gemini\config\skills")) {
      $dst = Join-Path $root "real-world-design"
      if ((Test-Path -LiteralPath (Join-Path $dst "SKILL.md")) -or -not (Test-Path -LiteralPath (Split-Path -Parent $root))) { continue }
      New-Item -ItemType Directory -Force -Path $root | Out-Null
      New-Item -ItemType Junction -Path $dst -Target $det.designerSkill | Out-Null
      Write-Host "OK link      $dst -> $($det.designerSkill)"
    }
  } else { Write-Host "WARN real-world-design not found anywhere: UI phases will stop until it is installed" }
}

# ------------------------------------------------------------------ MCP
$doBlender = [bool]$mod.blenderMcp; $doVoxel = [bool]($mod.voxelMcp -and $cfg.paths.voxelai); $terminalPath = if ($mod.terminalMcp) { [string]$cfg.paths.terminalmcp } else { "" }
if ($terminalPath -and -not (Test-Path -LiteralPath (Join-Path $terminalPath "bin\terminalmcp.js"))) { Write-Host "WARN TerminalMCP incomplete at $terminalPath (bin\terminalmcp.js missing): skipped"; $terminalPath = "" }
function Invoke-GameMcp([string]$Target, [string]$Mode, [switch]$Create) {
  $a = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $McpScript, "-Target", $Target)
  if ($cfg.paths.voxelai) { $a += "-VoxelPath"; $a += [string]$cfg.paths.voxelai }
  if ($Create) { $a += "-Create" }
  if ($Mode -eq "claude") { $a += "-Claude" } elseif ($Mode -eq "generic") { $a += "-Generic" } elseif ($Mode -eq "codex") { $a += "-Codex" }
  if (-not $doBlender) { $a += "-SkipBlender" }
  if (-not $doVoxel) { $a += "-SkipVoxel" }
  if ($terminalPath) { $a += "-TerminalPath"; $a += $terminalPath }
  & powershell @a
}
if ($doBlender -or $doVoxel -or $terminalPath) {
  Write-Host ""; Write-Host "--- MCP (keeps every other server) ---"
  foreach ($h in $pickedHosts) {
    switch ($hostCatalog[$h].Mcp) {
      "kilo" {
        $kj = "$User\.config\kilo\kilo.json"; $kjc = "$User\.config\kilo\kilo.jsonc"
        if (Test-Path -LiteralPath $kjc) { Invoke-GameMcp $kjc "kilo" } elseif (Test-Path -LiteralPath $kj) { Invoke-GameMcp $kj "kilo" } else { New-Item -ItemType Directory -Force -Path "$User\.config\kilo" | Out-Null; Invoke-GameMcp $kj "kilo" -Create }
        Write-Host "OK MCP       Kilo"
      }
      "claude" { Invoke-GameMcp "$User\.claude.json" "claude"; Write-Host "OK MCP       Claude" }
      "cursor" { Invoke-GameMcp "$User\.cursor\mcp.json" "generic"; Write-Host "OK MCP       Cursor" }
      "antigravity" {
        foreach ($t in @("$User\.gemini\config\mcp_config.json", "$User\.gemini\antigravity\mcp.json")) {
          if (Test-Path -LiteralPath (Split-Path -Parent $t)) { Invoke-GameMcp $t "generic" }
        }
        Write-Host "OK MCP       Antigravity"
      }
      "codex" { $ct = "$User\.codex\config.toml"; if (Test-Path -LiteralPath $ct) { Invoke-GameMcp $ct "codex"; Write-Host "OK MCP       Codex" } }
    }
  }
}

# ------------------------------------------------------------------ Unity CLI + official skills
if ($mod.unityCli) {
  Write-Host ""; Write-Host "--- Unity CLI ---"
  if (-not $det.unityCli) {
    Write-Host "MISSING. Install (no admin):  `$env:UNITY_CLI_CHANNEL='beta'; irm https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.ps1 | iex"
  } else {
    Write-Host "OK $(& unity --version 2>$null)  editors: $($det.unityEditors -join ', ')"
    try { $auth = (& unity auth status --format json --no-banner 2>$null | ConvertFrom-Json).data; if (-not $auth.loggedIn) { Write-Host "RUN: unity auth login" } } catch {}
    Write-Host "Per project the pipeline package is added by scripts\install-gds-editor.ps1 (unity pipeline install)."
  }
}
if ($mod.unityOfficialSkills) {
  if ($det.unitySkills) { Write-Host "OK Unity official skills  $($det.unitySkills)" }
  elseif (Get-Command npx -ErrorAction SilentlyContinue) { try { & npx --yes skills add Unity-Technologies/skills -g -y } catch { Write-Host "WARN npx skills: $_" } }
  else { Write-Host "Later: npx skills add Unity-Technologies/skills -g -y" }
}

# ------------------------------------------------------------------ Blender addon
if ($mod.blenderMcp -and $det.uvx) {
  try { & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $SkillSrc "scripts\install-blender-mcp.ps1") } catch { Write-Host "WARN blender addon: $_" }
}

Write-Host ""; Write-Host "--- doctor ---"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $SkillSrc "scripts\doctor.ps1") -ConfigPath (Join-Path $Canon "config.json") | ForEach-Object { Write-Host $_ }

Write-Host ""
Write-Host "=== Next ==="
Write-Host "1. Restart the agent clients (Kilo / Claude Code / Codex / Antigravity)."
if ($pickedHosts -contains "claude") { Write-Host "2. Claude Code, realistic games: /plugin install unreal-engine-skills-for-claude-code@claude-plugins-official" }
if ($det.unreal.Count -gt 0 -and -not ($det.unreal | Where-Object { $_ -match 'UE_5\.(8|9)|UE_[6-9]' })) { Write-Host "3. Unreal found ($($det.unreal -join ', ')) but the official MCP needs UE 5.8+: install it from the Epic Launcher for style=realistic." }
Write-Host "4. Blender: N panel -> MCP -> Start MCP Server (only for hero props / buildings)."
Write-Host "Then: /game <your idea>"
