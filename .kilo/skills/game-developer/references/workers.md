# Workers — un job, un cervello, zero pigrizia

Il parent **non implementa**. Lancia `Task` (`subagent_type: general`, `background: false`). Ogni worker riceve SOLO il prompt sotto, più 6 righe di contesto. Niente transcript precedente, niente “poi faccio anche la UI”.

Se un worker chiude senza i file del gate, il parent **rilancia lo stesso worker** (stesso prompt + “GATE ROSSO: manca X”). Max 2 retry. Poi FAIL visibile all’utente.

## Contesto minimo (le uniche 8 righe per ogni worker)

```
PROJECT=<abs path Unity/Godot>
GDD=<abs path GDD.md>
CONTEXT=<abs path GAME_CONTEXT.md>
TASKS=<abs path GAME_TASKS.md>
SKILL=<abs path game-developer/>
PHASE=<id>
ENGINE=unity|godot
STYLE=<from GDD>
```

Vietato incollare conversazioni, screenshot chat, o “abbiamo già fatto greybox”. Il worker rilegge `GDD.md`, `GAME_CONTEXT.md`, `GAME_TASKS.md` e `docs/gates/` da disco.

## Come lanciare

```
Task:
  description: <phase id>
  subagent_type: general
  prompt: <blocco PHASE x da questo file, con le 8 righe sostituite>
```

Un worker alla volta per fasi dipendenti (greybox → assets → systems → ui → playtest).
Asset Blender: **un prop per worker**, in parallelo solo dopo che la lista in `ASSET-LEDGER.md` e `GAME_TASKS.md` è lockata (max 3 paralleli).

---

## PHASE gdd

Tu fai SOLO l’intervista GDD. Leggi `SKILL/references/gdd-interview.md` e `gdd-template.md`.
Scrivi `PROJECT/GDD.md` (se PROJECT ancora vuoto, scrivi nel workspace e il parent lo sposterà).
NON aprire Unity, Blender, Voxel, UI.
Stop quando `status: locked` e l’utente ha confermato il recap.

Gate: `GDD.md` contiene `status: locked`.

---

## PHASE project

Tu fai SOLO attach o create. Leggi `SKILL/references/project-attach.md` e `unity-cli.md`.
NON modellare, NON scrivere gameplay, NON UI.
Crea le cartelle `art/ blender/ voxel/ cc0/ exports/`, `screenshots/`, `ui/`, `docs/gates/`, `Assets/_Game/...`.
Scrivi `docs/gates/04-project.md` con `projectPath` e `PASS`.

Gate: `ProjectSettings/` + `docs/gates/04-project.md` con PASS.

---

## PHASE task-decomposition

Tu fai SOLO la scomposizione atomica dei task e l'inizializzazione della memoria centrale.
Leggi `SKILL/references/task-decomposition.md`, `context-management.md`, e i template `SKILL/templates/GAME_TASKS.md` e `GAME_CONTEXT.md`.
Genera:
1. `PROJECT/GAME_TASKS.md`: esplodi ogni prop, script, prefab, coordinate di piazzamento, UI prompt e test in righe singole numerate (TASK-001..TASK-NNN). VIETATO raggruppare ("modelli 3D" o "props" = FAIL immediato; devi scrivere sedia, tavolo, porta, maniglia, barile, etc.).
2. `PROJECT/GAME_CONTEXT.md`: compila la visione di gioco, game loop (30s, 3m, macro), condizioni win/fail, controlli, setup engine, e la mappatura iniziale di chi possiede gli script e gli oggetti previsti nella scena.
NON modellare, NON aprire Unity.

Gate: `PROJECT/GAME_TASKS.md` (> 15 task atomici con ID) + `PROJECT/GAME_CONTEXT.md` compilato su disco.

---

## PHASE greybox

Tu fai SOLO cubi + player che si muove. Leggi `greybox.md`, `unity-loop.md`, `geometra.md`.
Cubi sono OK in QUESTA fase. Vietato Blender. Vietato UI Toolkit. Vietato dire che il gioco è finito.
Obbligo: Input System, CharacterController, `PlayerMovementTests` che **giri** (`run_tests` o `unity test`).
Play Mode + screenshot `screenshots/010-greybox-play.png`.
Scrivi `docs/gates/06-greybox.md`.

Gate: test movimento verde + PNG greybox su disco + 0 errori console.

---

## PHASE blender-asset

Tu fai SOLO UN asset 3D. Nome: `$ASSET_ID` (es. `prop_crate`).
Leggi `SKILL/references/blender-mcp.md` + `blender-game-assets.md` + `asset-contract.md`.

VIETATO:
- `bpy.ops.wm.read_homefile` / `read_factory_settings`
- `blender --background` / `blender -b`
- un solo `execute_blender_code` che fa cubo+export
- Unity, UI, altri prop

