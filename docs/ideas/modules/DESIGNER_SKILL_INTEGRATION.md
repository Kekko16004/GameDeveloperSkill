# DesignerSkill Standalone Integration

Sistema modulare per integrare DesignerSkill come componente standalone, aggiornabile indipendentemente.

---

## 🎯 Obiettivi

1. **Standalone:** L'utente GitHub può scaricare GameDeveloperSkill e ottenere anche DesignerSkill automaticamente
2. **Modulare:** DesignerSkill è un submodule Git aggiornabile sostituendo una cartella
3. **Fallback:** Funziona anche senza DesignerSkill (skippa fase UI con warning)
4. **Hot-reload:** Modifiche a DesignerSkill si riflettono immediatamente senza reinstallazione

---

## 📦 Architettura

```
GameDeveloperSkill/
├── game-developer/           # Core skill
│   ├── modules/
│   │   ├── designer-skill/   # ← Git submodule (DesignerSkill embedded)
│   │   │   ├── real-world-design/
│   │   │   │   ├── SKILL.md
│   │   │   │   ├── command/
│   │   │   │   └── ...
│   │   │   └── .git         # Submodule ha proprio Git
│   │   └── README.md
│   ├── references/
│   │   └── ui-bridge.md      # Documentazione ponte UI
│   └── scripts/
│       ├── check-designer-skill.ps1
│       └── update-modules.ps1
├── .gitmodules               # Configurazione submodules
└── README.md
```

---

## 🔧 Setup Git Submodule

### Per Repository Owner (Prima volta)

```bash
# Aggiungi DesignerSkill come submodule
cd GameDeveloperSkill
git submodule add https://github.com/YOUR_ORG/DesignerSkill.git game-developer/modules/designer-skill

# Commit
git add .gitmodules game-developer/modules/designer-skill
git commit -m "Add DesignerSkill as submodule"
git push
```

### Per Utente GitHub (Clone)

```bash
# Clone con submodules automatici
git clone --recurse-submodules https://github.com/YOUR_ORG/GameDeveloperSkill.git

# Oppure se già clonato senza --recurse-submodules
cd GameDeveloperSkill
git submodule update --init --recursive
```

---

## 🔄 Update DesignerSkill

### Aggiornamento Manuale (Utente)

```powershell
# Update submodule alla latest
cd GameDeveloperSkill
git submodule update --remote game-developer/modules/designer-skill

# Oppure entra e pull
cd game-developer/modules/designer-skill
git pull origin main
cd ../../..

# Commit la nuova versione (opzionale)
git add game-developer/modules/designer-skill
git commit -m "Update DesignerSkill to latest"
```

### Script Automatico

```powershell
# game-developer/scripts/update-modules.ps1
.\game-developer\scripts\update-modules.ps1 -Module designer-skill
```

**Script:**
```powershell
param([string]$Module = "all")

$modules = @("designer-skill")
if($Module -ne "all") { $modules = @($Module) }

foreach($m in $modules) {
    $path = "game-developer/modules/$m"
    if(Test-Path $path) {
        Write-Host "Updating $m..."
        git submodule update --remote $path
        Write-Host "✓ $m updated"
    } else {
        Write-Host "⚠ $m not found, initializing..."
        git submodule update --init --recursive $path
    }
}
```

---

## 🔍 Detection System (Priority Cascade)

Il sistema cerca DesignerSkill in 4 posti, in ordine:

### 1. **Embedded Submodule** (Priorità massima)
```
game-developer/modules/designer-skill/real-world-design/SKILL.md
```

✅ Sempre preferito se presente  
✅ Versione controllata dal repo  
✅ Hot-reload automatico

### 2. **Config Path Esterno**
```json
// game-developer/config.json
{
  "paths": {
    "designerSkill": "C:\\Users\\YOURNAME\\Desktop\\DesignerSkill"
  }
}
```

✅ Usato se submodule non presente  
✅ Permette versione custom dell'utente

### 3. **System-Wide Installation**
```
~/.config/kilo/skills/real-world-design/SKILL.md
~/.claude/skills/real-world-design/SKILL.md
```

✅ Fallback se nessun path configurato  
✅ Installato dall'installer se trovato su Desktop

### 4. **Skip con Warning**
Se nessuna trovata:
```
⚠ DesignerSkill not found. UI generation will be skipped.
Install: git submodule update --init --recursive
Or download from: https://github.com/YOUR_ORG/DesignerSkill
```

---

