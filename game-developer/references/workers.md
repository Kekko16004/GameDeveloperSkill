# Workers — un job, un cervello, zero pigrizia

Il parent **non implementa**. Lancia `Task` (`subagent_type: general`, `background: false`). Ogni worker riceve SOLO il prompt sotto, più 8 righe di contesto. Niente transcript precedente, niente “poi faccio anche la UI”.

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

Un worker alla volta per fasi dipendenti (greybox → kits → systems → ui → playtest).
Art: **un pezzo per worker** per kit-dress, oppure **fino a 3 modelli Poly Pizza in batch** per blender-asset (in parallelo o sequenza rapida fast-track, solo se il ledger dice `source: polypizza`).

---

## PHASE gdd

Tu fai SOLO l’intervista GDD. Leggi `gdd-interview.md`, `tool-stack.md`, `gdd-template.md`.
Domanda 13 = tool stack per TUTTO il gioco (tabella raccomandata). Lock in `GDD.md` sezione Tool stack.
Scrivi `PROJECT/GDD.md` (se PROJECT ancora vuoto, scrivi nel workspace e il parent lo sposterà).
NON aprire Unity, Blender, Voxel, UI, Sloyd.
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
Leggi `SKILL/references/task-decomposition.md`, `art-pipeline.md`, `context-management.md`, e i template `SKILL/templates/GAME_TASKS.md` e `GAME_CONTEXT.md`.
Genera:
1. `PROJECT/GAME_TASKS.md`: esplodi ogni prop, script, prefab, coordinate di piazzamento, UI prompt e test in righe singole numerate (TASK-001..TASK-NNN). VIETATO raggruppare ("modelli 3D" o "props" = FAIL immediato). Per ogni mesh indica `source: kenney|kaykit|probuilder|blender`.
2. `PROJECT/GAME_CONTEXT.md`: visione, game loop, win/fail, controlli, mapping script.
3. `PROJECT/ASSET-LEDGER.md`: una riga per pezzo visibile, source dal catalogo `cc0-sources.md`. Default kit, non Blender.

NON modellare, NON aprire Unity.

Gate: `PROJECT/GAME_TASKS.md` (> 15 task atomici con ID) + `PROJECT/GAME_CONTEXT.md` + `ASSET-LEDGER.md`.

---

## PHASE greybox

Tu fai SOLO geometria giocabile + player che si muove. Leggi `greybox.md`, `probuilder-levels.md`, `unity-loop.md`, `geometra.md`.
Cubi / ProBuilder sono OK in QUESTA fase. Vietato Blender. Vietato kit-dress. Vietato UI Toolkit. Vietato dire che il gioco è finito.
Obbligo: Input System, CharacterController, `PlayerMovementTests` che **giri** (`run_tests` o `unity test`).
Preferisci `manage_probuilder` per pavimento, muri, porta-vano. Se ping fallisce: cubi Unity.
Play Mode + screenshot `screenshots/010-greybox-play.png`.
Scrivi `docs/gates/06-greybox.md`.

Gate: test movimento verde + PNG greybox su disco + 0 errori console.

---

## PHASE kit-fetch

Tu fai SOLO il download dei pack CC0 del genere GDD.
Leggi `cc0-sources.md`. Esegui:

```
powershell -File SKILL/scripts/fetch-cc0-kits.ps1 -ProjectPath PROJECT -Genre <medieval|dungeon|scifi|city|pirate|interior|prototype>
```

NON importare in scena. NON mischiare due famiglie. NON scaricare Quaternius Pro/Source né Sloyd.
Gate: `art/cc0/` contiene almeno un pack unzippato + `docs/gates/07-kit-fetch.md`.

---

## PHASE kit-dress

Tu fai SOLO UN pezzo da kit. Nome: `$ASSET_ID`.
Leggi `kit-dress.md` + `asset-contract.md` + `geometra.md` + riga ledger.

VIETATO: Blender remodel, Sloyd, Meshy, un secondo pack di stile, “visto che ci sono vesto anche la sedia”.

OBBLIGO: file kit → `art/exports/$ASSET_ID.*` → prefab + collider → piazza alle coordinate del task → screenshot `screenshots/030-import-$ASSET_ID.png`.

Gate: prefab + PNG + riga ledger `source: kenney|kaykit|quaternius-standard`. Parent Read dello screenshot. Player che affonda = retry.

---

## PHASE blender-asset (Fast-Track Poly Pizza, fino a 3 modelli in batch)

Tu fai l'import da Poly Pizza per 1 fino a 3 asset della lista ledger (`$ASSET_ID_1`, `$ASSET_ID_2`, `$ASSET_ID_3`).
Se il pezzo esiste in Kenney/KayKit/Quaternius Standard: STOP, di’ al parent di lanciare kit-dress.
Leggi `blender-mcp.md` + `blender-game-assets.md` + `polypizza.md` + `asset-contract.md`.

