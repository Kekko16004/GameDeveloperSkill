---
name: game-developer
description: Pipeline autonoma da idea a vertical slice beta-ready, qualsiasi genere e stile, sempre continua e in parallelo (scheduler a ondate di subagent). Engine scelto dall'utente alla prima domanda — Unity 6 URP, Nucleon (MCP dell'editor via ncli.py: build da spec, lint, screenshot, test Lua in Play), Unreal 5.8 (MCP ufficiale), Godot. Intervista GDD approfondita e adattiva, poi worker isolati con contratto. Ponte Unity CLI (`unity command gds_*`, eval, test, play, screenshot). Mondi procedurali seedati (terreno, isola, dungeon, caverna, voxel), case Blender procedurali, livelli da blueprint, lint scena deterministico, lookdev, art review a punteggio, personaggi, VFX, UI via real-world-design. Dopo la slice: design review (mappa del gioco dal codice, schermate e orfani, run simulate a tempi) e gate di iterazione con header leggibile da macchina; collabora con game-launch-strategist (ondate → gate → issue_status/TODO) ma funziona anche da sola. Trigger: idea di gioco, /game, /gdd, /playtest, /resumegame, mondo procedurale, Unity, Nucleon, NucleonEngine, Unreal, Godot, Blender, Voxel, gate, fix dal focus group, design review.
---

# Game Developer Orchestrator

