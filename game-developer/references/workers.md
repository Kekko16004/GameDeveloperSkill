# Workers — un job, un cervello, zero pigrizia

Il parent **non implementa**. Lancia un subagent isolato per ogni task/fase. Ogni worker riceve SOLO il blocco PHASE sotto più le 9 righe di contesto e il **contratto** (DECISIONI, OWNS, DO / DO NOT, PROGRESS, REPORT, più le regole 7-9 su scelte di design, decisioni e salvataggi). Niente transcript precedente, niente "poi faccio anche la UI".

| Host | Come si lancia un worker |
|---|---|
| Claude Code | tool `Agent`, `subagent_type: "general-purpose"`, **in background** (default): tutti i worker di un'ondata nello stesso messaggio, il parent viene svegliato a ogni chiusura |
| Kilo Code / OpenCode / Codex | tool `Task` (`general`) o l'equivalente subagent del client, più chiamate nello stesso messaggio |
| Host senza subagent | stesso flusso, il parent esegue un worker alla volta in sequenza con lo stesso contratto e la memoria su disco: mai fermarsi a chiedere una chat nuova |

Il layer deterministico ([gds-editor.md](gds-editor.md)) fa il lavoro di precisione: il worker scrive JSON e chiama `unity command gds_*` ([unity-cli.md](unity-cli.md); fallback `eval` / CoplayDev `execute_code`), non piazza pezzi a mano. Ogni gate che tocca la scena cita `lint: {"issues":0,...}` da `gds_lint`. Altri engine → stessi worker, stessi gate, verbi dell'adapter di [engines.md](engines.md): Nucleon [nucleon-loop.md](nucleon-loop.md) (`ncli.py`), Unreal [unreal-loop.md](unreal-loop.md), Godot [godot-loop.md](godot-loop.md).

## Contesto minimo (le uniche 9 righe per ogni worker)

```
PROJECT=<abs path Unity/Unreal>
GDD=<abs path GDD.md>
CONTEXT=<abs path GAME_CONTEXT.md>
TASKS=<abs path GAME_TASKS.md>
SKILL=<abs path game-developer/>
PHASE=<id> (+ TASK-id)
ENGINE=unity|nucleon|unreal|godot   (scelta dell'utente, GDD Q0; il worker legge SOLO la riga del suo engine in engines.md)
STYLE=<GDD style + famiglia kit + lookdev preset>
GENRE=<riga di genres.md>
```

Vietato incollare conversazioni, screenshot chat, o "abbiamo già fatto greybox". Il worker rilegge `GDD.md`, `GAME_CONTEXT.md`, `GAME_TASKS.md`, `art/kit-catalog.json`, `art/blueprints/` e `docs/gates/` da disco.

## Contratto (in OGNI prompt di worker o helper, dopo le 9 righe)

Lezione Buffet Panic!: due helper paralleli hanno sovrascritto lo stesso `.cs`; un worker è uscito dal brief e ha reso un report vago; i rate limit hanno ucciso worker a metà; decisioni già prese sono state riaperte più volte.

```
DECISIONI=<abs path DECISIONI.md>  — leggilo PER PRIMO. Quello che c'è è deciso: non riaprirlo, non segnalarlo come problema.
OWNS=<lista esplicita dei file/cartelle che questo worker può scrivere>
DO=<cosa fare, 2-6 punti numerati = gli item del report>
DO NOT=<cosa non fare: altre fasi, file vicini, "già che ci sono", tuning/bilanciamento non chiesto>
PROGRESS=<abs path docs/progress/<PHASE>-<TASK-id>.md>
REPORT=formato fisso di SKILL/templates/worker-report.md
```

1. **Proprietà dei file.** Il worker scrive solo i file in `OWNS` (+ il proprio gate e il proprio PROGRESS). Prima di scrivere un file non suo, o un file suo che è cambiato da quando l'ha letto (data/sha1 diversi da quelli annotati in PROGRESS), **si ferma e lo riporta** in "Stop sui file" del report. Niente merge creativi.
2. **Parallelo.** Il parent non lancia mai in parallelo due worker con file in comune negli `OWNS` (cartelle comprese). Un file condiviso (es. `PlayerController.cs`, `strings.csv`) ha un solo proprietario per giro; gli altri gli chiedono la modifica tramite il report. Un solo worker alla volta guida l'Editor Unity (lock qui sotto).
3. **Recinto DO / DO NOT.** Fuori da `DO` = deviazione: si fa solo se serve per chiudere un item di `DO`, e si scrive in "Deviazioni". Bilanciamento, tuning, testi e stile non chiesti sono sempre DO NOT.
4. **Report fisso** ([templates/worker-report.md](../templates/worker-report.md)): fatto (un item di DO per riga, con path di evidenza), deviazioni, aperto, file cambiati, stop sui file, numeri JSON. Il parent confronta il report con il brief: item mancante, lavoro fuori DO non dichiarato, "fatto" senza path → **FAIL, rilancio** con `GATE ROSSO:` + la differenza.
5. **Avanzamento riprendibile** ([templates/progress-checkpoint.md](../templates/progress-checkpoint.md)): il worker crea PROGRESS nel primo minuto e lo aggiorna dopo OGNI passo (fatto, prossimo passo, file toccati con sha1, lock). Rilanciato dopo un crollo (rate limit, sessione chiusa) **legge PROGRESS per primo** e riparte dal "Prossimo passo", senza rifare il fatto. Il parent, se un worker muore, lo rilancia con lo stesso prompt + `RIPRENDI da PROGRESS`.
6. **Deliverable mai in `Temp/` o `Library/`** (Unity li svuota alla chiusura). Catture, clip, backup, log da tenere → `captures/`, `screenshots/`, `docs/`, `_backup/`. `Temp/` solo per file usa-e-getta.
7. **Scelte di design dette chiaro.** Se il worker implementa una cosa in modo diverso dal brief (una soglia, un comportamento, un testo, un flusso), lo scrive in "Deviazioni" e in `design_changes` del gate: cosa, perché, `decided_by: implementer`. **Mai** "il proprietario ha chiesto X" se X non è nel brief o in `DECISIONI.md` con la fonte (lezione Buffet Panic!: una scelta del worker è stata attribuita al proprietario).
8. **Decisioni: solo proposte etichettate.** Un worker che pensa che una decisione vada cambiata non la cambia: scrive `Riapre la decisione: D-NNN — prove — proposta` nella sezione "Proposte" del report ([launch-link.md](launch-link.md) §4).
9. **Salvataggi del proprietario.** Prima di ogni Play/exe che può scrivere salvataggi o preferenze: backup (cartelle dei salvataggi + chiavi di registro/PlayerPrefs), salvataggi del Play in una cartella temporanea se il gioco lo permette, ripristino alla fine con controllo "identici" (hash). La riga va nel gate (`saves:`).

