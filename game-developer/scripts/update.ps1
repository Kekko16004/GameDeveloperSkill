# Updates game-developer: git pull of the GameDeveloperSkill repo, then re-runs the installer with the choices
# already saved in config.json (hosts, modules turned off). Existing config values are kept by the installer.
# Works from the repo checkout or from the installed copy (then the repo lives in %LOCALAPPDATA%\skill-repos).

$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/Kekko16004/GameDeveloperSkill.git"
$SkillDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$User = $env:USERPROFILE

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Write-Host "FAIL git not found: install Git for Windows"; exit 1 }

# repo: the checkout this script lives in, else a cached clone
$repo = Split-Path -Parent $SkillDir
if (-not (Test-Path -LiteralPath (Join-Path $repo ".git"))) {
  $repo = Join-Path $env:LOCALAPPDATA "skill-repos\GameDeveloperSkill"
  if (-not (Test-Path -LiteralPath (Join-Path $repo ".git"))) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $repo) | Out-Null
    & git clone --quiet $RepoUrl $repo
    if ($LASTEXITCODE -ne 0) { Write-Host "FAIL git clone $RepoUrl"; exit 1 }
  }
}
$before = & git -C $repo rev-parse --short HEAD
& git -C $repo pull --ff-only --quiet
if ($LASTEXITCODE -ne 0) { Write-Host "FAIL git pull in $repo (local changes or diverged branch)"; exit 1 }
$after = & git -C $repo rev-parse --short HEAD
Write-Host $(if ($before -eq $after) { "OK repo      $repo already at $after" } else { "OK repo      $repo $before -> $after" })

# saved choices from the installed copy
$cfg = $null
foreach ($c in @("$User\.agents\skills\game-developer\config.json", (Join-Path $SkillDir "config.json"))) {
  if (Test-Path -LiteralPath $c) { try { $cfg = Get-Content -LiteralPath $c -Raw | ConvertFrom-Json; break } catch {} }
}
$installerModules = @("skillFiles", "commands", "unityCli", "unityOfficialSkills", "blenderMcp", "voxelMcp", "terminalMcp", "designSkill")
$argsList = @("-Quiet")
if ($cfg) {
  if ($cfg.hosts) { $argsList += "-Hosts"; $argsList += (@($cfg.hosts) -join ",") }
  $off = @($cfg.modules.PSObject.Properties | Where-Object { $_.Value -eq $false -and $installerModules -contains $_.Name } | ForEach-Object { $_.Name })
  if ($off.Count) { $argsList += "-SkipModules"; $argsList += ($off -join ",") }
}

Write-Host "Installer:   $($argsList -join ' ')"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo "game-developer\install.ps1") @argsList
exit $LASTEXITCODE
