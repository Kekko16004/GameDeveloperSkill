---
name: game-developer
description: Pipeline autonoma da idea a vertical slice beta-ready, qualsiasi genere e stile. Intervista GDD approfondita e adattiva, poi UN worker isolato per fase. Unity 6 URP per low-poly / toon / stylized / voxel / 2D, Unreal 5.8 (MCP ufficiale) per il realistico. Ponte Unity CLI (`unity command gds_*`, eval, test, play, screenshot). Mondi procedurali seedati (terreno, isola, dungeon, caverna, voxel), case Blender procedurali, livelli da blueprint, lint scena deterministico, lookdev, art review a punteggio, personaggi, VFX, UI via real-world-design. Trigger: idea di gioco, /game, /gdd, /playtest, /resumegame, mondo procedurale, Unity, Unreal, Blender, Voxel.
---

# Game Developer Orchestrator

This skill folder is NOT the game project. After the Skill tool loads this file, use the `Base directory` it reports. Canonical install: `%USERPROFILE%\.agents\skills\game-developer\` (other hosts link to it). Never `Read references/...` relative to the game cwd.

Read `config.json` here (fallback `config/defaults.json`), then [workers.md](references/workers.md).

Tu (parent) **non scrivi gameplay, non modelli, non fai UI, non piazzi pezzi**. Lanci worker. Un worker che chiude senza i file del gate è un bug, non un "quasi fatto".

## Perché

Un agente solo con 50k token di chat chiude in fretta: cubi al posto dell'art, prop sottoterra, niente luci, niente menu, "fatto" senza prova. Ogni worker vede 9 righe di contesto + UN reference + i JSON su disco, e ogni fase chiude con prove misurabili (lint, test, screenshot con voto).

## Due layer

1. **Deterministico** — C# in `Assets/_Game/Editor/GDS/` + runtime in `Assets/_Game/Scripts/GDS/` ([gds-editor.md](references/gds-editor.md)), chiamato con `unity command gds_*` ([unity-cli.md](references/unity-cli.md)): `World` (mondi procedurali), `LevelBuilder` (blueprint → edificio/livello), `Village`, `PB` (ProBuilder), `SceneLint` (gate `issues: 0`), `LookDev` (preset), `Shots` (screenshot reali), `KitCatalog`, `VFX`, `Characters`, `VoxelWorld` runtime. Blender: `templates/blender/gds_building.py` (case vere da spec). Unreal: `templates/unreal/gds_ue.py`.
2. **LLM (worker)** — decide *cosa* (spec, blueprint, palette, preset, clip), mai *dove al centimetro*. Si corregge la spec e si ricostruisce; la scena non si ritocca a mano.

## Strumenti

| Ruolo | Tool | File |
|---|---|---|
| GDD (blocchi A-D, tante domande, follow-up) | intervista | [gdd-interview.md](references/gdd-interview.md) |
| Genere → camera, controller, sistemi, test | ricette | [genres.md](references/genres.md) |
| Stile → motore, asset, look, shader | tabella | [styles.md](references/styles.md) |
| Dimensioni | Geometra | [geometra.md](references/geometra.md) |
| Ponte Unity (primario) | Unity CLI + Pipeline: `gds_*`, `eval`, `run_tests`, `editor_play`, `screenshot` | [unity-cli.md](references/unity-cli.md) + [unity-loop.md](references/unity-loop.md) |
| Ponte Unity (secondario) | CoplayDev unity-mcp (`execute_code`, `manage_ui`, `generate_model`) | [unity-loop.md](references/unity-loop.md) |
| Realistico | Unreal 5.8 MCP ufficiale + `gds_ue.py` + Megascans/Fab + PCG | [unreal-loop.md](references/unreal-loop.md) |
| Mondo procedurale | `gds_world` (terrain / island / dungeon / cave / voxel) | [world-gen.md](references/world-gen.md) + [environments.md](references/environments.md) |
| Edifici esterni | spec JSON → `scripts/gds-building.ps1` (Blender headless) | [blender-building.md](references/blender-building.md) |
| Livelli / interni | blueprint → `gds_build` / `GDS.PB` | [level-builder.md](references/level-builder.md) + [probuilder-levels.md](references/probuilder-levels.md) |
| Insediamenti | `gds_village` | [village.md](references/village.md) |
| QA scena | `gds_lint` | [scene-lint.md](references/scene-lint.md) |
| Art | kit CC0 (Kenney/KayKit/Quaternius) o Synty Starter; realistico: Megascans | [art-pipeline.md](references/art-pipeline.md) + [cc0-sources.md](references/cc0-sources.md) |
| Look | `gds_lookdev` preset + palette + toon/outline | [lookdev.md](references/lookdev.md) |
| Art review | `gds_sheet` + rubric R1-R7 + board di riferimento | [art-direction.md](references/art-direction.md) |
| Personaggi | KayKit / Kenney animati / Quaternius UAL → `GDS.Characters` + NavMesh | [characters.md](references/characters.md) |
| VFX | `gds_vfx` + Cartoon FX Free | [vfx.md](references/vfx.md) |
| Hero prop | Blender MCP: Poly Pizza → Poly Haven → Sketchfab CC0 → tier gen3d GDD | [blender-mcp.md](references/blender-mcp.md) + [polypizza.md](references/polypizza.md) + [gen3d.md](references/gen3d.md) |
| Voxel hero model | VoxelAI | [voxelai.md](references/voxelai.md) |
| OS / input / browser | TerminalMCP stdio | [terminalmcp.md](references/terminalmcp.md) |
| HUD/Menu | real-world-design → UI Toolkit (**obbligatorio**, scelta utente per ogni schermata) | [ui-bridge.md](references/ui-bridge.md) |
| Audio | Kenney CC0 + AudioManager | [audio-pipeline.md](references/audio-pipeline.md) |
| QA | Play Mode + test + lint | [playtest.md](references/playtest.md) + [gates.md](references/gates.md) |
| Microtask / memoria | task atomici, snapshot su disco, `/resumegame` | [task-decomposition.md](references/task-decomposition.md) + [context-management.md](references/context-management.md) |
| Stack globale | confermato una volta nel GDD | [tool-stack.md](references/tool-stack.md) + [doctor.md](references/doctor.md) |

Vietato modellare a mano in `execute_blender_code` (ammesso: wipe, sanitize, `gds_building.py`). Vietato Sloyd. Vietato gen3d fuori tier/budget GDD. Vietato HDRI sui materiali dei prop (ok come skybox). Vietato `--http` TerminalMCP. Blender MCP = `uvx mcp-for-blender` stdio → TCP 9876. Vietato piazzare muri/pavimenti/alberi uno a uno: si scrive la spec.

### Blender MCP: tool dedicati

0. Wipe scena prima di ogni import. 1. `search_*` + `download_*` (Poly Pizza / Poly Haven / Sketchfab). 2. `get_object_info` per i bounds. 3. `get_viewport_screenshot` 1 PNG finale. 4. `export_scene` GLB. `execute_blender_code` solo per wipe e sanitize.

## Console

`start-dashboard.bat` apre la TUI (`tools/tui/gds_tui.py`): progetto, FabCLI, DesignerSkill.

- `project.path` vuoto → chiedi il percorso e salvalo.
- `fab.enabled` false/assente → niente Fab. true: `fab.cli` o `fabcli` sul PATH; `fabcli auth status`; `fabcli download <uid> -o "<fab.library_path>"`. Solo per il realistico o per la libreria personale dell'utente.
- `designerSkillPolicy.allowUpdate` false → non ricopiare DesignerSkill (`paths.designerSkill`).

## Aggiornamento

Se l'utente chiede di aggiornare la skill: `scripts/update.bat` (git pull del repo + reinstallazione con host e moduli salvati in `config.json`; i valori già impostati restano). Poi va riavviato il client.

## Cosa fa il parent

1. Doctor (`scripts/doctor.ps1`).
2. `GDD.md` non `locked` → intervista (unica fase in cui parli con l'utente): blocchi A-D, tante domande, follow-up su ciò che è vago, default consigliati. Recap dichiarato vs inferito, correzioni, lock.
3. Worker **project** (Unity: create/attach + `install-gds-editor.ps1` + `gds_ping`; Unreal: plugin MCP + `gds_ue.py`).
4. Worker **task-decomposition** → `GAME_TASKS.md`, `GAME_CONTEXT.md` (genre, style), `ASSET-LEDGER.md`, `art/blueprints/PLAN.md`, `art/reference/BOARD.md`, `art/world/<name>.json` se procedurale.
5. Worker **greybox** (ground top Y=0, controller del genere, test movimento verde, lint 0).
6. Worker **kit-fetch** → **world-gen** (se mondo procedurale) → **building-gen** (batch 5, se edifici esterni) → **level-build** (1 blueprint per worker, max 3 in parallelo) → **village** (solo insediamenti) → **hero-asset** (batch 3) → **import-art**. Ogni gate con `lint: issues 0`.
7. Worker **lookdev** → **art-review** (media ≥ 4, altrimenti fix list e rilancio, max 2 giri).
8. Worker **characters** (+ NavMesh se nemici) → **systems** (un verbo = script + test).
9. Worker **ui-main-menu**, **ui-hud**, **ui-pause**, **ui-gameover** (real-world-design, 3-4 varianti, SCELTA UTENTE per ciascuna).
10. Worker **juice** → **art-review** (seconda passata) → **playtest** → **slice** solo se tutti i gate PASS.

**Sessione:** `continuous` (Claude Code / Kilo con subagent): il parent incatena le fasi, memoria su disco. `hard-stop` (Antigravity / monochat): banner + `/resumegame` dopo ogni macrotask ([session-cuts.md](references/session-cuts.md)).

## Isolamento (tassativo)

- `Task` con `subagent_type: general`. Prompt = blocco di workers.md + 9 righe. Niente history.
- Il worker non fa altre fasi. Il parent rilegge solo `docs/gates/*.md` e `docs/lint/*.json`.
- "Ho costruito X" senza spec/blueprint JSON + JSON di build + PNG = FAIL. "Ho usato Blender" senza `screenshots/blender-*.png` e GLB = FAIL. Gate di scena senza `lint: {"issues":0` = FAIL.

## Slice FAIL se manca uno

- Main Menu scena index 0
- HUD con obiettivo visibile
- Mondo del GDD costruito (world JSON / blueprint / village) senza primitive Unity visibili
- `Global_Volume` + `LookDev_<preset>.asset` (Unreal: `gds_ue.lookdev`)
- Art review PASS (media ≥ 4, nessun voto < 3) o voti riportati onestamente all'utente dopo 2 giri
- Personaggio animato (o giustificazione GDD: FP senza corpo)
- `docs/lint/scene-lint.json` con `issues: 0`
- Screenshot Play Mode dove si capisce cosa fare
- Test di ogni verbo eseguiti (output nel gate)

## Hard rules

- Primitive Unity solo nel greybox. Poi ogni cosa visibile = kit / mondo GDS / ProBuilder con palette / GLB.
- Una famiglia di asset per slice (riga di styles.md).
- UI: `real-world-design` sempre, Variant Studio 3-4 opzioni, scelta dell'utente per ogni schermata, coerenza token col Main Menu. UXML a mano come primo passo = FAIL.
- Dopo script o copia GDS: `recompile` → `recompile_status` → `console` 0 errori, poi usa.
- Niente YAML `.unity`/`.prefab` a mano con l'Editor aperto.
- Scope = slice del GDD.
- Unity 6000.x (6000.5+ con ProBuilder ≥ 6.1.2, l'installer lo gestisce). Unreal solo 5.8+.
