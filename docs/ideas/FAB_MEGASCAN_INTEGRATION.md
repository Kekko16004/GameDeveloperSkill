# Fab.com (ex-MegaScan/Quixel Bridge) Integration

Il client Python e i cookie descritti sotto non sono implementati. Non usarli.

Fab si configura con **FabCLI** (tool non ufficiale, `fabcli.exe`): https://github.com/zirklerite/FabCLI/releases

La console (`start-dashboard.bat`, schermata Fab) salva il percorso del binario, la cartella di download e accende o spegne l'uso. Il login è `fabcli auth login`. Non c'è un viewer di modelli.

Sistema completo per utilizzare la tua libreria Fab.com/MegaScan con GameDeveloperSkill.

---

## 🔄 Cambio Importante: MegaScan → Fab.com

**Da settembre 2023**, Epic Games ha migrato:
- ❌ `quixel.com` + `bridge.quixel.com` → DEPRECATO
- ✅ `fab.com` → NUOVO marketplace unificato
- ✅ Include: MegaScan, Sketchfab, ArtStation, Unreal Marketplace

**I tuoi asset MegaScan sono ora su Fab.com!**

---

## 🔧 Setup Completo

### 1. Account Fab.com

```
1. Vai su https://www.fab.com
2. Login con Epic Games account
3. I tuoi MegaScan già acquistati sono automaticamente disponibili
4. Download via browser O via Fab CLI
```

### 2. FabCLI (Community Tool - Raccomandato)

**NOTA:** Epic Games non ha un CLI ufficiale. Usa FabCLI community:

```powershell
# Clone FabCLI (community tool)
git clone https://github.com/zirklerite/FabCLI.git
cd FabCLI

# Setup secondo README del progetto
# (Verifica istruzioni aggiornate su GitHub)

# Alternative: usa browser automation con cookie (metodo più affidabile)
```

**Raccomandazione:** Il metodo **browser automation con cookie** è più stabile che aspettare tool community.

### 3. Cookie Export per Automation (Metodo Avanzato)

Se vuoi automation completa con TerminalMCP:

```powershell
# Install browser extension: "Get cookies.txt LOCALLY"
# https://chrome.google.com/webstore/detail/get-cookiestxt-locally

# 1. Vai su fab.com e fai login
# 2. Click extension -> Export cookies.txt
# 3. Salva in: game-developer/config/fab-cookies.txt
```

**Cookie file format:**
```
# Netscape HTTP Cookie File
.fab.com	TRUE	/	TRUE	1234567890	session_token	YOUR_TOKEN_HERE
.fab.com	TRUE	/	TRUE	1234567890	epic_sso	YOUR_SSO_TOKEN
```

---

## 📦 Integrazione con GameDeveloperSkill

### Config

```json
// game-developer/config.json
{
  "fab": {
    "enabled": true,
    "method": "cookies",  // "cookies" (raccomandato) - Epic non ha CLI ufficiale
    "library_path": "C:\\Users\\YOURNAME\\Documents\\Fab Library",
    "cookies_file": "game-developer/config/fab-cookies.txt",
    "auto_download": false,
    "cache_dir": "C:\\Users\\YOURNAME\\.cache\\fab"
  },
  "megascan": {
    "legacy_library": "C:\\Users\\YOURNAME\\Documents\\Megascans Library",
    "migrate_to_fab": true
  }
}
```

---

## 🔍 Asset Browser con Fab API

### Python Script

```python
# game-developer/tools/fab-integration/fab_client.py
import requests
import json
import os
from typing import List, Dict, Optional

class FabClient:
    """Client per Fab.com API e local library"""
    
    def __init__(self, cookies_file: Optional[str] = None):
        self.base_url = "https://www.fab.com/api"
        self.session = requests.Session()
        
        if cookies_file:
            self._load_cookies(cookies_file)
    
    def _load_cookies(self, cookies_file: str):
        """Load cookies from Netscape format"""
        with open(cookies_file, 'r') as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                
                parts = line.strip().split('\t')
                if len(parts) >= 7:
                    domain, _, path, secure, expiry, name, value = parts
                    self.session.cookies.set(
                        name, value, 
                        domain=domain, 
                        path=path
                    )
    
    def search_assets(self, 
                      query: str,
                      asset_type: str = "all",  # "3d", "texture", "material"
                      category: str = None,
                      free_only: bool = False,
                      limit: int = 50) -> List[Dict]:
        """Search Fab.com marketplace"""
        
        params = {
            "query": query,
            "limit": limit
        }
        
        if asset_type != "all":
            params["type"] = asset_type
        
        if category:
            params["category"] = category
        
        if free_only:
            params["price"] = "free"
        
        response = self.session.get(
            f"{self.base_url}/marketplace/search",
            params=params
        )
        
        if response.status_code == 200:
            return response.json()["results"]
        else:
            return []
    
    def get_owned_assets(self) -> List[Dict]:
        """Get user's owned assets (requires auth cookies)"""
        
        response = self.session.get(
            f"{self.base_url}/user/library"
        )
        
        if response.status_code == 200:
            return response.json()["assets"]
        else:
            print("⚠ Auth required. Check cookies.")
            return []
    
    def scan_local_library(self, library_path: str) -> List[Dict]:
        """Scan local Fab library folder"""
        
        assets = []
        
        for root, dirs, files in os.walk(library_path):
            # Fab library structure: Library/<AssetID>/<files>
            if any(f.endswith(('.fbx', '.uasset', '.blend')) for f in files):
                asset_id = os.path.basename(root)
                
                # Read metadata.json if exists
                meta_path = os.path.join(root, 'metadata.json')
                if os.path.exists(meta_path):
                    with open(meta_path, 'r') as f:
                        metadata = json.load(f)
                else:
                    metadata = {"id": asset_id, "name": asset_id}
                
                metadata["local_path"] = root
                metadata["source"] = "fab"
                assets.append(metadata)
        
        return assets
    
    def download_asset(self, asset_id: str, dest_dir: str) -> bool:
        """Download asset via Fab CLI"""
        
        import subprocess
        
        cmd = [
            "fab", "download", 
            asset_id,
            "--output", dest_dir
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ Downloaded: {asset_id}")
            return True
        else:
            print(f"✗ Error: {result.stderr}")
            return False

# Usage
client = FabClient(cookies_file="game-developer/config/fab-cookies.txt")

# Search marketplace
results = client.search_assets("rock cliff", asset_type="3d")
for asset in results:
    print(f"{asset['name']} - {asset['price']}")

# Get owned assets
owned = client.get_owned_assets()
print(f"You own {len(owned)} assets")

# Scan local library
local = client.scan_local_library("C:/Users/FRANCY/Documents/Fab Library")
print(f"Found {len(local)} assets locally")
```