VIETATO:
- Fare 5 passaggi e 4 screenshot intermedi per asset già pronti (è inutile e spreca token/tempo).
- `read_homefile` / `read_factory_settings` / `blender -b`
- `execute_blender_code` che crea mesh da zero, cubi, bevel, boolean, “handmade”
- Hunyuan / Rodin / Sketchfab / Sloyd / Meshy
- muri/pavimenti/stanze (ProBuilder + kit)
- Unity, UI, altri prop

PROTOCOLLO FAST-TRACK (Esegui per ciascun modello, max 3 per run):
Per ogni `$ASSET_ID`:
0. `execute_blender_code`: **RESET SCENA OBBLIGATORIO**. Pulizia totale oggetti/mesh/materiali (`for obj in list(bpy.data.objects): bpy.data.objects.remove(obj, do_unlink=True)`). Mai importare sopra geometrie residue!
1. `blender_get_addon_status` + `blender_get_polypizza_status` (verifica iniziale una tantum).
2. `blender_search_polypizza_models` query inglese, `licence=CC0`, limit 8.
3. `blender_download_polypizza_model` `normalize_size=true` `target_size` Geometra.
4. Sanitize block ONLY (lights/cameras rimossi, pivot Y=0 a terra) + `blender_export_scene` GLB in `art/exports/$ASSET_ID.glb`.
5. `get_viewport_screenshot` → **1 SOLO PNG finale di verifica**: `screenshots/blender-$ASSET_ID.png`. Zero shot intermedi!
6. Aggiorna riga `ASSET-LEDGER.md`: `source: polypizza`, id, licence, attribution.

GLB < 15KB = FAIL. Cubo default = FAIL. MCP giù: avvia Blender; porta 9876 chiusa → RUN Start MCP Server, STOP.

Gate: 1 PNG finale `screenshots/blender-$ASSET_ID.png` per ciascun asset + relativi GLB. Parent Read solo del PNG finale.

---

## PHASE import-art

Tu fai SOLO import GLB/FBX ancora fuori da Unity (`Assets/_Game/Art/`), strip luci/camere, collider, prefab.
NON modellare. NON UI. NON rifare kit già importati da kit-dress.
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

## PHASE juice (Audio Pipeline & Game Feel)

Tu fai SOLO Audio SFX CC0 + hit-stop/shake + game feel. Leggi `audio-pipeline.md` e `juice.md`.
1. Esegui `fetch-cc0-audio.ps1 -ProjectPath PROJECT` per scaricare i pack Kenney CC0 (passi, interazioni, click UI, atmosfera).
2. Verifica che `Assets/_Game/Scripts/Audio/AudioManager.cs` sia presente e compilato con 0 errori.
3. Istanzia il prefab o GameObject `AudioManager` nella scena di gioco `MainGame.unity`.
4. Collega i suoni chiave:
   - Passi su superficie al `PlayerController.cs` (`AudioManager.Instance.PlayFootstep()`).
   - Apertura/chiusura porte e bauli (`AudioManager.Instance.PlaySFX()`).
   - Click pulsanti del menu e HUD (`AudioManager.Instance.PlayUI()`).
5. NON dire “il gioco è finito”.
Gate: `docs/gates/10-juice.md` + `Assets/_Game/Audio/SFX/` popolata + console 0 errori.

---

## PHASE playtest

Tu fai SOLO QA. Leggi `playtest.md`.
Play Mode reale. WASD. Screenshot. Console 0 errori.
FAIL se dallo screenshot non si capisce l’obiettivo (manca testo HUD / prompt / menu).
FAIL se i modelli in Game View sono ancora primitivi Unity (cubo default) e `art/exports/` è vuoto e non c’è kit in `Assets/_Game/Art/`.
ProBuilder rooms + kit walls = OK.
Scrivi `docs/playtest.md` e `docs/gates/11-playtest.md`.
NON inventare test verdi. Incolla job_id / output.

---

## PHASE slice

Tu fai SOLO il recap. Leggi tutti i `docs/gates/*.md`.
Se uno è rosso, NON dichiarare slice fatta. Elenca i rossi.
Gate: `docs/gates/12-slice.md`.

---

## HARD STOP

Dopo il gate PASS di QUESTA fase: aggiorna GAME_TASKS.md + GAME_CONTEXT.md, stampa il banner in `session-cuts.md`, **FERMA**. Non lanciare un'altra phase. Max 3 kit-dress (o blender-asset) nella stessa chat, poi STOP anche se la lista non e finita.
