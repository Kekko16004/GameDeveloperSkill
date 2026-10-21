# GameDeveloperSkill

Skill multi-host (Claude Code, Kilo, Codex, Antigravity, Cursor...) che porta un'idea a una **vertical slice giocabile e curata**, di qualsiasi genere e stile: intervista GDD approfondita, poi un worker isolato per fase, ognuna chiusa da prove su disco (lint, test, screenshot con voto).

| Stile | Motore | Come |
|---|---|---|
| low-poly, toon, stylized, voxel, 2D | Unity 6 URP | Unity CLI (`unity command gds_*`), kit CC0, mondi procedurali GDS, Blender per le case |
| realistico | Unreal 5.8 | MCP ufficiale Epic, Megascans/Fab, Landscape + PCG, `gds_ue.py` |

## Skill aggiuntiva: `fivem-sollumz/`

Pipeline Blender + Sollumz per modelli GTA V / FiveM (prop statici, fisici, animati con YCD, UV, DUI, porte, luci,
Gen8 + Gen9), 100% pilotabile da Python. Vedi [fivem-sollumz/README.md](fivem-sollumz/README.md).

## Avvio

```bat
install.bat            :: rileva host e tool, installa la skill una volta e la collega a ogni host
update.bat             :: git pull + reinstalla con host e moduli salvati (anche game-developer\scripts\update.bat)
start-dashboard.bat    :: console: progetto, FabCLI, DesignerSkill
```

Poi nel client: `/game <idea>` (o `/gdd`, `/playtest`, `/resumegame`).

## Cosa c'è dentro

```
game-developer/
  SKILL.md                 orchestratore (parent)
  references/              un file per fase/tema, letto on demand
  templates/Editor/GDS/    layer C# deterministico (World, LevelBuilder, Village, PB, SceneLint, LookDev, Shots, ...) + comandi CLI
  templates/Runtime/GDS/   runtime: Noise, VoxelWorld (chunk, greedy meshing, scava/costruisci), SkyGradient shader
  templates/world/         spec di esempio: terrain, island, dungeon, cave, voxel
  templates/blender/       generatore procedurale di edifici
  templates/unreal/        gds_ue.py (lookdev, lint, screenshot, import Fab, heightmap)
  templates/*.md|json      DECISIONI, TESTER_README, feel-baseline, progress-checkpoint, worker-report, gate, gate-plan
  scripts/                 doctor, install GDS nel progetto, fetch kit/audio CC0, edifici Blender headless,
                           gate_link.py (contratto con game-launch-strategist), design_review.py (schermate/orfani, run a tempi)
  command/                 /game /gdd /playtest /resumegame
  tools/tui/               console
docs/                      audit, roadmap, sample render
```

## Pipeline

`/game` → intervista (blocchi A-E, domande adattive) → (controllo di mercato offerto) → project → task (60-80, per deliverable) → greybox + test → kit → **world-gen** → edifici/livelli → hero prop → lookdev → **art review a punteggio** → personaggi → sistemi (verbo = script + test) → feel baseline (scena vera) → UI (scelta utente per ogni schermata) → baseline di qualità → juice → art review → playtest → slice.

Dopo la slice: **design review** (mappa del gioco dal codice, mappa schermate con controllo orfani, run simulate a tempi) → piano dei gate → **gate di iterazione** con header leggibile da macchina → review "dopo". Con `game-launch-strategist` le due skill si passano il lavoro con file fissi (`references/launch-link.md`, contratto `gdl-v2`); senza, la skill lavora da sola.

## Documentazione

- `INSTALL.md` — installazione e setup
- `docs/AUDIT-2026-09.md` — perché la pipeline è fatta così (con fonti)
- `docs/ROADMAP.md` — idee non ancora fatte
