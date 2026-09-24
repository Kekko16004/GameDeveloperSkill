# GameDeveloperSkill - Quick Start Scripts

Tutti gli script di avvio nella root per facilità d'uso.

---

## 🚀 Installazione

```powershell
# Windows - Run as Administrator
.\install-all.bat
```

**Cosa fa:**
1. Installa skill Kilo
2. Setup Git LFS
3. Verifica dipendenze
4. Crea shortcuts

---

## Console

```bat
start-dashboard.bat
```

Niente browser. Tre schermate:

- **Progetto** — percorso del gioco, GDD, contesto, screenshot, GLB, doctor
- **FabCLI** — eseguibile, cartella download, login
- **DesignerSkill** — copia i file sugli host, oppure lasciali stare

`fabcli` non è incluso. Si scarica da https://github.com/zirklerite/FabCLI/releases (`fabcli-v*-windows64.zip`). Poi nella console: percorso dell'exe, cartella download, `Accedi`.

---

## 🔍 Check Dipendenze

```powershell
.\scripts\check-dependencies.ps1
```

**Verifica:**
- Python, Node.js, Git
- Git LFS (optional)
- Blender (optional)
- Unity/Godot/Unreal (optional)
- Config file

---

## 🔧 Setup Git LFS

```powershell
.\scripts\setup-git-lfs.ps1

# In progetto specifico
.\scripts\setup-git-lfs.ps1 -ProjectPath "C:\Projects\MyGame"

# Force overwrite
.\scripts\setup-git-lfs.ps1 -Force
```

---

## 📁 Struttura

```
GameDeveloperSkill/
├── install-all.bat           # Installer completo
├── start-dashboard.bat       # Console (Windows)
├── start-dashboard.ps1       # Console (PowerShell)
├── scripts/
│   ├── check-dependencies.ps1
│   └── setup-git-lfs.ps1
└── game-developer/
    ├── install.ps1           # Skill installer (chiamato da install-all)
    └── tools/
        └── tui/gds_tui.py      # console
```

---

## 🎯 Workflow Completo

### 1. Prima Installazione

```powershell
# Run as Admin
.\install-all.bat
```

### 2. Configura API Keys

Edita `game-developer/config.json`:

```json
{
  "gen3d": {
    "tier": "meshy",
    "meshy_api_key": "YOUR_KEY_HERE"
  },
  "fab": {
    "enabled": false,
    "cli": "C:\\Tools\\fabcli\\fabcli.exe",
    "library_path": "C:\\Users\\YOUR_USERNAME\\Documents\\Fab Library"
  }
}
```

### 3. FabCLI

Dalla console, schermata Fab. Non esportare cookie: FabCLI fa il login da solo con `fabcli auth login`.

### 4. Apri la console

```bat
start-dashboard.bat
```

### 5. Crea Gioco

```bash
# In Kilo chat
/game Create a dungeon crawler, low poly style
```

---

## 🔧 Troubleshooting

### "Python not found"
```powershell
winget install Python.Python.3.12
```

### "Git LFS not found"
```powershell
winget install GitHub.GitLFS
```

### La console non parte
```bat
python --version
python game-developer\tools\tui\gds_tui.py --check
```

---

## 📊 Verifica Setup

```powershell
# Check tutto
.\scripts\check-dependencies.ps1

# Output atteso:
# [OK] Python 3.12
# [OK] Node.js v20
# [OK] Git 2.43
# [OK] Git LFS 3.4
# [OK] config.json exists
# [OK] All dependencies ready!
```

---

## Docs

- **Setup completo:** `SETUP_GUIDE.md`
- **Ambienti (caverna, dungeon, villaggio...):** `game-developer/references/environments.md`
- **Storico versioni:** `docs/archive/`

---

**Versione:** 2.0.1  
**Status:** ✅ Production Ready
