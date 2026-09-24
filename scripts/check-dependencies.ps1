#!/usr/bin/env pwsh
# Check all dependencies for GameDeveloperSkill

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  GameDeveloperSkill - Dependency Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$hasErrors = $false

# Check Python
Write-Host "[*] Checking Python..." -ForegroundColor Yellow
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pyVersion = python --version
    Write-Host "  [OK] $pyVersion" -ForegroundColor Green
} else {
    Write-Host "  [X] Python not found" -ForegroundColor Red
    Write-Host "      Install: https://www.python.org/downloads/" -ForegroundColor Gray
    $hasErrors = $true
}

# Check Node.js
Write-Host "[*] Checking Node.js..." -ForegroundColor Yellow
if (Get-Command node -ErrorAction SilentlyContinue) {
    $nodeVersion = node --version
    Write-Host "  [OK] Node.js $nodeVersion" -ForegroundColor Green
} else {
    Write-Host "  [X] Node.js not found" -ForegroundColor Red
    Write-Host "      Install: https://nodejs.org/" -ForegroundColor Gray
    $hasErrors = $true
}

# Check Git
Write-Host "[*] Checking Git..." -ForegroundColor Yellow
if (Get-Command git -ErrorAction SilentlyContinue) {
    $gitVersion = git --version
    Write-Host "  [OK] $gitVersion" -ForegroundColor Green
} else {
    Write-Host "  [X] Git not found" -ForegroundColor Red
    Write-Host "      Install: https://git-scm.com/" -ForegroundColor Gray
    $hasErrors = $true
}

# Check Git LFS
Write-Host "[*] Checking Git LFS..." -ForegroundColor Yellow
if (Get-Command git-lfs -ErrorAction SilentlyContinue) {
    $lfsVersion = git lfs version
    Write-Host "  [OK] $lfsVersion" -ForegroundColor Green
} else {
    Write-Host "  [!] Git LFS not found (optional)" -ForegroundColor Yellow
    Write-Host "      Install: winget install GitHub.GitLFS" -ForegroundColor Gray
}

# Check Blender
Write-Host "[*] Checking Blender..." -ForegroundColor Yellow
if (Get-Command blender -ErrorAction SilentlyContinue) {
    $blenderVersion = blender --version 2>&1 | Select-Object -First 1
    Write-Host "  [OK] $blenderVersion" -ForegroundColor Green
} else {
    Write-Host "  [!] Blender not found (optional)" -ForegroundColor Yellow
    Write-Host "      Install: https://www.blender.org/download/" -ForegroundColor Gray
}

# Check Unity
Write-Host "[*] Checking Unity..." -ForegroundColor Yellow
$unityPath = "C:\Program Files\Unity\Hub\Editor\*\Editor\Unity.exe"
if (Test-Path $unityPath) {
    Write-Host "  [OK] Unity installed" -ForegroundColor Green
} else {
    Write-Host "  [!] Unity not found (optional)" -ForegroundColor Yellow
    Write-Host "      Install: https://unity.com/download" -ForegroundColor Gray
}

# Check Godot
Write-Host "[*] Checking Godot..." -ForegroundColor Yellow
if (Get-Command godot -ErrorAction SilentlyContinue) {
    Write-Host "  [OK] Godot installed" -ForegroundColor Green
} else {
    Write-Host "  [!] Godot not found (optional)" -ForegroundColor Yellow
    Write-Host "      Install: https://godotengine.org/download/" -ForegroundColor Gray
}

# Check Unreal
Write-Host "[*] Checking Unreal Engine..." -ForegroundColor Yellow
$unrealPath = "C:\Program Files\Epic Games\UE_*"
if (Test-Path $unrealPath) {
    Write-Host "  [OK] Unreal Engine installed" -ForegroundColor Green
} else {
    Write-Host "  [!] Unreal Engine not found (optional)" -ForegroundColor Yellow
    Write-Host "      Install: https://www.unrealengine.com/download" -ForegroundColor Gray
}

# Check config file
Write-Host "[*] Checking config..." -ForegroundColor Yellow
$configPath = Join-Path $PSScriptRoot "..\game-developer\config.json"
if (Test-Path $configPath) {
    Write-Host "  [OK] config.json exists" -ForegroundColor Green
} else {
    Write-Host "  [!] config.json not found" -ForegroundColor Yellow
    Write-Host "      Copy from: game-developer\config.example.json" -ForegroundColor Gray
}

Write-Host ""
if ($hasErrors) {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  [X] Some required dependencies missing" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    exit 1
} else {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  [OK] All required dependencies ready!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
}
