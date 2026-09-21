# Pipeline

Parent = dispatcher. Implementazione = worker. Dettaglio prompt: [workers.md](workers.md).
Art routing: [art-pipeline.md](art-pipeline.md). Layer deterministico: [gds-editor.md](gds-editor.md).

```
0  doctor                          parent
1-3 GDD interview (19 domande) + LOCK   parent parla; oppure worker gdd
4  project attach|create + GDS editor scripts + packages     worker project
5  task-decomposition               worker task-decomposition (GAME_TASKS + GAME_CONTEXT + ASSET-LEDGER + lista blueprint)
6  greybox + movement test          worker greybox  (GDS.PB.Room / primitives blueprint; ground top = Y 0)
7a kit-fetch + kit-catalog          worker kit-fetch (fetch-cc0-kits.ps1 + GDS.KitCatalog.BuildJson → art/kit-catalog.json)
7b building-gen (Blender procedurale, batch max 5 spec)  worker building-gen  ← case/locande/torri-casa VERE: gds-building.ps1 → FBX + preview
7c level-build (1 blueprint = 1 worker) worker level-build  ← kit L/T/U + interni + attach + recinzioni, o shell ProBuilder per interni/dungeon
7d village (se il GDD e esterno)   worker village (GDS.Village: terreno, strade, piazza, lotti con edifici 7b/7c, lampioni, bosco)
7e hero-asset (Poly Pizza / Poly Haven / Sketchfab / gen3d tier)   worker hero-asset (batch max 3, sanitize, export, poi riga props nel blueprint)
7f import-art                       se restano GLB fuori Unity
8  lookdev                          worker lookdev (GDS.LookDev.Apply(preset GDD) + palette + toon/outline opzionali)
9  characters (+ navmesh se nemici) worker characters (GDS.Characters + skill initialize-ai-navigation)
10 systems + test per verbo         worker systems
11a Main Menu UI Toolkit            worker ui-main-menu   <-- obbligatorio, real-world-design
11b HUD / 11c Pause / 11d GameOver   worker ui-hud / ui-pause / ui-gameover (real-world-design)
12 juice (VFX + audio + hit-stop)   worker juice (GDS.VFX + audio-pipeline)
13 playtest                         worker playtest (SceneLint 0 + Play Mode + WASD + screenshot)
14 slice recap                      worker slice  (FAIL se un gate e rosso)
```

`session-mode: continuous` (Claude Code / Kilo con subagent): il parent lancia il worker successivo appena il gate e PASS, senza fermarsi. `hard-stop` (Antigravity / monochat): banner + `/resumegame` dopo ogni riga (vedi session-cuts.md).
`GDD.md` campo `phase:` aggiornato dal parent dopo ogni gate PASS.

## Memoria su disco (per host che perdono contesto)

Ogni fase legge/scrive solo file piccoli e strutturati, mai la chat:

| File | Chi lo scrive | Chi lo legge |
|---|---|---|
| `GDD.md` (19 risposte lockate) | gdd | tutti |
| `GAME_CONTEXT.md` / `GAME_TASKS.md` | task-decomposition, poi ogni worker | tutti, `/resumegame` |
| `ASSET-LEDGER.md` | task-decomposition, hero-asset | level-build, slice |
| `art/kit-catalog.json` | kit-fetch | level-build |
| `art/specs/*.json` | building-gen (uno per edificio Blender) | building-gen (rebuild), village |
| `art/blueprints/*.json` | level-build (uno per edificio/area), village (`village_*.json`) | level-build / village (rebuild), playtest |
| `docs/lint/scene-lint.json`, `docs/lint/build-*.json` | GDS scripts | parent (gate) |
| `docs/gates/NN-*.md` | ogni worker | parent, slice |

## File gate

Ogni worker scrive `docs/gates/NN-name.md`:

```
phase: level-build
status: PASS|FAIL
blueprint: art/blueprints/house_a.json
build: {"status":"PASS","pieces":38,"props":6,"scattered":25,"missingRoles":[],"warnings":[]}
lint: {"issues":0,"buried":0,"floating":0,"noCollider":0,"pinkMaterial":0}
evidence:
  - screenshots/020-build-house_a.png
notes: ...
```

Senza questo file la fase non e fatta. Chat "fatto" non conta. Senza riga `lint:` con `issues: 0` la fase e FAIL per ogni worker che tocca la scena (greybox, level-build, hero-asset, import-art, lookdev, characters, juice, playtest).

## Anti-pigrizia

| Sintomo | Azione parent |
|---|---|
| Worker piazza muri/pavimenti uno a uno con `manage_gameobject` | scarta. Rilancia level-build con blueprint |
| Worker usa ProBuilder MCP face-by-face (extrude/delete per indice) per una stanza | scarta. `GDS.PB.Room` / blueprint `mode: probuilder` |
| Cubi Unity default visibili dopo level-build | FAIL. Blueprint con `roles` mancanti → kit-catalog, non cubi |
| Edificio esterno "scatola" senza infissi/tetto/dettagli in una slice che li richiede | retry building-gen (spec Blender) o `attach` nel blueprint kit |
| Worker scrive Python Blender a mano invece di una spec per `gds_building.py` | FAIL. Solo spec + gds-building.ps1 (o exec del generatore via MCP) |
| Worker apre Blender per un crate Kenney | scarta. Riga `props` nel blueprint |
| Worker usa bpy cubi / Sloyd / gen3d fuori tier GDD | FAIL |
| Worker punta blender a http://localhost:9876/mcp | FAIL. Serve uvx stdio |
| Mix Kenney + KayKit nella stessa stanza | FAIL. Una famiglia |
| GLB < 15KB su riga hero | retry. E un cubo |
| Gate senza `lint: issues 0` | FAIL retry (`RunJson(autoFix:true)` poi `RunJson()`) |
| Screenshot lookdev senza Volume/fog/ombre (scena piatta) | retry lookdev |
| UI senza mock HTML real-world-design | retry ui. UXML a mano = FAIL |
| Gioco parte in FP senza menu | retry ui-main-menu. Slice bloccata |
| Screenshot illeggibile | retry hud + playtest |
| Worker ha fatto 3 fasi in un turno | scarta il lavoro extra |
| Contesto parent enorme | non implementare tu. Lancia il prossimo worker |

## Greybox vs art

Greybox = `GDS.PB.Room` / blueprint primitives, deve **giocarsi**. Art = level-build sostituisce i primitives con blueprint `mode: kit` (stesso `name` → rebuild in place). Non dichiarare slice se restano primitives visibili (ProBuilder shell + kit = OK).
