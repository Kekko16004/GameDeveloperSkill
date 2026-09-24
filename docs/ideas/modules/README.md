# Moduli GameDeveloperSkill

Questa cartella contiene i moduli opzionali e embedded che estendono le funzionalità core della skill.

## Struttura

```
modules/
├── designer-skill/       # DesignerSkill embedded (submodule Git)
├── megascan/            # MegaScan/Quixel Bridge integration
├── style-presets/       # Preset stili visuali (realistic, toon, voxel, etc.)
└── README.md
```

## DesignerSkill Embedded

### Installazione come Submodule
```bash
git submodule add https://github.com/YOUR_DESIGNER_SKILL_REPO modules/designer-skill
git submodule update --init --recursive
```

### Hot Reload
Il sistema rileva automaticamente `modules/designer-skill/` e lo usa invece del path esterno in `config.json`.

**Priorità:**
1. `modules/designer-skill/` (embedded)
2. `config.paths.designerSkill` (path esterno)
3. `~/.config/kilo/skills/real-world-design` (system-wide)

### Update
```bash
cd modules/designer-skill
git pull origin main
cd ../..
git add modules/designer-skill
git commit -m "Update DesignerSkill to latest"
```

## MegaScan Integration

Modulo per integrare la libreria MegaScan/Quixel dell'utente.

**Setup:** Vedi `megascan/SETUP.md`

## Style Presets

Preset visuali completi che configurano:
- Lookdev settings
- Material palettes  
- Shader packages
- Asset preferences (kit families)
- Post-processing stacks

**Stili disponibili:** Vedi `style-presets/CATALOG.md`
