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

**Ogni input della tabella controlli (verbi del GDD, Q4) è provato dal percorso vero** (`t.hold`/`t.tap`, l'iniezione di input del motore), non chiamando la funzione: la rotella del mouse **e** i tasti numerici cambiano davvero arma (cambia l'arma attiva, non solo un'animazione), la pausa si apre e si chiude, la ricarica parte dal tasto. Se l'harness non sa produrre un input, è un `engine_gap:` nel gate, mai un input non testato. Motivo: un test che chiama la funzione passa anche quando l'input vero non arriva.

Unity: `run_tests`. Fallback `unity test <project> --mode EditMode --timeout 300 --format json`.
Play Mode input: MCP inject, altrimenti TerminalMCP `window: Unity` + `shot: true`.

Nucleon: un `Content/Scripts/test_<verbo>.lua` per verbo con l'harness `gds_test.lua` ([nucleon/tests.md](nucleon/tests.md)): input vero con `t.hold("W", 1)` / `t.tap("E")` (`SimulateKey` passa da `Config/Input.lua` e dallo script del pawn), numeri nel messaggio di FAIL. Si lancia con `NC_GDS_TEST=1` nell'ambiente dell'editor e `ncli play-test --seconds 120 --expect "GDS-TEST DONE pass=<n> fail=0" --shot screenshots/play.png` (si ferma da solo al `DONE`). Build pacchettizzata: `NC_GDS_TEST=1 NC_GDS_TEST_EXIT=1` → exit code 0/3.

## Feel in scena reale (suite di regressione)

Lezione Buffet Panic! (gate 46 → 49): la "body clearance" del gate 46 spingeva il vassoio nei muri e la pila esplodeva sulle porte. La sim del vassoio è rimasta verde (8/8) perché girava in una scena vuota, senza muri.

- Le sim di "feel" del verbo core girano nella **geometria vera del livello**: porte, muri, angoli, sprint, stop vicino a un muro. Una scena di test vuota non vale come prova.
- Input pilotato e seed fisso; ≥ 6 casi × 8 run; output JSON (Nucleon: `t.feel({...})` → righe `GDS-FEEL {json}` lette da `ncli play-test --grep GDS-FEEL --verbose`).
- Baseline in `docs/tests/feel-baseline.json` ([template](../templates/feel-baseline.json)), scritta dalla fase feel-baseline.
- **Ogni gate** che tocca fisica, controller, tuning, collider o la scena del livello rilancia la suite e incolla `feel: {"baseline":..., "worse":[...]}`. Un caso peggiore oltre la `tolerance` = **FAIL**, a meno che il proprietario lo approvi: allora riga in `DECISIONI.md`, voce in `approvedRegressions` e baseline aggiornata.
- Un miglioramento si registra solo aggiornando la baseline nello stesso gate.

## Budget di performance (gate)

Il GDD fissa `targetFps` (Q22). **La performance si misura dal primo giocabile e a ogni gate, non alla fine**: ogni gate con una scena che si gioca misura il frame nella scena vera (la camminata del livello), con **vsync spento** (Nucleon `NC_D3D12_VSYNC=0`; Unity `QualitySettings.vsyncCount = 0` e `Application.targetFrameRate = -1`: con vsync un frame da 16 ms nasconde il costo vero) e incolla `perf:` nel gate; ogni gate di scena aggiunge anche `scene: {instances, drawCalls, outOfReach}` ([gates.md](gates.md) 26). **Mai chiamare «giocabile» qualcosa senza un tempo di frame.** Nucleon `t.perf("<nome>", 10, "W")` in un `test_perf.lua` (camminata nel livello) + `ncli play-test --fps <targetFps>` → p50/p95/p99/max ms; p95 sopra `1000/targetFps` = FAIL salvo ok del proprietario (riga in `DECISIONI.md`). Unity: Profiler/`FrameTimingManager` nella stessa camminata. Solo su GPU vera: con rendering software (CI, Xvfb, llvmpipe) il numero non vale e il gate lo dice (`perf: skipped: software renderer`). Nucleon limita il dt a 100 ms: un p95 di 100 ms vuol dire "≤ 10 fps", non 100 ms esatti.

## Controllo del look al primo giocabile

Appena la scena e' giocabile, il parent guarda frame veri del gioco dalla camera di gioco (non anteprime di asset) e li confronta con la reference board di stile ([art-direction.md](art-direction.md), [styles.md](styles.md)): se non si riconosce lo stesso gioco, torna a lookdev prima di costruire altro.

## Passeggiata del parent (prima di dire al proprietario «la build si apre»)

I PASS dei worker non bastano: una partita vera in prima persona ha trovato ciò che i test verdi non vedono (cambio arma da un input, arma senza inerzia, frame spesi in zone irraggiungibili). Il **parent stesso**, sulla build che consegna, con input veri e guardando i frame (dietro il lock dell'editor):

1. **cammina** per tutto il percorso giocabile (avanti, laterale, salto/accovacciata se nel GDD) e legge il frame time (`perf:`, vsync spento);
2. **guarda** attorno col mouse: sway visibile, niente clipping, niente zone vuote o rotte;
3. **ogni verbo del GDD**; per un FPS: spara con ogni arma, ricarica, mira (ADS), cambia arma con **ogni** input (rotella e tasti numerici), pausa e ripresa ([genres.md](genres.md) regole FPS);
4. uno screenshot per passo, **letto** (una riga su cosa mostra), tabella passo / input / esito / foto in `docs/gates/playthrough-NN.md`.

Un passo rosso = niente «apri». Un input che non si riesce a produrre si dice al proprietario (`engine_gap:`), non si salta. Vale dopo ogni gate di iterazione che cambia controlli, armi o livello.

## Telemetria del playtest (kit di playtest, opt-in)

Nucleon: `Content/Scripts/gds_telemetry.lua` (`ncli setup`): registra solo con il consenso del giocatore (`exports.gds_telemetry:SetOptIn(true)` da un prompt al primo avvio o dalle opzioni) o con `NC_GDS_TELEMETRY=1` nelle build dei tester; CSV locale in `Saved/telemetry/` (posizione ogni 2 s, idle, quit, eventi del gioco `exports.gds_telemetry:Log("death", {cause = "spikes"})`). I file tornano a mano (canale scelto al Q29). `python SKILL/scripts/telemetry_report.py <cartella> --out docs/playtest/telemetry.md --json docs/playtest/telemetry.json`: dove si muore e perché, dove si smette, tempo al primo obiettivo, zone mai visitate. Il JSON è "test reale" per game-launch-strategist (mai mescolato con le critiche simulate).

## Catture per store e trailer

Nucleon: `ncli capture plan.json` (harness `gds_capture.lua`) in Play vero: camera (`position`/`lookAt`/`fov`, `follow`), tasti premuti come un giocatore, HUD nascosto, sequenze di frame → GIF (con Pillow). `manifest.json` etichetta ogni file `produced: real-play`. Dall'editor la foto è la vista di gioco (MCP); per le misure da store (1920×1080) `ncli capture plan.json --write-only <cartella del gioco pacchettizzato>` e si avvia il gioco.

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