OBBLIGO: 5 chiamate MCP separate. Dopo OGNI passo `blender_get_viewport_screenshot` su disco:

1. addon_status + scene_info. Pulizia oggetti (NON homefile). Blockout Geometra Y=0 → `screenshots/blender-$ASSET_ID-1-blockout.png`
2. Layer pezzi + bevel 1 segmento → `...-2-bevel.png`
3. Ferramenta (chiodi vertices=6, staffe) → `...-3-hardware.png`
4. 3 materiali PBR (look BSDF by type, non by name) → `...-4-mats.png`
5. transform_apply, export GLB, screenshot finale → `screenshots/blender-$ASSET_ID.png` + `art/exports/$ASSET_ID.glb`

GLB < 15KB = FAIL. Meno di 5 PNG = FAIL. Se MCP giu: avvia Blender via TerminalMCP; se 9876 chiuso, gate FAIL + messaggio RUN Start MCP Server. MAI cubi Unity al posto del GLB.

Gate: 5 PNG + GLB. Parent Read step 2 e finale. Cubo/scena vuota = retry.

---

## PHASE import-art

Tu fai SOLO import GLB in Unity (`Assets/_Game/Art/`), strip luci/camere, collider, prefab.
NON modellare. NON UI.
Screenshot Unity `screenshots/030-import-$ASSET_ID.png` del prefab in scena.
Gate: `docs/gates/07-import.md`.

---

## PHASE systems

Tu fai SOLO i verbi del GDD (oltre move già nel greybox): interact, pause, win/fail, giorno/notte se nel GDD.
Ogni verbo = script + test che gira nella stessa modifica.
Prompt a schermo minimo: cosa fare adesso (es. “Saccheggia la casa prima del coprifuoco”).
NON Main Menu. NON modellare.
Gate: `docs/gates/08-systems.md` + test names.

---

## PHASE ui-main-menu

Tu fai SOLO il Main Menu.
OBBLIGO Skill tool `real-world-design` mode=game. Vietato inventare UXML a mano come primo passo. Vietato saltare Variant Studio / mock HTML + Playwright.
Flusso: tokens → 3-4 varianti HTML → screenshot 1440x900 `screenshots/040-ui-main-menu-variants.png` → pick (o prima variante se lo studio non parte, MA il mock HTML deve esistere) → `ui-transpiler.mjs` → UXML/USS + UIDocument + PanelSettings.
Scena MainMenu **build index 0**. Spawn FP nel livello = FAIL.
Gate: mock HTML su disco + UXML + PNG + `docs/gates/09-ui-main-menu.md`.

---

## PHASE ui-hud

Tu fai SOLO HUD. Skill `real-world-design` mode=game OBBLIGATORIA (stesso flusso del menu: tokens, mock HTML, Playwright).
Vitali, obiettivo testuale visibile, prompt `[E]`, orologio se nel GDD.
UI Toolkit + PanelSettings. IMGUI = FAIL.
Screenshot Play Mode `screenshots/041-ui-hud.png`. Gate `docs/gates/09-ui-hud.md`. Mock HTML mancante = FAIL.

---

## PHASE ui-pause

Tu fai SOLO Pause. Skill `real-world-design` obbligatoria. Esc, timeScale 0, Riprendi / Menu.
Screenshot `screenshots/042-ui-pause.png`. Gate `docs/gates/09-ui-pause.md`.

---

## PHASE ui-gameover

Tu fai SOLO Game Over / Victory. Skill `real-world-design` obbligatoria. Pulsante Riprova.
Screenshot `screenshots/043-ui-gameover.png`. Gate `docs/gates/09-ui-gameover.md`.

---

## PHASE juice

Tu fai SOLO SFX CC0 + hit-stop/shake. Leggi `juice.md`.
NON “il gioco è finito”.
Gate: `docs/gates/10-juice.md`.

---

## PHASE playtest

Tu fai SOLO QA. Leggi `playtest.md`.
Play Mode reale. WASD. Screenshot. Console 0 errori.
FAIL se dallo screenshot non si capisce l’obiettivo (manca testo HUD / prompt / menu).
FAIL se i modelli in Game View sono ancora primitivi Unity e `art/exports/` è vuoto.
Scrivi `docs/playtest.md` e `docs/gates/11-playtest.md`.
NON inventare test verdi. Incolla job_id / output.

---

## PHASE slice

Tu fai SOLO il recap. Leggi tutti i `docs/gates/*.md`.
Se uno è rosso, NON dichiarare slice fatta. Elenca i rossi.
Gate: `docs/gates/12-slice.md`.

---

## HARD STOP

Dopo il gate PASS di QUESTA fase: aggiorna GAME_TASKS.md + GAME_CONTEXT.md, stampa il banner in `session-cuts.md`, **FERMA**. Non lanciare un'altra phase. Max 3 blender-asset nella stessa chat, poi STOP anche se la lista non e finita.
