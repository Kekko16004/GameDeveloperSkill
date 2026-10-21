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
- Each blueprint that another worker could build in parallel (the scheduler runs up to `parallel.maxWorkers` at once).
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
| Quality baseline (a11y, ui-quality, onboarding, loc, playtest kit, store capture) + feel baseline | 4-7 |
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

## Quality baseline tasks (GDD Block E, [quality-baseline.md](quality-baseline.md))

Planned at decomposition, not bolted on at the end. ESSENTIAL rows always; optional rows only if the GDD says `yes`.

| Task | When | Merge | Evidence |
|---|---|---|---|
| `LOC` string table + `loc_check` + font fallbacks for the GDD languages | right after project setup, **before** the first UI/system text | one task (+1 if CJK/AR: fallback + RTL screen) | `loc_check` JSON 0 errors, 1 PNG per script |
| `A11Y` remap kb+pad + restore defaults, text size, reduced motion (+ optional items) | after the HUD and Pause are chosen | essentials in one task, optionals in a second | tests + PNG of every screen at 150 % |
| `UIQ` fades ≤ 0.5 s skippable + hover/focus on every button + notice queue + shared-number check | after the 4 UI screens | one task | test/check JSON + PNG of hover/focus |
| `ONB` tutorial ≤ 4 steps + first-time hints + progressive disclosure | after systems | one task | PlayMode test of the steps + PNG |
| `FEEL` real-scene feel sims + `docs/tests/feel-baseline.json` | after the core verb works in the real level | one task | gate with JSON |
| `PKIT` telemetry CSV + fresh-profile variant + `TESTER_README.md` | before the first build for testers | one task | CSV sample + README + variant save path |
| `CAP` store-capture tool | before store/focus-group screenshots | one task | `captures/<date>/manifest.json` |

Every later task that adds text uses string keys; every task that touches physics/controller/level runs the feel suite (gates.md §12).

## Owner decisions and focus-group waves

- **`DECISIONI.md`**: before writing tasks, read it (and, if present, `launch/00-intenzioni.md` + "Decisioni prese" in `launch/TODO.md`). No task may reopen a settled decision; a task that contradicts one is dropped, not "proposed".
- **Waves → gates → tasks** ([launch-link.md](launch-link.md) §5): when `launch/fg/waves/*-sintesi.md` or `launch/issue_status.json` exist, the parent writes `docs/gates/plan-wNN.md` ([templates/gate-plan.md](../templates/gate-plan.md)) with only the **approved** proposals (§5.2: `in_lavorazione`, `ok del proprietario <date>` in the TODO, `00-intenzioni.md`, or said in chat → `DECISIONI.md`). One gate = one coherent batch (same screens or system, testable in one play session, usually 3-15 h), ordered (regressions from earlier gates first, then impact per hour, then dependencies), with hours. Then one task per gate item with `fg:wNN key:<key>[,<key>] gate:NN` in `Note`, phase `iterate-gate` ([workers.md](workers.md)), preceded by a `design-review` task when the review is older than the last gate.
- **Gate closed** (PASS): the parent runs `gate_link.py check`, `apply-status --write` (→ `risolto` / `da_verificare` in `issue_status.json`) and `todo --run` (→ `todo_track.py done`). Never edit `launch/` by hand beyond that ([launch-link.md](launch-link.md) §3).
- **Owner notes without a wave** (he played and lists problems): same flow, the plan source is his list; `closes:` only for keys that exist, otherwise `nessuno: note del proprietario`.

## User-provided assets

`asset-strategy: user-provided | hybrid` → `art/ASSET_MANIFEST.md` (file name, folder `art/exports/`, size in metres, pivot at base, `.glb`/`.fbx`) and ONE row per asset: `[WAIT-USER-ASSET] prop_x.glb → validate + import + rebuild blueprints that use it`. On `/resumegame` "ho messo i modelli": check the file (> 5 KB), mark `[x]`, `asset_ready: true`, rebuild.

## Lifecycle (il parent, per ogni task)

1. **Scegli:** TUTTI i `[ ]` con `Dipende` tutti `[x]` e `OWNS` disgiunti → un'ondata in parallelo (max `parallel.maxWorkers`, regola del lock e scheduler in [workers.md](workers.md)); a ogni chiusura il posto libero va al prossimo pronto.
2. **Avvio:** `[/]` + `Inizio` = ora (`HH:MM`).
3. **Chiusura:** gate verificato su disco → `[x]` + evidenza; oppure, dopo 2 retry con l'errore preciso, `[!]` + motivo in `Note`. `Durata` = minuti dall'Inizio (retry inclusi). Aggiorna i contatori, `Tempo totale` e il puntatore in `GAME_CONTEXT.md`.
4. **`[!]` non ferma la catena:** si salta e si continua con i task che non lo citano in `Dipende`. Si ferma tutto solo se nessun task è più eseguibile. I `[!]` si elencano all'utente alla fine (o al prossimo checkpoint), con il motivo.
5. **`[/]` trovato all'avvio** (`/resumegame`, sessione crollata, rate limit): controlla il gate su disco. Gate PASS → `[x]`; gate mancante o FAIL → rilancia lo stesso worker con `RIPRENDI da PROGRESS` se `docs/progress/<PHASE>-<TASK>.md` esiste (riparte dal "Prossimo passo"), altrimenti di nuovo `[ ]` (e via il lock `Temp/gds-unity.lock` se lo teneva quel task).
6. **Decisione del proprietario** detta durante il lavoro: il parent la aggiunge subito a `DECISIONI.md` (ID, data, area, fonte) prima di lanciare il worker successivo.