## Retry

Se un worker chiude senza i file del gate, o con un report che non corrisponde al brief, il parent **rilancia lo stesso worker** con lo stesso prompt più `GATE ROSSO:` e **l'errore preciso**: la riga mancante del gate, il JSON di lint/build con `issues > 0`, le prime righe di `unity command console` o del test fallito. Mai solo "manca X". Max 2 retry, poi `[!]` (vedi il ciclo in [task-decomposition.md](task-decomposition.md)).

## Un solo editor: lock

C'è un editor e una scena: due worker che compilano, costruiscono o lintano insieme si rovinano il risultato a vicenda. Per andare veloci si **separa il lavoro**:

- **Fuori dall'editor, in parallelo (fino a `parallel.maxWorkers`, default 6):** blueprint / world / village / spec Blender, script (C#, Lua, GDScript) senza compilare, test scritti, mock UI, ricerca e download asset, Blender headless, conversione `html2rml.py`.
- **Dentro l'editor, uno alla volta** (qualsiasi recompile, build, lint, test, play, screenshot):

| engine | prendi | rilascia |
|---|---|---|
| unity | `powershell -File SKILL/scripts/unity-lock.ps1 -ProjectPath PROJECT -Owner <PHASE:TASK-id>` | stesso comando + `-Release` |
| nucleon | `python SKILL/scripts/ncli.py --project PROJECT lock acquire --owner <PHASE:TASK-id>` | `... lock release --owner <PHASE:TASK-id>` |
| unreal / godot | un solo client MCP / un solo processo headless: stesso file di lock JSON di ncli (`ncli lock` funziona per qualsiasi cartella) | idem |

  La sequenza va tenuta corta: niente ragionamenti lunghi mentre hai il lock, correggi il JSON e rientra. Rilascia anche se fallisci. Il lock più vecchio di 10 minuti viene considerato abbandonato.
- Un worker solo prende comunque il lock: costa zero e protegge da worker rimasti appesi.
- Vale anche per gli helper che un worker lancia a sua volta: stesso contratto, `OWNS` disgiunti, un solo helper con l'editor.

## Scheduler a ondate (sempre continuo, tutto il parallelo possibile)

Il parent non lancia "una fase alla volta": lancia **un'ondata** = tutti i task pronti insieme.

1. **Pronti** = righe `[ ]` di `GAME_TASKS.md` con tutti i `Dipende` a `[x]` (i `[!]` e chi dipende da loro restano fuori).
2. **Raggruppa**: task con `OWNS` disgiunti nella stessa ondata; due task con un file in comune → il secondo all'ondata dopo. Max `parallel.maxWorkers` (GDD `parallel:`) worker vivi.
3. **Lancia tutti nello stesso messaggio** (Claude Code: più `Agent` in background in una risposta). I worker che toccano l'editor si mettono in coda da soli sul lock: preparano tutto fuori (JSON, script) e prendono il lock solo per la sequenza breve build → lint → shot.
4. **A ogni chiusura** (notifica): verifica gate + report (contratto 4), aggiorna `GAME_TASKS.md`, e **riempi subito il posto libero** con il prossimo task pronto: niente attesa che l'ondata finisca tutta.
5. **Mai fermarsi**: un `[!]` dopo 2 retry si salta; il parent si ferma solo quando nessun task è più eseguibile, o per una scelta dell'utente.
6. **Scelte dell'utente raggruppate**: le varianti UI di tutte le schermate si preparano in parallelo e si mostrano **insieme** in una sola domanda (una galleria per schermata, una risposta per tutte); intanto gli altri track continuano. Lo stesso per asset dell'utente e controllo di mercato: una sola sosta, non una per schermata.
7. **Checkpoint** (ogni 10 `[x]`, prima di art-review / playtest / slice) = l'unico punto in cui si aspetta che i worker con il lock finiscano.

Track che girano in parallelo dopo il greybox (ognuno con i suoi `OWNS`):

```
ART      kit-fetch → world-gen → building-gen (batch) → level-build ×N (JSON in parallelo, build in coda) → hero-asset ×N → lookdev → art-review
CODE     systems: un verbo = script + test (scritti fuori dall'editor) → compile/test in coda → feel-baseline
UI       mock designer di TUTTE le schermate → scelta utente unica → UXML / RML / UMG → baseline-ui
AUDIO    fetch CC0 + AudioManager / suoni Nucleon → juice
QUALITY  baseline-* (loc, a11y, playtest-kit, store-capture) appena il suo sistema esiste
```

Granularità: **un blueprint per worker** in level-build, hero-asset a batch di 3, building-gen a batch di 5. `characters` dopo il primo level-build; `juice`, seconda `art-review`, `playtest`, `slice` in coda quando i track sono chiusi.

---

> **Le PHASE qui sotto sono scritte con i comandi Unity.** Con `ENGINE=nucleon|unreal|godot` ogni comando si traduce con il verbo dell'adapter ([engines.md](engines.md)): `gds_ping`→ping, `gds_build/world/village`→build, `gds_lint`→lint, `gds_shot`/`screenshot`→shot, `run_tests`/`editor_play`→test/play, `unity-lock.ps1`→lock. Il gate resta identico (stesse righe, stesso `lint: {"issues":0`).

## PHASE gdd

Tu fai SOLO l'intervista GDD. Leggi `gdd-interview.md`, `genres.md`, `styles.md`, `world-gen.md`, `tool-stack.md`, `gdd-template.md`, `gen3d.md`, `lookdev.md`, `quality-baseline.md`.
Blocchi A-E, tante domande, follow-up su tutto ciò che è vago, default consigliati. Tutti i campi elencati in fondo a `gdd-interview.md` vanno lockati in `GDD.md`.
Scrivi `PROJECT/GDD.md` (se PROJECT ancora vuoto, scrivi nel workspace e il parent lo sposterà).
NON aprire Unity, Blender, Voxel, UI.
Stop quando `status: locked` e l'utente ha confermato il recap.

Gate: `GDD.md` contiene `status: locked` e tutti i campi della lista in `gdd-interview.md`.

---

## PHASE project

