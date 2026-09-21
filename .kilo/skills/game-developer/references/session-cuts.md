# Session cuts — meccanici, non a sensazione

Dopo N tool call il modello diventa pigro. Questa skill NON lascia scegliere. Taglia.

## HARD STOP (obbligatorio)

Dopo **ogni macrotask** il parent:

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
| greybox | cubi + move test |
| blender-asset | **UN** prop (max 3 prop nella stessa sessione, poi STOP comunque) |
| import-art | GLB → Unity |
| systems | un blocco verbi, non tutto il GDD se >4 script |
| ui-main-menu | DesignerSkill + UXML |
| ui-hud | DesignerSkill + UXML |
| ui-pause | DesignerSkill + UXML |
| ui-gameover | DesignerSkill + UXML |
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