## Checkpoint ogni 10 task `[x]`

Le run lunghe si rompono così: un sistema nuovo rompe un verbo vecchio, oppure un worker con poco contesto lascia uno script a metà. Ogni 10 task chiusi (e sempre prima di art-review, playtest e slice) il parent lancia un worker **checkpoint** (prende il lock Unity):

1. `unity command recompile` → `console` 0 errori (Nucleon: `ncli exe compile-blueprints` se ci sono `.ncbp`, `ncli log` 0 errori).
2. **Test incrementali, suite intera ai punti fermi.** Al checkpoint ogni 10 task: solo i test toccati dai file cambiati dall'ultimo checkpoint (Nucleon `ncli affected` → `NC_GDS_TEST=<lista>` + `--expect` già pronto; un file "core" cambiato — input, progetto, pawn, livello, `game.lua` — fa girare tutto; ogni `test_<verbo>.lua` dichiara `-- covers: <glob>`; Unity: le categorie dei test degli asmdef toccati). **Prima di art-review, playtest e slice: sempre la suite intera** (`run_tests` / `NC_GDS_TEST=1` + `ncli play-test --expect "GDS-TEST DONE pass=<tutti> fail=0"`). Nucleon in più, a ogni checkpoint: `ncli lua-check --strict` (chiamate sconosciute, argomenti delle native, sintassi) prima di qualsiasi Play.
3. `gds_lint` su ogni scena di gioco → `issues: 0`. Se esiste `docs/tests/feel-baseline.json`: suite di feel nella scena vera → `worse: []` (playtest.md).
4. Scansione degli script `Assets/_Game/Scripts/`: `TODO`, `NotImplementedException`, metodi vuoti in classi registrate in `GAME_CONTEXT.md`, script del registro non più su disco. Ognuno diventa un task di fix o viene giustificato nel report.
5. `unity command gds_scene_map` → `docs/scene-map.md` aggiornata (Nucleon: `ncli call scene_list` → stessa tabella).
6. **Solo prima di art-review / playtest / slice:** confronto con il GDD (verbi, win/fail, schermate UI, stile, mondo) → differenze in `docs/gates/drift-<n>.md`. Ogni differenza non voluta = task di fix.
7. Tutto verde → `git add -A && git commit -m "checkpoint TASK-<ultimo>: <n> task, tests <passati>/<totali>, lint 0"`. Rosso → task di fix prima di qualsiasi altro task (stessa fase del colpevole), poi si rifà il checkpoint.

Report in `docs/gates/checkpoint-<n>.md` (JSON e conteggi, niente prosa). Se qualcosa si rompe dopo, `git diff` contro l'ultimo checkpoint mostra cosa è cambiato; nel caso peggiore `git restore` riporta gli asset a uno stato buono (prima chiedere all'utente).

## Speed

- Task liberi sempre in parallelo (scheduler a ondate, fino a `parallel.maxWorkers`): blueprint, batch hero, mock UI, script e test mentre l'editor costruisce. Il lavoro fuori dall'editor (JSON, script, Blender, mock) va in parallelo, i comandi dell'editor passano dal lock.
- **Colonna `Dipende` stretta**: un task dipende solo da ciò che usa davvero (un blueprint dal kit-catalog, non dal blueprint precedente; un sistema dal greybox, non dall'art). Ogni dipendenza inutile serializza la run.
- **Colonna `Editor`** (`sì`/`no`): i task `no` non aspettano mai il lock; il parent li lancia anche mentre un altro worker tiene l'editor.
- Un worker può chiudere **task consecutivi della stessa fase** in un solo giro (es. 3 blueprint dello stesso kit) se ognuno scrive la propria riga di gate.
- Le chiamate deterministiche restituiscono JSON: incolla il JSON nel gate, non descriverlo di nuovo.
- La colonna `Durata` serve: dopo un paio di run mostra dove si perde tempo (retry di lookdev, compile lunghi). Un task che dura più del triplo della mediana della sua fase va annotato in `Note` con la causa.