Tu fai SOLO attach o create + strumentazione. Leggi `SKILL/references/project-attach.md`, `unity-cli.md`, `gds-editor.md` (Nucleon: `nucleon-loop.md` §1-2 e §9; Unreal: `unreal-loop.md`; Godot: `godot-loop.md`).

**ENGINE=nucleon** (al posto dei punti 1-4 Unity):
1. Attach, oppure `python SKILL/scripts/ncli.py --exe <paths.nucleon> exe new-project PROJECT --template <first-person|third-person|top-down|empty dal genere>`.
2. `python SKILL/scripts/ncli.py setup PROJECT`: harness `Content/Scripts/gds_test.lua` + `test_move.lua`, `art/blueprints/_example.json`, cartelle della skill, righe `.gitignore`.
3. Trasporto: editor aperto dal proprietario con Editor Preferences > AI > Enable Server (chiedilo UNA volta, nel recap del GDD) → HTTP; altrimenti `--stdio <editor>` (`--save current` su ogni build).
4. Verifica: `ncli ping` (upAxis `z`), `ncli lint --write docs/lint/scene-lint.json` → JSON, `NC_GDS_TEST=1` + `ncli play-test --expect "GDS-TEST DONE pass=1 fail=0"` con `test_move.lua`.
5. Poi i punti 5-6 sotto (gen3d key, `git init` + primo commit).
Gate Nucleon: `project.ncproject` + `ncli ping` JSON + lint JSON + play-test PASS + `docs/gates/04-project.md` PASS.

**ENGINE=unity:**
1. Attach o `unity projects create ... --template com.unity.template.urp-blank` (2D: `com.unity.template.universal-2d`). Unity 6000.x installato; 6000.5+ richiede ProBuilder ≥ 6.1.2 (l'installer usa le versioni consigliate dall'Editor).
2. `powershell -File SKILL/scripts/install-gds-editor.ps1 -ProjectPath PROJECT` (+ `-WithToonShader` se `toon: yes`, `-WithOutline` se `outline: yes`). Copia GDS Editor + Runtime, esempi `art/world/`, pacchetti, e `unity pipeline install`.
3. Apri/lascia aprire l'Editor: `unity command recompile` → `recompile_status` completed → `unity command console` 0 errori. `unity command package_add` per Cinemachine se il GDD lo usa.
4. Verifica: `unity command gds_ping` e `unity command gds_lint` rispondono JSON.
5. Se `GDD gen3d: meshy|tripo`: verifica che `MESHY_API_KEY`/`TRIPO_API_KEY` sia nell'env del MCP (non chiederla in chat, non loggarla).
6. Git: se il progetto non è già un repo, `git init` + `.gitignore` Unity (Library/, Temp/, Logs/, obj/, UserSettings/, Build*/, `Assets/_Game/Art/AssetStore/`, `art/cc0/**/*.zip`) + primo commit `project: GDS ready`. Serve ai checkpoint ogni 10 task.
Crea le cartelle `art/ blender/ voxel/ cc0/ exports/ blueprints/`, `screenshots/`, `captures/`, `ui/`, `docs/gates/`, `docs/lint/`, `docs/progress/`, `docs/tests/`, `Assets/_Game/...`, e `DECISIONI.md` dal template (righe vere dal GDD lock: lingue, piattaforme, scelte "no" del blocco E).
NON modellare, NON scrivere gameplay, NON UI.
Scrivi `docs/gates/04-project.md` con `projectPath`, versione Unity, output di `GDS.SceneLint.RunJson()` e `PASS`.

Gate: `ProjectSettings/` + `Assets/_Game/Editor/GDS/GDS.Editor.asmdef` + `gds_ping` JSON + console 0 errori + `docs/gates/04-project.md` PASS.

---

## PHASE task-decomposition

Tu fai SOLO la scomposizione dei task e l'inizializzazione della memoria centrale.
Leggi `SKILL/references/task-decomposition.md`, `art-pipeline.md`, `level-builder.md`, `context-management.md`, e i template `SKILL/templates/GAME_TASKS.md` e `GAME_CONTEXT.md`.
Genera:
1. `PROJECT/GAME_TASKS.md`: righe numerate (TASK-001..), un task = un deliverable (60-80 totali). Per l'art: **un task per edificio Blender** (`BG-inn`: stile, volumi, porte, balconi → `art/specs/inn.json`), **un task per blueprint kit/ProBuilder** (`BP-house_a`: volumi, aperture, partizioni, attach, prop, scatter), **un task per il villaggio** (`VL-hamlet`: strade, piazza, pesi edifici) se il GDD e esterno, e **un task per hero asset**. VIETATO "modelli 3D"/"props" generici, VIETATO un task per muro.
2. `PROJECT/GAME_CONTEXT.md`: visione, game loop, win/fail, controlli, mapping script, lookdev preset, famiglia kit.
3. `PROJECT/ASSET-LEDGER.md`: una riga per blueprint e per hero asset, `source:` dal catalogo `cc0-sources.md` o tier gen3d del GDD.
4. `PROJECT/art/reference/BOARD.md` + 4-8 immagini di riferimento ([art-direction.md](art-direction.md)).
5. Se il mondo è procedurale (`GDD world`, vedi world-gen.md): `PROJECT/art/world/<name>.json` partendo da `art/world/example_<mode>.json` (seed, dimensione, scatter con nomi TODO fino al kit-fetch).
6. Task della baseline di qualità dal blocco E del GDD ([quality-baseline.md](quality-baseline.md)): gli ESSENZIALI sempre, gli opzionali solo se `yes`; il task feel-baseline dopo il primo verbo core.
7. `PROJECT/art/blueprints/PLAN.md`: tabella edifici/aree → `source: blender-gen|kit|probuilder`, posizione/rotazione nel livello (griglia Geometra 4 m) o `lot: village`, così building-gen / level-build / village non inventano nulla. Default per esterni low-poly: **blender-gen** per le case, kit per props/recinzioni/lampioni/alberi, ProBuilder per interni.
NON modellare, NON aprire Unity.

Gate: `GAME_TASKS.md` (60-80 task per deliverable, max 90, regole di merge di task-decomposition.md) + `GAME_CONTEXT.md` (con `genre:` e `style:`) + `ASSET-LEDGER.md` + `art/blueprints/PLAN.md` + `art/reference/BOARD.md`.

---

## PHASE greybox

