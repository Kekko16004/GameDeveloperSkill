# Checkpoint — HARD STOP, non consiglio

Memoria su disco: `GAME_CONTEXT.md`, `GAME_TASKS.md`, `art/blueprints/PLAN.md` + `*.json` (il livello), `art/kit-catalog.json` (misure kit), `docs/lint/*.json` (stato scena), `docs/gates/*.md` (cosa e PASS). Tagli sessione: [session-cuts.md](session-cuts.md).

In `session-mode: continuous` il taglio non serve: il parent lancia il worker successivo. In `hard-stop` vale tutto quanto segue.

## Quando tagliare

Non “se il contesto pesa”. Taglia **sempre** dopo la macrotask corrente. Vedi tabella in session-cuts.md.

Ogni 3 level-build (o hero-asset) nella stessa chat: STOP anche se la lista non e finita (solo hard-stop).

## Cosa scrivere prima dello STOP

1. `GAME_TASKS.md`: `[x]` + path evidenza.
2. `GAME_CONTEXT.md`: manifest, script, oggetti, **Prossimo Task Immediato** una riga.
3. Banner HARD STOP (testo fisso in session-cuts.md).

## `/resumegame`

Nuova chat. Leggi `GAME_CONTEXT.md`, `GAME_TASKS.md`, `docs/gates/` (solo i nomi + status) e, se la fase e art, `art/blueprints/PLAN.md` + `art/kit-catalog.json` (solo `suggestedModule`/`notes`). Esegui **una** macrotask (hard-stop) o continua la catena (continuous). Non rifare GDD.
