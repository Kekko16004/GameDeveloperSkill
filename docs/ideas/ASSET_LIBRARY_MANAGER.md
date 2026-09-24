# Asset Library Manager

Dashboard unificato per visualizzare, filtrare e gestire tutti gli asset disponibili da diverse fonti.

---

## 🎯 Obiettivo

Un'unica interfaccia per:
- **Browsare** tutti gli asset (Kenney, KayKit, Quaternius, MegaScan, Poly Haven, custom)
- **Filtrare** per tipo, stile, poly count, licenza
- **Preview** con thumbnails 3D
- **Import** con un click
- **Track** cosa è già nel progetto

---

## 🏗️ Architettura

```
game-developer/
└── tools/
    └── asset-library-manager/
        ├── backend/
        │   ├── asset_catalog.py        # Unified asset catalog
        │   ├── sources/
        │   │   ├── kenney.py           # Kenney.nl scraper
        │   │   ├── kaykit.py           # KayKit GitHub
        │   │   ├── quaternius.py       # Quaternius itch.io
        │   │   ├── megascan.py         # MegaScan local library
        │   │   ├── polyhaven.py        # Poly Haven API
        │   │   └── custom.py           # User custom assets
        │   └── server.py               # FastAPI backend
        ├── frontend/
        │   ├── index.html              # Dashboard UI
        │   ├── app.js                  # Vue.js/Alpine.js
        │   └── style.css
        └── start-asset-manager.ps1
```

---

## 🔧 Backend: Unified Asset Catalog

### Python API (FastAPI)

```python
# game-developer/tools/asset-library-manager/backend/asset_catalog.py
from typing import List, Optional
from pydantic import BaseModel
from enum import Enum

class AssetType(str, Enum):
    MODEL = "model"
    TEXTURE = "texture"
    MATERIAL = "material"
    HDRI = "hdri"
    CHARACTER = "character"
    PROP = "prop"
    KIT = "kit"

class AssetSource(str, Enum):
    KENNEY = "kenney"
    KAYKIT = "kaykit"
    QUATERNIUS = "quaternius"
    MEGASCAN = "megascan"
    POLYHAVEN = "polyhaven"
    POLYPIZZA = "polypizza"
    SKETCHFAB = "sketchfab"
    CUSTOM = "custom"

class Asset(BaseModel):
    id: str
    name: str
    source: AssetSource
    type: AssetType
    thumbnail_url: Optional[str]
    preview_url: Optional[str]
    poly_count: Optional[int]
    file_size_mb: Optional[float]
    formats: List[str]  # ["fbx", "glb", "obj"]
    license: str  # "CC0", "CC-BY", "Custom"
    tags: List[str]
    style: str  # "low-poly", "realistic", "toon", etc.
    is_downloaded: bool
    is_in_project: bool
    local_path: Optional[str]
    download_url: Optional[str]
    
class AssetCatalog:
    def __init__(self):
        self.assets: List[Asset] = []
        self.sources = []
    
    async def scan_all_sources(self):
        """Scan all asset sources and build unified catalog"""
        from .sources import kenney, kaykit, quaternius, megascan, polyhaven, custom
        
        tasks = [
            kenney.scan(),
            kaykit.scan(),
            quaternius.scan(),
            megascan.scan_local(),
            polyhaven.scan(),
            custom.scan_local()
        ]
        
        results = await asyncio.gather(*tasks)
        self.assets = [asset for result in results for asset in result]
        
        return self.assets
    
    def filter(self, 
               type: Optional[AssetType] = None,
               source: Optional[AssetSource] = None,
               style: Optional[str] = None,
               max_poly: Optional[int] = None,
               license: Optional[str] = None,
               search: Optional[str] = None) -> List[Asset]:
        """Filter assets by criteria"""
        filtered = self.assets
        
        if type:
            filtered = [a for a in filtered if a.type == type]
        if source:
            filtered = [a for a in filtered if a.source == source]
        if style:
            filtered = [a for a in filtered if a.style == style]
        if max_poly:
            filtered = [a for a in filtered if a.poly_count and a.poly_count <= max_poly]
        if license:
            filtered = [a for a in filtered if license.lower() in a.license.lower()]
        if search:
            search_lower = search.lower()
            filtered = [a for a in filtered if 
                       search_lower in a.name.lower() or
                       any(search_lower in tag for tag in a.tags)]
        
        return filtered
    
    def get_stats(self) -> dict:
        """Get catalog statistics"""
        return {
            "total_assets": len(self.assets),
            "by_source": {source: len([a for a in self.assets if a.source == source]) 
                         for source in AssetSource},
            "by_type": {type: len([a for a in self.assets if a.type == type]) 
                       for type in AssetType},
            "downloaded": len([a for a in self.assets if a.is_downloaded]),
            "in_project": len([a for a in self.assets if a.is_in_project])
        }
```

