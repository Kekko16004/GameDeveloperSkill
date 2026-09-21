param(
  [Parameter(Mandatory = $true)][string]$ProjectPath,
  [ValidateSet("rpg", "interface", "impact", "digital", "all")]
  [string]$Pack = "all"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$audioArtDir = Join-Path $ProjectPath "art\cc0\audio"
$unityAudioDir = Join-Path $ProjectPath "Assets\_Game\Audio"
$unityScriptsDir = Join-Path $ProjectPath "Assets\_Game\Scripts\Audio"

New-Item -ItemType Directory -Force -Path $audioArtDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $unityAudioDir "SFX") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $unityAudioDir "Ambience") | Out-Null
New-Item -ItemType Directory -Force -Path $unityScriptsDir | Out-Null

$catalog = @{
  rpg       = @{ Name = "kenney_rpg-audio.zip"; Url = "https://kenney.nl/media/pages/assets/rpg-audio/8e99002d76-1677590336/kenney_rpg-audio.zip" }
  interface = @{ Name = "kenney_interface-sounds.zip"; Url = "https://kenney.nl/media/pages/assets/interface-sounds/fa43c1dd4d-1677589452/kenney_interface-sounds.zip" }
  impact    = @{ Name = "kenney_impact-sounds.zip"; Url = "https://kenney.nl/media/pages/assets/impact-sounds/87b4ddecda-1677589768/kenney_impact-sounds.zip" }
  digital   = @{ Name = "kenney_digital-audio.zip"; Url = "https://kenney.nl/media/pages/assets/digital-audio/216eac4753-1677590265/kenney_digital-audio.zip" }
}

$keys = if ($Pack -eq "all") { @("rpg", "interface", "impact") } else { @($Pack) }

foreach ($k in $keys) {
  $item = $catalog[$k]
  $zipPath = Join-Path $audioArtDir $item.Name
  $extractDir = Join-Path $audioArtDir $k

  if (-not (Test-Path -LiteralPath $zipPath) -or ((Get-Item -LiteralPath $zipPath).Length -lt 1000)) {
    Write-Host "DOWNLOAD Audio: $($item.Name)"
    Invoke-WebRequest -Uri $item.Url -OutFile $zipPath -UseBasicParsing -UserAgent "Mozilla/5.0"
  } else {
    Write-Host "SKIP download: $($item.Name) (cached)"
  }

  if (-not (Test-Path -LiteralPath $extractDir)) {
    Write-Host "EXTRACT: $($item.Name)"
    Expand-Archive -LiteralPath $zipPath -DestinationPath $extractDir -Force
  }

  $audioFiles = Get-ChildItem -Path $extractDir -Recurse -Include "*.ogg", "*.wav", "*.mp3" -File
  foreach ($f in $audioFiles) {
    $targetSub = if ($f.Name -like "*ambien*" -or $f.Name -like "*loop*" -or $f.Name -like "*wind*") { "Ambience" } else { "SFX" }
    $destFile = Join-Path (Join-Path $unityAudioDir $targetSub) $f.Name
    if (-not (Test-Path -LiteralPath $destFile)) {
      Copy-Item -LiteralPath $f.FullName -Destination $destFile -Force
    }
  }
}

$mgrSrc = Join-Path $ScriptDir "AudioManager.cs"
$mgrDest = Join-Path $unityScriptsDir "AudioManager.cs"
if (Test-Path -LiteralPath $mgrSrc) {
  Copy-Item -LiteralPath $mgrSrc -Destination $mgrDest -Force
  Write-Host "COPIED AudioManager.cs -> $mgrDest"
}

$indexContent = @"
# Audio CC0 Library Index (Kenney Audio)

Packs scaricati e organizzati in `Assets/_Game/Audio/`:
- **SFX**: Suoni di passi, interazioni con porte, bauli, urti, campane, click UI.
- **Ambience**: Loop sonori atmosferici di sottofondo.
- **AudioManager.cs**: Singleton installato in `Assets/_Game/Scripts/Audio/AudioManager.cs`.

Licenza: Creative Commons Zero (CC0) - Pubblico Dominio.
"@

Set-Content -LiteralPath (Join-Path $audioArtDir "AUDIO_INDEX.md") -Value $indexContent -Encoding UTF8
Write-Host "OK Audio pipeline setup completed for $ProjectPath"
