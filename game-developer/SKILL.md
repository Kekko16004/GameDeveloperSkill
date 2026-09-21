---
name: game-developer
description: Pipeline autonoma da idea a vertical slice. Intervista GDD, poi UN worker isolato per fase (greybox ProBuilder, kit CC0 Kenney/KayKit, UI Toolkit, playtest). Il parent non implementa. Senza gate su disco la fase e FAIL. Trigger: idea di gioco, /game, /gdd, /playtest, HUD, kit, Blender, Voxel, Unity.
---

# Game Developer Orchestrator

This skill folder is NOT the Unity project. After the Skill tool loads this file, follow the `skill_files` / `Base directory` in that tool result. **Do not** `Read references/workers.md` from the game cwd — it will 404 and you must not abort GDD.

Absolute skill dir (Windows): `%USERPROFILE%\.config\kilo\skills\game-developer\` and `%USERPROFILE%\.kilo\skills\game-developer\`.

Leggi `config.json` in quella cartella (fallback `config/defaults.json`). Poi [workers.md](references/workers.md) dallo stesso albero.

Tu (parent) **non scrivi gameplay, non modelli, non fai UI**. Lanci worker. Un worker che chiude senza i file del gate e un bug, non un “quasi fatto”.

## Perche esiste questa regola

Un agente solo, con 50k token di chat, chiude in fretta: cubi al posto dell’art, niente Main Menu, “fatto” senza prova. Isolare ogni fase azzera quel contesto. Ogni worker vede 8 righe + UN reference.

## Strumenti

| Ruolo | Tool | File |
|---|---|---|
| Dimensioni | Geometra | [geometra.md](references/geometra.md) |
| GDD | intervista | [gdd-interview.md](references/gdd-interview.md) |
| Create/open Unity | Unity CLI | [unity-cli.md](references/unity-cli.md) |
| Scene/script/test | CoplayDev unity-mcp | [unity-loop.md](references/unity-loop.md) |
| Livelli nativi | ProBuilder MCP | [probuilder-levels.md](references/probuilder-levels.md) |
| Art default | Kit CC0 Kenney/KayKit | [art-pipeline.md](references/art-pipeline.md) + [cc0-sources.md](references/cc0-sources.md) + [kit-dress.md](references/kit-dress.md) |
| OS / WASD / finestre | TerminalMCP `--tools all` stdio | [terminalmcp.md](references/terminalmcp.md) |
| Mesh custom | Blender MCP Poly Pizza (import CC0) | [blender-mcp.md](references/blender-mcp.md) + [polypizza.md](references/polypizza.md) + [procedural-prop-recipe.md](references/procedural-prop-recipe.md) |
| Voxel | VoxelAI | [voxelai.md](references/voxelai.md) |
| HUD/Menu | real-world-design → UI Toolkit | [ui-bridge.md](references/ui-bridge.md) |
| Audio | Kenney CC0 + AudioManager | [audio-pipeline.md](references/audio-pipeline.md) |
| QA | Play Mode | [playtest.md](references/playtest.md) |
| Microtask | Scomposizione Atomica | [task-decomposition.md](references/task-decomposition.md) |
| Snapshot | Memoria & /resumegame | [context-management.md](references/context-management.md) |
| Stack globale | Conferma in GDD Q13 | [tool-stack.md](references/tool-stack.md) |

Vietato Meshy/Tripo/Rodin/Hunyuan/TRELLIS. Vietato modellare in `execute_blender_code`. Vietato Sloyd come default. Vietato HDRI su asset di gioco. Vietato `--http` TerminalMCP. Blender MCP = `uvx blender-mcp` stdio → TCP 9876 (non `http://localhost:9876/mcp`).