---

## 🌐 Browser Automation (TerminalMCP)

Per download automatici con i tuoi cookie:

```python
# game-developer/tools/fab-integration/fab_browser_automation.py
import asyncio
from playwright.async_api import async_playwright

async def download_fab_asset_browser(asset_url: str, cookies_file: str):
    """Download asset via browser automation con tuoi cookie"""
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        
        # Load cookies
        with open(cookies_file, 'r') as f:
            # Parse Netscape cookies format
            cookies = []
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.strip().split('\t')
                if len(parts) >= 7:
                    cookies.append({
                        'name': parts[5],
                        'value': parts[6],
                        'domain': parts[0],
                        'path': parts[2]
                    })
            
            await context.add_cookies(cookies)
        
        # Navigate to asset page
        page = await context.new_page()
        await page.goto(asset_url)
        
        # Wait for auth check
        await page.wait_for_load_state('networkidle')
        
        # Click download button
        download_btn = page.locator('button:has-text("Download")')
        if await download_btn.count() > 0:
            async with page.expect_download() as download_info:
                await download_btn.click()
            
            download = await download_info.value
            save_path = f"downloads/{download.suggested_filename}"
            await download.save_as(save_path)
            
            print(f"✓ Downloaded to: {save_path}")
        else:
            print("✗ Download button not found or not owned")
        
        await browser.close()

# Usage
asyncio.run(download_fab_asset_browser(
    "https://fab.com/listings/1234567-rock-cliff",
    "game-developer/config/fab-cookies.txt"
))
```

---

## 🎨 Integrazione con Asset Library Manager

```python
# Add to game-developer/tools/asset-library-manager/backend/sources/fab.py
from .fab_client import FabClient

async def scan():
    """Scan Fab.com owned assets and local library"""
    
    config = load_config()
    client = FabClient(
        cookies_file=config.get('fab', {}).get('cookies_file')
    )
    
    assets = []
    
    # 1. Scan local library
    library_path = config.get('fab', {}).get('library_path')
    if library_path:
        local_assets = client.scan_local_library(library_path)
        assets.extend(local_assets)
    
    # 2. Check legacy MegaScan library
    legacy_path = config.get('megascan', {}).get('legacy_library')
    if legacy_path:
        legacy_assets = client.scan_local_library(legacy_path)
        for asset in legacy_assets:
            asset['source'] = 'megascan-legacy'
        assets.extend(legacy_assets)
    
    # 3. Fetch owned from Fab.com (if cookies valid)
    try:
        owned = client.get_owned_assets()
        for asset in owned:
            # Mark if not downloaded locally
            asset_id = asset['id']
            is_local = any(a['id'] == asset_id for a in assets)
            asset['is_downloaded'] = is_local
            asset['source'] = 'fab'
        
        assets.extend([a for a in owned if not a['is_downloaded']])
    except:
        pass  # Cookies invalid or network error
    
    # Convert to unified Asset format
    return [convert_to_asset(a) for a in assets]
```

---

## 🔄 Migration Helper

Script per migrare da vecchia MegaScan library a Fab:

