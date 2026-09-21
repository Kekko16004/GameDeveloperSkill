---
name: game-developer
description: Pipeline autonoma da idea a vertical slice Unity beta-ready. Intervista GDD (19 domande), poi UN worker isolato per fase. Case vere dal generatore Blender procedurale (spec JSON), livelli e villaggi da blueprint (GDS.LevelBuilder / GDS.Village / ProBuilder), lint scena deterministico, lookdev con post-processing, personaggi CC0 animati, VFX, UI Toolkit via real-world-design. Trigger: idea di gioco, /game, /gdd, /playtest, HUD, kit, Blender, Voxel, Unity.
---

# Game Developer Orchestrator

This skill folder is NOT the Unity project. After the Skill tool loads this file, follow the `skill_files` / `Base directory` in that tool result. **Do not** `Read references/workers.md` from the game cwd — it will 404 and you must not abort GDD.

Absolute skill dir (Windows): `%USERPROFILE%\.config\kilo\skills\game-developer\`, `%USERPROFILE%\.kilo\skills\game-developer\`, `%USERPROFILE%\.claude\skills\game-developer\`.

Leggi `config.json` in quella cartella (fallback `config/defaults.json`). Poi [workers.md](references/workers.md) dallo stesso albero.

Tu (parent) **non scrivi gameplay, non modelli, non fai UI, non piazzi pezzi**. Lanci worker. Un worker che chiude senza i file del gate e un bug, non un "quasi fatto".

## Perche esiste questa regola

Un agente solo, con 50k token di chat, chiude in fretta: cubi al posto dell'art, prop sottoterra, niente luci, niente Main Menu, "fatto" senza prova. Isolare ogni fase azzera quel contesto. Ogni worker vede 8 righe + UN reference + i JSON su disco.

## Due layer

1. **Deterministico** — C# in `Assets/_Game/Editor/GDS/` ([gds-editor.md](references/gds-editor.md)): `LevelBuilder` (blueprint JSON → edificio L/T/U + interni + dettagli + scatter in una chiamata), `Village` (mondo intero), `PB` (stanze/torri/scale ProBuilder vere), `SceneLint` (sepolti/flottanti/collider/rosa/non-URP → `issues: 0` o FAIL, con auto-fix), `LookDev` (sole, fog, skybox, Volume ACES/bloom/AO, camera), `KitCatalog`, `VFX`, `Characters` — via CoplayDev `execute_code`. Piu il generatore Blender `templates/blender/gds_building.py` ([blender-building.md](references/blender-building.md)): case vere da una spec di 20 righe, headless via `scripts/gds-building.ps1`.
2. **LLM (worker)** — decide *cosa* (blueprint, palette, preset, quali clip), non *dove al centimetro*.

## Strumenti

| Ruolo | Tool | File |
|---|---|---|
| Dimensioni | Geometra | [geometra.md](references/geometra.md) |
| GDD (19 domande: stack, sessione, asset, gen3d+budget, asset store, GPU, look) | intervista | [gdd-interview.md](references/gdd-interview.md) |
| Create/open Unity | Unity CLI | [unity-cli.md](references/unity-cli.md) |
| Scene/script/test/graphics/vfx/code | CoplayDev unity-mcp (`execute_code`, `manage_graphics`, `manage_vfx`, `manage_camera`, `manage_animation`, `manage_ui`) | [unity-loop.md](references/unity-loop.md) |
| Edifici veri (esterni) | spec JSON → `scripts/gds-building.ps1` (Blender procedurale headless: infissi, cornici, tetti, travi, balconi, interni) | [blender-building.md](references/blender-building.md) |
| Livelli / interni | blueprint JSON → `GDS.LevelBuilder` (kit L/T/U, partizioni, attach, recinzioni) / `GDS.PB` | [level-builder.md](references/level-builder.md) + [probuilder-levels.md](references/probuilder-levels.md) |
| Mondo | `GDS.Village` (terreno, strade, piazza, lotti, lampioni, bosco) | [village.md](references/village.md) |
| QA scena | `GDS.SceneLint` | [scene-lint.md](references/scene-lint.md) |
| Art default | Kit CC0 (Kenney/KayKit/Quaternius) o Synty Starter (Asset Store, se GDD) | [art-pipeline.md](references/art-pipeline.md) + [cc0-sources.md](references/cc0-sources.md) |
| Look | `GDS.LookDev` preset + palette + toon/outline opzionali | [lookdev.md](references/lookdev.md) |
| Personaggi | KayKit / Kenney animati / Quaternius UAL → `GDS.Characters` + NavMesh | [characters.md](references/characters.md) |
| VFX | `GDS.VFX` + `manage_vfx` + Cartoon FX Free | [vfx.md](references/vfx.md) |
| Hero prop | Blender MCP: Poly Pizza / Poly Haven models / Sketchfab CC0; tier gen3d dal GDD | [blender-mcp.md](references/blender-mcp.md) + [polypizza.md](references/polypizza.md) + [gen3d.md](references/gen3d.md) |
| Voxel | VoxelAI | [voxelai.md](references/voxelai.md) |
| OS / WASD / finestre / browser | TerminalMCP `--tools all` stdio | [terminalmcp.md](references/terminalmcp.md) |
| HUD/Menu | real-world-design → UI Toolkit (**obbligatorio**) | [ui-bridge.md](references/ui-bridge.md) |
| Audio | Kenney CC0 + AudioManager | [audio-pipeline.md](references/audio-pipeline.md) |
| QA | Play Mode + lint | [playtest.md](references/playtest.md) |
| Microtask | Scomposizione Atomica (1 task = 1 blueprint / 1 hero / 1 verbo) | [task-decomposition.md](references/task-decomposition.md) |
| Snapshot | Memoria su disco & /resumegame | [context-management.md](references/context-management.md) |
| Stack globale | Conferma in GDD Q13 | [tool-stack.md](references/tool-stack.md) |

Vietato modellare a mano in `execute_blender_code` (ammesso solo: wipe, sanitize, `exec` di `gds_building.py`). Vietato Sloyd. Vietato gen3d fuori dal tier/budget GDD. Vietato HDRI su materiali di prop (ok come skybox). Vietato `--http` TerminalMCP. Blender MCP = `uvx blender-mcp` stdio → TCP 9876 (non `http://localhost:9876/mcp`). Vietato piazzare muri/pavimenti uno a uno con `manage_gameobject`: si scrive il blueprint.

