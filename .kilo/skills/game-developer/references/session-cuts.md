# Session cuts — configurabili da intervista GDD (session-mode)

Il contesto vive su disco (`GAME_CONTEXT.md`, `GAME_TASKS.md`, `art/blueprints/*.json`, `art/kit-catalog.json`, `docs/lint/*.json`, `docs/gates/*.md`): un worker nuovo ricostruisce lo stato da quei file in < 2k token, quindi anche un host debole riparte senza rileggere chat.

La gestione del contesto dipende dalla modalità scelta in `GDD.md` (domanda 14 dell'intervista):
- **`continuous`** (**Consigliato per Claude Code e Kilo Code** con subagents): i subagents isolati eseguono i compiti con contesti dedicati. Il parent aggiorna `GAME_TASKS.md` e `GAME_CONTEXT.md` come checkpoint, ma **non si ferma** e prosegue automaticamente.
- **`hard-stop`** (**Consigliato per Antigravity** e ambienti monochat senza subagents): blocco rigido obbligatorio a ogni macrotask con cambio chat forzato per non saturare la sessione.

## Comportamento in modalità HARD STOP (`session-mode: hard-stop`)

Se `session-mode: hard-stop` è attivo in `GDD.md`, dopo **ogni macrotask** il parent:

1. Aggiorna `GAME_TASKS.md` e `GAME_CONTEXT.md` (puntatore al prossimo task).
2. Stampa ESATTAMENTE questo banner (niente parafrasi morbide):
3. **FERMA**. Non lanciare il worker della fase successiva. Non “faccio ancora un prop”. Non “chiudo lo slice”.

```
======================================================================
[HARD STOP — NUOVA CHAT OBBLIGATORIA]
Completato: <PHASE / TASK-id>
Prossimo:   <PHASE / TASK-id>
File: GAME_CONTEXT.md + GAME_TASKS.md

Apri una NUOVA chat nella cartella del progetto Unity e scrivi:
/resumegame

Continuare in QUESTA chat e VIETATO. Lo slice verra marcato FAIL.
======================================================================
```

## Macrotask (una per sessione, poi STOP)

| id | cosa |
|---|---|
| gdd | lock GDD |
| project | attach/create |
| task-decomposition | GAME_TASKS + GAME_CONTEXT |
| greybox | shell ProBuilder/primitives da PLAN.md + move test |
| kit-fetch | download pack + `art/kit-catalog.json` |
| level-build | **UN** blueprint (max 3 nella stessa sessione, poi STOP) |
| hero-asset | batch fino a 3 hero prop (1 PNG ciascuno, poi STOP) |
| import-art | GLB residui → Unity + rebuild blueprint |
| lookdev | preset + palette + luci |
| characters | rig + animator + navmesh |
| systems | un blocco verbi, non tutto il GDD se >4 script |
| ui-main-menu | DesignerSkill: 3-4 varianti → STOP scelta utente → UXML |
| ui-hud | DesignerSkill: 3-4 varianti coerenti col menu → STOP scelta utente → UXML |
| ui-pause | DesignerSkill: 3-4 varianti coerenti col menu → STOP scelta utente → UXML |
| ui-gameover | DesignerSkill: 3-4 varianti coerenti col menu → STOP scelta utente → UXML |
| juice | SFX |
| playtest | QA |
| slice | recap gate |

`/game` fa al massimo **una** macrotask dopo il lock GDD, poi HARD STOP.
`/resumegame` fa al massimo **una** macrotask, poi HARD STOP di nuovo.

Eccezione unica: GDD interview (domande all’utente) puo stare nella stessa chat del lock. Appena lockato → STOP prima di greybox.

## Cosa NON e un motivo per continuare

- “il contesto e ancora ok”
- “faccio in fretta i 3 GLB”
- “l’utente ha detto procedi” (procedi = fai LA macrotask corrente, poi stop)
- “mancano 2 file, li butto giu”
- dichiarare slice PASS nella stessa chat del greybox

## Se l’utente insiste a continuare nella stessa chat

Rispondi una riga: `HARD STOP attivo. /resumegame in chat nuova.` Non implementare.
