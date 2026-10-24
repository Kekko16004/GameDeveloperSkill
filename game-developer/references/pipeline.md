# Pipeline

Parent = dispatcher. Implementazione = worker. Dettaglio prompt: [workers.md](workers.md).
Art routing: [art-pipeline.md](art-pipeline.md). Layer deterministico: [gds-editor.md](gds-editor.md).

```
0  doctor                          parent
1-3 GDD interview (blocchi A-E, domande adattive) + LOCK   parent parla; oppure worker gdd
3m controllo di mercato precoce     OFFERTO (game-launch-strategist Mirata, launch-link.md), non imposto
    engine = scelta dell'utente (Q0): stesse fasi su unity / nucleon / unreal / godot, verbi dell'adapter (engines.md)
4  project attach|create + layer deterministico dell'engine (GDS / ncli + templates/nucleon / gds_ue)   worker project
5  task-decomposition               worker task-decomposition (GAME_TASKS + GAME_CONTEXT + ASSET-LEDGER + lista blueprint)
6  greybox + movement test          worker greybox  (GDS.PB.Room / primitives blueprint; ground top = Y 0)
7a kit-fetch + kit-catalog          worker kit-fetch (fetch-cc0-kits.ps1 + gds_catalog → art/kit-catalog.json)
7w world-gen (se mondo procedurale) worker world-gen (gds_world: terrain / island / dungeon / cave / voxel → spawn, scatter, layout)
7b building-gen (Blender procedurale, batch max 5 spec)  worker building-gen  ← case/locande/torri-casa VERE: gds-building.ps1 → FBX + preview
7c level-build (1 blueprint = 1 worker) worker level-build  ← kit L/T/U + interni + attach + recinzioni, o shell ProBuilder per interni/dungeon
7d village (SOLO insediamento — environments.md)   worker village (GDS.Village: terreno, strade, piazza, lotti con edifici 7b/7c, lampioni, bosco). Caverna/dungeon/interno/citta/sci-fi: il mondo e fatto da 7c, non da village
7e hero-asset (script procedurale `blender -b`; organico: Poly Pizza / Poly Haven / Sketchfab / gen3d tier)   worker hero-asset (batch max 3, sanitize, export, poi riga props nel blueprint)
7f import-art                       se restano GLB fuori Unity
8  lookdev                          worker lookdev (gds_lookdev preset GDD + palette + toon/outline opzionali)
8r art-review                       worker art-review (gds_sheet + rubric R1-R7, media ≥ 4, fix list → rilancio fasi)
9  characters (+ navmesh se nemici) worker characters (GDS.Characters + skill initialize-ai-navigation)
10 systems + test per verbo         worker systems
10f feel-baseline                   worker feel-baseline (sim del verbo core nella scena VERA → docs/tests/feel-baseline.json)
11a Main Menu UI Toolkit            worker ui-main-menu   <-- obbligatorio (Variant Studio: 3-4 varianti → scelta utente → UXML)
11b HUD / 11c Pause / 11d GameOver   worker ui-hud / ui-pause / ui-gameover (Variant Studio: 3-4 varianti coerenti col menu → scelta utente ciascuna)
11e baseline-* (a11y, ui-quality, onboarding, loc, playtest-kit, store-capture)   worker baseline-<item> (quality-baseline.md)
12 juice (VFX + audio + hit-stop)   worker juice (gds_vfx + audio-pipeline)
12r art-review                      worker art-review (seconda passata, con VFX e UI)
13 playtest                         worker playtest (SceneLint 0 + Play Mode + WASD + screenshot)
14 slice recap                      worker slice  (FAIL se un gate e rosso)

--- dopo la slice: iterazione (ondate del focus group o note del proprietario) ---
15 design-review                    worker design-review (mappa del gioco + mappa schermate + run a tempi, sola lettura)
16 piano dei gate                   parent: docs/gates/plan-wNN.md solo con le proposte approvate (launch-link.md §5)
17 iterate-gate (uno per gate)      worker iterate-gate → gate con header → gate_link.py check / apply-status / todo
18 design-review "dopo"             run toccate con --before; controllo orfani dopo un redesign; poi il prossimo gate
```