### REGOLA BLENDER MCP: USA I TOOL DEDICATI (MAI SOLO execute_blender_code)
0. Wipe preventivo scena OBBLIGATORIO prima di ogni import.
1. `search_polypizza_models` + `download_polypizza_model` / `search_polyhaven_assets(asset_type="models")` + `download_polyhaven_asset` / `search_sketchfab_models` + `download_sketchfab_model`.
2. `get_scene_info` + `get_object_info` per bounding box. 3. `get_viewport_screenshot` 1 PNG finale. 4. `set_texture` per PBR. 5. `export_scene` GLB. 6. `bpy_api_lookup`.
`execute_blender_code` SOLO per: wipe iniziale; sanitize finale (luci/camere via, pivot Y=0, decimate).

## Cosa fa il parent

1. Doctor (`scripts/doctor.ps1`).
2. Se `GDD.md` non e `locked` → worker **gdd** (o intervista tu, e l'unica fase in cui parli con l'utente). 19 domande, tutte.
3. Recap detto vs inferito. Correzione = rimostra. Poi lock.
4. Worker **project** (attach/create + `install-gds-editor.ps1` + packages + `execute_code` verificato).
5. Worker **task-decomposition** → `GAME_TASKS.md` + `GAME_CONTEXT.md` + `ASSET-LEDGER.md` + `art/blueprints/PLAN.md`.
6. Worker **greybox** (`GDS.PB.Room` / blueprint primitives, ground top Y=0, lint 0). Test movimento verde.
7. Worker **kit-fetch** (+ `GDS.KitCatalog`). Poi **building-gen** (case Blender, batch 5), **un worker level-build per blueprint** (parallelo max 3), **village** se il GDD e esterno, **hero-asset** batch max 3 per i prop unici, **import-art** se serve. Ogni gate con `lint: issues 0`.
8. Worker **lookdev** (preset GDD). Screenshot con Volume visibile.
9. Worker **characters** (+ NavMesh se nemici).
10. Worker **systems** (un verbo/script per task con test dedicato).
11. Worker **ui-main-menu** (real-world-design obbligatorio). Poi ui-hud, ui-pause, ui-gameover. Senza Main Menu = FAIL.
12. Worker **juice** (VFX + audio + hit-stop).
13. Worker **playtest**. Lint 0 + screenshot leggibile.
14. Worker **slice** solo se tutti i gate PASS.

**Sessione:** `continuous` (Claude Code / Kilo con subagent): il parent incatena le fasi senza fermarsi; la memoria e su disco. `hard-stop` (Antigravity / monochat): banner + `/resumegame` dopo ogni macrotask, max 3 level-build per chat (session-cuts.md).

## Isolamento (tassativo)

- `Task` con `subagent_type: general`. Prompt = blocco in workers.md. Niente history.
- Worker non legge altre phases. Non "poi faccio anche il menu".
- Parent rilegge solo `docs/gates/*.md` + i JSON in `docs/lint/`.
- Dichiarare "ho costruito la casa" senza `art/blueprints/<name>.json` + `docs/lint/build-<name>.json` = FAIL.
- Dichiarare "ho usato Blender" senza `screenshots/blender-*.png` e GLB = FAIL.
- Gate di una fase che tocca la scena senza `lint: {"issues":0` = FAIL.

## Slice FAIL se manca uno

- Main Menu scena index 0 (non spawn FP nel livello)
- HUD con testo obiettivo visibile
- Almeno 2 edifici finiti (spec Blender `art/specs/*.json` + FBX, o blueprint kit con `attach`) e nessun primitive Unity visibile; esterni: `docs/lint/village-*.json` con `buildings >= 6`
- `Global_Volume` + `LookDev_<preset>.asset` (scena illuminata, non piatta)
- Personaggio animato (o giustificazione GDD: es. FP senza corpo)
- `docs/lint/scene-lint.json` con `issues: 0`
- Play Mode screenshot dove si capisce cosa fare
- Test movimento eseguito (job_id o output in gate)

## Hard rules residue

- Primitives Unity solo in greybox. Dopo, ogni cosa visibile = kit / ProBuilder con materiale palette / GLB.
- Una famiglia kit per slice (Kenney **o** KayKit **o** Quaternius **o** Synty). Hero prop CC0 possono vestirla se low-poly.
- UI: Skill `real-world-design` sempre. Variant Studio con 3-4 opzioni e SCELTA UTENTE OBBLIGATORIA per CIASCUNA schermata (Main Menu, HUD, Pause, GameOver). Vietato generare HUD/Pause/GameOver in automatico senza mostrare varianti di layout e attendere il pick dell'utente (mantenendo però coerenza di token/stile del Main Menu). UXML a mano come primo passo = FAIL.
- Dopo `create_script` o copia GDS: wait compile, `read_console`, poi usa.
- No YAML `.unity` se Editor e vivo.
- Scope = GDD slice. Non open world.
- Unity 6000.0 / 6000.3 LTS consigliati. 6000.5+: ProBuilder ≥ 6.1.2 (l'installer lo fissa).