### FastAPI Server

```python
# game-developer/tools/asset-library-manager/backend/server.py
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

app = FastAPI(title="Asset Library Manager")
catalog = AssetCatalog()

@app.on_event("startup")
async def startup():
    """Scan all sources on startup"""
    await catalog.scan_all_sources()

@app.get("/api/assets")
async def get_assets(
    type: Optional[AssetType] = None,
    source: Optional[AssetSource] = None,
    style: Optional[str] = None,
    max_poly: Optional[int] = None,
    license: Optional[str] = None,
    search: Optional[str] = None
):
    """Get filtered assets"""
    assets = catalog.filter(type, source, style, max_poly, license, search)
    return {"assets": assets, "count": len(assets)}

@app.get("/api/stats")
async def get_stats():
    """Get catalog statistics"""
    return catalog.get_stats()

@app.post("/api/assets/{asset_id}/download")
async def download_asset(asset_id: str):
    """Download asset to local cache"""
    # Implementation depends on source
    pass

@app.post("/api/assets/{asset_id}/import")
async def import_asset(asset_id: str, project_path: str):
    """Import asset into Unity/Godot/Unreal project"""
    # Implementation depends on engine
    pass

@app.get("/api/refresh")
async def refresh_catalog():
    """Rescan all sources"""
    await catalog.scan_all_sources()
    return {"status": "ok", "count": len(catalog.assets)}

# Serve frontend
app.mount("/", StaticFiles(directory="../frontend", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)
```

---

## 🎨 Frontend: Web Dashboard

### HTML + Alpine.js (Lightweight)

