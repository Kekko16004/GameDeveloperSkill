# Changelog

## 2026-10-25: nuovo installer (skillkit 1.1) e aggiornamento

Lo stesso installer gira anche in DesignerSkill e GameLaunchAnalyzer. Prima la skill compariva due volte in Claude, Codex e Kilo, e alcune copie restavano indietro di versione.

| Cosa | Dove |
|---|---|
| App da terminale (rail verticale, multiselect con le frecce, spinner, riepilogo; truecolor/256/16 colori, glifi full/cp437/ascii, it/en) | `installer/`, `installer/DESIGN.md` |
| Una copia in `~/.agents/skills`; link solo per Claude Code, Antigravity e Cline; copie doppie e nomi vecchi (`real-world-design`) spostati in un backup | `installer/lib/hosts.mjs` |
| Dipendenze dai loro repo, sempre all'ultimo commit: designer, game-launch-strategist (opzionale, proposta in tutte e due le direzioni), skill ufficiali Unity, TerminalMCP (Fonlogen/TerminalMCP: skill + MCP `terminal`), Blender MCP, VoxelAI | `skillkit.json` |
| MCP scritti nel formato di ogni host (Claude CLI, JSON/JSONC, TOML di Codex); le voci dell'utente non vengono toccate; le chiavi restano riferimenti a variabili d'ambiente | `installer/lib/mcp.mjs` |
| `update` (pull + dipendenze + reinstalla), `doctor [--fix]`, `uninstall`, `--dry-run`, `--dev`, ricevuta in `~/.agents/skillkit/game-developer.json` | `install.bat`, `update.bat`, `install.sh`, `update.sh` |
| `scripts/update.mjs` aggiorna dalla skill installata; console: la schermata design mostra lo stato e ha i pulsanti Aggiorna e Ripara | `game-developer/scripts/update.mjs`, `tools/tui/gds_tui.py` |
| Rimossi `install.ps1`, `install-mcp.ps1` e `scripts/update.ps1` | |

## 2026-10-24: Nucleon aggiornato a `5cf63bb` (sistema materiali in stile UE)

L'engine ha ricevuto 138 commit: il sistema materiali (14 shading model come preset di uno slab Substrate, layer e layer function,
World Position Offset e vento nei materiali, parallax/triplanar/detail normal, domini post-process/sky/fog/decal/light function/volume/UI,
Subsurface Profile `.ncsss`, Material Function `.ncmatfunc`, Parameter Collection `.ncmpc`), il fix dei motion vector di FSR 3 e
gli scalability preset che non cambiano più la risoluzione. MCP e natives sono invariati.

| Cosa | Dove |
|---|---|
| `nc_mat.py`: `auto` (ruolo per slot glTF da nomi materiale/texture/catalogo, atlanti protetti, materiali condivisi per il batching, ORM dalle mappe separate, immagini GLB estratte, vento della vegetazione solo sulle piante vere), `assign` (materiali + vento sul livello), `make` (39 preset: vetro, acqua, car paint, pelle, stoffa, neon...), `check` (anteprima del Material document con modelli on/off: nero, piatto o identico = fallito) | nuovo `scripts/nc_mat.py` |
| Provato su HEAD: kit KayKit → 8 materiali condivisi, 81 entità con materiali e 53 con vento; 7 shading model renderizzati per la prima volta (OpenGL): Car Paint, Cloth, Water e Skin funzionano; **Glass sospetto** (la sfera sparisce, nessun riflesso), segnalato in M1 | `docs/samples/nucleon-materials-*.jpg` |
| Lookdev Nucleon = `auto` → `assign` → `make` → `check` → `look` | `nucleon-loop.md` §8a, `workers.md` PHASE lookdev, `styles.md` |
| Benchmark: H10 costo del sistema materiali (models/sets/WPO/layers/deferred off, con screenshot), FSR 3 Quality/Performance in H9 | `tools/nucleon-bench` |
| Snapshot API aggiornato (601 nomi legacy: MaterialParameters, PostMaterial, RuntimeVirtualTexture) | `scripts/data/nucleon-api.json` |
| A1 ancora presente su `5cf63bb` (anche con i materiali assegnati); C1 non corretto | `docs/NUCLEON-ENGINE-NOTES.md` |