## 🛠️ Implementazione Tecnica

### Check Script
```powershell
# game-developer/scripts/check-designer-skill.ps1
$locations = @(
    "game-developer\modules\designer-skill\real-world-design\SKILL.md",  # Embedded
    "$env:USERPROFILE\Desktop\DesignerSkill\real-world-design\SKILL.md", # Desktop
    "$env:USERPROFILE\.config\kilo\skills\real-world-design\SKILL.md",   # Kilo
    "$env:USERPROFILE\.claude\skills\real-world-design\SKILL.md"          # Claude
)

$found = $null
foreach($loc in $locations) {
    if(Test-Path $loc) {
        $found = $loc
        break
    }
}

if($found) {
    Write-Host "✓ DesignerSkill found: $found"
    $obj = @{ found = $true; path = $found; type = "embedded" }
    if($found -notlike "*modules\designer-skill*") { $obj.type = "external" }
    return $obj | ConvertTo-Json
} else {
    Write-Host "✗ DesignerSkill not found"
    return @{ found = $false } | ConvertTo-Json
}
```

### Runtime Detection (C#)
```csharp
// GDS.DesignerSkillBridge.cs
public static class DesignerSkillBridge {
    private static string _skillPath = null;
    private static bool _available = false;
    
    public static bool IsAvailable => _available;
    public static string SkillPath => _skillPath;
    
    static DesignerSkillBridge() {
        DetectDesignerSkill();
    }
    
    private static void DetectDesignerSkill() {
        // Priority 1: Embedded submodule
        var embedded = Path.Combine(Application.dataPath, "../game-developer/modules/designer-skill/real-world-design");
        if(Directory.Exists(embedded) && File.Exists(Path.Combine(embedded, "SKILL.md"))) {
            _skillPath = Path.GetFullPath(embedded);
            _available = true;
            Debug.Log($"[GDS] DesignerSkill: embedded ({_skillPath})");
            return;
        }
        
        // Priority 2: Config path
        var config = LoadConfig();
        if(config.paths.designerSkill != null) {
            var configPath = Path.Combine(config.paths.designerSkill, "real-world-design");
            if(Directory.Exists(configPath)) {
                _skillPath = configPath;
                _available = true;
                Debug.Log($"[GDS] DesignerSkill: external config ({_skillPath})");
                return;
            }
        }
        
        // Priority 3: System-wide
        var systemPaths = new[] {
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".config/kilo/skills/real-world-design"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".claude/skills/real-world-design")
        };
        
        foreach(var sp in systemPaths) {
            if(Directory.Exists(sp) && File.Exists(Path.Combine(sp, "SKILL.md"))) {
                _skillPath = sp;
                _available = true;
                Debug.Log($"[GDS] DesignerSkill: system-wide ({_skillPath})");
                return;
            }
        }
        
        // Not found
        _available = false;
        Debug.LogWarning("[GDS] DesignerSkill not found. UI generation will be skipped.");
    }
    
    public static void InvokeDesignerSkill(string prompt) {
        if(!IsAvailable) {
            throw new Exception("DesignerSkill not available. Install it first.");
        }
        
        // Invoke via agent skill call
        // Implementation depends on MCP/agent system
    }
}
```

---

## 📋 Installer Integration

### Modifiche a `install.ps1`

```powershell
# Check embedded submodule first
$embeddedDS = Join-Path $SkillSrc "modules\designer-skill\real-world-design\SKILL.md"
if(Test-Path $embeddedDS) {
    Write-Host "✓ DesignerSkill embedded submodule found"
    $designerSource = "embedded"
} else {
    # Check if submodule exists but not initialized
    if(Test-Path (Join-Path $SkillSrc "modules\designer-skill")) {
        Write-Host "⚠ DesignerSkill submodule exists but not initialized"
        Write-Host "  Run: git submodule update --init --recursive"
        $designerSource = "uninitialized"
    } else {
        # Fallback to external path check
        $dsSrc = Join-Path $User "Desktop\DesignerSkill\real-world-design"
        if(Test-Path (Join-Path $dsSrc "SKILL.md")) {
            Write-Host "✓ DesignerSkill found on Desktop (external)"
            $designerSource = "desktop"
            # Copy to system-wide as before
        } else {
            Write-Host "⚠ DesignerSkill not found"
            Write-Host "  Install: git submodule update --init"
            Write-Host "  Or download from: [REPO_URL]"
            $designerSource = "none"
        }
    }
}

# Store detection result in config
$cfg.modules.designSkillStatus = $designerSource
```

