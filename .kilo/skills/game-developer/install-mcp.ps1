param(
  [Parameter(Mandatory = $true)][string]$Target,
  [switch]$Create,
  [switch]$Claude,
  [switch]$Generic,
  [switch]$Codex,
  [string]$VoxelPath = "",
  [switch]$SkipBlender,
  [switch]$SkipVoxel,
  [string]$TerminalPath = "",
  [switch]$Godot
)

$ErrorActionPreference = "Stop"

function Write-Utf8([string]$path, [string]$text) {
  $dir = Split-Path -Parent $path
  if ($dir -and -not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
  }
  $utf8 = New-Object System.Text.UTF8Encoding $false
  [System.IO.File]::WriteAllText($path, $text.TrimEnd() + "`n", $utf8)
}

function Read-Raw([string]$path) {
  if (-not (Test-Path -LiteralPath $path)) { return $null }
  return [System.IO.File]::ReadAllText($path)
}

function Already-Has([string]$raw, [string]$name) {
  return $raw -match ('"' + [regex]::Escape($name) + '"\s*:')
}

function Join-Snippets([string[]]$parts) {
  return (($parts | ForEach-Object { $_.TrimEnd() }) -join ",`n")
}

$py = "python"
$pyCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pyCmd) { $py = "py" }

$kiloBlender = @'
    "blender": {
      "type": "local",
      "command": ["cmd", "/c", "uvx", "blender-mcp"],
      "enabled": true,
      "environment": {
        "BLENDER_HOST": "localhost",
        "BLENDER_PORT": "9876"
      }
    }
'@

$genericBlender = @'
    "blender": {
      "command": "cmd",
      "args": ["/c", "uvx", "blender-mcp"],
      "env": {
        "BLENDER_HOST": "localhost",
        "BLENDER_PORT": "9876"
      }
    }
'@

$voxelCmdJson = ($VoxelPath -replace '\\', '\\')
$kiloVoxel = @"
    "voxelai": {
      "type": "local",
      "command": ["$py", "$voxelCmdJson\\mcp_server"],
      "enabled": true
    }
"@

$genericVoxel = @"
    "voxelai": {
      "command": "$py",
      "args": ["$voxelCmdJson\\mcp_server"]
    }
"@

$kiloTerminal = $null
$genericTerminal = $null
if ($TerminalPath) {
  $tm = ($TerminalPath -replace '\\', '\\')
  $kiloTerminal = @"
    "terminal": {
      "type": "local",
      "command": ["node", "$tm\\bin\\terminalmcp.js", "--tools", "all"],
      "enabled": true
    }
"@
  $genericTerminal = @"
    "terminal": {
      "command": "node",
      "args": ["$tm\\bin\\terminalmcp.js", "--tools", "all"]
    }
"@
}

function Collect-Snippets([bool]$kilo) {
  $list = New-Object System.Collections.Generic.List[string]
  if (-not $SkipBlender) { $list.Add($(if ($kilo) { $kiloBlender } else { $genericBlender })) | Out-Null }
  if (-not $SkipVoxel -and $VoxelPath) { $list.Add($(if ($kilo) { $kiloVoxel } else { $genericVoxel })) | Out-Null }
  if ($kiloTerminal) {
    $list.Add($(if ($kilo) { $kiloTerminal } else { $genericTerminal })) | Out-Null
  }
  return @($list)
}