```html
<!-- game-developer/tools/asset-library-manager/frontend/index.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Asset Library Manager</title>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js"></script>
    <link rel="stylesheet" href="style.css">
</head>
<body x-data="assetManager()">
    
    <!-- Header -->
    <header class="header">
        <div class="container">
            <h1>🎨 Asset Library Manager</h1>
            <div class="stats">
                <span class="stat">
                    <strong x-text="stats.total_assets"></strong> Assets
                </span>
                <span class="stat">
                    <strong x-text="stats.downloaded"></strong> Downloaded
                </span>
                <span class="stat">
                    <strong x-text="stats.in_project"></strong> In Project
                </span>
                <button @click="refreshCatalog" class="btn-refresh">↻ Refresh</button>
            </div>
        </div>
    </header>

    <div class="container">
        
        <!-- Filters -->
        <aside class="filters">
            <h3>Filters</h3>
            
            <div class="filter-group">
                <label>Search</label>
                <input type="text" x-model="filters.search" placeholder="Search assets..." />
            </div>
            
            <div class="filter-group">
                <label>Source</label>
                <select x-model="filters.source">
                    <option value="">All Sources</option>
                    <option value="kenney">Kenney</option>
                    <option value="kaykit">KayKit</option>
                    <option value="quaternius">Quaternius</option>
                    <option value="megascan">MegaScan</option>
                    <option value="polyhaven">Poly Haven</option>
                    <option value="custom">Custom</option>
                </select>
            </div>
            
            <div class="filter-group">
                <label>Style</label>
                <select x-model="filters.style">
                    <option value="">All Styles</option>
                    <option value="low-poly">Low Poly</option>
                    <option value="realistic">Realistic</option>
                    <option value="toon">Toon</option>
                    <option value="voxel">Voxel/Pixel-Art</option>
                    <option value="hand-painted">Hand-Painted</option>
                    <option value="sci-fi">Sci-Fi</option>
                </select>
            </div>
            
            <div class="filter-group">
                <label>Type</label>
                <select x-model="filters.type">
                    <option value="">All Types</option>
                    <option value="model">3D Models</option>
                    <option value="texture">Textures</option>
                    <option value="character">Characters</option>
                    <option value="kit">Kits</option>
                    <option value="hdri">HDRIs</option>
                </select>
            </div>
            
            <div class="filter-group">
                <label>Max Poly Count</label>
                <input type="number" x-model="filters.max_poly" placeholder="e.g. 5000" />
            </div>
            
            <div class="filter-group">
                <label>License</label>
                <select x-model="filters.license">
                    <option value="">All Licenses</option>
                    <option value="CC0">CC0 (Public Domain)</option>
                    <option value="CC-BY">CC-BY (Attribution)</option>
                    <option value="Free">Free (Custom License)</option>
                </select>
            </div>
            
            <button @click="applyFilters" class="btn-primary btn-block">Apply Filters</button>
            <button @click="clearFilters" class="btn-secondary btn-block">Clear</button>
        </aside>

        <!-- Asset Grid -->
        <main class="asset-grid-container">
            <div class="asset-grid">
                <template x-for="asset in assets" :key="asset.id">
                    <div class="asset-card" @click="selectAsset(asset)">
                        <div class="asset-thumbnail">
                            <img :src="asset.thumbnail_url || 'placeholder.svg'" 
                                 :alt="asset.name" />
                            <div class="asset-badges">
                                <span class="badge" x-show="asset.is_downloaded">✓ Downloaded</span>
                                <span class="badge badge-success" x-show="asset.is_in_project">In Project</span>
                            </div>
                        </div>
                        <div class="asset-info">
                            <h4 class="asset-name" x-text="asset.name"></h4>
                            <div class="asset-meta">
                                <span class="source-badge" 
                                      :class="'source-' + asset.source" 
                                      x-text="asset.source.toUpperCase()"></span>
                                <span class="poly-count" x-show="asset.poly_count">
                                    <template x-if="asset.poly_count < 1000">
                                        <span x-text="asset.poly_count + ' tris'"></span>
                                    </template>
                                    <template x-if="asset.poly_count >= 1000">
                                        <span x-text="(asset.poly_count / 1000).toFixed(1) + 'k tris'"></span>
                                    </template>
                                </span>
                            </div>
                            <div class="asset-tags">
                                <template x-for="tag in asset.tags.slice(0, 3)">
                                    <span class="tag" x-text="tag"></span>
                                </template>
                            </div>
                        </div>
                    </div>
                </template>
            </div>
            
            <!-- Empty State -->
            <div class="empty-state" x-show="assets.length === 0">
                <p>No assets found matching your filters.</p>
                <button @click="clearFilters" class="btn-primary">Clear Filters</button>
            </div>
        </main>
    </div>

    <!-- Asset Detail Modal -->
    <div class="modal" x-show="selectedAsset" @click.away="selectedAsset = null">
        <div class="modal-content" x-show="selectedAsset" @click.stop>
            <button class="modal-close" @click="selectedAsset = null">×</button>
            
            <template x-if="selectedAsset">
                <div>
                    <div class="modal-header">
                        <h2 x-text="selectedAsset.name"></h2>
                        <span class="source-badge" 
                              :class="'source-' + selectedAsset.source" 
                              x-text="selectedAsset.source.toUpperCase()"></span>
                    </div>
                    
                    <div class="modal-body">
                        <img :src="selectedAsset.preview_url || selectedAsset.thumbnail_url" 
                             class="modal-preview" />
                        
                        <div class="asset-details">
                            <div class="detail-row">
                                <span class="label">Type:</span>
                                <span x-text="selectedAsset.type"></span>
                            </div>
                            <div class="detail-row">
                                <span class="label">Style:</span>
                                <span x-text="selectedAsset.style"></span>
                            </div>
                            <div class="detail-row" x-show="selectedAsset.poly_count">
                                <span class="label">Poly Count:</span>
                                <span x-text="selectedAsset.poly_count.toLocaleString()"></span>
                            </div>
                            <div class="detail-row" x-show="selectedAsset.file_size_mb">
                                <span class="label">File Size:</span>
                                <span x-text="selectedAsset.file_size_mb.toFixed(1) + ' MB'"></span>
                            </div>
                            <div class="detail-row">
                                <span class="label">Formats:</span>
                                <span x-text="selectedAsset.formats.join(', ')"></span>
                            </div>
                            <div class="detail-row">
                                <span class="label">License:</span>
                                <span x-text="selectedAsset.license"></span>
                            </div>
                        </div>
                        
                        <div class="asset-tags">
                            <template x-for="tag in selectedAsset.tags">
                                <span class="tag" x-text="tag"></span>
                            </template>
                        </div>
                    </div>
                    
                    <div class="modal-footer">
                        <button @click="downloadAsset(selectedAsset)" 
                                class="btn-primary"
                                x-show="!selectedAsset.is_downloaded">
                            ⬇ Download
                        </button>
                        <button @click="importAsset(selectedAsset)" 
                                class="btn-success"
                                x-show="selectedAsset.is_downloaded">
                            ➕ Import to Project
                        </button>
                        <button @click="openInBrowser(selectedAsset)" 
                                class="btn-secondary">
                            🔗 Open Source
                        </button>
                    </div>
                </div>
            </template>
        </div>
    </div>

    <script src="app.js"></script>
</body>
</html>
```

