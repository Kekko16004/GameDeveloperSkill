# Playtest

Una feature non e spedita finche **non gira**. “Dovrebbe funzionare” in chat = 0.

## FAIL automatici (slice rossa)

- Nessun Main Menu: il giocatore spawna gia nel livello
- HUD senza frase obiettivo visibile nello screenshot
- `GDS.SceneLint.RunJson()` con `issues > 0` (sepolti, flottanti, senza collider, materiali rosa)
- Game View con primitives Unity visibili (cubo/capsula default) o nessun blueprint in `art/blueprints/`
- Nessun `Global_Volume` / scena piatta senza fog e ombre (lookdev saltato)
- Mix di due famiglie kit (Kenney + KayKit) visibile nello stesso shot
- Console errori
- Test movimento non eseguito (manca job_id / output in `docs/gates/`)
- Suite di feel nella scena vera peggiore di `docs/tests/feel-baseline.json` senza ok del proprietario in `DECISIONI.md`
- Screenshot di playtest/store prodotti da un helper che ha alterato lo stato (timer fermo, punti aggiunti, eventi piazzati a mano)
- Manca un ESSENZIALE della baseline (rimappatura, dimensione testo, movimento ridotto, transizioni, hover/focus: [quality-baseline.md](quality-baseline.md))

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

Nucleon: un `Content/Scripts/test_<verbo>.lua` per verbo con l'harness `gds_test.lua` ([nucleon-loop.md](nucleon-loop.md) §6): input vero con `t.hold("W", 1)` / `t.tap("E")` (`SimulateKey` passa da `Config/Input.lua` e dallo script del pawn), numeri nel messaggio di FAIL. Si lancia con `NC_GDS_TEST=1` nell'ambiente dell'editor e `ncli play-test --seconds 120 --expect "GDS-TEST DONE pass=<n> fail=0" --shot screenshots/play.png` (si ferma da solo al `DONE`). Build pacchettizzata: `NC_GDS_TEST=1 NC_GDS_TEST_EXIT=1` → exit code 0/3.

## Feel in scena reale (suite di regressione)

Lezione Buffet Panic! (gate 46 → 49): la "body clearance" del gate 46 spingeva il vassoio nei muri e la pila esplodeva sulle porte. La sim del vassoio è rimasta verde (8/8) perché girava in una scena vuota, senza muri.

- Le sim di "feel" del verbo core girano nella **geometria vera del livello**: porte, muri, angoli, sprint, stop vicino a un muro. Una scena di test vuota non vale come prova.
- Input pilotato e seed fisso; ≥ 6 casi × 8 run; output JSON (Nucleon: `t.feel({...})` → righe `GDS-FEEL {json}` lette da `ncli play-test --grep GDS-FEEL --verbose`).
- Baseline in `docs/tests/feel-baseline.json` ([template](../templates/feel-baseline.json)), scritta dalla fase feel-baseline.
- **Ogni gate** che tocca fisica, controller, tuning, collider o la scena del livello rilancia la suite e incolla `feel: {"baseline":..., "worse":[...]}`. Un caso peggiore oltre la `tolerance` = **FAIL**, a meno che il proprietario lo approvi: allora riga in `DECISIONI.md`, voce in `approvedRegressions` e baseline aggiornata.
- Un miglioramento si registra solo aggiornando la baseline nello stesso gate.

## Catture fedeli alle regole

Lezione Buffet Panic! (gate 48 → 50): lo script di cattura teneva fermo il timer (l'HUD nascondeva l'orologio → "bug" fantasma), aggiungeva mance senza piatti, piazzava disturbi a mano contro le regole di estrazione. I tester simulati hanno segnalato problemi che il gioco non aveva.

- Gli helper di screenshot/clip sono **in sola lettura sulle regole**: possono muovere la camera, cambiare modo HUD, mettere in pausa *dopo* lo stato, mai alterare timer, punteggi, economia, spawn o estrazioni.
- Lo stato si prepara con **seed veri o sistemi veri** (giocare fino al momento, `--seed`, debug spawn che passa dalle stesse regole del gioco).
- Ogni cattura ha un'etichetta (in `captures/<data>/manifest.json` o `screenshots/000-index.md`): `produced: real-play | seed:<n> | debug-spawn:<rule> | staged:<cosa>`.
- Prima che le catture vadano al playtest, a un focus group o allo store: controllo **"catture vs regole"**, una riga per immagine: HUD coerente (orologio, numeri, quota), eventi possibili con le regole, niente prompt se il modo è `minimal/none`. Una `staged` non va allo store senza ok del proprietario.
- Un "bug" visto solo in una cattura si riproduce in Play prima di aprire un task.

## Report

`docs/playtest.md` tabella verb / test / result / screenshot / console.
`screenshots/000-index.md` aggiornato.
Gate: `docs/gates/13-playtest.md` (con la riga `lint:`).