Tu fai SOLO geometria giocabile + player che si muove. Leggi `greybox.md`, `level-builder.md`, `unity-loop.md`, `geometra.md`, `scene-lint.md`.
Terreno: cubo/plane con **faccia superiore a Y=0** (cubo `[n,0.2,n]` a `y=-0.1`) e collider.
Stanze/edifici del greybox: `GDS.PB.Room(...)` oppure blueprint `mode: probuilder|primitives` da `art/blueprints/PLAN.md` (stesso `name` che userà level-build → rebuild in place). Vietato piazzare muri uno a uno.
Un muro per linea condivisa: stanze adiacenti = blueprint nella stessa cartella + `group`; il builder costruisce la linea una volta sola con le porte di entrambi (`omit` / `wallOwner` per forzare). Lint deve mostrare `overlappingWalls: 0`, `overlappingFloors: 0`.
Obbligo: Input System, controller della riga di `genres.md`, `PlayerMovementTests` che **giri** (`unity command run_tests` o `unity test`).
Vietato Blender. Vietato kit. Vietato UI Toolkit. Vietato dire che il gioco è finito.
Lint: `unity command gds_lint --autofix true` poi `gds_lint` → `issues: 0`.
Play Mode + screenshot `screenshots/010-greybox-play.png`.
Scrivi `docs/gates/06-greybox.md` (test job_id, lint JSON, PNG).

Gate: test movimento verde + lint 0 + PNG greybox su disco + 0 errori console.

---

## PHASE kit-fetch

Tu fai SOLO download + catalogo dei pack della famiglia GDD.
Leggi `cc0-sources.md`, `art-pipeline.md`, `gds-editor.md`. Esegui:

```
powershell -File SKILL/scripts/fetch-cc0-kits.ps1 -ProjectPath PROJECT -Genre <medieval|dungeon|scifi|city|pirate|interior|prototype|nature|characters|vfx>
```

Se `GDD assetStore: yes` e famiglia = Synty: apri Package Manager > My Assets (TerminalMCP browser se serve) e importa POLYGON Starter Pack in `Assets/_Game/Art/AssetStore/`.
Copia i modelli usati in `Assets/_Game/Art/Kits/<family>/` (FBX o glTF, non entrambi). Poi:
`unity command gds_catalog --folder Assets/_Game/Art/Kits/<family>/<pack>` → se `notes` dice che la scala non è metrica: `unity command gds_kit_scale --folder <kit> --scale <suggestedScale>` UNA volta (è relativo) e rifai il catalogo finché `scale looks metric`. Colori fuori palette GDD: `gds_recolor` per ogni materiale in `materials` del catalogo.
NON importare in scena. NON mischiare due famiglie. NON scaricare Quaternius Pro/Source né Sloyd.
Gate: `art/cc0/` con almeno un pack + `art/kit-catalog.json` con `count > 0` + `docs/gates/07-kit-fetch.md` (incolla `suggestedModule` e `notes`).

---

## PHASE world-gen (se il mondo del GDD è procedurale)

Tu fai SOLO il mondo da spec. Leggi `world-gen.md`, `scene-lint.md`, `art/kit-catalog.json`, `GDD.md` (world, worldSize, landmark, style).
1. Apri `art/world/<name>.json`: nomi scatter/prop = file veri del catalogo (stessa famiglia), dimensione da `worldSize`, `flat` per villaggio/arena/landmark, `seed` fisso.
2. `unity command gds_world --spec art/world/<name>.json` → `status: PASS`, `warnings` vuoti (nome mancante → correggi la spec e rilancia; mai a mano nella scena).
3. `gds_lint --autofix true` poi `gds_lint` → `issues: 0`.
4. `unity command gds_sheet --prefix screenshots/review/world`.
VIETATO: spostare alberi/rocce a mano, cambiare seed senza annotarlo, mondi più grandi del GDD.
Gate: `docs/gates/07-world.md` con il JSON del risultato, `lint:`, PNG.

---

## PHASE building-gen (Blender procedurale, batch fino a 5 spec)

Tu fai SOLO gli edifici esterni "veri" della lista `art/blueprints/PLAN.md` marcati `source: blender-gen`. Leggi `blender-building.md`, `geometra.md`, `GDD.md` (style/palette/lookdev).
Per ogni edificio (max 5 per run):
1. Scrivi `art/specs/<name>.json`: `style` dal GDD (medieval/fantasy/village/modern/scifi/dungeon), `volumes` (1-3 rettangoli, metri interi, piani 1-3), `doors` sul lato S, 0-1 `balconies`, 0-1 `chimneys`, `interior.partitions` se il player entra, `export: art/exports/building_<name>.glb`, `preview: screenshots/blender-building_<name>.png`. Palette GDD via `styleOverride` se serve.
2. `powershell -File SKILL/scripts/gds-building.ps1 -Spec PROJECT/art/specs/<name>.json -ProjectPath PROJECT` → leggi `GDS_RESULT` (`tris` 2k-40k, `bytes` > 50k).
3. Read del PNG preview: se manca tetto/finestre/porta (spec incoerente) correggi la spec e rilancia. Mai ritoccare a mano in Blender.
4. Aggiorna `ASSET-LEDGER.md` (`source: blender-gen`, spec path, fbx path).
VIETATO: `execute_blender_code` con modellazione a mano, addon, `blender -b` con script diversi da `gds_building.py`, edifici curvi (usa `GDS.PB.Tower`), piu di 5 spec per run.
Gate: `docs/gates/07-building-<name>.md` per edificio con `GDS_RESULT`, PNG, FBX in `Assets/_Game/Art/Exports/`. Il piazzamento lo fa village / level-build (con lint).

---

## PHASE level-build

Tu fai SOLO UN blueprint: `$BP_NAME` (riga di `art/blueprints/PLAN.md`). Leggi `level-builder.md`, `scene-lint.md`, `geometra.md`, `art/kit-catalog.json`.
1. Scegli dal catalogo i file per i ruoli `floor wall wallDoor wallWindow corner roof stair` (stessa famiglia). Se manca `wall`/`floor` nel kit → `mode: probuilder` (interni/dungeon) oppure edificio `building-gen` come `props` con `collider: mesh`. MAI cubi Unity.
2. Scrivi `art/blueprints/$BP_NAME.json`: pianta con `volumes` (L/T/U se PLAN.md lo dice), `openings` per volume, `partitions` interne con porta, `stairs` + `floorHoles` se >1 piano, `attach` (lanterne, insegne, tende, fioriere: almeno 2 per facciata visibile), `fences` se il lotto ne ha, `props` interni con coordinate relative, `scatter` esterno con `avoidRadius`.
3. Lock Unity (`unity-lock.ps1 -Owner level-build:$BP_NAME`), poi `unity command gds_build --blueprint art/blueprints/$BP_NAME.json` → leggi `missingRoles`/`warnings`, correggi il JSON e rilancia finché `missingRoles: []`.
4. `unity command gds_lint --autofix true` poi `gds_lint` → `issues: 0`. Un muro per linea condivisa: lint deve mostrare `overlappingWalls: 0 overlappingFloors: 0` (se no: correggi `openings`/`omit`/`wallOwner` e ricostruisci i DUE blueprint della linea; warning "built by X, not in the scene" = costruisci X).
5. `unity command gds_shot --out screenshots/020-build-$BP_NAME.png --view orbit1`, poi rilascia il lock (`-Release`). Se il build fallisce: rilascia, correggi il JSON fuori lock, rientra.
VIETATO: `manage_gameobject` per piazzare muri, ProBuilder MCP face-by-face, Blender, seconda famiglia, "visto che ci sono faccio anche la casa B".
Gate: `docs/gates/07-build-$BP_NAME.md` con `build:` JSON, `lint:` JSON, PNG. Parent Read del PNG solo per stile (coerenza famiglia), non per misurare.

