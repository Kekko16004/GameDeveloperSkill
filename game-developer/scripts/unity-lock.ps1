# Unity Editor lock — one Editor, many workers. Workers author JSON/specs in parallel, but only the lock holder
# runs `unity command` (recompile, gds_build/world/village, gds_lint, run_tests, play, shot).
#   powershell -File SKILL/scripts/unity-lock.ps1 -ProjectPath PROJECT -Owner level-build:house_a          # acquire (waits)
#   powershell -File SKILL/scripts/unity-lock.ps1 -ProjectPath PROJECT -Owner level-build:house_a -Release # release
# A lock older than -StaleMinutes is considered abandoned (crashed worker) and taken over.
param(
  [Parameter(Mandatory)][string]$ProjectPath,
  [Parameter(Mandatory)][string]$Owner,
  [switch]$Release,
  [int]$StaleMinutes = 10,
  [int]$TimeoutMinutes = 20
)
$ErrorActionPreference = 'Stop'
$dir = Join-Path $ProjectPath 'Temp'
$lock = Join-Path $dir 'gds-unity.lock'
New-Item -ItemType Directory -Force -Path $dir | Out-Null

if ($Release) {
  if ((Test-Path -LiteralPath $lock) -and -not ((Get-Content -LiteralPath $lock -Raw) -like "$Owner|*")) {
    Write-Output "{`"lock`":`"not-owner`",`"owner`":`"$Owner`"}"; exit 0
  }
  Remove-Item -LiteralPath $lock -Force -ErrorAction SilentlyContinue
  Write-Output "{`"lock`":`"released`",`"owner`":`"$Owner`"}"
  exit 0
}

$deadline = (Get-Date).AddMinutes($TimeoutMinutes)
while ($true) {
  try {
    # CreateNew fails if the file exists: atomic acquire.
    $fs = [System.IO.File]::Open($lock, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes("$Owner|$(Get-Date -Format s)")
    $fs.Write($bytes, 0, $bytes.Length); $fs.Close()
    Write-Output "{`"lock`":`"acquired`",`"owner`":`"$Owner`"}"
    exit 0
  } catch [System.IO.IOException] {
    $item = Get-Item -LiteralPath $lock -ErrorAction SilentlyContinue
    if ($item -and $item.LastWriteTime -lt (Get-Date).AddMinutes(-$StaleMinutes)) {
      Remove-Item -LiteralPath $lock -Force -ErrorAction SilentlyContinue
      continue
    }
    $holder = if ($item) { (Get-Content -LiteralPath $lock -Raw -ErrorAction SilentlyContinue) } else { '' }
    if ((Get-Date) -gt $deadline) {
      Write-Output "{`"lock`":`"timeout`",`"holder`":`"$holder`"}"
      exit 1
    }
    if ($holder -like "$Owner|*") { Write-Output "{`"lock`":`"already-held`",`"owner`":`"$Owner`"}"; exit 0 }
    Start-Sleep -Seconds 10
  }
}
