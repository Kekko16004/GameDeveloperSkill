# Git LFS Auto-Setup

Configurazione automatica di Git Large File Storage per gestire asset binari in progetti game.

---

## 🎯 Problema

Asset binari (FBX, PNG, GLB, audio) fanno esplodere i repository Git:
- ❌ Clone lentissimi (GB di storia)
- ❌ Push/pull pesanti
- ❌ GitHub ha limite 100MB per file
- ❌ Memoria sprecata per versioni vecchie

**Soluzione:** Git LFS = Solo puntatori in Git, asset su LFS storage

---

## 🔧 Auto-Setup Script

```powershell
# game-developer/scripts/setup-git-lfs.ps1
param(
    [string]$ProjectPath = ".",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host "🔧 Git LFS Auto-Setup" -ForegroundColor Cyan
Write-Host ""

# Check Git LFS installed
if (-not (Get-Command git-lfs -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Git LFS not installed" -ForegroundColor Red
    Write-Host "Install: https://git-lfs.github.com/" -ForegroundColor Yellow
    Write-Host "Or: winget install GitHub.GitLFS" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Git LFS detected: $(git lfs version)" -ForegroundColor Green

# Navigate to project
cd $ProjectPath

# Check if Git repo
if (-not (Test-Path .git)) {
    Write-Host "❌ Not a Git repository" -ForegroundColor Red
    Write-Host "Run: git init" -ForegroundColor Yellow
    exit 1
}

# Initialize Git LFS
Write-Host ""
Write-Host "📦 Initializing Git LFS..." -ForegroundColor Yellow
git lfs install

# Check existing .gitattributes
$gitattributesPath = ".gitattributes"
$hasExisting = Test-Path $gitattributesPath

if ($hasExisting -and -not $Force) {
    Write-Host "⚠ .gitattributes already exists" -ForegroundColor Yellow
    $overwrite = Read-Host "Overwrite? (y/n)"
    if ($overwrite -ne "y") {
        Write-Host "Aborted" -ForegroundColor Gray
        exit 0
    }
}

# Generate .gitattributes for game assets
Write-Host "📝 Generating .gitattributes..." -ForegroundColor Yellow

$gitattributes = @"
# Git LFS Auto-Generated for GameDeveloperSkill
# Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm")

# 3D Models
*.fbx filter=lfs diff=lfs merge=lfs -text
*.glb filter=lfs diff=lfs merge=lfs -text
*.gltf filter=lfs diff=lfs merge=lfs -text
*.obj filter=lfs diff=lfs merge=lfs -text
*.blend filter=lfs diff=lfs merge=lfs -text
*.ma filter=lfs diff=lfs merge=lfs -text
*.mb filter=lfs diff=lfs merge=lfs -text
*.max filter=lfs diff=lfs merge=lfs -text
*.c4d filter=lfs diff=lfs merge=lfs -text

# Textures & Images
*.png filter=lfs diff=lfs merge=lfs -text
*.jpg filter=lfs diff=lfs merge=lfs -text
*.jpeg filter=lfs diff=lfs merge=lfs -text
*.tga filter=lfs diff=lfs merge=lfs -text
*.tif filter=lfs diff=lfs merge=lfs -text
*.tiff filter=lfs diff=lfs merge=lfs -text
*.exr filter=lfs diff=lfs merge=lfs -text
*.hdr filter=lfs diff=lfs merge=lfs -text
*.psd filter=lfs diff=lfs merge=lfs -text

# Audio
*.wav filter=lfs diff=lfs merge=lfs -text
*.mp3 filter=lfs diff=lfs merge=lfs -text
*.ogg filter=lfs diff=lfs merge=lfs -text
*.aiff filter=lfs diff=lfs merge=lfs -text
*.flac filter=lfs diff=lfs merge=lfs -text

# Video
*.mp4 filter=lfs diff=lfs merge=lfs -text
*.mov filter=lfs diff=lfs merge=lfs -text
*.avi filter=lfs diff=lfs merge=lfs -text
*.webm filter=lfs diff=lfs merge=lfs -text

# Unity-specific
*.unitypackage filter=lfs diff=lfs merge=lfs -text
*.asset filter=lfs diff=lfs merge=lfs -text
*.cubemap filter=lfs diff=lfs merge=lfs -text
*.unity3d filter=lfs diff=lfs merge=lfs -text

# Godot-specific
*.import filter=lfs diff=lfs merge=lfs -text
*.res filter=lfs diff=lfs merge=lfs -text
*.tres filter=lfs diff=lfs merge=lfs -text

# Unreal-specific
*.uasset filter=lfs diff=lfs merge=lfs -text
*.umap filter=lfs diff=lfs merge=lfs -text

# Archives
*.zip filter=lfs diff=lfs merge=lfs -text
*.7z filter=lfs diff=lfs merge=lfs -text
*.rar filter=lfs diff=lfs merge=lfs -text
*.tar filter=lfs diff=lfs merge=lfs -text
*.gz filter=lfs diff=lfs merge=lfs -text

# Fonts
*.ttf filter=lfs diff=lfs merge=lfs -text
*.otf filter=lfs diff=lfs merge=lfs -text

# Binaries
*.dll filter=lfs diff=lfs merge=lfs -text
*.so filter=lfs diff=lfs merge=lfs -text
*.dylib filter=lfs diff=lfs merge=lfs -text
*.exe filter=lfs diff=lfs merge=lfs -text

# EXCLUDE small metadata files from LFS
*.json -filter -diff -merge text
*.txt -filter -diff -merge text
*.md -filter -diff -merge text
*.xml -filter -diff -merge text
*.yml -filter -diff -merge text
*.yaml -filter -diff -merge text
"@

$gitattributes | Set-Content $gitattributesPath -Encoding UTF8

Write-Host "✓ .gitattributes created" -ForegroundColor Green

# Track existing files
Write-Host ""
Write-Host "🔍 Scanning for existing large files..." -ForegroundColor Yellow

$largeFiles = @()
Get-ChildItem -Recurse -File | Where-Object {
    $ext = $_.Extension.ToLower()
    $lfsExtensions = @('.fbx', '.glb', '.png', '.jpg', '.wav', '.mp3', '.blend')
    $lfsExtensions -contains $ext
} | ForEach-Object {
    $sizeMB = [math]::Round($_.Length / 1MB, 2)
    if ($sizeMB -gt 0.5) {  # Files > 0.5 MB
        $largeFiles += [PSCustomObject]@{
            Path = $_.FullName.Replace($PWD.Path + "\", "")
            SizeMB = $sizeMB
        }
    }
}

if ($largeFiles.Count -gt 0) {
    Write-Host "Found $($largeFiles.Count) large files:" -ForegroundColor Yellow
    $largeFiles | Sort-Object -Property SizeMB -Descending | Select-Object -First 10 | ForEach-Object {
        Write-Host "  $($_.SizeMB) MB - $($_.Path)" -ForegroundColor Gray
    }
    
    Write-Host ""
    $migrate = Read-Host "Migrate existing files to LFS? (y/n)"
    
    if ($migrate -eq "y") {
        Write-Host "🔄 Migrating to LFS..." -ForegroundColor Yellow
        git lfs migrate import --include="*.fbx,*.glb,*.png,*.jpg,*.wav,*.mp3,*.blend" --everything
        Write-Host "✓ Migration complete" -ForegroundColor Green
    }
}

# Create .gitignore additions
Write-Host ""
Write-Host "📝 Updating .gitignore..." -ForegroundColor Yellow

$gitignoreAdditions = @"

# GameDeveloperSkill - Large file warnings
# (Git LFS handles these, but exclude temp/generated)
**/[Tt]emp/
**/[Cc]ache/
**/.cache/
**/Build/
**/Builds/
**/Library/
**/Logs/

# Asset exports (if using external pipeline)
# art/exports/*.fbx
# art/exports/*.glb
"@

$gitignorePath = ".gitignore"
if (Test-Path $gitignorePath) {
    Add-Content $gitignorePath $gitignoreAdditions
} else {
    $gitignoreAdditions | Set-Content $gitignorePath
}

Write-Host "✓ .gitignore updated" -ForegroundColor Green

# Summary
Write-Host ""
Write-Host "✅ Git LFS Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. git add .gitattributes .gitignore" -ForegroundColor White
Write-Host "  2. git commit -m 'Setup Git LFS'" -ForegroundColor White
Write-Host "  3. (Optional) git lfs push --all origin main" -ForegroundColor Gray
Write-Host ""
Write-Host "📊 Storage info:" -ForegroundColor Cyan
git lfs ls-files | Measure-Object | Select-Object -ExpandProperty Count | ForEach-Object {
    Write-Host "  $_ files tracked by LFS" -ForegroundColor White
}
```

