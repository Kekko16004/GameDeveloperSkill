# Pipeline

Parent = dispatcher. Implementazione = worker. Dettaglio prompt: [workers.md](workers.md).

```
0 doctor                         parent
1-3 GDD interview + LOCK         parent parla; oppure worker gdd
4 project attach|create          worker project
5 task-decomposition             worker task-decomposition (GAME_TASKS.md + GAME_CONTEXT.md)
6 greybox + movement test        worker greybox
7a blender-asset x N props       worker per file (parallelo max 3)
7b import GLB                    worker import-art
7c level dressing                posizionamento coordinate scena
8 systems + test per verbo       worker systems
9a Main Menu UI Toolkit          worker ui-main-menu   <-- obbligatorio
9b HUD                           worker ui-hud
9c Pause                         worker ui-pause
9d GameOver                      worker ui-gameover
10 juice                         worker juice
11 playtest                      worker playtest
12 slice recap                   worker slice  (FAIL se un gate e rosso)
```

HARD STOP dopo ogni riga della pipeline (vedi session-cuts.md). Una macrotask per chat. `/resumegame` per la successiva.
`GDD.md` campo `phase:` aggiornato dal parent dopo ogni gate PASS.

## File gate

Ogni worker scrive `docs/gates/NN-name.md`:

```
phase: greybox
status: PASS|FAIL
evidence:
  - screenshots/010-greybox-play.png
  - run_tests job_id=...
notes: ...
```

Senza questo file la fase non e fatta. Chat “fatto” non conta.

## Anti-pigrizia

| Sintomo | Azione parent |
|---|---|
| Worker dice Blender ma mancano i 5 PNG o il GLB | retry. Cubi Unity = FAIL |
| Un solo PNG Blender (dump) | retry. Servono 5 screenshot |
| GLB < 15KB | retry. E un cubo |
| UI senza mock HTML real-world-design | retry ui. UXML a mano = FAIL |
| Gioco parte in FP senza menu | retry ui-main-menu. Slice bloccata |
| Screenshot illeggibile (mare di cubi, niente testo) | retry hud + playtest |
| Worker ha fatto 3 fasi in un turno | scarta il lavoro extra. Rilancia le fasi una a una |
| Contesto parent enorme | non implementare tu. Lancia il prossimo worker |

## Greybox vs art

Greybox = cubi OK, deve **giocarsi**. Art = sostituisce i cubi visibili del slice. Non dichiarare slice se i cubi sono ancora l’unica mesh.
