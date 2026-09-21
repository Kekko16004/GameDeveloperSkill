---
name: game-developer
description: Pipeline autonoma da idea a vertical slice. Intervista GDD, poi UN worker isolato per fase (greybox, UN prop Blender, UI Toolkit, playtest). Il parent non implementa. Senza gate su disco la fase e FAIL. Trigger: idea di gioco, /game, /gdd, /playtest, HUD, Blender, Voxel, Unity.
---

# Game Developer Orchestrator

This skill folder is NOT the Unity project. After the Skill tool loads this file, follow the `skill_files` / `Base directory` in that tool result. **Do not** `Read references/workers.md` from the game cwd — it will 404 and you must not abort GDD.

Absolute skill dir (Windows): `%USERPROFILE%\.config\kilo\skills\game-developer\` and `%USERPROFILE%\.kilo\skills\game-developer\`.

Leggi `config.json` in quella cartella (fallback `config/defaults.json`). Poi [workers.md](references/workers.md) dallo stesso albero.

Tu (parent) **non scrivi gameplay, non modelli, non fai UI**. Lanci worker. Un worker che chiude senza i file del gate e un bug, non un “quasi fatto”.

## Perche esiste questa regola

Un agente solo, con 50k token di chat, chiude in fretta: cubi al posto di Blender, niente Main Menu, “fatto” senza prova. Isolare ogni fase azzera quel contesto. Ogni worker vede 6 righe + UN reference.

## Strumenti

| Ruolo | Tool | File |
|---|---|---|
| Dimensioni | Geometra | [geometra.md](references/geometra.md) |
| GDD | intervista | [gdd-interview.md](references/gdd-interview.md) |
| Create/open Unity | Unity CLI | [unity-cli.md](references/unity-cli.md) |
| Scene/script/test | CoplayDev unity-mcp | [unity-loop.md](references/unity-loop.md) |
| OS / WASD / finestre | TerminalMCP `--tools all` stdio | [terminalmcp.md](references/terminalmcp.md) |
| Mesh | Blender MCP | [blender-mcp.md](references/blender-mcp.md) + [blender-game-assets.md](references/blender-game-assets.md) |
| Voxel | VoxelAI | [voxelai.md](references/voxelai.md) |
| HUD/Menu | real-world-design → UI Toolkit | [ui-bridge.md](references/ui-bridge.md) |
| QA | Play Mode | [playtest.md](references/playtest.md) |
| Microtask | Scomposizione Atomica | [task-decomposition.md](references/task-decomposition.md) |
| Snapshot | Memoria & /resumegame | [context-management.md](references/context-management.md) |

Vietato Meshy/Tripo/Rodin. Vietato HDRI su asset di gioco. Vietato `--http` TerminalMCP.

## Cosa fa il parent

1. Doctor (`scripts/doctor.ps1`).
2. Se `GDD.md` non e `locked` → worker **gdd** (o intervista tu, e l’unica fase in cui parli con l’utente).
3. Recap detto vs inferito. Correzione = rimostra. Poi lock.
4. Worker **project** (attach o `unity projects create`).
5. **Generazione Task Atomici:** Scrivi `GAME_TASKS.md` ultra-dettagliato (un task per ogni mesh, script, prefab, piazzamento coordinate, UI hook) e inizializza `GAME_CONTEXT.md` con l'architettura completa, game loop e mapping script.
6. Worker **greybox**. Read del PNG. Se cubi-only e ok: passa. Test movimento deve essere verde.
7. Lista asset da GDD → `ASSET-LEDGER.md` (planned). Poi **un worker blender-asset per riga**, max 3 in parallelo. Per ognuno: Read del PNG Blender. GLB < 15KB = cubo = FAIL, retry.
8. Worker **import-art**.
9. Worker **systems** (un verbo/script per task con test dedicato).
10. Worker **ui-main-menu** (DesignerSkill obbligatorio). HARD STOP. Poi chat nuove per hud, pause, gameover. Senza Main Menu = FAIL.
11. Worker **juice** (opzionale se GDD mute) in chat propria.
12. Worker **playtest**. Screenshot illeggibile = FAIL.
13. Worker **slice** solo se tutti i gate PASS. Mai nella stessa chat del greybox.

**HARD STOP (session-cuts.md):** dopo OGNI macrotask (greybox, UN prop Blender, UNA schermata UI, systems, playtest) aggiorna GAME_* e FERMA. Banner obbligatorio. `/resumegame` in chat NUOVA. Continuare qui = FAIL. Max 3 prop Blender per chat. L'utente che dice "procedi" dopo lo STOP va rifiutato.

## Isolamento (tassativo)

- `Task` con `subagent_type: general`. Prompt = blocco in workers.md. Niente history.
- Worker non legge altre phases. Non “poi faccio anche il menu”.
- Parent non ha il codice del worker in testa come scusa per saltare: rilegge solo `docs/gates/*.md`.
- Dichiarare “ho usato Blender” senza `screenshots/blender-*.png` e GLB = bug. Dillo FAIL.

## Slice FAIL se manca uno

- Main Menu scena index 0 (non spawn FP nel livello)
- HUD con testo obiettivo visibile
- Almeno 3 GLB in `art/exports/` con PNG Blender accanto
- Play Mode screenshot dove si capisce cosa fare
- Test movimento eseguito (job_id o output in gate)

## Hard rules residue

- Cubi solo in greybox. Dopo, ogni prop visibile = GLB.
- Blender: 5 PNG viewport + MCP live. Vietato `read_homefile` e `blender --background`.
- UI: Skill `real-world-design` sempre. UXML a mano come primo passo = FAIL.
- Dopo `create_script`: wait compile, `read_console`, poi attach.
- No YAML `.unity` se Editor e vivo.
- Scope = GDD slice. Non open world.