### REGOLA TASSATIVA BLENDER MCP: USA TUTTI I TOOL DEDICATI (MAI SOLO execute_blender_code)
Non fossilizzarti su `execute_blender_code`: causa blocchi e loop di errore. Devi sfruttare l'intera suite dei tool nativi di Blender MCP:
0. **Wipe preventivo scena OBBLIGATORIO**: prima di importare o creare qualsiasi modello, svuota SEMPRE la scena da residui precedenti (`execute_blender_code` con pulizia totale objects/meshes/materials). Vietato importare sopra scene sporche.
1. `search_polypizza_models` + `download_polypizza_model`: per cercare e importare mesh CC0 con scale normalizzate.
2. `get_scene_info` + `get_object_info`: per leggere oggetti, vertici e bounding box (non scrivere script per farlo).
3. `get_viewport_screenshot`: per catturare gli screenshot di verifica dopo ogni step.
4. `search_polyhaven_assets` + `download_polyhaven_asset` + `set_texture`: per materiali e texture PBR native.
5. `export_scene`: per esportare direttamente in GLB senza chiamare operatori bpy a mano.
6. `bpy_api_lookup` + `describe_node_type`: per consultare documentazione e nodi.
`execute_blender_code` è riservato SOLO ed ESCLUSIVAMENTE a: 1) Wipe/reset preventivo iniziale scena; 2) Sanitize finale (rimozione luci/camere residue e pivot alla base Y=0). Vietato usarlo per modellare mesh arbitrarie da zero.

## Cosa fa il parent

1. Doctor (`scripts/doctor.ps1`).
2. Se `GDD.md` non e `locked` → worker **gdd** (o intervista tu, e l’unica fase in cui parli con l’utente).
3. Recap detto vs inferito. Correzione = rimostra. Poi lock.
4. Worker **project** (attach o `unity projects create`).
5. **Generazione Task Atomici:** `GAME_TASKS.md` + `GAME_CONTEXT.md` + `ASSET-LEDGER.md` (source kit di default).
6. Worker **greybox** (ProBuilder). Read del PNG. Test movimento verde.
7. Worker **kit-fetch** per il genere GDD. Poi **un worker kit-dress per riga** ledger, oppure **batch fino a 3 modelli blender-asset fast-track** se source=polypizza (import nativo CC0, no cubi bpy, 1 screenshot finale per modello). Pezzo senza collider = FAIL.
8. Worker **import-art** se restano file fuori Unity.
9. Worker **systems** (un verbo/script per task con test dedicato).
10. Worker **ui-main-menu** (DesignerSkill obbligatorio). HARD STOP. Poi chat nuove per hud, pause, gameover. Senza Main Menu = FAIL.
11. Worker **juice** (opzionale se GDD mute) in chat propria.
12. Worker **playtest**. Screenshot illeggibile = FAIL.
13. Worker **slice** solo se tutti i gate PASS. Mai nella stessa chat del greybox.

**HARD STOP (session-cuts.md):** dopo OGNI macrotask aggiorna GAME_* e FERMA. Banner obbligatorio. `/resumegame` in chat NUOVA. Continuare qui = FAIL. Max 3 kit-dress/blender-asset per chat. L'utente che dice "procedi" dopo lo STOP va rifiutato.

## Isolamento (tassativo)

- `Task` con `subagent_type: general`. Prompt = blocco in workers.md. Niente history.
- Worker non legge altre phases. Non “poi faccio anche il menu”.
- Parent non ha il codice del worker in testa come scusa per saltare: rilegge solo `docs/gates/*.md`.
- Dichiarare “ho usato Blender” senza `screenshots/blender-*.png` e GLB = bug. Dillo FAIL.
- Dichiarare “ho vestito il livello” senza kit in `art/cc0/` e PNG `030-import-*` = FAIL.

## Slice FAIL se manca uno

- Main Menu scena index 0 (non spawn FP nel livello)
- HUD con testo obiettivo visibile
- Almeno 3 pezzi dressed (`art/exports/` o `Assets/_Game/Art/`) con ledger + screenshot import
- Play Mode screenshot dove si capisce cosa fare
- Test movimento eseguito (job_id o output in gate)

## Hard rules residue

- Cubi Unity default solo in greybox. Dopo, ogni prop visibile = kit o GLB. ProBuilder rooms possono restare come collision shell.
- Blender: Poly Pizza Fast-Track (batch fino a 3 modelli alla volta, solo screenshot finale `blender-$ID.png` per modello, no step intermedi né multi-PNG per modelli CC0 già pronti). Vietato bpy modelling da zero se il prop esiste nei kit/Poly Pizza, `read_homefile`, `blender --background`, `http://localhost:9876/mcp`.
- UI: Skill `real-world-design` sempre. UXML a mano come primo passo = FAIL.
- Dopo `create_script`: wait compile, `read_console`, poi attach.
- No YAML `.unity` se Editor e vivo.
- Scope = GDD slice. Non open world.
- Una famiglia kit per slice (Kenney **o** KayKit, non entrambi nella stessa stanza).