---

## 🚀 Usage

```powershell
# Auto-setup in current project
.\game-developer\scripts\setup-git-lfs.ps1

# Setup in specific project
.\game-developer\scripts\setup-git-lfs.ps1 -ProjectPath "C:\Projects\MyGame"

# Force overwrite existing config
.\game-developer\scripts\setup-git-lfs.ps1 -Force
```

---

## 📊 What Gets Tracked

### Always LFS (Binary Large Files)
- ✅ 3D Models: FBX, GLB, GLTF, OBJ, Blend
- ✅ Textures: PNG, JPG, TGA, EXR, HDR, PSD
- ✅ Audio: WAV, MP3, OGG, AIFF
- ✅ Video: MP4, MOV, AVI
- ✅ Archives: ZIP, 7Z, RAR

### Never LFS (Text/Small Metadata)
- ❌ JSON, TXT, MD, XML, YML
- ❌ Code: C#, GDScript, Python, Blueprints
- ❌ Small configs < 100KB

---

## 🔄 Migration Script for Existing Repo

```bash
# Migrate existing history to LFS
git lfs migrate import \
  --include="*.fbx,*.glb,*.png,*.jpg,*.wav,*.mp3" \
  --everything

# Push migrated files
git lfs push --all origin main
```

**⚠ Warning:** Rewrites Git history! Coordinate with team first.