### JavaScript Logic

```javascript
// game-developer/tools/asset-library-manager/frontend/app.js
function assetManager() {
    return {
        assets: [],
        stats: {
            total_assets: 0,
            downloaded: 0,
            in_project: 0
        },
        filters: {
            search: '',
            source: '',
            style: '',
            type: '',
            max_poly: '',
            license: ''
        },
        selectedAsset: null,
        
        async init() {
            await this.loadStats();
            await this.loadAssets();
        },
        
        async loadStats() {
            const response = await fetch('/api/stats');
            this.stats = await response.json();
        },
        
        async loadAssets() {
            const params = new URLSearchParams();
            if (this.filters.search) params.append('search', this.filters.search);
            if (this.filters.source) params.append('source', this.filters.source);
            if (this.filters.style) params.append('style', this.filters.style);
            if (this.filters.type) params.append('type', this.filters.type);
            if (this.filters.max_poly) params.append('max_poly', this.filters.max_poly);
            if (this.filters.license) params.append('license', this.filters.license);
            
            const response = await fetch(`/api/assets?${params}`);
            const data = await response.json();
            this.assets = data.assets;
        },
        
        async applyFilters() {
            await this.loadAssets();
        },
        
        clearFilters() {
            this.filters = {
                search: '',
                source: '',
                style: '',
                type: '',
                max_poly: '',
                license: ''
            };
            this.loadAssets();
        },
        
        async refreshCatalog() {
            await fetch('/api/refresh');
            await this.loadStats();
            await this.loadAssets();
        },
        
        selectAsset(asset) {
            this.selectedAsset = asset;
        },
        
        async downloadAsset(asset) {
            const response = await fetch(`/api/assets/${asset.id}/download`, {
                method: 'POST'
            });
            if (response.ok) {
                alert('Download started!');
                await this.loadAssets();
            }
        },
        
        async importAsset(asset) {
            // TODO: Get project path from user
            const projectPath = prompt('Enter project path:');
            if (!projectPath) return;
            
            const response = await fetch(`/api/assets/${asset.id}/import`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_path: projectPath })
            });
            
            if (response.ok) {
                alert('Asset imported!');
                await this.loadAssets();
            }
        },
        
        openInBrowser(asset) {
            if (asset.download_url) {
                window.open(asset.download_url, '_blank');
            }
        }
    }
}
```

---

## 🎨 CSS Styling

