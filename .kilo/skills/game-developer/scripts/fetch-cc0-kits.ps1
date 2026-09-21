param(
  [Parameter(Mandatory = $true)][string]$ProjectPath,
  [ValidateSet("medieval", "dungeon", "scifi", "city", "pirate", "interior", "prototype", "nature", "characters", "vfx", "all")]
  [string]$Genre = "medieval"
)

$ErrorActionPreference = "Stop"
$SkillRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Fetch = Join-Path $SkillRoot "scripts\cc0-fetch.ps1"

$artDir = Join-Path $ProjectPath "art\cc0"
New-Item -ItemType Directory -Force -Path $artDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $ProjectPath "Assets\_Game\Art\Kits") | Out-Null

$kenney = @{
  dungeon   = @{ Name = "kenney_modular-dungeon-kit_1.0.zip"; Url = "https://kenney.nl/media/pages/assets/modular-dungeon-kit/7bed87605b-1771926065/kenney_modular-dungeon-kit_1.0.zip" }
  castle    = @{ Name = "kenney_castle-kit.zip"; Url = "https://kenney.nl/media/pages/assets/castle-kit/a395102d20-1711543616/kenney_castle-kit.zip" }
  furniture = @{ Name = "kenney_furniture-kit.zip"; Url = "https://kenney.nl/media/pages/assets/furniture-kit/440e0608a4-1677580847/kenney_furniture-kit.zip" }
  space     = @{ Name = "kenney_modular-space-kit_1.0.zip"; Url = "https://kenney.nl/media/pages/assets/modular-space-kit/8261428a47-1771146076/kenney_modular-space-kit_1.0.zip" }
  pirate    = @{ Name = "kenney_pirate-kit.zip"; Url = "https://kenney.nl/media/pages/assets/pirate-kit/e6d4bb1525-1771333093/kenney_pirate-kit.zip" }
  suburban  = @{ Name = "kenney_city-kit-suburban_20.zip"; Url = "https://kenney.nl/media/pages/assets/city-kit-suburban/2c871b7af2-1745479373/kenney_city-kit-suburban_20.zip" }
  nature    = @{ Name = "kenney_nature-kit.zip"; Url = "https://kenney.nl/media/pages/assets/nature-kit/37ac38a37b-1677698939/kenney_nature-kit.zip" }
  minidungeon = @{ Name = "kenney_mini-dungeon.zip"; Url = "https://kenney.nl/media/pages/assets/mini-dungeon/6cd72dc849-1785314274/kenney_mini-dungeon.zip" }
  prototype = @{ Name = "kenney_prototype-kit.zip"; Url = "https://kenney.nl/media/pages/assets/prototype-kit/4d3b7073ed-1724832076/kenney_prototype-kit.zip" }
  charsProtagonists = @{ Name = "kenney_animated-characters-protagonists.zip"; Url = "https://kenney.nl/media/pages/assets/animated-characters-protagonists/608191acc4-1774773108/kenney_animated-characters-protagonists.zip" }
  charsSurvivors = @{ Name = "kenney_animated-characters-survivors.zip"; Url = "https://kenney.nl/media/pages/assets/animated-characters-survivors/27b16052a7-1774772958/kenney_animated-characters-survivors.zip" }
  charsRetro = @{ Name = "kenney_animated-characters-retro.zip"; Url = "https://kenney.nl/media/pages/assets/animated-characters-retro/93305a3c49-1774772819/kenney_animated-characters-retro.zip" }
  particles = @{ Name = "kenney_particle-pack.zip"; Url = "https://kenney.nl/media/pages/assets/particle-pack/f8fe0f8cb8-1677578741/kenney_particle-pack.zip" }
}

$kaykit = @{
  dungeon     = "https://github.com/KayKit-Game-Assets/KayKit-Dungeon-Remastered-1.0.git"
  medieval    = "https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0.git"
  furniture   = "https://github.com/KayKit-Game-Assets/KayKit-Furniture-Bits-1.0.git"
  space       = "https://github.com/KayKit-Game-Assets/KayKit-Space-Base-Bits-1.0.git"
  city        = "https://github.com/KayKit-Game-Assets/KayKit-City-Builder-Bits-1.0.git"
  prototype   = "https://github.com/KayKit-Game-Assets/KayKit-Prototype-Bits-1.0.git"
  adventurers = "https://github.com/KayKit-Game-Assets/KayKit-Character-Pack-Adventures-1.0.git"
  skeletons   = "https://github.com/KayKit-Game-Assets/KayKit-Character-Pack-Skeletons-1.0.git"
}

function Get-Kenney([string]$key) {
  $pack = $kenney[$key]
  $destDir = Join-Path $artDir "kenney"
  if (Test-Path -LiteralPath $Fetch) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $Fetch -Url $pack.Url -OutDir $destDir -Name $pack.Name
  } else {
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null
    $dest = Join-Path $destDir $pack.Name
    Invoke-WebRequest -Uri $pack.Url -OutFile $dest -UseBasicParsing -UserAgent "GameDeveloperSkill/1.0"
    Expand-Archive -LiteralPath $dest -DestinationPath (Join-Path $destDir ([IO.Path]::GetFileNameWithoutExtension($pack.Name))) -Force
  }
}

function Get-Kay([string]$key) {
  $url = $kaykit[$key]
  $name = ($url.TrimEnd(".git") -split "/")[-1]
  $dest = Join-Path $artDir $name
  if (Test-Path -LiteralPath $dest) {
    Write-Host "SKIP clone $name (exists)"
    return
  }
  Write-Host "CLONE $url"
  git clone --depth 1 $url $dest
}

switch ($Genre) {
  "medieval" {
    Get-Kenney "castle"
    Get-Kenney "furniture"
    Get-Kenney "nature"
    Get-Kay "medieval"
    Get-Kay "adventurers"
  }
  "dungeon" {
    Get-Kenney "dungeon"
    Get-Kenney "furniture"
    Get-Kay "dungeon"
    Get-Kay "skeletons"
  }
  "scifi" {
    Get-Kenney "space"
    Get-Kay "space"
  }
  "city" {
    Get-Kenney "suburban"
    Get-Kay "city"
  }
  "pirate" {
    Get-Kenney "pirate"
  }
  "interior" {
    Get-Kenney "furniture"
    Get-Kay "furniture"
  }
  "prototype" {
    Get-Kay "prototype"
    Get-Kenney "prototype"
  }
  "nature" {
    Get-Kenney "nature"
  }
  "characters" {
    Get-Kenney "charsProtagonists"
    Get-Kenney "charsSurvivors"
    Get-Kenney "charsRetro"
    Get-Kenney "minidungeon"
    Get-Kay "adventurers"
    Get-Kay "skeletons"
    Write-Host "Quaternius Universal Animation Library / Base Characters: itch download button (CC0) -> art/cc0/quaternius/  https://quaternius.itch.io/universal-animation-library"
  }
  "vfx" {
    Get-Kenney "particles"
  }
  "all" {
    foreach ($k in $kenney.Keys) { Get-Kenney $k }
    foreach ($k in $kaykit.Keys) { Get-Kay $k }
  }
}

Write-Host "OK kits in $artDir"
Write-Host "Pick ONE family per slice. Ledger every file. Do not mix Kenney + KayKit in the same room."