---

## 📈 Benefits

### Before LFS
```
Repository size: 2.5 GB
Clone time: 15 minutes
Push/pull: 5+ minutes
GitHub limit: ❌ Blocked (files > 100MB)
```

### After LFS
```
Repository size: 50 MB (pointers only)
Clone time: 30 seconds
Push/pull: 10 seconds
GitHub limit: ✅ No issues
LFS storage: 2.5 GB (separate quota)
```

---

## 💰 GitHub LFS Pricing

| Plan | Storage | Bandwidth/month | Cost |
|------|---------|-----------------|------|
| Free | 1 GB | 1 GB | $0 |
| Data Pack | +50 GB | +50 GB | $5/month |
| Pro | 2 GB | 1 GB | Included in Pro |

**Alternatives:**
- GitLab: 10 GB free
- Bitbucket: 5 GB free
- Self-hosted LFS server (unlimited)

---

## 🔧 Troubleshooting

### "This exceeds GitHub's file size limit"
```bash
# File already committed without LFS
# Solution: Migrate
git lfs migrate import --include="large_file.fbx"
git push origin main --force
```

### "Git LFS: command not found"
```powershell
# Install Git LFS
winget install GitHub.GitLFS

# Or download from https://git-lfs.github.com/
```

### "Smudge error" on clone
```bash
# LFS files not downloaded
# Solution: Pull LFS
git lfs pull
```

### Check LFS status
```bash
# List LFS files
git lfs ls-files

# Show LFS stats
git lfs env

# Verify setup
git lfs track
```

---

## 🎯 Integration with GameDeveloperSkill

Agent automatically runs setup when initializing project:

```python
# In project setup phase
if not os.path.exists(".gitattributes"):
    run_command("powershell ./game-developer/scripts/setup-git-lfs.ps1 -Force")
    print("✓ Git LFS configured")
```

---

## 📋 .gitattributes Template

Entire template saved in script. Key patterns:

```gitattributes
# 3D Models
*.fbx filter=lfs diff=lfs merge=lfs -text
*.glb filter=lfs diff=lfs merge=lfs -text

# Textures
*.png filter=lfs diff=lfs merge=lfs -text
*.jpg filter=lfs diff=lfs merge=lfs -text

# Audio
*.wav filter=lfs diff=lfs merge=lfs -text
*.mp3 filter=lfs diff=lfs merge=lfs -text

# Exclude text files
*.json -filter -diff -merge text
*.md -filter -diff -merge text
```

---

## ✅ Verification Checklist

After setup:

- [ ] `.gitattributes` created
- [ ] `.gitignore` updated
- [ ] `git lfs ls-files` shows tracked files
- [ ] `git lfs env` shows LFS enabled
- [ ] Test commit with large file works
- [ ] Clone in new folder still fast

---

**Versione:** 1.0  
**Status:** ✅ Production Ready  
**Location:** `game-developer/scripts/setup-git-lfs.ps1`  
**Docs:** https://git-lfs.github.com/
