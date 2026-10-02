# Task decomposition — atomic by *deliverable*, not by click

Macro tasks ("make the village") make an agent stop early. Micro tasks ("place wall 17") burn tokens: 110+ rows, each with its own context load, prompt and gate. The rule is in between:

**One task = one verifiable deliverable = usually one deterministic call or one script+test.** Target **60-80 tasks** for a vertical slice (hard cap 90). Never a task without evidence on disk.

## Merge rules (what goes in ONE task)

| Merge into one task | Because |
|---|---|
| A whole building / room / area | one blueprint JSON → one `gds_build` → one lint |
| The whole procedural world (terrain + layers + scatter + water + spawn) | one `gds_world` call |
| Import + materials + collider + prefab of the same asset | the builder/import does all of it in one pass |
| Up to 3 hero props from the same source | hero-asset batch |
| Up to 5 Blender building specs | building-gen batch |
| A verb's script + its test + its prompt hook (`DoorInteractable` + `Interact_OpensDoor` + `[E] Apri`) | same worker, same compile, same test run |
| Small related settings (tags/layers + input actions + quality) | one project-setup task |
| Palette + lookdev preset + torches | one lookdev task |
| All SFX wiring for one system (door open/close/locked) | one audio task |

## Keep separate (never merge)

- Different gates: greybox ≠ world ≠ blueprint ≠ lookdev ≠ UI screen ≠ playtest.
- Each UI screen (the user picks a variant per screen).
- Each blueprint that another worker could build in parallel (max 3 at once).
- Anything with a `[WAIT-USER-ASSET]` or user choice.
- Each art-review pass.

## Typical slice budget (≈ 70)

| Block | Tasks |
|---|---|
| Setup (project, packages, GDS, input, scenes) | 4-5 |
| Reference board + world spec + PLAN | 2-3 |
| Greybox + movement test | 3 |
| Kit fetch + catalog | 2 |
| World-gen (1) + building-gen batches (1-2) | 2-4 |
| Blueprints (buildings/rooms/areas) | 6-12 |
| Hero props (batches of 3) | 2-4 |
| Lookdev + art review ×2 + fixes | 4-6 |
| Characters (player, 1-2 enemy types) + NavMesh | 3-4 |
| Systems (one verb/system = script + test + hook) | 10-15 |
| UI (4 screens + inventory/dialogue if any) | 4-6 |
| Audio + VFX + juice | 5-7 |
| Playtest + fixes + slice recap | 4-6 |

If the count goes above 90: merge by the table above. Below 50 for a normal slice: something macro slipped in — split it by deliverable.

## Row format (`GAME_TASKS.md`)

Colonne: `ID | Fase | Descrizione | Spec / File | Evidenza | Dipende | Stato | Inizio | Durata | Note`.

```
| TASK-021 | BP | BP-house_a — 3x2 cells, 1 floor, door S1, window N0, kit roof, interior table+2 chairs+chest, origin (0,0,12) | art/blueprints/house_a.json | build JSON + lint 0 + PNG | 009 | [x] | 14:05 | 12 | kenney |
| TASK-034 | SYS | Interact: IInteractable + DoorInteractable (slerp) + raycast in PlayerController + HUD prompt [E] + test Interact_OpensDoor | Scripts/Interaction/* | test green + console 0 | 012 | [/] | 14:20 | | |
| TASK-040 | WORLD | Overworld terrain 400 m, seed 42, flat village spot (0,0,35), pines/oaks/rocks scatter | art/world/overworld.json | world JSON PASS + lint 0 + sheet | 009, 012 | [ ] | | | |
```

`Dipende` elenca solo le dipendenze vere (stesso asset, stessa scena, stesso script), così un `[!]` blocca il minimo indispensabile.

The description carries every number the worker needs (sizes, origins, counts, names from the catalog), so the worker never re-reads the GDD for it.

## User-provided assets

