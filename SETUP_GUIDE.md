# 🎮 GameDeveloperSkill - Setup Completo

Guida completa per configurare tutti i componenti, MCP servers, API keys e dipendenze necessarie per utilizzare GameDeveloperSkill al massimo delle sue potenzialità.

---

## 📋 Indice
1. [Prerequisiti Software](#prerequisiti-software)
2. [Installazione Skill](#installazione-skill)
3. [MCP Servers](#mcp-servers)
4. [API Keys e Servizi Esterni](#api-keys-e-servizi-esterni)
5. [Configurazione Motori di Gioco](#configurazione-motori-di-gioco)
6. [DesignerSkill Integration](#designerskill-integration)
7. [Verifica Installazione](#verifica-installazione)
8. [Troubleshooting](#troubleshooting)

---

## 🔧 Prerequisiti Software

### Essenziali
- **Node.js** ≥ 18.0 ([nodejs.org](https://nodejs.org))
- **Python** ≥ 3.10 con `uv`/`uvx` ([astral.sh/uv](https://astral.sh/uv))
- **Git** ([git-scm.com](https://git-scm.com))
- **PowerShell** ≥ 5.1 (già presente su Windows)

### Blender
- **Blender** ≥ 4.2 o 5.x ([blender.org](https://blender.org))
- Installazione MCP addon: `uvx mcp-for-blender install-addon`

### Unity (se utilizzi Unity)
- **Unity Hub** ([unity.com](https://unity.com))
- **Unity Editor** 6000.0 LTS o 6000.3 LTS (raccomandato)
- **Unity CLI**: `winget install Unity.CLI`
- Autenticazione: `unity auth login` poi `unity license activate`

### Godot (se utilizzi Godot)
- **Godot** ≥ 4.3 ([godotengine.org](https://godotengine.org))
- **Godot AI MCP** (opzionale): [hi-godot/godot-ai](https://github.com/hi-godot/godot-ai)

### Unreal Engine (se utilizzi Unreal)
- **Unreal Engine** ≥ 5.3 ([unrealengine.com](https://unrealengine.com))
- **Unreal MCP** (coming soon - in sviluppo)

---

## 📦 Installazione Skill

### Opzione 1: Installazione Automatica (Raccomandato)
```powershell
cd "C:\Users\TUONOME\Desktop\GameDeveloperSkill"
.\install.bat
```

### Opzione 2: Installazione Personalizzata
```powershell
powershell -ExecutionPolicy Bypass -File .\game-developer\install.ps1
```

**Parametri disponibili:**
- `-All`: Installa tutto senza prompt
- `-Quiet`: Usa valori di default
- `-Hosts kilo,claude`: Specifica solo certi host
- `-SkipModules designSkillCheck`: Salta moduli specifici

### Cosa viene installato
✅ Skill files in `~/.config/kilo/skills/game-developer` (e altri host)  
✅ Comandi `/game`, `/gdd`, `/playtest`, `/resumegame`  
✅ MCP servers configurati in `kilo.json`/`.claude.json`  
✅ Unity CLI tools  
✅ Blender MCP addon  

---

## 🔌 MCP Servers

### 1. **Blender MCP** (Obbligatorio per modellazione)

**Installazione:**
```powershell
# Installa addon in Blender
uvx mcp-for-blender install-addon

# Aggiorna all'ultima versione
uvx --upgrade mcp-for-blender install-addon
```

**Configurazione in Blender:**
1. Apri Blender
2. `Edit` → `Preferences` → `Add-ons`
3. Cerca "MCP for Blender" e attiva
4. Premi `N` nella viewport 3D
5. Tab `MCP for Blender` → `Start MCP Server`
6. Porta di default: `9876`

**Config file (già gestito dall'installer):**
```json
{
  "mcpServers": {
    "blender": {
      "command": "cmd",
      "args": ["/c", "uvx", "blender-mcp"],
      "env": {
        "BLENDER_HOST": "localhost",
        "BLENDER_PORT": "9876"
      }
    }
  }
}
```

**Verifica funzionamento:**
- Blender deve essere aperto con server attivo
- Check: `uvx blender-mcp --help` non deve dare errore

---

### 2. **CoplayDev Unity MCP** (Obbligatorio per Unity)

**Installazione nel progetto Unity:**
1. Apri Unity con il tuo progetto
2. `Window` → `Package Manager`
3. Click `+` → `Add package from git URL...`
4. Incolla: `https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity`
5. Dopo l'import: `Window` → `MCP` → `Start Server`

**Configurazione automatica:**
```powershell
# Nel progetto Unity
Window → MCP for Unity → Configure All Detected Clients
```

**Ports di default:**
- HTTP: `9877`
- WebSocket: `9878`

**Verifica:**
- Unity deve mostrare `MCP Server Running` nella console
- Finestra MCP mostra status verde

---

### 3. **VoxelAI MCP** (Opzionale - per generazione voxel)

**Setup:**
```powershell
# Clona VoxelAI (se non già presente)
git clone https://github.com/YOUR_PATH/VoxelAIArtist "C:\Users\TUONOME\Desktop\Dev Things\VoxelAIArtist"
```

**Config in `game-developer/config.json`:**
```json
{
  "paths": {
    "voxelai": "C:\\Users\\TUONOME\\Desktop\\Dev Things\\VoxelAIArtist"
  },
  "mcp": {
    "voxelaiWorkdirMode": "per-project"
  }
}
```

**Nota:** Il workdir viene creato automaticamente in `<project>/art/voxel/` per ogni gioco.

---

### 4. **TerminalMCP** (Opzionale ma raccomandato - per playtest automatico)

**Installazione:**
```powershell
# Clone
git clone --depth 1 https://github.com/Fonlogen/TerminalMCP "C:\Users\TUONOME\Desktop\Dev Things\TerminalMCP"

# Installa dipendenze
cd "C:\Users\TUONOME\Desktop\Dev Things\TerminalMCP"
npm install
```

**Config (già gestito dall'installer):**
```json
{
  "mcpServers": {
    "terminalmcp": {
      "command": "node",
      "args": ["C:/Users/TUONOME/Desktop/Dev Things/TerminalMCP/bin/terminalmcp.js"],
      "env": {}
    }
  }
}
```

**Capabilities:**
- Controllo finestre (focus, resize, screenshot)
- Input simulato (keyboard, mouse)
- Browser automation (Playwright)
- Process management

---

### 5. **Godot AI MCP** (Opzionale - solo se usi Godot)

**Installazione:**
```bash
# Clone repository
git clone https://github.com/hi-godot/godot-ai

# Installa plugin in Godot
cp -r godot-ai/addons/godot_ai ~/.config/godot/addons/

# Installa client
cd godot-ai
npm install -g .
```

**Attach al progetto:**
```bash
cd /path/to/your/godot/project
godot-ai attach
```

**Nota:** Con Godot AI puoi fare playtest senza TerminalMCP usando il remote debugging.

---

## 🔑 API Keys e Servizi Esterni

### Blender MCP Integrations

#### Poly Haven (Gratis, nessuna key)
- ✅ Automatico
- HDRIs, textures, models CC0
- Rate limit: ragionevole uso normale

#### Poly Pizza (Gratis, nessuna key)
- ✅ Automatico  
- 10k+ modelli CC0/CC-BY
- Nessuna registrazione richiesta

#### Sketchfab (Gratis con account)
1. Crea account su [sketchfab.com](https://sketchfab.com)
2. Settings → Password & API → Generate token
3. In Blender: `Edit` → `Preferences` → `Add-ons` → `MCP for Blender`
4. Incolla API token nel campo Sketchfab

---

### Generative 3D Services (Opzionali)

#### **TIER: none** (Default - $0)
✅ Nessuna configurazione  
Usa solo: Poly Pizza, Poly Haven, Sketchfab CC0, kits

---

#### **TIER: local** ($0 - richiede GPU NVIDIA)
**Requisiti:**
- NVIDIA GPU ≥ 8GB VRAM (12GB+ raccomandato)
- CUDA Toolkit 11.8+

**Installazione Modly:**
```powershell
# Download da GitHub
# https://github.com/lightningpixel/modly/releases
# Estrai e avvia Modly.exe

# Installa extensions in Modly:
# - Hunyuan3D-2mini
# - TripoSG  
# - TRELLIS2
```

**Config in GDD:**
```markdown
gen3d: local
gen3dBudgetCredits: 0
gen3dMaxAssets: 5
```

**Workflow:**
1. Agent genera prompt + reference image
2. Tu apri Modly desktop app
3. Generi il modello localmente
4. Salvi GLB in `art/exports/`
5. Agent importa e sanitizza

---

#### **TIER: meshy** (Paid - migliore per stylized)
**Registrazione:**
1. [meshy.ai](https://meshy.ai) → Sign up
2. Free tier: ~200 credits/mese
3. Pricing: Text-to-3D ~70 credits, Image-to-3D ~35 credits

**API Key:**
1. Dashboard → API Keys → Create new key
2. Copia la key

**Configurazione:**

**Per Kilo:**
```json
// ~/.config/kilo/kilo.json
{
  "mcpServers": {
    "coplaydev": {
      "env": {
        "MESHY_API_KEY": "msy_TUAKEY"
      }
    }
  }
}
```

**Per Claude Code:**
```json
// ~/.claude.json
{
  "mcpServers": {
    "coplaydev": {
      "env": {
        "MESHY_API_KEY": "msy_TUAKEY"
      }
    }
  }
}
```

**Config in GDD:**
```markdown
gen3d: meshy
gen3dBudgetCredits: 400
gen3dMaxAssets: 5
```

---

#### **TIER: tripo** (Paid - veloce)
**Setup:**
1. [tripo3d.ai](https://tripo3d.ai) → Sign up
2. Free tier disponibile
3. Dashboard → API → Generate key

**Configurazione:**
```json
{
  "mcpServers": {
    "coplaydev": {
      "env": {
        "TRIPO_API_KEY": "tripo_TUAKEY"
      }
    }
  }
}
```

**Config in GDD:**
```markdown
gen3d: tripo
gen3dBudgetCredits: 300
gen3dMaxAssets: 5
```

---

#### **TIER: hyper3d** (Paid - alta qualità PBR)
**Setup:**
1. Ottieni Hyper3D Rodin API key
2. In Blender: `Preferences` → `Add-ons` → `MCP for Blender`
3. Abilita Hyper3D Rodin integration
4. Incolla API key

**Config in GDD:**
```markdown
gen3d: hyper3d
gen3dBudgetCredits: 500
gen3dMaxAssets: 3
```

**Note:** Genera PBR materials, geometria migliore, ma più lento.

---

#### **TIER: hunyuan-cloud** (Gratis - HuggingFace Space)
**Setup:**
1. Nessuna API key
2. Richiede TerminalMCP per browser automation
3. Usa Hunyuan3D-2.1 space su HuggingFace

**Workflow:**
1. Agent genera prompt
2. TerminalMCP apre browser su HF space
3. Submit prompt
4. Download GLB quando pronto
5. Import in `art/exports/`

**Config in GDD:**
```markdown
gen3d: hunyuan-cloud
gen3dMaxAssets: 3
```

**Licenza:** Verifica licenza EU sul modello generato.

---

### MegaScan / Quixel Bridge (Se hai accesso)

**Setup:**
```json
// game-developer/config.json
{
  "paths": {
    "quixelBridge": "C:\\Program Files\\Quixel\\Bridge",
    "megaScanLibrary": "C:\\Users\\TUONOME\\Documents\\Megascans Library"
  },
  "art": {
    "megaScanEnabled": true,
    "megaScanApiKey": "YOUR_KEY_IF_NEEDED"
  }
}
```

**Nota:** MegaScan integration è in sviluppo attivo. Per ora usa manualmente Bridge e importa in `Assets/_Game/Art/MegaScans/`.

---

## 🎮 Configurazione Motori di Gioco

### Unity

**Editor raccomandato:**
```powershell
# Installa Unity 6 LTS
unity install 6000.0.30f1 --yes --accept-eula

# Oppure tramite Hub
# Unity Hub → Installs → Install Editor → 6000.0 LTS
```

**Packages automatici (installati dal worker 'project'):**
- `com.unity.inputsystem`
- `com.unity.cinemachine`
- `com.unity.textmeshpro`
- `com.unity.render-pipelines.universal`
- `com.unity.probuilder@6.1.2`
- CoplayDev Unity MCP (via git)

**Rendering opzionale (toon/outline):**
```json
// Aggiunti automaticamente se GDD specifica "toon" o "outline"
{
  "optionalRenderingPackages": {
    "toon": "https://github.com/Delt06/urp-toon-shader.git?path=Packages/com.deltation.toon-shader",
    "outline": "https://github.com/CristianQiu/Unity-URP-Outline.git"
  }
}
```

---

### Godot

**Setup progetto:**
```bash
# Crea progetto Godot 4.3+
godot --editor --path /path/to/project

# Installa plugin Godot AI (opzionale)
# Segui: https://github.com/hi-godot/godot-ai
```

**Config in `game-developer/config.json`:**
```json
{
  "paths": {
    "godot": "C:\\Program Files\\Godot\\Godot_v4.3-stable_win64.exe"
  },
  "engines": {
    "godotEnabled": true
  }
}
```

**Import pipeline:**
- GLB assets vanno in `res://_game/art/`
- Scripts generati in `res://_game/scripts/`
- Scenes in `res://_game/scenes/`

---

### Unreal Engine

**Status:** 🚧 In sviluppo

**Setup futuro:**
```json
{
  "paths": {
    "unreal": "C:\\Program Files\\Epic Games\\UE_5.4"
  },
  "engines": {
    "unrealEnabled": true,
    "unrealVersion": "5.4"
  }
}
```

**Roadmap:**
- Unreal MCP server
- Blueprint graph generation
- Nanite/Lumen auto-setup
- Level builder per UE5

---

## 🎨 DesignerSkill Integration

GameDeveloperSkill **richiede** DesignerSkill per generare UI (Main Menu, HUD, Pause, GameOver).

### Opzione 1: Path Esistente (Default)
Se hai già DesignerSkill su Desktop:
```json
// game-developer/config.json
{
  "paths": {
    "designerSkill": "C:\\Users\\TUONOME\\Desktop\\DesignerSkill"
  }
}
```

L'installer cerca automaticamente in:
- `C:\Users\TUONOME\Desktop\DesignerSkill\real-world-design`
- E installa in tutti gli host (Kilo, Claude, Codex, Antigravity)

### Opzione 2: Embedded Submodule (Coming Soon)
```powershell
# Clone GameDeveloperSkill con submodules
git clone --recurse-submodules https://github.com/TUOREPO/GameDeveloperSkill

# DesignerSkill sarà in game-developer/modules/designer-skill/
# Hot-reload automatico senza path esterni
```

### Verifica DesignerSkill
```powershell
# In Kilo/Claude/Antigravity
/skills list

# Dovresti vedere:
# - game-developer
# - real-world-design (DesignerSkill)
```

---

## ✅ Verifica Installazione

### Doctor Script
```powershell
cd "C:\Users\TUONOME\Desktop\GameDeveloperSkill\game-developer"
powershell .\scripts\doctor.ps1
```

**Output atteso:**
```
[PASS] Unity CLI installed
[PASS] Blender MCP addon detected
[PASS] Blender server responding on :9876
[PASS] CoplayDev Unity MCP package found
[PASS] DesignerSkill (real-world-design) installed
[PASS] TerminalMCP available
[PASS] Node.js >=18.0
[PASS] Python >=3.10
[PASS] uvx available
[INFO] VoxelAI: C:\Users\...\VoxelAIArtist
[INFO] Gen3D tier: none (0 keys configured)
[WARN] Godot MCP: not installed (optional)
```

### Test Manuale

#### Test Blender MCP
```powershell
# In un coding agent con Blender aperto
@blender get_scene_info user_prompt="test connection"

# Dovrebbe restituire info sulla scena Blender corrente
```

#### Test Unity MCP
```powershell
# Con Unity progetto aperto e MCP server running
# In coding agent
@coplaydev list_scenes

# Dovrebbe listare le scene del progetto
```

#### Test DesignerSkill
```powershell
# In coding agent
/real-world-design create a simple login screen

# Dovrebbe generare mock HTML/CSS
```

---

## 🛠️ Troubleshooting

### Blender MCP non risponde
**Sintomo:** `Connection refused :9876`

**Fix:**
1. Apri Blender
2. `N` panel → `MCP for Blender` → `Start MCP Server`
3. Se già avviato: Stop e Start
4. Verifica firewall Windows non blocchi porta 9876

---

### Unity MCP non trova il package
**Sintomo:** `Package not found` o menu MCP assente

**Fix:**
```powershell
# Rimuovi e reinstalla
# In Unity Package Manager:
# 1. Trova "MCP for Unity" nella lista
# 2. Remove
# 3. + → Add from git URL
# 4. https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity
# 5. Window → MCP → Start Server
```

---

### DesignerSkill non trovato
**Sintomo:** `real-world-design skill not found`

**Fix manuale:**
```powershell
# Clone DesignerSkill se mancante
git clone https://github.com/YOUR_DESIGNER_SKILL_REPO "C:\Users\TUONOME\Desktop\DesignerSkill"

# Reinstalla con check attivo
cd GameDeveloperSkill
powershell .\game-developer\install.ps1 -Quiet

# Verifica
ls "$env:USERPROFILE\.config\kilo\skills\real-world-design\SKILL.md"
# Deve esistere
```

---

### Meshy/Tripo API non funziona
**Sintomo:** `API key invalid` o `rate limit exceeded`

**Check:**
```powershell
# Verifica key è nel file giusto
cat "$env:USERPROFILE\.config\kilo\kilo.json" | Select-String "MESHY_API_KEY"

# Output atteso:
# "MESHY_API_KEY": "msy_..."
```

**Fix:**
1. Regenera API key sul dashboard del servizio
2. Aggiorna in `kilo.json` / `.claude.json`
3. Riavvia coding agent

---

### TerminalMCP errori Node
**Sintomo:** `Cannot find module` o `ERR_MODULE_NOT_FOUND`

**Fix:**
```powershell
cd "C:\Users\TUONOME\Desktop\Dev Things\TerminalMCP"
rm -r node_modules
rm package-lock.json
npm install
```

---

### ProBuilder 6.1.2 non compila
**Sintomo:** `Assembly errors` dopo import ProBuilder

**Fix:**
```powershell
# Solo Unity 6000.5+
# In Unity Package Manager:
# 1. Cerca ProBuilder
# 2. Se versione < 6.1.2: Update to 6.1.2
# 3. Se non disponibile: Remove e reinstalla
# 4. Window → Package Manager → + → Add by name → com.unity.probuilder@6.1.2
```

---

### Git LFS problemi con asset grandi
**Sintomo:** `This exceeds GitHub file size limit` su push

**Fix automatico (esegui una volta per progetto):**
```powershell
cd /path/to/unity/project

# Setup Git LFS
git lfs install
git lfs track "*.fbx"
git lfs track "*.glb"
git lfs track "*.png"
git lfs track "*.jpg"
git lfs track "Assets/_Game/Art/**"
git add .gitattributes
git commit -m "Setup Git LFS"
```

---

## 📞 Supporto

**Repository:** [github.com/TUOREPO/GameDeveloperSkill](https://github.com)  
**Issues:** Apri issue su GitHub per bug/feature requests  
**Discord:** [Link coming soon]  

**File diagnostici utili per segnalazioni:**
- `~/.config/kilo/skills/game-developer/last-doctor.txt`
- `<project>/docs/GAME_CONTEXT.md`
- `<project>/docs/lint/*.json`
- Unity console log: `%APPDATA%\..\LocalLow\<Company>\<Game>\Player.log`

---

## 🚀 Quick Start After Setup

```powershell
# 1. Apri Blender e avvia MCP server (N panel)
# 2. Avvia coding agent (Kilo/Claude/Antigravity)
# 3. In chat:

/game Voglio fare un dungeon crawler medievale low poly con trappole e guerriero

# 4. Rispondi all'intervista (19 domande a blocchi)
# 5. Il sistema genera tutto automaticamente
# 6. Apri Unity quando il worker 'project' lo crea
# 7. Window → MCP → Start Server
# 8. Attendi completamento pipeline
# 9. Playtest automatico con TerminalMCP
```

**Durata tipica:** 45-90 minuti per vertical slice beta-ready.

---

**Versione:** 1.0.0  
**Ultima modifica:** 2025  
**Compatibile con:** GameDeveloperSkill v2.0+