---

## 📖 README Integration

### GameDeveloperSkill README.md

Aggiungi sezione:

```markdown
## 📦 DesignerSkill Integration

GameDeveloperSkill include **DesignerSkill** come modulo embedded per generare UI professionali.

### Installazione Automatica (Raccomandato)
```bash
git clone --recurse-submodules https://github.com/YOUR_ORG/GameDeveloperSkill.git
```

### Se hai già clonato senza submodules
```bash
cd GameDeveloperSkill
git submodule update --init --recursive
```

### Aggiorna DesignerSkill
```bash
git submodule update --remote game-developer/modules/designer-skill
```

### Usa tua versione custom
Modifica `game-developer/config.json`:
```json
{
  "paths": {
    "designerSkill": "C:\\Path\\To\\Your\\DesignerSkill"
  }
}
```

### Funziona senza?
Sì! Se DesignerSkill non è trovato, la fase UI viene skippata con warning.
```

---

## 🔗 GitHub Release Automation

### Workflow CI/CD

```yaml
# .github/workflows/release.yml
name: Release with Submodules

on:
  release:
    types: [published]

jobs:
  package:
    runs-on: windows-latest
    steps:
      - name: Checkout with submodules
        uses: actions/checkout@v3
        with:
          submodules: recursive
      
      - name: Verify DesignerSkill
        run: |
          if (Test-Path "game-developer/modules/designer-skill/real-world-design/SKILL.md") {
            Write-Host "✓ DesignerSkill submodule OK"
          } else {
            Write-Error "✗ DesignerSkill submodule missing"
            exit 1
          }
      
      - name: Create release archive
        run: |
          Compress-Archive -Path * -DestinationPath GameDeveloperSkill-${{ github.ref_name }}.zip
      
      - name: Upload to release
        uses: actions/upload-release-asset@v1
        with:
          upload_url: ${{ github.event.release.upload_url }}
          asset_path: ./GameDeveloperSkill-${{ github.ref_name }}.zip
          asset_name: GameDeveloperSkill-${{ github.ref_name }}.zip
          asset_content_type: application/zip
```

---

## 🎯 User Experience

### Per Nuovo Utente GitHub

1. **Clone repo:**
   ```bash
   git clone --recurse-submodules https://github.com/YOUR_ORG/GameDeveloperSkill.git
   ```

2. **Run installer:**
   ```powershell
   cd GameDeveloperSkill
   .\install.bat
   ```

3. **DesignerSkill è già incluso** e configurato automaticamente ✓

### Per Update

```powershell
# Update GameDeveloperSkill
git pull

# Update tutti i submodules (incluso DesignerSkill)
git submodule update --remote --recursive

# Oppure script comodo
.\game-developer\scripts\update-modules.ps1
```

---

## 🛡️ Fallback Graceful

Se DesignerSkill manca durante fase UI:

```markdown
[PHASE: UI] ⚠ DesignerSkill not available

Options:
1. Skip UI generation (continue without UI)
2. Use placeholder UI (gray boxes with labels)
3. Stop and install DesignerSkill now

Install commands:
  git submodule update --init --recursive
  Or download: https://github.com/YOUR_ORG/DesignerSkill

Choose [1/2/3]:
```

---

## 📊 Detection Report (Doctor)

```powershell
powershell .\game-developer\scripts\doctor.ps1
```

Output:
```
=== DesignerSkill Status ===
[PASS] DesignerSkill found: embedded submodule
       Path: C:\...\GameDeveloperSkill\game-developer\modules\designer-skill
       Version: v2.1.0 (git submodule)
       Hot-reload: ✓ enabled
       
Alternative paths checked:
  [ ] C:\Users\...\Desktop\DesignerSkill
  [✓] C:\Users\...\.config\kilo\skills\real-world-design (system-wide backup)
```

---

## 🚀 Benefits

✅ **One-click setup:** Clone con --recurse-submodules e tutto funziona  
✅ **Version locking:** Submodule punta a commit specifico  
✅ **Easy updates:** `git submodule update --remote`  
✅ **Standalone:** No dipendenze esterne da path Windows  
✅ **Fallback:** Funziona anche senza DesignerSkill  
✅ **Modulare:** Sostituire `modules/designer-skill/` aggiorna tutto  

---

**Versione:** 1.0  
**Status:** ✅ Ready for Implementation  
**Next:** Setup .gitmodules e add submodule