This skill folder is NOT the game project. After the Skill tool loads this file, use the `Base directory` it reports. Canonical install: `%USERPROFILE%\.agents\skills\game-developer\` (other hosts link to it). Never `Read references/...` relative to the game cwd.

Read `config.json` here (fallback `config/defaults.json`), then [workers.md](references/workers.md) and [engines.md](references/engines.md).

Tu (parent) **non scrivi gameplay, non modelli, non fai UI, non piazzi pezzi**. Lanci worker. Un worker che chiude senza i file del gate è un bug, non un "quasi fatto".

## Perché

Un agente solo con 50k token di chat chiude in fretta: cubi al posto dell'art, prop sottoterra, niente luci, niente menu, "fatto" senza prova. Ogni worker vede 9 righe di contesto + UN reference + i JSON su disco, e ogni fase chiude con prove misurabili (lint, test, screenshot con voto). Tutti i task pronti partono insieme (scheduler a ondate), l'editor ha un solo driver alla volta (lock): veloce senza pestarsi i piedi.

## Due layer

1. **Deterministico** — Unity: C# in `Assets/_Game/Editor/GDS/` + runtime in `Assets/_Game/Scripts/GDS/` ([gds-editor.md](references/gds-editor.md)), chiamato con `unity command gds_*` ([unity-cli.md](references/unity-cli.md)): `World` (mondi procedurali), `LevelBuilder` (blueprint → edificio/livello), `Village`, `PB` (ProBuilder), `SceneLint` (gate `issues: 0`), `LookDev` (preset), `Shots` (screenshot reali), `KitCatalog`, `VFX`, `Characters`, `VoxelWorld` runtime. Nucleon: `scripts/ncli.py build` (spec JSON → entità in un solo batch JSON-RPC, rebuild in place), `ncli lint`, `ncli shot`, `ncli play-test` + harness Lua `templates/nucleon/Content/Scripts/gds_test.lua`, `scripts/html2rml.py` (mock → RmlUi). Blender: `templates/blender/gds_building.py` (case vere da spec). Unreal: `templates/unreal/gds_ue.py`.
2. **LLM (worker)** — decide *cosa* (spec, blueprint, palette, preset, clip), mai *dove al centimetro*. Si corregge la spec e si ricostruisce; la scena non si ritocca a mano.

## Strumenti

| Ruolo | Tool | File |
|---|---|---|
| GDD (blocchi A-E, tante domande, follow-up) | intervista | [gdd-interview.md](references/gdd-interview.md) |
| Baseline (accessibilità, UI, onboarding, lingue, kit playtest, cattura store) | blocco E + task | [quality-baseline.md](references/quality-baseline.md) |
| Lancio / focus group (`game-launch-strategist`) | contratto condiviso `gdl-v3`: ondate → piano dei gate, gate → `issue_status` / TODO / stato attuale; funziona anche da sola | [launch-link.md](references/launch-link.md) + `scripts/gate_link.py` |
| Design review (dopo la slice) | mappa del gioco dal codice, mappa schermate (raggiungibilità, orfani), run simulate a tempi, prima e dopo ogni gate | [design-review.md](references/design-review.md) + `scripts/design_review.py` |
| Gate di iterazione | header leggibile da macchina, meccanica vera, foto guardate, salvataggi, rischi introdotti | [gates.md](references/gates.md) §17-25 + [templates/gate.md](templates/gate.md) |
| **Engine (scelta dell'utente, Q0)** | adapter a 8 verbi: ping, build, lint, shot, test, play, lock, package | [engines.md](references/engines.md) |
| Genere → camera, controller, sistemi, test | ricette | [genres.md](references/genres.md) |
| Stile → asset, look, shader (non l'engine) | tabella | [styles.md](references/styles.md) |
| Dimensioni | Geometra | [geometra.md](references/geometra.md) |
| Ponte Unity (primario) | Unity CLI + Pipeline: `gds_*`, `eval`, `run_tests`, `editor_play`, `screenshot` | [unity-cli.md](references/unity-cli.md) + [unity-loop.md](references/unity-loop.md) |
| Ponte Unity (secondario) | CoplayDev unity-mcp (`execute_code`, `manage_ui`, `generate_model`) | [unity-loop.md](references/unity-loop.md) |
| Nucleon | `scripts/ncli.py` (client dell'MCP dell'editor: build/cycle con cache, lint in Play, serve, lua-check, affected, capture, tools-check) + `nc_gds.py` (kit catalog, stanze kit, kitScale) + `nc_world.py` (terreno/isola/villaggio/dungeon/caverna, look) + `nc_mat.py` (materiali: 14 shading model dell'engine per ruolo, ORM, vento delle piante, assegnazione al livello, check dei modelli mai eseguiti) + `tools/nucleon-bench` (benchmark → piano di esecuzione per l'engine) + `templates/nucleon/` (test, sonda, capture, telemetria) + `html2rml.py` | [nucleon-loop.md](references/nucleon-loop.md) + bug noti dell'engine [docs/NUCLEON-ENGINE-NOTES.md](../docs/NUCLEON-ENGINE-NOTES.md) |
| Unreal | Unreal 5.8 MCP ufficiale + `gds_ue.py` + Megascans/Fab + PCG | [unreal-loop.md](references/unreal-loop.md) |
| Godot (raro) | headless + addon MCP se c'è | [godot-loop.md](references/godot-loop.md) |
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
| Hero prop | **Script Blender procedurale headless** (`blender -b -P Tools/<asset>_build.py`, `scripts/blender/hero_kit.py`) dal riferimento → GLB → import nel motore (Nucleon: `ncli asset_import` + spec + `shot`). Fallback solo per organico (persone, animali) o se l'utente lo chiede: Poly Pizza → Poly Haven → Sketchfab CC0 → tier gen3d | [hero-procedural.md](references/hero-procedural.md) (+ [blender-mcp.md](references/blender-mcp.md), [gen3d.md](references/gen3d.md) per il fallback) |
| Voxel hero model | VoxelAI | [voxelai.md](references/voxelai.md) |
| OS / input / browser | TerminalMCP stdio | [terminalmcp.md](references/terminalmcp.md) |
| HUD/Menu | real-world-design → UI Toolkit / RmlUi / UMG (**obbligatorio**, varianti di tutte le schermate in parallelo, scelta utente in una domanda unica) | [ui-bridge.md](references/ui-bridge.md) |
| Audio | Kenney CC0 + AudioManager | [audio-pipeline.md](references/audio-pipeline.md) |
| QA | Play Mode + test + lint; repro-first dei bug (`test_bug_*`), `gds_bisect.py`, budget di performance, telemetria opt-in (`telemetry_report.py`), catture store/trailer | [playtest.md](references/playtest.md) + [gates.md](references/gates.md) |
| Microtask / memoria | task atomici, snapshot su disco, `/resumegame` | [task-decomposition.md](references/task-decomposition.md) + [context-management.md](references/context-management.md) |
| Stack globale | confermato una volta nel GDD | [tool-stack.md](references/tool-stack.md) + [doctor.md](references/doctor.md) |

Vietato modellare a mano in `execute_blender_code` (ammesso: wipe, sanitize, `gds_building.py`). Gli hero prop si modellano con uno script deterministico `Tools/<asset>_build.py` lanciato da `blender -b` ([hero-procedural.md](references/hero-procedural.md)): è il percorso di default, approvato dal proprietario il 2026-10-24. Vietato Sloyd. Vietato gen3d fuori tier/budget GDD. Vietato HDRI sui materiali dei prop (ok come skybox). Vietato `--http` TerminalMCP. Blender MCP = `uvx mcp-for-blender` stdio → TCP 9876. Vietato piazzare muri/pavimenti/alberi uno a uno: si scrive la spec.

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
2. `GDD.md` non `locked` → intervista (unica fase in cui parli con l'utente): **Q0 engine (scelta dell'utente, definitiva)**, poi blocchi A-E (un turno per blocco), tante domande, follow-up su ciò che è vago, default consigliati. Recap dichiarato vs inferito, correzioni, lock. Poi **offri** (non imporre) il controllo di mercato `game-launch-strategist` Mirata ([launch-link.md](references/launch-link.md)).
3. Worker **project** (Unity: create/attach + `install-gds-editor.ps1` + `gds_ping`; Nucleon: `ncli exe new-project` o attach + `templates/nucleon` + `ncli ping`/`lint`/`play-test`; Unreal: plugin MCP + `gds_ue.py`; Godot: godot-loop.md).
4. Worker **task-decomposition** → `GAME_TASKS.md`, `GAME_CONTEXT.md` (genre, style), `ASSET-LEDGER.md`, `art/blueprints/PLAN.md`, `art/reference/BOARD.md`, `art/world/<name>.json` se procedurale.
5. Worker **greybox** (ground top Y=0, controller del genere, test movimento verde, lint 0).
6. **Da qui in poi tutto in parallelo per track** (ART / CODE / UI / AUDIO / QUALITY, [workers.md](references/workers.md) "Scheduler a ondate"); i numeri sotto sono le dipendenze dentro ogni track. Worker **kit-fetch** → **world-gen** (se mondo procedurale) → **building-gen** (batch 5, se edifici esterni) → **level-build** (1 blueprint per worker, tutti in parallelo, build in coda sul lock) → **village** (solo insediamenti) → **hero-asset** (batch 3) → **import-art**. Ogni gate con `lint: issues 0`.
7. Worker **lookdev** → **art-review** (media ≥ 4, altrimenti fix list e rilancio, max 2 giri).
8. Worker **characters** (+ NavMesh se nemici) → **systems** (un verbo = script + test) → **feel-baseline** (sim del verbo core nella scena vera).
9. **ui-tokens** → worker **variants** di tutte le schermate in parallelo (real-world-design, 3-4 varianti ciascuna) → **una domanda unica all'utente** con tutte le gallerie → worker **implement** per schermata in parallelo (Unity UXML, Nucleon RML con `html2rml.py`). Il track UI parte subito dopo il project, non aspetta l'art.
10. Worker **baseline-*** (essenziali sempre, opzionali dal blocco E) → **juice** → **art-review** (seconda passata) → **playtest** → **slice** solo se tutti i gate PASS.
11. **Dopo la slice: iterazione** (ondate del focus group o note del proprietario). Worker **design-review** (mappa del gioco, mappa schermate, run a tempi: [design-review.md](references/design-review.md)) → **piano dei gate** `docs/gates/plan-wNN.md` con le sole proposte approvate (un gate = un blocco coerente, in ordine, con le ore: [launch-link.md](references/launch-link.md) §5) → un worker **iterate-gate** per gate → `gate_link.py check` + `apply-status --write` + `todo --run` → review "dopo" e controllo orfani. Prima della prossima ondata: `gate_link.py since --out docs/design-review/changes-since-wNN.md`.

**Ciclo task** ([task-decomposition.md](references/task-decomposition.md)): `Inizio`/`Durata` su ogni riga, `[!]` dopo 2 retry non ferma la catena (si va avanti con i task che non dipendono da lui), **checkpoint ogni 10 task `[x]`** e prima di art-review/playtest/slice: tutti i test + lint + scansione script + `gds_scene_map` + git commit.

**Decisioni:** ogni decisione del proprietario va subito, con data e fonte, in `DECISIONI.md` ([context-management.md](references/context-management.md)); con `launch/` valgono anche `00-intenzioni.md` e "Decisioni prese" di `launch/TODO.md`. Mai riaperte in silenzio: solo proposte etichettate `Riapre la decisione: …` con prove. "Il proprietario ha chiesto X" solo con la fonte.

**Con o senza la skill launch:** `gate_link.py detect` → `linked` / `launch-only` / `solo`. Da sola la skill fa tutto (decisioni da `DECISIONI.md`, lavoro dalle note del proprietario, design review sua); con `launch/` scrive in `launch/` **solo** tramite `gate_link.py` ([launch-link.md](references/launch-link.md) §1-3).

**Sessione: sempre continua.** Il parent incatena i worker fino alla slice senza banner né chat nuove; memoria su disco ([context-management.md](references/context-management.md)). Claude Code: tutti i task pronti con `OWNS` disgiunti in un solo messaggio (`Agent` in background, max `parallel.maxWorkers`), ogni posto liberato si riempie subito. `/resumegame` serve solo dopo un crollo.

## Isolamento (tassativo)

- Claude Code: tool `Agent` con `subagent_type: "general-purpose"` in background, più worker nello stesso messaggio; Kilo/OpenCode: `Task` `general` ([workers.md](references/workers.md)). Prompt = blocco di workers.md + 9 righe + **contratto**: `DECISIONI` (leggi per primo, non riaprire), `OWNS` (file suoi; un file non suo o cambiato = stop e report), `DO / DO NOT`, `PROGRESS` (checkpoint riprendibile), report a formato fisso (diverso dal brief = FAIL). Niente history.
- Worker paralleli non condividono mai file; un solo worker guida l'editor.
- Un solo editor: lavoro fuori dall'editor (JSON, script, test, Blender, mock) in parallelo; ogni comando dell'editor dietro il lock (Unity `scripts/unity-lock.ps1`, Nucleon `ncli lock`).
- Nucleon: i worker usano `ncli.py`, mai lo schema MCP completo nel contesto; screenshot su file, mai base64 in chat.
- Il worker non fa altre fasi. Il parent rilegge solo `docs/gates/*.md` e `docs/lint/*.json`.
- "Ho costruito X" senza spec/blueprint JSON + JSON di build + PNG = FAIL. "Ho usato Blender" senza `screenshots/blender-*.png` e GLB = FAIL. Gate di scena senza `lint: {"issues":0` = FAIL.

## Slice FAIL se manca uno

- Main Menu come prima schermata (Unity scena index 0; Nucleon menu RmlUi mostrato per primo da `game.lua`)
- HUD con obiettivo visibile
- Mondo del GDD costruito (world JSON / blueprint / village) senza primitive visibili (Unity cubi, Nucleon shape: `ncli lint --no-primitives` → 0)
- `Global_Volume` + `LookDev_<preset>.asset` (Nucleon: `lighting`/`environment` del livello + Post Process, shot; Unreal: `gds_ue.lookdev`)
- Art review PASS (media ≥ 4, nessun voto < 3) o voti riportati onestamente all'utente dopo 2 giri
- Personaggio animato (o giustificazione GDD: FP senza corpo)
- `docs/lint/scene-lint.json` con `issues: 0`
- Screenshot Play Mode dove si capisce cosa fare
- Test di ogni verbo eseguiti (output nel gate)
- Baseline essenziale (rimappatura tastiera + pad, dimensione testo, movimento ridotto, transizioni ≤ 0,5 s, hover/focus) e feel `worse: []` contro la baseline

## Hard rules

- Primitive (Unity cubi, Nucleon shape) solo nel greybox (`ncli lint --no-primitives` dopo). Poi ogni cosa visibile = kit / mondo GDS / ProBuilder con palette / GLB.
- Una famiglia di asset per slice (riga di styles.md).
- UI: `real-world-design` sempre, Variant Studio 3-4 opzioni, scelta dell'utente per ogni schermata, coerenza token col Main Menu. UXML a mano come primo passo = FAIL.
- Dopo script o copia GDS: `recompile` → `recompile_status` → `console` 0 errori, poi usa (Nucleon: `.ncbp` → `ncli exe compile-blueprints` 0 failed; `ncli log` 0 errori).
- Niente YAML `.unity`/`.prefab` né `.nclevel` a mano con l'editor aperto (lo riscrive al salvataggio).
- Feel del verbo core: sim nella **geometria vera** del livello, baseline `docs/tests/feel-baseline.json`; peggio della baseline = gate FAIL salvo ok del proprietario ([playtest.md](references/playtest.md)).
- Gli helper di cattura non toccano le regole (timer, punti, spawn): seed o sistemi veri, ogni cattura etichettata, controllo "catture vs regole" prima di playtest/store.
- Mai deliverable in `Temp/` o `Library/` di Unity: si svuotano alla chiusura.
- Scope = slice del GDD.
- Gate di iterazione: fix verificato nella **meccanica vera, in gioco normale, da ogni lato** (non solo il caso del report); foto guardate; salvataggi del proprietario con backup e ripristino identici; **niente build** se non chieste, **niente suite di test** se `DECISIONI.md` dice che prova lui; `risks` = rischi di gameplay introdotti, mai vuoto; scelte cambiate dette chiaro (`decided_by`).
- Dopo ogni redesign di schermate, menu, negozio o flusso: controllo orfani (`design_review.py screens --before`). Nessuna schermata o funzione resta senza ingresso per sbaglio.
- Unity 6000.x (6000.5+ con ProBuilder ≥ 6.1.2, l'installer lo gestisce). Nucleon 0.x da `main` (editor + `Nucleon` della stessa build). Unreal solo 5.8+. Godot 4.3+.
- Engine = risposta Q0 dell'utente: mai cambiato da stile, genere o hardware; un limite noto si dice una volta e decide lui.
