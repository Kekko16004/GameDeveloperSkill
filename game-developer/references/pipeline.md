# Pipeline

Parent = dispatcher. Implementazione = worker. Dettaglio prompt: [workers.md](workers.md).
Art routing: [art-pipeline.md](art-pipeline.md).

```
0 doctor                         parent
1-3 GDD interview + LOCK         parent parla; oppure worker gdd
4 project attach|create          worker project
5 task-decomposition             worker task-decomposition (GAME_TASKS.md + GAME_CONTEXT.md)
6 greybox + movement test        worker greybox  (ProBuilder rooms OK)
7a fetch CC0 kits                worker kit-fetch (genre from GDD)
7b kit-dress x N pieces          worker per file (parallelo max 3)  ← default art
7c blender-asset                 SOLO source=polypizza (import MCP fast-track batch max 3, no bpy cubes)
7d import-art                    se restano GLB fuori Unity
7e level dressing                coordinate da GAME_TASKS
8 systems + test per verbo       worker systems
9a Main Menu UI Toolkit          worker ui-main-menu   <-- obbligatorio
9b HUD                           worker ui-hud
9c Pause                         worker ui-pause
9d GameOver                      worker ui-gameover
10 juice                         worker juice
11 playtest                      worker playtest
12 slice recap                   worker slice  (FAIL se un gate e rosso)
```

HARD STOP dopo ogni riga della pipeline (vedi session-cuts.md). Una macrotask per chat. `/resumegame` per la successiva.
`GDD.md` campo `phase:` aggiornato dal parent dopo ogni gate PASS.

## File gate

Ogni worker scrive `docs/gates/NN-name.md`:

```
phase: greybox
status: PASS|FAIL
evidence:
  - screenshots/010-greybox-play.png
  - run_tests job_id=...
notes: ...
```

Senza questo file la fase non e fatta. Chat “fatto” non conta.

## Anti-pigrizia

| Sintomo | Azione parent |
|---|---|
| Worker apre Blender per un crate Kenney | scarta. Rilancia kit-dress |
| Worker usa Sloyd/Meshy/Hunyuan o bpy cubi | FAIL |
| Worker punta blender a http://localhost:9876/mcp | FAIL. Serve uvx stdio |
| Mix Kenney + KayKit nella stessa stanza | FAIL. Una famiglia |
| GLB < 15KB su riga blender | retry. E un cubo |
| Kit piece senza collider / screenshot | retry kit-dress |
| UI senza mock HTML real-world-design | retry ui. UXML a mano = FAIL |
| Gioco parte in FP senza menu | retry ui-main-menu. Slice bloccata |
| Screenshot illeggibile | retry hud + playtest |
| Worker ha fatto 3 fasi in un turno | scarta il lavoro extra |
| Contesto parent enorme | non implementare tu. Lancia il prossimo worker |

## Greybox vs art

Greybox = ProBuilder / cubi OK, deve **giocarsi**. Art = kit-dress sostituisce i cubi visibili. Non dichiarare slice se i cubi Unity primitivi sono ancora l’unica mesh visibile (ProBuilder rooms + kit walls = OK).
