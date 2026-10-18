# Changelog

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