function Inject-McpServers {
  param(
    [string]$Path,
    [string]$WrapperKey,
    [string[]]$NamedSnippets,
    [string[]]$Names,
    [string]$EmptyDoc
  )

  if ($NamedSnippets.Count -eq 0) { return }

  $raw = Read-Raw $Path
  if ($null -eq $raw -or $raw.Trim() -eq "") {
    Write-Utf8 $Path $EmptyDoc
    return
  }

  $missing = @()
  for ($i = 0; $i -lt $Names.Count; $i++) {
    if (-not (Already-Has $raw $Names[$i])) {
      $missing += $NamedSnippets[$i]
    }
  }
  if ($missing.Count -eq 0) {
    Write-Host "MCP already present in $Path"
    return
  }

  $inject = Join-Snippets $missing

  if ($raw -match [regex]::Escape('"' + $WrapperKey + '"') + '\s*:\s*\{') {
    $raw2 = [regex]::Replace(
      $raw,
      ('("' + [regex]::Escape($WrapperKey) + '"\s*:\s*\{)'),
      ('$1' + "`n" + $inject + ","),
      1
    )
    if ($raw2 -ne $raw) {
      Write-Utf8 $Path $raw2
      return
    }
  }

  $trimmed = $raw.TrimEnd()
  if ($trimmed.EndsWith("}")) {
    $comma = ","
    if ($trimmed -match '\{\s*\}$') { $comma = "" }
    $insert = $comma + "`n  `"$WrapperKey`": {`n" + $inject + "`n  }`n}"
    $raw2 = $trimmed.Substring(0, $trimmed.Length - 1).TrimEnd().TrimEnd(",") + $insert
    Write-Utf8 $Path $raw2
    return
  }

  Write-Host "WARN: could not inject MCP into $Path"
}

$kiloSnips = Collect-Snippets $true
$genSnips = Collect-Snippets $false
$names = @()
if (-not $SkipBlender) { $names += "blender" }
if (-not $SkipVoxel -and $VoxelPath) { $names += "voxelai" }
if ($TerminalPath) { $names += "terminal" }

$emptyInner = Join-Snippets $genSnips
$kiloInner = Join-Snippets $kiloSnips

$emptyClaude = @"
{
  "mcpServers": {
$emptyInner
  }
}
"@

$emptyKilo = @"
{
  "`$schema": "https://app.kilo.ai/config.json",
  "mcp": {
$kiloInner
  }
}
"@

if ($Claude -or $Generic) {
  Inject-McpServers -Path $Target -WrapperKey "mcpServers" -NamedSnippets $genSnips -Names $names -EmptyDoc $emptyClaude
  return
}

if ($Codex) {
  # TOML injection into Codex config.toml
  $raw = Read-Raw $Target
  if ($null -eq $raw) { Write-Host "WARN no $Target"; return }
  $sections = @()
  $tmLiteral = $TerminalPath -replace "'", "''"
  if (-not $SkipBlender -and ($raw -notmatch '\[mcp_servers\.blender\]')) {
    $sections += @"

[mcp_servers.blender]
command = 'cmd'
args = ['/c', 'uvx', 'blender-mcp']
[mcp_servers.blender.env]
BLENDER_HOST = 'localhost'
BLENDER_PORT = '9876'
"@
  }
  if (-not $SkipVoxel -and $VoxelPath -and ($raw -notmatch '\[mcp_servers\.voxelai\]')) {
    $vlLiteral = $VoxelPath -replace "'", "''"
    $sections += @"

[mcp_servers.voxelai]
command = '$py'
args = ['$vlLiteral\mcp_server']
"@
  }
  if ($TerminalPath -and ($raw -notmatch '\[mcp_servers\.terminal\]')) {
    $sections += @"

[mcp_servers.terminal]
command = 'node'
args = ['$tmLiteral\bin\terminalmcp.js', '--tools', 'all']
"@
  }
  if ($sections.Count -eq 0) { Write-Host "MCP already present in $Target"; return }
  $appended = ($raw.TrimEnd() + ($sections -join "")) + "`n"
  Write-Utf8 $Target $appended
  Write-Host "OK TOML   $Target"
  return
}

if (-not (Test-Path -LiteralPath $Target) -and -not $Create) { return }
Inject-McpServers -Path $Target -WrapperKey "mcp" -NamedSnippets $kiloSnips -Names $names -EmptyDoc $emptyKilo