---

## PHASE village (SOLO se il GDD descrive un insediamento)

NON e il default del mondo. Caverna, dungeon, cripta, interno, citta, base sci-fi, natura aperta: NON lanciare questa fase — il mondo lo fa `level-build` secondo [environments.md](environments.md) (kit genre, lookdev preset, recipe caverna).



Tu fai SOLO il layout del mondo. Leggi `village.md`, `scene-lint.md`, `GDD.md` (mappa/ambiente). Prerequisiti su disco: gli edifici di building-gen in `Assets/_Game/Art/Exports/` e/o i blueprint kit in `art/blueprints/`.
1. Scrivi `art/blueprints/village_<name>.json` (template `SKILL/templates/blueprints/village_example.json`): strade = percorsi del GDD, piazza = hub, `buildings` con pesi (cottage 3, hero 1), `streetProps`/`plazaProps`/`fenceFile` dal kit catalog, `scatter` alberi/rocce dal kit nature, `terrain.enabled` false se il GDD e un interno.
2. `unity command gds_village --spec art/blueprints/village_<name>.json` → `buildings >= 6`, `warnings: []` (file mancanti → correggi nomi dal catalogo).
3. `gds_lint --autofix true` poi `gds_lint` → `issues: 0`.
4. Player spawn sulla piazza (sposta il Player del greybox). `gds_shot --view aerial` → `screenshots/025-village-aerial.png`, `--view hero` → `screenshots/026-village-street.png`.
VIETATO: piazzare edifici a mano, modificare i lotti generati, terreno senza collider, strade fuori dalla zona piatta.
Gate: `docs/gates/07-village.md` con il JSON village, `lint:`, i 2 PNG.

---

## PHASE hero-asset (batch fino a 3)

