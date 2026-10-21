# Memoria su disco e ripresa

La run è **sempre continua**: il parent incatena i worker (subagent) senza fermarsi e senza cambi chat; il contesto del parent resta piccolo perché legge solo gate e JSON, mai i transcript dei worker. Memoria su disco: `GAME_CONTEXT.md`, `GAME_TASKS.md`, **`DECISIONI.md`** (decisioni del proprietario), `docs/progress/*.md` (avanzamento dei worker), `art/blueprints/PLAN.md` + `*.json` (il livello), `art/kit-catalog.json` (misure kit), `docs/lint/*.json` (stato scena), `docs/gates/*.md` (cosa e PASS), `docs/tests/feel-baseline.json` (feel del verbo core).

## DECISIONI.md (sempre)

Su Buffet Panic! decisioni già prese (lingue, stile, Steam Deck, quote) sono state riaperte più volte da worker che non le conoscevano: il proprietario si è stancato.

- Il progetto ha `DECISIONI.md` ([template](../templates/DECISIONI.md)), creato dalla fase project.
- Il parent **aggiunge ogni decisione del proprietario con la data** appena viene presa (anche detta in chat, anche "va bene così"): ID, data, area, decisione, fonte. Non si cancella: un cambio è una riga nuova che "sostituisce D-NNN".
- **Ogni prompt di worker** contiene: `DECISIONI=<path> — leggilo per primo; non riaprire e non segnalare come problema ciò che è deciso lì` ([workers.md](workers.md) § Contratto).
- Se esistono `launch/00-intenzioni.md` e la sezione "Decisioni prese" di `launch/TODO.md` (skill `game-launch-strategist`), valgono anche quelle ([launch-link.md](launch-link.md) §4): quelle che mancano in `DECISIONI.md` si copiano con `fonte:`.
- Una decisione si riapre **solo** come proposta etichettata (`Riapre la decisione: D-NNN — prove — proposta`) e diventa lavoro solo con una riga nuova del proprietario che "sostituisce D-NNN". Mai cambiata in silenzio, mai contata come problema.

## Avanzamento dei worker

Ogni worker tiene `docs/progress/<PHASE>-<TASK>.md` ([template](../templates/progress-checkpoint.md)) aggiornato dopo ogni passo. Se un worker muore (rate limit, chat chiusa), si rilancia con lo stesso prompt + `RIPRENDI da PROGRESS`: legge il file per primo e continua dal "Prossimo passo".

## Contesto del parent

- Il parent non legge mai l'output lungo di un worker: solo il report a formato fisso (workers.md) e i file del gate.
- Dopo ogni ondata del scheduler aggiorna `GAME_TASKS.md` + `GAME_CONTEXT.md` (puntatore "Prossimo Task Immediato" = la prossima ondata). Così una chat nuova o un crollo ripartono in < 2k token.
- Se il client compatta la conversazione, nessun problema: lo stato è su disco. Non si chiede mai all'utente di aprire una chat nuova.

## `/resumegame` (solo dopo un crollo: rate limit, client chiuso, PC riavviato)

Leggi `DECISIONI.md` (+ i file di launch se esistono), `GAME_CONTEXT.md`, `GAME_TASKS.md`, `docs/gates/` (solo i nomi + status), `docs/progress/` dei task `[/]` e, se la fase e art, `art/blueprints/PLAN.md` + `art/kit-catalog.json` (solo `suggestedModule`/`notes`). Se ci sono ondate nuove del focus group (`launch/fg/waves/*-sintesi.md` più recente dell'ultimo `docs/gates/plan-wNN.md`), scrivi il piano dei gate con le sole proposte approvate e mostra le altre al proprietario in una riga ciascuna ([launch-link.md](launch-link.md) §5). Se `docs/design-review/` è più vecchia dell'ultimo gate, il primo worker è la design review. Poi riprendi lo scheduler a ondate da lì e vai avanti fino alla slice. Non rifare GDD.