## 2026-10-21 (3): Nucleon bench, then execution plan

| Cosa | Dove |
|---|---|
| Kit benchmark: driver in gioco (camera, CSV per frame, marcatori), matrice di config (una modifica contro base), ipotesi H1-H9 con regole di verdetto | nuovo `tools/nucleon-bench/` (`bench.py`, `gds_bench.lua`, `configs.json`) |
| `analyze`: p50/p95/p99, hitch e correlazione con caricamenti di pagine/texture, passate GPU per scenario, contatori dell'engine, frame più lenti → REPORT.md | `bench.py analyze` |
| `plan`: EXECUTION-PLAN.md con i brief K1-K5 (bug noti) e solo le H confermate, in ordine di guadagno misurato, ciascuno con un prompt pronto per Claude Code | `bench.py plan`, `briefs.json` |
| A1 isolato su HEAD: il colpevole è il percorso **GPU-driven** (`NC_GPU_DRIVEN=0` corregge; basecolor, `NC_GD_COUNT=0` e `NC_PREPASS_MASKED=0` no) | `docs/NUCLEON-ENGINE-NOTES.md`, `docs/samples/nucleon-bug-a1-isolation.jpg` |
| Note dell'engine riviste con la lettura del codice (A2-A5, B1-B6, C1-C2); nuovi A6 (contatori del profiler con nomi pendenti: crash con `os.exit`) e A7 (readback di `makeSrgbCopy` dopo ogni restream) | `docs/NUCLEON-ENGINE-NOTES.md` |

## 2026-10-21 (2) — Nucleon: mondi, kit, lint in Play, sessione, capture, telemetria, bug dell'engine

Tutto provato sull'editor compilato da `main@d8e49bc` (Linux/Xvfb). Demo: `docs/samples/nucleon-glade-*.jpg` (terreno generato, foresta,
villaggio KayKit CC0, cielo e luce del tramonto; lint in Play 0 problemi su 275 oggetti).