`asset-strategy: user-provided | hybrid` → `art/ASSET_MANIFEST.md` (file name, folder `art/exports/`, size in metres, pivot at base, `.glb`/`.fbx`) and ONE row per asset: `[WAIT-USER-ASSET] prop_x.glb → validate + import + rebuild blueprints that use it`. On `/resumegame` "ho messo i modelli": check the file (> 5 KB), mark `[x]`, `asset_ready: true`, rebuild.

## Lifecycle (il parent, per ogni task)

1. **Scegli:** primo `[ ]` con `Dipende` tutti `[x]` (più task liberi della stessa fase → in parallelo, max 3, regola del lock in [workers.md](workers.md)).
2. **Avvio:** `[/]` + `Inizio` = ora (`HH:MM`).
3. **Chiusura:** gate verificato su disco → `[x]` + evidenza; oppure, dopo 2 retry con l'errore preciso, `[!]` + motivo in `Note`. `Durata` = minuti dall'Inizio (retry inclusi). Aggiorna i contatori, `Tempo totale` e il puntatore in `GAME_CONTEXT.md`.
4. **`[!]` non ferma la catena:** si salta e si continua con i task che non lo citano in `Dipende`. Si ferma tutto solo se nessun task è più eseguibile. I `[!]` si elencano all'utente alla fine (o al prossimo checkpoint), con il motivo.
5. **`[/]` trovato all'avvio** (`/resumegame`, sessione crollata): controlla il gate su disco. Gate PASS → `[x]`; gate mancante o FAIL → di nuovo `[ ]` (e via il lock `Temp/gds-unity.lock` se lo teneva quel task).

## Checkpoint ogni 10 task `[x]`

Le run lunghe si rompono così: un sistema nuovo rompe un verbo vecchio, oppure un worker con poco contesto lascia uno script a metà. Ogni 10 task chiusi (e sempre prima di art-review, playtest e slice) il parent lancia un worker **checkpoint** (prende il lock Unity):

1. `unity command recompile` → `console` 0 errori.
2. **Tutti** i test (`run_tests`), non solo quelli dell'ultimo task.
3. `gds_lint` su ogni scena di gioco → `issues: 0`.
4. Scansione degli script `Assets/_Game/Scripts/`: `TODO`, `NotImplementedException`, metodi vuoti in classi registrate in `GAME_CONTEXT.md`, script del registro non più su disco. Ognuno diventa un task di fix o viene giustificato nel report.
5. `unity command gds_scene_map` → `docs/scene-map.md` aggiornata.
6. **Solo prima di art-review / playtest / slice:** confronto con il GDD (verbi, win/fail, schermate UI, stile, mondo) → differenze in `docs/gates/drift-<n>.md`. Ogni differenza non voluta = task di fix.
7. Tutto verde → `git add -A && git commit -m "checkpoint TASK-<ultimo>: <n> task, tests <passati>/<totali>, lint 0"`. Rosso → task di fix prima di qualsiasi altro task (stessa fase del colpevole), poi si rifà il checkpoint.

Report in `docs/gates/checkpoint-<n>.md` (JSON e conteggi, niente prosa). Se qualcosa si rompe dopo, `git diff` contro l'ultimo checkpoint mostra cosa è cambiato; nel caso peggiore `git restore` riporta gli asset a uno stato buono (prima chiedere all'utente).

## Speed

- Task liberi in parallelo (max 3 worker): blueprint, batch hero, mock UI mentre i sistemi compilano. Il lavoro fuori da Unity (JSON, script, Blender, mock) va in parallelo, i comandi Unity passano dal lock.
- Un worker può chiudere **task consecutivi della stessa fase** in un solo giro (es. 3 blueprint dello stesso kit) se ognuno scrive la propria riga di gate.
- Le chiamate deterministiche restituiscono JSON: incolla il JSON nel gate, non descriverlo di nuovo.
- La colonna `Durata` serve: dopo un paio di run mostra dove si perde tempo (retry di lookdev, compile lunghi). Un task che dura più del triplo della mediana della sua fase va annotato in `Note` con la causa.