Tu fai SOLO gli hero asset `$ASSET_ID_1..3` del ledger (prop unici che nessun kit ha). Leggi **`hero-procedural.md`** (percorso di default), `asset-contract.md`; per il fallback `blender-mcp.md`, `polypizza.md`, `gen3d.md` e `GDD.md → gen3d:`.
**Default: script procedurale headless.** Per ogni asset: riferimento (immagine dell'utente o board) → `PROJECT/Tools/$ASSET_ID_build.py` con `SKILL/scripts/blender/hero_kit.py` (parti da `SKILL/templates/blender/hero/*.py`) → `blender -b -P Tools/$ASSET_ID_build.py -- art/exports/$ASSET_ID.glb art/preview/$ASSET_ID` → leggi i PNG accanto al riferimento, scrivi le differenze, correggi, ricostruisci (2-4 giri) → import nel motore + screenshot del motore (Nucleon: `ncli call asset_import`, spec showcase, `ncli build --save current`, `ncli shot`). Riga ledger `source: procedural (Tools/$ASSET_ID_build.py)`.
**Fallback** (solo organico: persone, animali, volti; o se l'utente lo chiede), con i passi 0-4 qui sotto. Ordine: Poly Pizza → Poly Haven models → Sketchfab CC0 → tier gen3d del GDD (solo se `gen3d != none`, entro `gen3dMaxAssets` e budget).
Per ogni asset:
0. `execute_blender_code`: RESET SCENA (rimuovi tutti objects/meshes/materials).
1. Ricerca + download nativo (`search_polypizza_models` / `search_polyhaven_assets(asset_type="models")` / `search_sketchfab_models`) oppure `generate_model` (CoplayDev, provider dal GDD) / Hyper3D.
2. Sanitize block ONLY (luci/camere via, pivot base Y=0, `normalize_size` alla misura Geometra, decimate > 15k tris) + `export_scene` → `art/exports/$ASSET_ID.glb`.
3. `get_viewport_screenshot` → 1 PNG `screenshots/blender-$ASSET_ID.png`.
4. Riga ledger: `source`, id, licence, attribution, crediti usati.
Poi aggiungi il prop alla lista `props` del blueprint giusto (`art/blueprints/<bp>.json`) e rilancia `GDS.LevelBuilder.BuildFromFile` + lint (l'import-art lo fa se il GLB non è ancora in `Assets/_Game/Art/`).
VIETATO: bpy modelling a mano via MCP (`execute_blender_code`), cubi, `read_homefile`, muri/pavimenti, superare il budget, PBR fotorealistico accanto a Kenney senza flatten materiale.
GLB < 15KB = FAIL. MCP giù: avvia Blender; porta 9876 chiusa → STOP.
Gate: `docs/gates/07-hero-$ASSET_ID.md` per asset con script, PNG di anteprima + screenshot del motore, riga `STATS`, GLB, riga ledger, `lint:` dopo il rebuild (checklist in `hero-procedural.md`).

---

## PHASE import-art

Tu fai SOLO import GLB/FBX ancora fuori da Unity (`art/exports/*` → `Assets/_Game/Art/Exports/`), strip luci/camere, collider, prefab.
Poi rilancia i blueprint che li citano (`GDS.LevelBuilder.BuildFromFile`) e lint 0.
NON modellare. NON UI.
Gate: `docs/gates/07-import.md` con lista prefab + `lint:`.

---

## PHASE lookdev

Tu fai SOLO il look. Leggi `lookdev.md`, `gds-editor.md`, `GDD.md → lookdev/toon/outline/hdri/palette`.
1. (HDRI opzionale) Blender MCP `download_polyhaven_asset(asset_type="hdris", resolution="2k")` → copia `.hdr` in `Assets/_Game/Art/HDRI/`.
2. `unity command gds_lookdev --preset <preset> [--hdri <asset>]` → `applied` deve contenere `volume` e `camera-post`.
3. `unity command gds_palette --colors "<hex GDD>"` e assegna `Mat_Palette_*` alle shell ProBuilder (`manage_material` o rebuild blueprint con `material`).
4. Se `toon: yes`: pacchetto installato dal project → `GDS.LookDev.ConvertMaterials("Universal Render Pipeline/Lit", "Toon")`. Se `outline: yes`: `manage_graphics feature_add` della feature del pacchetto.
5. Luci locali: `GDS.VFX.AttachTorches("torch")` per interni; 1 fill light sull'obiettivo.
6. `read_console` 0 errori. Lint 0. Screenshot Game view `screenshots/035-lookdev.png` (bloom/fog/ombre visibili).
NON toccare gameplay/UI. NON YAML.
**ENGINE=nucleon** (al posto dei passi 1-5, [nucleon-loop.md](nucleon-loop.md) §8a): `ncli session-stop` → `nc_mat.py auto --project P --catalog art/kit-catalog.json --style <GDD style> --name <kit>` → `nc_mat.py assign` (materiali + vento delle piante sul livello) → materiali a mano per le superfici del GDD (`nc_mat.py make glass|water|carPaint|skin|neon ...`) → `nc_mat.py check` su ogni shading model nuovo (fallito = `defaultLit` con le stesse texture + nota in `docs/NUCLEON-ENGINE-NOTES.md`) → `nc_world.py look` → `serve` → shot in Game View.
Gate: `docs/gates/08-lookdev.md` con l'`applied` JSON (Nucleon: l'output di `auto`/`assign`/`check`), preset, PNG, `lint:`.

---

## PHASE art-review (dopo lookdev e dopo juice)

Tu fai SOLO la valutazione estetica. Leggi `art-direction.md`, `styles.md`, `art/reference/BOARD.md`. Non modifichi la scena.
1. `unity command gds_sheet --prefix screenshots/review/<fase>` (Unreal: `gds_ue.shot`).
2. Read di ogni PNG + board. Punteggio R1-R7 con una riga di evidenza ciascuno.
3. Media ≥ 4 e nessun voto < 3 → PASS. Altrimenti fix list su file di spec (world JSON, blueprint, preset, VFX), mai "sistemo la scena".
Gate: `docs/gates/15-art-review.md`. Il parent rilancia le fasi citate nella fix list, poi di nuovo art-review (max 2 giri, poi riporta i voti all'utente).

---

## PHASE characters

Tu fai SOLO personaggi + animazioni (+ NavMesh se il GDD ha nemici). Leggi `characters.md`, `gds-editor.md`.
1. Pack dal GDD (KayKit Adventurers/Skeletons, Kenney Animated, Quaternius UBC+UAL) → `Assets/_Game/Art/Characters/<pack>/`.
2. `GDS.Characters.SetHumanoidFolder(...)`, `ListClips()`, `BuildController("Player", ...)`, `MakePrefab(...)`. Stesso per `Enemy`.
3. Sostituisci la capsula del greybox con `char_player` (mantieni `PlayerController` + Input). `animator.SetFloat("Speed", ...)` nel controller.
4. Nemici: Skill `initialize-ai-navigation` → NavMeshSurface bake, `NavMeshAgent`, `EnemyChase.cs` + test `Enemy_ChasesPlayer`.
5. Altezza player 1.6–2.0 m (Geometra) — altrimenti `SetImportScale` sulla cartella.
6. Lint 0. Play Mode screenshot `screenshots/050-characters.png` (personaggio in walk).
Gate: `docs/gates/09-characters.md` con JSON delle chiamate, test, PNG, `lint:`.

---

## PHASE systems

Tu fai SOLO i verbi del GDD (oltre move già nel greybox): interact, pause, win/fail, giorno/notte se nel GDD.
Ogni verbo = script + test che gira nella stessa modifica.
Prompt a schermo minimo: cosa fare adesso (es. "Saccheggia la casa prima del coprifuoco").
NON Main Menu. NON modellare.
Testi a schermo solo come chiavi della string table (`strings.csv`), mai stringhe nel codice. Ogni numero mostrato in più schermate ha un solo getter ([quality-baseline.md](quality-baseline.md) §2).
Gate: `docs/gates/10-systems.md` + test names.

---

## PHASE feel-baseline (dopo il primo verbo core giocabile nel livello vero)

Tu fai SOLO le simulazioni di "feel" del verbo core e la baseline. Leggi `playtest.md` (§ Feel in scena reale), `SKILL/templates/feel-baseline.json`.
1. Sim deterministica (input pilotato, seed fisso) nella **scena di gioco vera**, non in una scena di test vuota: porte, muri, angoli, sprint, stop vicino a un muro, più i casi del genere (salto su bordo, curva a velocità piena...). Min 6 casi × 8 run.
2. Comando o test ripetibile (`unity command <game>_feelsim --suite real --format json` o PlayMode test) che stampa JSON con le metriche per caso.
3. Scrivi `docs/tests/feel-baseline.json` (casi, metriche, `tolerance`, `direction`, gate, comando).
DO NOT: cambiare tuning o fisica per far uscire numeri migliori.
Gate: `docs/gates/10-feel-baseline.md` con il JSON incollato + path della baseline.

---

## PHASE baseline-<item> (a11y | ui-quality | onboarding | loc | playtest-kit | store-capture)

Tu fai SOLO l'item della baseline del tuo task. Leggi `quality-baseline.md` (sezione dell'item), `GDD.md` blocco E, `DECISIONI.md`.
- **a11y:** rimappatura tastiera + pad con "Ripristina predefiniti", dimensione testo, movimento ridotto (+ opzionali scelti nel GDD); prompt HUD che leggono il binding corrente. Test per ognuno; screenshot di ogni schermata al 150 %.
- **ui-quality:** transizioni ≤ 0,5 s saltabili, hover + focus su ogni pulsante (mouse, tastiera, pad), coda notifiche (se `yes`), controllo coerenza numeri.
- **onboarding:** tutorial ≤ 4 passi, suggerimenti alla prima occasione (salvati per profilo), comparsa graduale nelle schermate dense.
- **loc:** `strings.csv` (`key,context,max_chars,<lingue>`), fallback font CJK/arabo (RTL), `loc_check` (mancanti, placeholder, duplicati, oltre `max_chars`, stringhe nel codice UI) = 0 errori; uno screenshot per scrittura.
- **playtest-kit:** telemetria CSV opt-in locale per livello, variante build demo/profilo pulito con cartella salvataggi propria, `TESTER_README.md` dal template.
- **store-capture:** tool solo Editor, HUD `full|minimal|none`, prompt nascosti, seed fissi, screenshot taglia store + sequenze di frame GIF in `captures/<data>/` + `manifest.json`.
DO NOT: ridisegnare schermate già scelte dall'utente (solo stati, scala, transizioni); cambiare controlli di default se `DECISIONI.md` li fissa.
Gate: `docs/gates/16-baseline-<item>.md` con test, check JSON, PNG.

---

## PHASE ui-* (due giri: `variants` in parallelo → una scelta → `implement` in parallelo)

Prima un task breve **ui-tokens** (palette GDD + preset lookdev → `ui/tokens.css`, nessuna schermata). Poi, in parallelo, un worker **variants** per ogni schermata (Main Menu, HUD, Pause, Game Over, + quelle del GDD): 3-4 varianti HTML con layout davvero diversi + gallery PNG, stessi token. Ogni prompt `ui-*` porta la riga `UI_ROUTE=<ui-route del GDD>` dopo le 9 righe: il worker non fa domande, la passa a `designer` (game-ui.md §4). `concept`/`both`: prompt immagine da `game-prompt.mjs --target image` (setting, titolo, voci di menu dal GDD), un'immagine per direzione col tool di image gen (Canva `generate-image`, caricarlo con ToolSearch), salvate in `ui/mocks/concepts/`, mostrate come varianti; dopo la scelta, la replica HTML è la variante da transpilare. Se il worker non raggiunge il tool, fa `direct` e lo scrive nel gate: il parent genera le immagini e rilancia il worker con i PNG. Il parent **raccoglie tutte le gallerie e fa UNA sola domanda all'utente** (una scelta per schermata, nella stessa risposta); mentre aspetta, gli altri track continuano. Poi un worker **implement** per schermata, in parallelo (OWNS: i suoi file UI + il suo controller; il cablaggio nella scena/progetto passa dal lock).
Transpiler per engine: Unity `scripts/ui-transpiler.mjs` → UXML/USS · Nucleon `scripts/html2rml.py mock.html PROJECT/UI/<screen>.rml --model <screen>` → RML/RCSS (+ `.preview.lua`; controllo `NC_EDITOR_UI_DOCUMENT` screenshot) · Unreal UMG via widget toolset · Godot Control scene.
Nelle sezioni qui sotto "MOSTRA ALL'UTENTE E ATTENDI LA SCELTA" = la domanda unica del parent, non una sosta per schermata.

---

## PHASE ui-main-menu

Tu fai SOLO il Main Menu.
OBBLIGO Skill tool `designer` mode=game. Vietato inventare UXML a mano come primo passo. Vietato saltare Variant Studio / mock HTML + Playwright.
Flusso: tokens (palette GDD + preset lookdev) → 3-4 varianti HTML con layout distinti → screenshot gallery 1440x900 `screenshots/040-ui-main-menu-variants.png` → **MOSTRA ALL'UTENTE E ATTENDI LA SCELTA (domanda unica del parent con tutte le schermate)** → solo dopo la scelta: transpiler dell'engine (Unity `ui-transpiler.mjs` → UXML/USS + UIDocument + PanelSettings; Nucleon `html2rml.py` → RML mostrato da `Content/Scripts/game.lua`).
Unity: scena MainMenu **build index 0**; Nucleon: il menu RmlUi è la prima cosa che `game.lua` mostra (modo `menu`, come il sample). Sfondo: screenshot lookdev o camera sul livello con Volume. Spawn FP nel livello = FAIL.
Gate: mock HTML su disco + UXML + PNG + `docs/gates/11-ui-main-menu.md`.

---

## PHASE ui-hud

Tu fai SOLO HUD. Skill `designer` mode=game OBBLIGATORIA.
REGOLA SCELTA UTENTE TASSATIVA: È VIETATO auto-generare l'HUD senza varianti. Mantieni i token di stile consolidati nel Main Menu (`ui/tokens.css`), ma devi SEMPRE creare 3-4 varianti di layout diverse (es. diegetico, barre angolari survival, bottom-bar compatta, minimal immersivo) in Variant Studio.
Screenshot gallery 1440x900 `screenshots/041-ui-hud-variants.png` → **MOSTRA ALL'UTENTE E ATTENDI LA SCELTA (domanda unica del parent con tutte le schermate)**.
Solo dopo la scelta dell'utente: `ui-transpiler.mjs` → UXML/USS + PanelSettings.
Vitali, obiettivo testuale visibile, prompt `[E]`, orologio se nel GDD. IMGUI = FAIL.
Screenshot Play Mode `screenshots/041-ui-hud.png`. Gate `docs/gates/11-ui-hud.md`. Mock HTML mancante = FAIL.

---

## PHASE ui-pause

Tu fai SOLO Pause. Skill `designer` obbligatoria.
REGOLA SCELTA UTENTE TASSATIVA: Mantieni i token del Main Menu, ma genera 3-4 varianti di layout (sidebar laterale, modale centrale, registro/libro diegetico, minimal).
Screenshot gallery `screenshots/042-ui-pause-variants.png` → **MOSTRA ALL'UTENTE E ATTENDI LA SCELTA (domanda unica del parent con tutte le schermate)**.
Solo dopo la scelta: transpiler UXML + controller (Esc, timeScale 0, Riprendi / Menu).
Screenshot `screenshots/042-ui-pause.png`. Gate `docs/gates/11-ui-pause.md`.

---

## PHASE ui-gameover

Tu fai SOLO Game Over / Victory. Skill `designer` obbligatoria.
REGOLA SCELTA UTENTE TASSATIVA: Mantieni i token del Main Menu, ma genera 3-4 varianti (pergamena/certificato, epitaffio scuro, statistiche dettagliate, cinematico).
Screenshot gallery `screenshots/043-ui-gameover-variants.png` → **MOSTRA ALL'UTENTE E ATTENDI LA SCELTA (domanda unica del parent con tutte le schermate)**.
Solo dopo la scelta: transpiler UXML + pulsante Riprova/Menu.
Screenshot `screenshots/043-ui-gameover.png`. Gate `docs/gates/11-ui-gameover.md`.

---

## PHASE juice (VFX + Audio + Game Feel)

Tu fai SOLO VFX, SFX CC0, hit-stop/shake. Leggi `vfx.md`, `audio-pipeline.md`, `juice.md`.
1. `unity command gds_vfx` (+ Cartoon FX Free se `assetStore: yes`).
2. Collega: dust ai passi, pickup all'interact, hit al danno + hit-stop 3 frame + `CinemachineImpulseSource`, sparkle al win.
3. `fetch-cc0-audio.ps1 -ProjectPath PROJECT`; `AudioManager.cs` compilato 0 errori; istanza in `MainGame.unity`; passi/porte/UI click collegati.
4. Lint 0. Screenshot Play Mode durante un hit/pickup `screenshots/060-juice.png`.
5. NON dire "il gioco è finito".
Gate: `docs/gates/12-juice.md` + `Assets/_Game/Prefabs/VFX/` + `Assets/_Game/Audio/SFX/` popolate + console 0 errori + `lint:`.

---

## PHASE playtest

Tu fai SOLO QA. Leggi `playtest.md`, `scene-lint.md`.
1. `unity command gds_lint` → `issues: 0` (altrimenti FAIL, non fixare tu: elenca).
2. Play Mode reale: `editor_play`, input da PlayMode test o TerminalMCP, `capture_game_view`, `console` 0 errori, `editor_stop`.
FAIL se dallo screenshot non si capisce l'obiettivo (manca testo HUD / prompt / menu).
FAIL se in Game View ci sono primitives Unity visibili (cubo/capsula default) o scena piatta senza Volume.
3. Rilancia le sim di feel in scena reale e confronta con `docs/tests/feel-baseline.json`: un caso peggiore della tolleranza = FAIL (salvo riga di approvazione del proprietario in `DECISIONI.md`).
4. Controllo "catture vs regole" su ogni screenshot che va al playtest o allo store ([playtest.md](playtest.md)).
Scrivi `docs/playtest.md` e `docs/gates/13-playtest.md`.
NON inventare test verdi. Incolla job_id / output / lint JSON.

---

## PHASE slice

Tu fai SOLO il recap. Leggi tutti i `docs/gates/*.md`.
Se uno è rosso, NON dichiarare slice fatta. Elenca i rossi.
Gate: `docs/gates/14-slice.md`.

---

## PHASE design-review (dopo la slice; prima e dopo ogni gate di gameplay/UI/flusso)

Tu fai SOLO la review, **in sola lettura** sul gioco: niente fix. Leggi `design-review.md`, `DECISIONI.md`, gli ultimi gate, e se ci sono `launch/fg/waves/wNN-mappa-gioco.md` / `-schermate.md` / `-runs.md` (punto di partenza, non si rifanno).
1. `docs/design-review/game-map.md` dal codice e dai dati, con file e discrepanze.
2. `docs/design-review/screen-map.md`: tabella + blocco `screens`; `design_review.py screens` (con `--before` se c'è una versione in `history/`).
3. `docs/design-review/runs.md`: ≥ 3 run a tempi con i segni; `design_review.py runs` (con `--before`).
4. Copia le versioni "prima" in `docs/design-review/history/*-gNN.md`.
OWNS: `docs/design-review/**`. DO NOT: toccare codice, scene, `launch/`; giudicare decisioni come problemi.
Gate: `docs/gates/review-gNN.md` con i numeri dei due script e l'elenco: orfani, tratti morti > 20 s, momenti con > 4 UI insieme, spirali, discrepanze.

---

## PHASE iterate-gate (dopo la slice: un gate del piano, da ondata o dalle note del proprietario)

Tu fai SOLO i punti del tuo gate (`docs/gates/plan-wNN.md` riga NN, o la lista del proprietario). Leggi `DECISIONI.md` per primo, poi `launch-link.md` §5-8, `design-review.md` §4, [templates/gate.md](../templates/gate.md).
1. **Prima:** misura il problema nel gioco vero (numeri, foto `-before`); review "prima" dalle run toccate.
1b. **Repro prima del fix** (ogni bug, ogni engine): un test che riproduce il bug e **fallisce sulla build attuale** con i numeri del report. Nucleon: copia `Tools/gds/test_bug_template.lua` in `Content/Scripts/test_bug_<chiave>.lua` (`ncli play-test --expect "GDS-TEST bug_<chiave> FAIL"`); Unity: un test PlayMode `Bug_<chiave>`. Poi fix della causa (mai del test), poi PASS + suite intera. Gate: `repro: {before: "FAIL <motivo>", after: PASS}`; il test resta nella suite. Un bug che non si riesce a far fallire in un test non è capito: si torna al punto 1. Se un test diventa rosso dopo un checkpoint verde: `python SKILL/scripts/gds_bisect.py --project PROJECT --test "<il test>"` trova il commit colpevole, citato nel gate.
2. **Causa vera**, poi fix. Bilanciamento, tuning e stile non chiesti = DO NOT.
3. **Verifica la meccanica vera nel gioco normale**, non solo il caso del report: tutte le direzioni e situazioni in cui il giocatore la incontra (davanti / di lato / da dietro, fermo / in corsa, con e senza il perk), con numeri prima → dopo. Un colpo che "non fa niente" da un lato è un bug anche se di fronte funziona.
4. **Foto guardate**, una per una, con una riga su cosa mostrano; una foto che contraddice il testo = rifai.
5. **Salvataggi:** backup e ripristino identici (Contratto 9).
6. **Niente build** se il proprietario non l'ha chiesta. **Niente suite di test** se `DECISIONI.md` dice che prova lui: restano compilazione 0, lint, controlli deterministici (testi, numeri) e, se il gate tocca fisica/controller/collider, la sim di feel nella scena vera.
7. **Dopo:** review "dopo" sulle run toccate; dopo un redesign controllo orfani (`design_review.py screens --before`).
8. Gate con header ([launch-link.md](launch-link.md) §7): `risks` = rischi di gameplay **introdotti** (cosa può peggiorare); `design_changes` con `decided_by`; `owner_try`; sezione `## Per il proprietario`. Poi `gate_link.py check` ✅.
OWNS: i file del piano per quel gate + `docs/gates/NN-*.md` + `docs/screens/NN/`. DO NOT: `launch/**` (lo aggiorna il parent con `gate_link.py`), decisioni, punti di altri gate.

---

## Fine fase

Il worker aggiorna il suo PROGRESS, scrive il gate e chiude con il report fisso. Il parent aggiorna `GAME_TASKS.md` + `GAME_CONTEXT.md` e riempie subito il posto libero dello scheduler con il prossimo task pronto. Nessuna sosta, nessun banner, nessuna chat nuova.
