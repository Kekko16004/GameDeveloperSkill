#!/usr/bin/env pwsh
# Setup Git LFS for game assets

param(
    [string]$ProjectPath = ".",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Git LFS Auto-Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Git LFS
if (-not (Get-Command git-lfs -ErrorAction SilentlyContinue)) {
    Write-Host "[X] Git LFS not installed" -ForegroundColor Red
    Write-Host "Install: winget install GitHub.GitLFS" -ForegroundColor Yellow
    Write-Host "Or: https://git-lfs.github.com/" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Git LFS detected: $(git lfs version)" -ForegroundColor Green

# Navigate
Set-Location $ProjectPath

# Check Git repo
if (-not (Test-Path .git)) {
    Write-Host "[X] Not a Git repository" -ForegroundColor Red
    Write-Host "Run: git init" -ForegroundColor Yellow
    exit 1
}

# Init LFS
Write-Host ""
Write-Host "[*] Initializing Git LFS..." -ForegroundColor Yellow
git lfs install

# .gitattributes
$gitattributesPath = ".gitattributes"
$hasExisting = Test-Path $gitattributesPath

if ($hasExisting -and -not $Force) {
    Write-Host "[!] .gitattributes exists" -ForegroundColor Yellow
    $overwrite = Read-Host "Overwrite? (y/n)"
    if ($overwrite -ne "y") {
        Write-Host "Aborted" -ForegroundColor Gray
        exit 0
    }
}

# Generate .gitattributes
Write-Host "[*] Generating .gitattributes..." -ForegroundColor Yellow

$content = @"
# Git LFS - GameDeveloperSkill
# Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm")

# 3D Models
*.fbx filter=lfs diff=lfs merge=lfs -text
*.glb filter=lfs diff=lfs merge=lfs -text
*.gltf filter=lfs diff=lfs merge=lfs -text
*.obj filter=lfs diff=lfs merge=lfs -text
*.blend filter=lfs diff=lfs merge=lfs -text

# Textures
*.png filter=lfs diff=lfs merge=lfs -text
*.jpg filter=lfs diff=lfs merge=lfs -text
*.jpeg filter=lfs diff=lfs merge=lfs -text
*.tga filter=lfs diff=lfs merge=lfs -text
*.psd filter=lfs diff=lfs merge=lfs -text
*.exr filter=lfs diff=lfs merge=lfs -text
*.hdr filter=lfs diff=lfs merge=lfs -text

# Audio
*.wav filter=lfs diff=lfs merge=lfs -text
*.mp3 filter=lfs diff=lfs merge=lfs -text
*.ogg filter=lfs diff=lfs merge=lfs -text

# Video
*.mp4 filter=lfs diff=lfs merge=lfs -text
*.mov filter=lfs diff=lfs merge=lfs -text

# Archives
*.zip filter=lfs diff=lfs merge=lfs -text
*.7z filter=lfs diff=lfs merge=lfs -text

# Exclude metadata
*.json -filter -diff -merge text
*.txt -filter -diff -merge text
*.md -filter -diff -merge text
"@

$content | Set-Content $gitattributesPath -Encoding UTF8

Write-Host "[OK] .gitattributes created" -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Git LFS Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next: git add .gitattributes && git commit -m 'Setup Git LFS'" -ForegroundColor Cyan
