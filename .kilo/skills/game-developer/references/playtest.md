# Playtest

Una feature non e spedita finche **non gira**. “Dovrebbe funzionare” in chat = 0.

## FAIL automatici (slice rossa)

- Nessun Main Menu: il giocatore spawna gia nel livello
- HUD senza frase obiettivo visibile nello screenshot
- Game View = solo primitivi Unity e `art/exports/` vuoto o GLB senza PNG Blender
- Console errori
- Test movimento non eseguito (manca job_id / output in `docs/gates/`)

## Verbi

| verb | test | live |
|---|---|---|
| move | posizione cambia | WASD + screenshot |
| jump | y sale da terra | Space |
| interact | flag / porta | E + prompt HUD visibile |
| pause | timeScale 0 + UI pause | Esc |
| win / fail | flag | schermata dedicata, non “ti svegli” |

Stesso commit: script + test.

Unity: `run_tests`. Fallback `unity test <project> --mode EditMode --timeout 300 --format json`.
Play Mode input: MCP inject, altrimenti TerminalMCP `window: Unity` + `shot: true`.

## Report

`docs/playtest.md` tabella verb / test / result / screenshot / console.
`screenshots/000-index.md` aggiornato.
Gate: `docs/gates/11-playtest.md`.