**Sempre continua e parallela.** I numeri sopra sono l'ordine delle dipendenze, non una coda: dopo il greybox i track ART / CODE / UI / AUDIO / QUALITY girano insieme con lo scheduler a ondate ([workers.md](workers.md) "Scheduler"); l'editor ha un solo driver alla volta (lock). L'utente viene interpellato solo per le scelte UI (una domanda unica per tutte le schermate) e per ciò che il GDD lascia aperto.
`GDD.md` campo `phase:` aggiornato dal parent dopo ogni gate PASS.

## Memoria su disco (per host che perdono contesto)

Ogni fase legge/scrive solo file piccoli e strutturati, mai la chat:

| File | Chi lo scrive | Chi lo legge |
|---|---|---|
| `GDD.md` (risposte lockate, engine Q0 compreso) | gdd | tutti |
| `GAME_CONTEXT.md` / `GAME_TASKS.md` | task-decomposition, poi ogni worker | tutti, `/resumegame` |
| `ASSET-LEDGER.md` | task-decomposition, hero-asset | level-build, slice |
| `art/kit-catalog.json` | kit-fetch | level-build |
| `art/specs/*.json` | building-gen (uno per edificio Blender) | building-gen (rebuild), village |
| `art/world/*.json` (+ `*.layout.json`) | task-decomposition, world-gen | world-gen (rebuild), systems (spawn), playtest |
| `art/reference/BOARD.md` | task-decomposition | art-review |
| `art/blueprints/*.json` | level-build (uno per edificio/area), village (`village_*.json`) | level-build / village (rebuild), playtest |
| `docs/lint/scene-lint.json`, `docs/lint/build-*.json` | GDS scripts | parent (gate) |
| `docs/gates/NN-*.md` | ogni worker | parent, slice |
| `DECISIONI.md` | parent (ogni decisione del proprietario, con data) | **tutti, per primo** |
| `docs/progress/<PHASE>-<TASK>.md` | il worker, dopo ogni passo | lo stesso worker quando riparte |
| `docs/tests/feel-baseline.json` | feel-baseline | ogni gate che tocca il verbo core, playtest |
| `launch/**` (ondate, sintesi, proposte, `TODO.md`, `00-intenzioni.md`) | game-launch-strategist | parent (piano dei gate, [launch-link.md](launch-link.md) §5) |
| `launch/issue_status.json` | game-launch-strategist; dal parent **solo** con `gate_link.py apply-status` | parent, worker iterate-gate (sola lettura) |
| `docs/design-review/*.md` (mappa, schermate, run, `changes-since-wNN.md`) | design-review; `gate_link.py since` | parent, iterate-gate, game-launch-strategist (stato attuale) |
| `docs/gates/plan-wNN.md` | parent | iterate-gate, game-launch-strategist |

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
| Report vago o diverso dal brief, file fuori OWNS | FAIL, rilancio con la differenza (workers.md § Contratto) |
| Worker ripropone una cosa già in `DECISIONI.md` | togli la parte, ricorda la riga D-NNN nel prompt del rilancio |
| Worker attribuisce al proprietario una scelta non nel brief | correggi in `decided_by: implementer`, dillo al proprietario così com'è |
| Fix provato solo nel caso del report (es. colpo di fronte, non di lato) | rilancio: meccanica vera nel gioco normale, tutte le direzioni |
| Redesign che lascia una schermata/funzione senza ingresso | `design_review.py screens --before`, ricollega o ritira apposta |
| Gate senza `risks` | FAIL: la prossima ondata non sa cosa ricontrollare |
| Sim di feel verde in scena vuota | non vale: suite nella scena vera contro la baseline |
| Cattura con stato finto (timer fermo, punti aggiunti) | rifai con seed/sistemi veri, etichetta `produced:` |
| Deliverable in `Temp/` o `Library/` | sposta in `captures/` / `docs/` prima di chiudere il gate |
| Contesto parent enorme | non implementare tu. Lancia il prossimo worker |

## Greybox vs art

Greybox = `GDS.PB.Room` / blueprint primitives, deve **giocarsi**. Art = level-build sostituisce i primitives con blueprint `mode: kit` (stesso `name` → rebuild in place). Non dichiarare slice se restano primitives visibili (ProBuilder shell + kit = OK).