| Cosa | Dove |
|---|---|
| `ncli cycle` (lock → build → lint → foto inquadrata → unlock in una chiamata), cache delle build (spec + catalog + builder invariati = salta) | `scripts/ncli.py` |
| Lint in Play: terreno vero, pendii, prop impilati, oggetti fuori dal terreno (`noGround`), via Raycast; zero falsi positivi sui test piantati | `ncli lint --play` + `templates/nucleon/Content/Scripts/gds_probe.lua` |
| Sessione persistente: un editor aperto per tutti i comandi (`serve` / `session-stop`) | `ncli serve` |
| Kit catalog offline (glTF/GLB/OBJ misurati, ruoli, modulo), stanze di pezzi kit, `kitScale`, pezzi per ruolo/nome, `origin` z `"ground"` | nuovo `scripts/nc_gds.py` |
| Mondi seedati: terreno/isola (heightmap, layer, foliage, radure, scatter all'altezza vera, acqua), dungeon/caverna, villaggio; blocco `reference` dai riferimenti; `look` (luce, cielo, nebbia, sole) | nuovo `scripts/nc_world.py` |
| `lua-check` (chiamate sconosciute con suggerimento, numero di argomenti delle native, sintassi) + `api-refresh`; `tools-check` (MCP cambiato) | `ncli.py`, `scripts/data/*.json` |
| Checkpoint incrementali (`ncli affected`), suite intera prima di art-review/playtest/slice | `task-decomposition.md` |
| Catture store/trailer in Play vero con GIF e manifest `produced: real-play` | `ncli capture` + `gds_capture.lua` |
| Telemetria opt-in del playtest + report | `gds_telemetry.lua`, nuovo `scripts/telemetry_report.py` |
| Budget di performance nel gate (`t.perf`, `play-test --fps`) | `gds_test.lua`, `playtest.md`, `gates.md` 25b |
| Repro-first dei bug (test che fallisce prima e passa dopo) + bisect sui checkpoint | `templates/nucleon/.../test_bug_template.lua`, nuovo `scripts/gds_bisect.py`, `workers.md`, `gates.md` 25a |
| Bug e lacune dell'engine con riproduzione (A1: modelli piccoli ripetuti col materiale sbagliato; MCP senza landscape/lighting; registry delle native) | nuovo `docs/NUCLEON-ENGINE-NOTES.md` |

## 2026-10-21 — Nucleon Engine, engine scelto dall'utente, run sempre continua e parallela

Fonti: sorgente `NucleonEngine/NucleonEngine` (`main`, `editor/src/mcp/*`, `docs/editor/MCP.md`, `docs/api/NATIVES.md`, `docs/engine/GAME_UI.md`, sample `ThirdPersonDemo`). Verificato sull'editor compilato da `main` (Linux, Xvfb, llvmpipe): `ncli` ping / build ×2 (rebuild in place) / lint `issues: 0` / shot / play-test, harness Lua PASS in Play In Editor con `SimulateKey`, `html2rml.py` aperto nell'UI editor senza errori. Non verificati: Windows/D3D12, trasporto HTTP con l'editor del proprietario, mondo landscape+foliage.

| Cosa | Dove |
|---|---|
| Engine = scelta dell'utente alla domanda Q0, definitiva; lo stile non sceglie più l'engine; contratto adapter a 8 verbi (ping, build, lint, shot, test, play, lock, package) per unity / nucleon / unreal / godot | nuovo `references/engines.md`, `gdd-interview.md` Q0, `styles.md`, `tool-stack.md`, `gdd-template.md`, `config/defaults.json` (`engines.preferred`) |
| Ponte Nucleon: MCP dell'editor via HTTP (token letto da `editor-settings.lua`) o stdio; batch JSON-RPC in un round trip; screenshot su file (mai base64 nel contesto); i worker non caricano gli schemi MCP | nuovo `scripts/ncli.py` |
| Layer deterministico Nucleon: spec JSON (stanze con varchi porta/finestra, pezzi, scatter seedato, shape, luci, player start) → entità sotto `BP_<nome>`, rebuild in place, `docs/lint/build-<nome>.json`; lint (kill Z, duplicati, floating/underground, primitive, errori di log) | `ncli build`, `ncli lint`, `templates/nucleon/specs/house_example.json` |
| Test dei verbi in Lua con input vero (`SimulateKey`), righe `GDS-TEST`, `GDS-FEEL` per la feel baseline; `play-test` si ferma al `DONE` | nuovo `templates/nucleon/Content/Scripts/gds_test.lua` + `test_move.lua`, `playtest.md` |
| UI: mock real-world-design → RmlUi (`.rml` + `.rcss` + `.preview.lua`, report dei cambi) | nuovo `scripts/html2rml.py`, `ui-bridge.md` §3b |
| Loop completo Nucleon (requisiti, coordinate Z up vs file Y up, fasi, regole) | nuovo `references/nucleon-loop.md`, PHASE project in `workers.md` |
| Godot minimo | nuovo `references/godot-loop.md` |
| Sessione sempre continua: tolti `session-mode`, `hard-stop`, banner e cambi chat; `/resumegame` solo dopo un crollo | via `references/session-cuts.md`; `context-management.md`, `SKILL.md`, `command/*.md` |
| Scheduler a ondate: tutti i task pronti con `OWNS` disgiunti in un messaggio (subagent in background, `parallel.maxWorkers` = 6), posto libero riempito subito, track ART / CODE / UI / AUDIO / QUALITY in parallelo, lock generico dell'editor | `workers.md` "Scheduler a ondate" e "Un solo editor: lock", `task-decomposition.md`, `pipeline.md`, colonna `Ed` in `templates/GAME_TASKS.md` |
| UI: varianti di tutte le schermate in parallelo, **una sola domanda** all'utente, implementazione in parallelo | `workers.md` PHASE ui-* |
| Doctor e installer: NucleonEditor (`paths.nucleon`), runtime accanto, `ncli ping` sul progetto, harness presente | `scripts/doctor.ps1`, `install.ps1`, `INSTALL.md` |

## 2026-10-21 — Nuova skill `fivem-sollumz` (Blender + Sollumz -> risorsa FiveM)

Fonti: sorgente Sollumz v2.9.0 e wiki ufficiale (GitHub Sollumz/Sollumz, Sollumz/wiki), docs Cfx.re
(citizenfx/fivem-docs: asset manual parti 1-9, legacy vs enhanced, DUI, resource manifest, Alchemist), dichiarazioni
native (citizenfx/natives, citizenfx/fivem ext/native-decls), CodeWalker.Core.

| Cosa | Dove |
|---|---|
| Libreria Python deterministica su Sollumz (drawable, shader, collisioni, LOD, luci, scheletri, YCD, UV anim, porte, fragment, YTD, YTYP, audit, export headless) | `fivem-sollumz/scripts/sz_fivem.py` |
| Spec JSON -> build -> export -> risorsa | `scripts/build_from_spec.py`, `templates/spec_examples/all_types.json` |
| PNG -> DDS con mipmap (texconv o Pillow), normal OpenGL -> DirectX, palette tint | `scripts/dds_convert.py` |
| Risorsa FiveM: `stream/` Gen8 + `stream_enhanced/` Gen9, Lua (spawn, anim, DUI, porte, tint, state bag) | `scripts/make_resource.py`, `templates/resource/` |
| Convertitore XML -> binario, Gen8 -> Gen9, `--info` di verifica (CodeWalker.Core) | `tools/CwXmlToBin/` |
| Ricette e riferimenti (statico, fisico/fragment, animato + trigger, DUI, porte, luci, mappa, veicoli/vestiti/armi) | `references/` |
| Self-test end-to-end (8 asset, verifica binari) | `scripts/selftest.py` |

## 2026-10-18 — Iterazione dopo la slice e contratto con `game-launch-strategist` (gdl-v2)

Fonti: `BuffetPanic/docs/gates/49-56*.md`, `launch/fg/waves/w09-*` (mappa del gioco, schermate, run a tempi, proposte, limite beta, sintesi), `launch/TODO.md`, `launch/00-intenzioni.md`, `launch/issue_status.json`, memoria delle decisioni del proprietario. Obiettivo: due skill complete da sole che collaborano senza attrito.

### Design review dentro la skill
| Lezione | Dove |
|---|---|
| Mappa totale del gioco dal codice (con file e discrepanze design ≠ codice), mappa delle schermate con raggiungibilità e voto evidente/trovabile/nascosta, run simulate a tempi con segni `[MORTO] [TOP] [FRUSTRA] [ABBANDONO] [CONFUSO] [TROPPA-UI:n] [SPIRALE]`, prima e dopo ogni gate | nuovo `references/design-review.md`, `workers.md` PHASE design-review, `pipeline.md` 15-18 |
| Controllo "funzione orfana" dopo ogni redesign (un negozio curato rimasto senza ingresso dopo il redesign del furgone) | `design-review.md` §2.3, `quality-baseline.md` §7, `gates.md` §24, SKILL.md hard rules |
| Script `design_review.py` (stdlib): `screens` (clic dalla radice, orfani, un solo ingresso, `--before` = chi ha perso l'ingresso), `runs` (secondi morti, tratto più lungo senza picco, UI insieme, `--before` = delta del gate), `self-test` | nuovo `scripts/design_review.py` |

### Gate di iterazione
| Lezione | Dove |
|---|---|
| Header leggibile da macchina (data, chiavi chiuse/da verificare, TODO, file, foto, rischi introdotti, cosa provare, scelte di design con `decided_by`, salvataggi, build) + sezione "Per il proprietario" | `launch-link.md` §7, nuovo `templates/gate.md`, `gates.md` §17 |
| Fix verificato nella meccanica vera in gioco normale, da ogni lato (un colpo che "non fa niente" di lato o da dietro), foto guardate, backup/ripristino dei salvataggi, niente build non chieste, niente suite di test se il proprietario prova da sé | `workers.md` PHASE iterate-gate + Contratto 9, `gates.md` §18-21, SKILL.md hard rules |
| Scelte di design cambiate dette chiaro; mai "il proprietario ha chiesto" senza fonte (un worker aveva attribuito al proprietario una sua scelta) | `workers.md` Contratto 7, `templates/worker-report.md` "Scelte di design", `gates.md` §22, `templates/DECISIONI.md` |
| Giro di regressione: ogni gate elenca i rischi di gameplay introdotti; la prossima ondata li ricontrolla (l'abbraccio dello zio del gate 56 è diventato un problema nuovo nell'ondata 9) | `launch-link.md` §8, `gates.md` §23 |
| Decisioni mai riaperte in silenzio: solo proposte etichettate "Riapre la decisione" con prove | `launch-link.md` §4, `workers.md` Contratto 8, `context-management.md`, `templates/DECISIONI.md`, SKILL.md |

### Contratto con `game-launch-strategist` (`references/launch-link.md` v2, testo condiviso)
| Cosa | Dove |
|---|---|
| Rilevamento reciproco e modi `linked` / `launch-only` / `solo`, ognuna completa da sola | `launch-link.md` §1, `gate_link.py detect` |
| Parole senza ambiguità (gate di sviluppo ≠ cancello Go/No-Go, `gate_dev`, chiave, `P-wNN-n`) e proprietà dei file | §2-3 |
| Lancio → sviluppo: pacchetto dell'ondata, quando una proposta è approvata, piano dei gate (un gate = blocco coerente, in ordine, con le ore) | §5, nuovo `templates/gate-plan.md`, `task-decomposition.md`, `templates/GAME_TASKS.md` (`fg:wNN key:… gate:NN`) |
| Sviluppo → lancio: `gate_link.py check` / `apply-status --write` / `todo --run` / `since --out docs/design-review/changes-since-wNN.md` (cambi, `fixes` per il JSON dell'ondata, rischi, cosa provare) | §6, nuovo `scripts/gate_link.py` (stdlib, `self-test`), `command/resumegame.md`, `context-management.md` |
| Vocabolario comune per mappa, schermate e run, così lo stesso script legge i file di tutte e due le skill | §9 |
| Controllo di mercato precoce (era §3) | §10 |

Altro: SKILL.md (descrizione, tabella strumenti, parent passo 11, hard rules), `README.md`.
Lato `game-launch-strategist`: le modifiche corrispondenti sono elencate a parte (copia identica del contratto in `references/dev-link.md` + adattamenti di wave_kit, sintesi, TODO, issue_status).

## 2026-10-17 — Lezioni dal progetto Buffet Panic!

Fonti: `BuffetPanic/docs/gates/45-52*.md`, `launch/00-intenzioni.md`, "Decisioni prese" di `launch/TODO.md`, `launch/fg/waves/w07-w08-sintesi.md`. Gruppi scelti dal proprietario: A+B, D, E (il gruppo C, pattern tecnici, è escluso; resta solo la regola su `Temp/`/`Library/`).

### A. Regressioni che nessuno vedeva
| Lezione | Dove |
|---|---|
| Sim di feel del verbo core nella **geometria vera** del livello (porte, muri, angoli, sprint); baseline in `docs/tests/feel-baseline.json`; peggio della baseline = gate FAIL salvo ok del proprietario (gate 46 → 49: vassoio nei muri, sim verde in scena vuota) | `references/playtest.md` § Feel in scena reale, `gates.md` §12, `workers.md` PHASE feel-baseline + playtest, `task-decomposition.md` (checkpoint), `templates/feel-baseline.json`, SKILL.md hard rules + slice |
| Gli helper di cattura non alterano le regole; set-up con seed/sistemi veri; ogni cattura etichettata `produced:`; controllo "catture vs regole" prima di playtest/store (gate 48 → 50: timer tenuto fermo dallo script = bug fantasma) | `playtest.md` § Catture fedeli alle regole, `gates.md` §13, `quality-baseline.md` §6, SKILL.md hard rules |
| Mai deliverable in `Temp/` o `Library/` di Unity (footage quasi perso) | `workers.md` § Contratto 6, `gates.md` §14, `pipeline.md` anti-pigrizia, SKILL.md hard rules |

### B. Worker
| Lezione | Dove |
|---|---|
| Proprietà dei file: `OWNS` in ogni prompt, stop e report prima di scrivere un file non suo o cambiato; worker paralleli senza file in comune; un solo worker con l'Editor (lock invariato), anche per gli helper | `workers.md` § Contratto 1-2 + lock, SKILL.md isolamento |
| Recinto DO / DO NOT + report a formato fisso (fatto con evidenza, deviazioni, aperto, file cambiati); report diverso dal brief = FAIL e rilancio | `workers.md` § Contratto 3-4 + Retry, `gates.md` §15, `templates/worker-report.md`, `command/resumegame.md` |
| Avanzamento riprendibile `docs/progress/<worker>.md`, aggiornato a ogni passo, letto per primo al rilancio (`RIPRENDI da PROGRESS`) | `workers.md` § Contratto 5, `task-decomposition.md` lifecycle 5, `context-management.md`, `templates/progress-checkpoint.md`, `command/resumegame.md` |
| `DECISIONI.md`: il parent aggiunge ogni decisione con data; ogni prompt dice "leggilo per primo, non riaprire" (lingue, stile, Steam Deck, quote riaperte più volte) | `context-management.md` § DECISIONI.md, `task-decomposition.md` § Owner decisions + lifecycle 6, `workers.md` § Contratto + PHASE project, `gdd-interview.md` lock, `gates.md` §16, `templates/DECISIONI.md`, SKILL.md |

### D. Cose che devono esistere dall'inizio (domande del GDD con default)
| Lezione | Dove |
|---|---|
| Nuovo **blocco E** dell'intervista (Q25-Q31) con default consigliati; ESSENZIALI dichiarati, non chiesti: rimappatura tastiera + pad con ripristino, dimensione testo, movimento ridotto, transizioni ≤ 0,5 s saltabili, hover/focus su ogni pulsante | `references/gdd-interview.md` blocco E, `gdd-template.md` § Quality baseline |
| Dettaglio di accessibilità, qualità UI (notifiche brevi, una alla volta, fonte unica dei numeri + controllo), onboarding (≤ 4 passi, suggerimenti alla prima occasione, comparsa graduale), localizzazione da subito (CSV `key,context,max_chars,<lingue>`, fallback CJK/RTL, niente stringhe nel codice), kit playtest (telemetria CSV opt-in locale, build profilo pulito, README tester), tool di cattura store (HUD full/minimal/none, seed fissi, screenshot + frame GIF) | nuovo `references/quality-baseline.md`, `ui-bridge.md` §4, `workers.md` PHASE baseline-* + systems |
| Task corrispondenti (LOC, A11Y, UIQ, ONB, FEEL, PKIT, CAP) con il momento giusto e l'evidenza | `task-decomposition.md` § Quality baseline tasks + budget, `pipeline.md` |
| README per i tester | `templates/TESTER_README.md` |

### E. Link con `game-launch-strategist`
| Lezione | Dove |
|---|---|
| Ondate del focus group → task con tag `fg:wNN key:<chiave>` (solo problemi aperti accettati dal proprietario); chiusura riportata in `launch/issue_status.json` (`status`, `note`, `gate`, `resolved`) | nuovo `references/launch-link.md` §2, `task-decomposition.md`, `templates/GAME_TASKS.md`, `context-management.md` /resumegame, `command/resumegame.md` |
| Controllo di mercato precoce offerto (non imposto) dopo il lock del GDD: modalità Mirata (posizionamento + comparabili + panel rapido) | `launch-link.md` §3, `gdd-interview.md`, `pipeline.md` 3m, SKILL.md parent 2 |
| Decisioni condivise: `launch/00-intenzioni.md` e "Decisioni prese" di `launch/TODO.md` | `launch-link.md` §1, `context-management.md`, `templates/GAME_CONTEXT.md`, SKILL.md |

Altro: `command/game.md` e `README.md` citano i blocchi A-E e le fasi nuove.