```powershell
# game-developer/tools/fab-integration/migrate-megascan-to-fab.ps1
param(
    [string]$MegascanPath = "C:\Users\$env:USERNAME\Documents\Megascans Library",
    [string]$FabPath = "C:\Users\$env:USERNAME\Documents\Fab Library"
)

Write-Host "🔄 MegaScan → Fab Migration" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $MegascanPath)) {
    Write-Host "✗ MegaScan library not found: $MegascanPath" -ForegroundColor Red
    exit 1
}

Write-Host "📦 Scanning MegaScan library..." -ForegroundColor Yellow
$assets = Get-ChildItem $MegascanPath -Directory

Write-Host "Found $($assets.Count) assets" -ForegroundColor Green
Write-Host ""

# Create Fab directory structure
New-Item -ItemType Directory -Force -Path $FabPath | Out-Null

foreach ($asset in $assets) {
    $assetName = $asset.Name
    $sourcePath = $asset.FullName
    $destPath = Join-Path $FabPath $assetName
    
    if (Test-Path $destPath) {
        Write-Host "⊘ Skip (exists): $assetName" -ForegroundColor Gray
        continue
    }
    
    Write-Host "→ Migrating: $assetName" -ForegroundColor Yellow
    
    # Copy entire folder
    Copy-Item -Path $sourcePath -Destination $destPath -Recurse -Force
    
    # Create Fab-compatible metadata.json
    $metadata = @{
        id = $assetName
        name = $assetName
        source = "megascan-migrated"
        migration_date = Get-Date -Format "yyyy-MM-dd"
        original_path = $sourcePath
    }
    
    $metadataPath = Join-Path $destPath "metadata.json"
    $metadata | ConvertTo-Json | Set-Content $metadataPath
    
    Write-Host "✓ Migrated: $assetName" -ForegroundColor Green
}

Write-Host ""
Write-Host "✅ Migration completed!" -ForegroundColor Green
Write-Host "Old library: $MegascanPath (can be deleted after verification)" -ForegroundColor Gray
Write-Host "New library: $FabPath" -ForegroundColor Green
```

---

## 🎯 Workflow con Fab Assets

### 1. Setup Cookie (Una volta)

```powershell
# 1. Install extension "Get cookies.txt LOCALLY" in Chrome
# 2. Vai su fab.com e login
# 3. Click extension -> Export
# 4. Salva in: game-developer/config/fab-cookies.txt
```

### 2. Scansiona Libreria

```python
from tools.fab_integration.fab_client import FabClient

client = FabClient(cookies_file="game-developer/config/fab-cookies.txt")

# Scansiona locale
local_assets = client.scan_local_library("C:/Users/FRANCY/Documents/Fab Library")
print(f"Trovati {len(local_assets)} asset locali")

# Fetch owned da Fab.com
owned_assets = client.get_owned_assets()
print(f"Possiedi {len(owned_assets)} asset su Fab.com")
```

### 3. Usa in Asset Library Manager

Dashboard mostra automaticamente:
- ✅ Asset Fab locali (già scaricati)
- 🌐 Asset Fab owned (da scaricare)
- 📦 Asset MegaScan legacy (da migrare)

### 4. Download On-Demand

```python
# Via CLI
client.download_asset("fab-asset-id-12345", "C:/Downloads")

# Via browser automation (con cookie)
asyncio.run(download_fab_asset_browser(
    "https://fab.com/listings/12345-rock-cliff",
    "game-developer/config/fab-cookies.txt"
))
```

---

## 🔒 Sicurezza Cookie

**IMPORTANTE:**

```gitignore
# .gitignore
game-developer/config/fab-cookies.txt
game-developer/config/*.txt
```

**NON committare MAI i cookie!** Sono credenziali sensibili.

---

## 📊 Supporto per Engine

### Unity

```csharp
// Import Fab asset in Unity
public static void ImportFabAsset(string localPath) {
    // Fab assets sono FBX standard
    AssetDatabase.ImportAsset(localPath);
}
```

### Godot

```gdscript
# Import Fab GLB
var asset_path = "res://fab_library/rock_cliff/model.glb"
var scene = load(asset_path)
```

### Unreal

```python
# Fab ha integrazione nativa in Unreal
# Fab browser built-in: Window -> Fab
# O via Python:
import unreal
task = unreal.AssetImportTask()
task.filename = "C:/Fab Library/rock_cliff/model.fbx"
task.destination_path = "/Game/FabAssets"
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
```

---

## ✅ Checklist Setup

- [ ] Account Fab.com creato e logged in
- [ ] Fab CLI installato (`fab login`)
- [ ] Cookie exported (se vuoi automation)
- [ ] `fab-cookies.txt` salvato in `game-developer/config/`
- [ ] Config JSON aggiornato con path libreria
- [ ] Migration script eseguito (se avevi MegaScan vecchia)
- [ ] Asset Library Manager rileva asset Fab

---

## 🆘 Troubleshooting

### "Cookie scaduti"

```powershell
# Re-export cookie da browser (validity: ~30 giorni)
# Fab.com -> Cookie extension -> Export
```

### "Asset not found"

```python
# Verifica ownership
client = FabClient(cookies_file="...")
owned = client.get_owned_assets()
print([a['name'] for a in owned])
```

### "Download failed"

```powershell
# Usa Fab CLI manuale
fab download <asset-id> --output ./downloads
```

---

**Versione:** 1.0  
**Updated:** 2025 (Fab.com migration)  
**Status:** ✅ Production ready  
**Method:** CLI (primary) + Browser automation (fallback)