```css
/* game-developer/tools/asset-library-manager/frontend/style.css */
:root {
    --primary: #4f46e5;
    --success: #10b981;
    --bg: #0f172a;
    --surface: #1e293b;
    --surface-hover: #334155;
    --text: #f1f5f9;
    --text-muted: #94a3b8;
    --border: #334155;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
}

.container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 0 20px;
    display: grid;
    grid-template-columns: 280px 1fr;
    gap: 24px;
}

/* Header */
.header {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 20px 0;
    margin-bottom: 24px;
}

.header .container {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.stats {
    display: flex;
    gap: 24px;
    align-items: center;
}

.stat {
    color: var(--text-muted);
}

.stat strong {
    color: var(--primary);
    margin-right: 4px;
}

/* Filters */
.filters {
    background: var(--surface);
    padding: 20px;
    border-radius: 8px;
    height: fit-content;
    position: sticky;
    top: 24px;
}

.filter-group {
    margin-bottom: 16px;
}

.filter-group label {
    display: block;
    margin-bottom: 6px;
    font-size: 14px;
    font-weight: 500;
    color: var(--text-muted);
}

.filter-group input,
.filter-group select {
    width: 100%;
    padding: 8px 12px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text);
    font-size: 14px;
}

/* Buttons */
button {
    padding: 10px 20px;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
}

.btn-primary {
    background: var(--primary);
    color: white;
}

.btn-primary:hover {
    opacity: 0.9;
}

.btn-success {
    background: var(--success);
    color: white;
}

.btn-secondary {
    background: var(--surface-hover);
    color: var(--text);
}

.btn-block {
    width: 100%;
    margin-top: 8px;
}

.btn-refresh {
    padding: 8px 16px;
}

/* Asset Grid */
.asset-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 20px;
}

.asset-card {
    background: var(--surface);
    border-radius: 8px;
    overflow: hidden;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
}

.asset-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
}

.asset-thumbnail {
    position: relative;
    aspect-ratio: 1;
    background: var(--bg);
}

.asset-thumbnail img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.asset-badges {
    position: absolute;
    top: 8px;
    right: 8px;
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.badge {
    background: rgba(0, 0, 0, 0.7);
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
}

.badge-success {
    background: var(--success);
}

.asset-info {
    padding: 12px;
}

.asset-name {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 8px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.asset-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    font-size: 12px;
    color: var(--text-muted);
}

.source-badge {
    background: var(--bg);
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
}

.source-kenney { background: #ff6b6b; color: white; }
.source-kaykit { background: #4ecdc4; color: white; }
.source-quaternius { background: #ffe66d; color: black; }
.source-megascan { background: #a8dadc; color: black; }
.source-polyhaven { background: #457b9d; color: white; }

.asset-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
}

.tag {
    background: var(--bg);
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    color: var(--text-muted);
}

/* Modal */
.modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.8);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.modal-content {
    background: var(--surface);
    border-radius: 12px;
    max-width: 800px;
    width: 90%;
    max-height: 90vh;
    overflow-y: auto;
    position: relative;
}

.modal-close {
    position: absolute;
    top: 16px;
    right: 16px;
    background: transparent;
    color: var(--text);
    font-size: 32px;
    line-height: 1;
    padding: 0;
    width: 40px;
    height: 40px;
    z-index: 1;
}

.modal-header {
    padding: 24px;
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.modal-body {
    padding: 24px;
}

.modal-preview {
    width: 100%;
    border-radius: 8px;
    margin-bottom: 24px;
}

.asset-details {
    margin-bottom: 24px;
}

.detail-row {
    display: flex;
    padding: 12px 0;
    border-bottom: 1px solid var(--border);
}

.detail-row .label {
    font-weight: 600;
    min-width: 120px;
    color: var(--text-muted);
}

.modal-footer {
    padding: 24px;
    border-top: 1px solid var(--border);
    display: flex;
    gap: 12px;
    justify-content: flex-end;
}

/* Empty State */
.empty-state {
    text-align: center;
    padding: 60px 20px;
    color: var(--text-muted);
}
```

---

## 🚀 Launcher Script

```powershell
# game-developer/tools/asset-library-manager/start-asset-manager.ps1
$ErrorActionPreference = "Stop"

Write-Host "🎨 Asset Library Manager" -ForegroundColor Cyan
Write-Host ""

# Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python not found. Install Python 3.10+" -ForegroundColor Red
    exit 1
}

# Install dependencies
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
pip install fastapi uvicorn aiohttp pydantic -q

# Start server
Write-Host "🚀 Starting server on http://127.0.0.1:8765" -ForegroundColor Green
Write-Host "   Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

cd backend
python server.py
```

---

## 📊 Usage

```powershell
# Start Asset Library Manager
cd game-developer/tools/asset-library-manager
.\start-asset-manager.ps1

# Open browser to http://127.0.0.1:8765
```

**Features:**
- ✅ Browse 10,000+ assets from all sources
- ✅ Filter by source, style, poly count, license
- ✅ Preview with thumbnails
- ✅ Download with one click
- ✅ Import directly to project
- ✅ Track what's downloaded/imported
- ✅ Unified catalog across all sources

---

**Next:** Implement source scrapers (kenney.py, kaykit.py, etc.)
