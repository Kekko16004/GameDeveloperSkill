# Workers — un job, un cervello, zero pigrizia

Il parent **non implementa**. Lancia `Task` (`subagent_type: general`, `background: false`). Ogni worker riceve SOLO il prompt sotto, più 8 righe di contesto. Niente transcript precedente, niente "poi faccio anche la UI".

Se un worker chiude senza i file del gate, il parent **rilancia lo stesso worker** (stesso prompt + "GATE ROSSO: manca X"). Max 2 retry. Poi FAIL visibile all'utente.

Il layer deterministico ([gds-editor.md](gds-editor.md)) fa il lavoro di precisione: il worker scrive JSON e chiama `execute_code`, non piazza pezzi a mano. Ogni gate che tocca la scena cita `lint: {"issues":0,...}` da `GDS.SceneLint.RunJson()`.

## Contesto minimo (le uniche 8 righe per ogni worker)

```
PROJECT=<abs path Unity/Godot>
GDD=<abs path GDD.md>
CONTEXT=<abs path GAME_CONTEXT.md>
TASKS=<abs path GAME_TASKS.md>
SKILL=<abs path game-developer/>
PHASE=<id>
ENGINE=unity|godot
STYLE=<from GDD: famiglia kit + lookdev preset>
```

Vietato incollare conversazioni, screenshot chat, o "abbiamo già fatto greybox". Il worker rilegge `GDD.md`, `GAME_CONTEXT.md`, `GAME_TASKS.md`, `art/kit-catalog.json`, `art/blueprints/` e `docs/gates/` da disco.

## Come lanciare

```
Task:
  description: <phase id>
  subagent_type: general
  prompt: <blocco PHASE x da questo file, con le 8 righe sostituite>
```

Un worker alla volta per fasi dipendenti (greybox → kit-fetch → building-gen → level-build → village → lookdev → characters → systems → ui → juice → playtest).
Art: **un blueprint per worker** per level-build (parallelo max 3 blueprint indipendenti), **fino a 3 hero asset in batch** per hero-asset.

---

## PHASE gdd

Tu fai SOLO l'intervista GDD. Leggi `gdd-interview.md`, `tool-stack.md`, `gdd-template.md`, `gen3d.md`, `lookdev.md`.
Tutte le 19 domande, a blocchi. Q13 tool stack, Q16 gen3d tier + budget, Q17 asset store, Q18 GPU/VRAM, Q19 look preset sono obbligatorie e vanno lockate in `GDD.md` (`gen3d:`, `gen3dBudgetCredits:`, `gen3dMaxAssets:`, `assetStore:`, `gpu:`, `vram:`, `lookdev:`, `toon:`, `outline:`, `hdri:`).
Scrivi `PROJECT/GDD.md` (se PROJECT ancora vuoto, scrivi nel workspace e il parent lo sposterà).
NON aprire Unity, Blender, Voxel, UI.
Stop quando `status: locked` e l'utente ha confermato il recap.

Gate: `GDD.md` contiene `status: locked` e tutti i campi Q13–Q19.

---

## PHASE project

Tu fai SOLO attach o create + strumentazione. Leggi `SKILL/references/project-attach.md`, `unity-cli.md`, `gds-editor.md`.
1. Attach o `unity projects create` (template URP). Unity **6000.0 / 6000.3 LTS**; 6000.5+ richiede ProBuilder ≥ 6.1.2.
2. `powershell -File SKILL/scripts/install-gds-editor.ps1 -ProjectPath PROJECT` (+ `-WithToonShader` se `GDD toon: yes`, `-WithOutline` se `outline: yes`). Copia `Assets/_Game/Editor/GDS/` e aggiorna il manifest (ProBuilder 6.1.2).
3. CoplayDev MCP: `manage_packages` per Input System, Cinemachine, ProBuilder; wait compile; `read_console` 0 errori; `manage_tools` → gruppo `scripting_ext` attivo.
4. Verifica: `execute_code` → `return GDS.SceneLint.RunJson();` deve rispondere JSON.
5. Se `GDD gen3d: meshy|tripo`: verifica che `MESHY_API_KEY`/`TRIPO_API_KEY` sia nell'env del MCP (non chiederla in chat, non loggarla).
Crea le cartelle `art/ blender/ voxel/ cc0/ exports/ blueprints/`, `screenshots/`, `ui/`, `docs/gates/`, `docs/lint/`, `Assets/_Game/...`.
NON modellare, NON scrivere gameplay, NON UI.
Scrivi `docs/gates/04-project.md` con `projectPath`, versione Unity, output di `GDS.SceneLint.RunJson()` e `PASS`.

Gate: `ProjectSettings/` + `Assets/_Game/Editor/GDS/GDS.Editor.asmdef` + console 0 errori + `docs/gates/04-project.md` PASS.

---

## PHASE task-decomposition

Tu fai SOLO la scomposizione dei task e l'inizializzazione della memoria centrale.
Leggi `SKILL/references/task-decomposition.md`, `art-pipeline.md`, `level-builder.md`, `context-management.md`, e i template `SKILL/templates/GAME_TASKS.md` e `GAME_CONTEXT.md`.
Genera:
1. `PROJECT/GAME_TASKS.md`: righe singole numerate (TASK-001..). Per l'art: **un task per edificio Blender** (`BG-inn`: stile, volumi, porte, balconi → `art/specs/inn.json`), **un task per blueprint kit/ProBuilder** (`BP-house_a`: volumi, aperture, partizioni, attach, prop, scatter), **un task per il villaggio** (`VL-hamlet`: strade, piazza, pesi edifici) se il GDD e esterno, e **un task per hero asset**. VIETATO "modelli 3D"/"props" generici, VIETATO un task per muro.
2. `PROJECT/GAME_CONTEXT.md`: visione, game loop, win/fail, controlli, mapping script, lookdev preset, famiglia kit.
3. `PROJECT/ASSET-LEDGER.md`: una riga per blueprint e per hero asset, `source:` dal catalogo `cc0-sources.md` o tier gen3d del GDD.
4. `PROJECT/art/blueprints/PLAN.md`: tabella edifici/aree → `source: blender-gen|kit|probuilder`, posizione/rotazione nel livello (griglia Geometra 4 m) o `lot: village`, così building-gen / level-build / village non inventano nulla. Default per esterni low-poly: **blender-gen** per le case, kit per props/recinzioni/lampioni/alberi, ProBuilder per interni.
NON modellare, NON aprire Unity.

Gate: `GAME_TASKS.md` (> 15 task atomici con ID) + `GAME_CONTEXT.md` + `ASSET-LEDGER.md` + `art/blueprints/PLAN.md`.

---

## PHASE greybox

Tu fai SOLO geometria giocabile + player che si muove. Leggi `greybox.md`, `level-builder.md`, `unity-loop.md`, `geometra.md`, `scene-lint.md`.
Terreno: cubo/plane con **faccia superiore a Y=0** (cubo `[n,0.2,n]` a `y=-0.1`) e collider.
Stanze/edifici del greybox: `GDS.PB.Room(...)` oppure blueprint `mode: probuilder|primitives` da `art/blueprints/PLAN.md` (stesso `name` che userà level-build → rebuild in place). Vietato piazzare muri uno a uno.
Obbligo: Input System, CharacterController, `PlayerMovementTests` che **giri** (`run_tests` o `unity test`).
Vietato Blender. Vietato kit. Vietato UI Toolkit. Vietato dire che il gioco è finito.
Lint: `GDS.SceneLint.RunJson(autoFix:true)` poi `RunJson()` → `issues: 0`.
Play Mode + screenshot `screenshots/010-greybox-play.png`.
Scrivi `docs/gates/06-greybox.md` (test job_id, lint JSON, PNG).

Gate: test movimento verde + lint 0 + PNG greybox su disco + 0 errori console.

---

## PHASE kit-fetch

Tu fai SOLO download + catalogo dei pack della famiglia GDD.
Leggi `cc0-sources.md`, `art-pipeline.md`, `gds-editor.md`. Esegui:

```
powershell -File SKILL/scripts/fetch-cc0-kits.ps1 -ProjectPath PROJECT -Genre <medieval|dungeon|scifi|city|pirate|interior|prototype|nature|characters|vfx>
```

Se `GDD assetStore: yes` e famiglia = Synty: apri Package Manager > My Assets (TerminalMCP browser se serve) e importa POLYGON Starter Pack in `Assets/_Game/Art/AssetStore/`.
Copia i modelli usati in `Assets/_Game/Art/Kits/<family>/` (FBX o glTF, non entrambi). Poi `execute_code`:
`return GDS.KitCatalog.BuildJson("Assets/_Game/Art/Kits/<family>/<pack>");` → se `notes` dice che la scala non è metrica: `GDS.KitCatalog.SetImportScale(folder, <fattore>)` una volta e rifai il catalogo.
NON importare in scena. NON mischiare due famiglie. NON scaricare Quaternius Pro/Source né Sloyd.
Gate: `art/cc0/` con almeno un pack + `art/kit-catalog.json` con `count > 0` + `docs/gates/07-kit-fetch.md` (incolla `suggestedModule` e `notes`).

---

## PHASE building-gen (Blender procedurale, batch fino a 5 spec)

Tu fai SOLO gli edifici esterni "veri" della lista `art/blueprints/PLAN.md` marcati `source: blender-gen`. Leggi `blender-building.md`, `geometra.md`, `GDD.md` (style/palette/lookdev).
Per ogni edificio (max 5 per run):
1. Scrivi `art/specs/<name>.json`: `style` dal GDD (medieval/fantasy/village/modern/scifi/dungeon), `volumes` (1-3 rettangoli, metri interi, piani 1-3), `doors` sul lato S, 0-1 `balconies`, 0-1 `chimneys`, `interior.partitions` se il player entra, `export: art/exports/building_<name>.glb`, `preview: screenshots/blender-building_<name>.png`. Palette GDD via `styleOverride` se serve.
2. `powershell -File SKILL/scripts/gds-building.ps1 -Spec PROJECT/art/specs/<name>.json -ProjectPath PROJECT` → leggi `GDS_RESULT` (`tris` 2k-40k, `bytes` > 50k).
3. Read del PNG preview: se manca tetto/finestre/porta (spec incoerente) correggi la spec e rilancia. Mai ritoccare a mano in Blender.
4. Aggiorna `ASSET-LEDGER.md` (`source: blender-gen`, spec path, fbx path).
VIETATO: `execute_blender_code` con modellazione a mano, addon, `blender -b` con script diversi da `gds_building.py`, edifici curvi (usa `GDS.PB.Tower`), piu di 5 spec per run.
Gate: `docs/gates/07-building-<name>.md` per edificio con `GDS_RESULT`, PNG, FBX in `Assets/_Game/Art/Exports/`. Il piazzamento lo fa village / level-build (con lint).

---

## PHASE level-build

Tu fai SOLO UN blueprint: `$BP_NAME` (riga di `art/blueprints/PLAN.md`). Leggi `level-builder.md`, `scene-lint.md`, `geometra.md`, `art/kit-catalog.json`.
1. Scegli dal catalogo i file per i ruoli `floor wall wallDoor wallWindow corner roof stair` (stessa famiglia). Se manca `wall`/`floor` nel kit → `mode: probuilder` (interni/dungeon) oppure edificio `building-gen` come `props` con `collider: mesh`. MAI cubi Unity.
2. Scrivi `art/blueprints/$BP_NAME.json`: pianta con `volumes` (L/T/U se PLAN.md lo dice), `openings` per volume, `partitions` interne con porta, `stairs` + `floorHoles` se >1 piano, `attach` (lanterne, insegne, tende, fioriere: almeno 2 per facciata visibile), `fences` se il lotto ne ha, `props` interni con coordinate relative, `scatter` esterno con `avoidRadius`.
3. `execute_code`: `return GDS.LevelBuilder.BuildFromFile("art/blueprints/$BP_NAME.json");` → leggi `missingRoles`/`warnings`, correggi il JSON e rilancia finché `missingRoles: []`.
4. `return GDS.SceneLint.RunJson(autoFix:true);` poi `return GDS.SceneLint.RunJson();` → `issues: 0`.
5. Screenshot Scene/Game view `screenshots/020-build-$BP_NAME.png`.
VIETATO: `manage_gameobject` per piazzare muri, ProBuilder MCP face-by-face, Blender, seconda famiglia, "visto che ci sono faccio anche la casa B".
Gate: `docs/gates/07-build-$BP_NAME.md` con `build:` JSON, `lint:` JSON, PNG. Parent Read del PNG solo per stile (coerenza famiglia), non per misurare.

---

## PHASE village (SOLO se il GDD descrive un insediamento)

NON e il default del mondo. Caverna, dungeon, cripta, interno, citta, base sci-fi, natura aperta: NON lanciare questa fase — il mondo lo fa `level-build` secondo [environments.md](environments.md) (kit genre, lookdev preset, recipe caverna).



Tu fai SOLO il layout del mondo. Leggi `village.md`, `scene-lint.md`, `GDD.md` (mappa/ambiente). Prerequisiti su disco: gli edifici di building-gen in `Assets/_Game/Art/Exports/` e/o i blueprint kit in `art/blueprints/`.
1. Scrivi `art/blueprints/village_<name>.json` (template `SKILL/templates/blueprints/village_example.json`): strade = percorsi del GDD, piazza = hub, `buildings` con pesi (cottage 3, hero 1), `streetProps`/`plazaProps`/`fenceFile` dal kit catalog, `scatter` alberi/rocce dal kit nature, `terrain.enabled` false se il GDD e un interno.
2. `execute_code`: `return GDS.Village.BuildFromFile("art/blueprints/village_<name>.json");` → `buildings >= 6`, `warnings: []` (file mancanti → correggi nomi dal catalogo).
3. `return GDS.SceneLint.RunJson(autoFix:true);` poi `RunJson()` → `issues: 0`.
4. Player spawn sulla piazza (sposta il Player del greybox). Screenshot aerea `screenshots/025-village-aerial.png` + strada `screenshots/026-village-street.png`.
VIETATO: piazzare edifici a mano, modificare i lotti generati, terreno senza collider, strade fuori dalla zona piatta.
Gate: `docs/gates/07-village.md` con il JSON village, `lint:`, i 2 PNG.

---

## PHASE hero-asset (batch fino a 3)

Tu fai SOLO gli hero asset `$ASSET_ID_1..3` del ledger (prop unici che nessun kit ha). Leggi `art-pipeline.md`, `blender-mcp.md`, `polypizza.md`, `gen3d.md`, `asset-contract.md`, e `GDD.md → gen3d:`.
Ordine: Poly Pizza → Poly Haven models → Sketchfab CC0 → tier gen3d del GDD (solo se `gen3d != none`, entro `gen3dMaxAssets` e budget).
Per ogni asset:
0. `execute_blender_code`: RESET SCENA (rimuovi tutti objects/meshes/materials).
1. Ricerca + download nativo (`search_polypizza_models` / `search_polyhaven_assets(asset_type="models")` / `search_sketchfab_models`) oppure `generate_model` (CoplayDev, provider dal GDD) / Hyper3D.
2. Sanitize block ONLY (luci/camere via, pivot base Y=0, `normalize_size` alla misura Geometra, decimate > 15k tris) + `export_scene` → `art/exports/$ASSET_ID.glb`.
3. `get_viewport_screenshot` → 1 PNG `screenshots/blender-$ASSET_ID.png`.
4. Riga ledger: `source`, id, licence, attribution, crediti usati.
Poi aggiungi il prop alla lista `props` del blueprint giusto (`art/blueprints/<bp>.json`) e rilancia `GDS.LevelBuilder.BuildFromFile` + lint (l'import-art lo fa se il GLB non è ancora in `Assets/_Game/Art/`).
VIETATO: bpy modelling da zero, cubi, `read_homefile`, `blender -b`, muri/pavimenti, superare il budget, PBR fotorealistico accanto a Kenney senza flatten materiale.
GLB < 15KB = FAIL. MCP giù: avvia Blender; porta 9876 chiusa → STOP.
Gate: `docs/gates/07-hero-$ASSET_ID.md` per asset con PNG, GLB, riga ledger, `lint:` dopo il rebuild.

---

## PHASE import-art

Tu fai SOLO import GLB/FBX ancora fuori da Unity (`art/exports/*` → `Assets/_Game/Art/Exports/`), strip luci/camere, collider, prefab.
Poi rilancia i blueprint che li citano (`GDS.LevelBuilder.BuildFromFile`) e lint 0.
NON modellare. NON UI.
Gate: `docs/gates/07-import.md` con lista prefab + `lint:`.

---

## PHASE lookdev

Tu fai SOLO il look. Leggi `lookdev.md`, `gds-editor.md`, `GDD.md → lookdev/toon/outline/hdri/palette`.
1. (HDRI opzionale) Blender MCP `download_polyhaven_asset(asset_type="hdris", resolution="2k")` → copia `.hdr` in `Assets/_Game/Art/HDRI/`.
2. `execute_code`: `return GDS.LookDev.Apply("<preset>", hdriPath:<o null>);` → `applied` deve contenere `volume` e `camera-post`.
3. `return GDS.LookDev.ApplyPalette(new[]{<hex GDD>});` e assegna `Mat_Palette_*` alle shell ProBuilder (`manage_material` o rebuild blueprint con `material`).
4. Se `toon: yes`: pacchetto installato dal project → `GDS.LookDev.ConvertMaterials("Universal Render Pipeline/Lit", "Toon")`. Se `outline: yes`: `manage_graphics feature_add` della feature del pacchetto.
5. Luci locali: `GDS.VFX.AttachTorches("torch")` per interni; 1 fill light sull'obiettivo.
6. `read_console` 0 errori. Lint 0. Screenshot Game view `screenshots/035-lookdev.png` (bloom/fog/ombre visibili).
NON toccare gameplay/UI. NON YAML.
Gate: `docs/gates/08-lookdev.md` con l'`applied` JSON, preset, PNG, `lint:`.

---

## PHASE characters

Tu fai SOLO personaggi + animazioni (+ NavMesh se il GDD ha nemici). Leggi `characters.md`, `gds-editor.md`.
1. Pack dal GDD (KayKit Adventurers/Skeletons, Kenney Animated, Quaternius UBC+UAL) → `Assets/_Game/Art/Characters/<pack>/`.
2. `GDS.Characters.SetHumanoidFolder(...)`, `ListClips()`, `BuildController("Player", ...)`, `MakePrefab(...)`. Stesso per `Enemy`.
3. Sostituisci la capsula del greybox con `char_player` (mantieni `PlayerController` + Input). `animator.SetFloat("Speed", ...)` nel controller.
4. Nemici: Skill `initialize-ai-navigation` → NavMeshSurface bake, `NavMeshAgent`, `EnemyChase.cs` + test `Enemy_ChasesPlayer`.
5. Altezza player 1.6–2.0 m (Geometra) — altrimenti `SetImportScale` sulla cartella.
6. Lint 0. Play Mode screenshot `screenshots/050-characters.png` (personaggio in walk).
Gate: `docs/gates/09-characters.md` con JSON delle chiamate, test, PNG, `lint:`.

---

## PHASE systems

Tu fai SOLO i verbi del GDD (oltre move già nel greybox): interact, pause, win/fail, giorno/notte se nel GDD.
Ogni verbo = script + test che gira nella stessa modifica.
Prompt a schermo minimo: cosa fare adesso (es. "Saccheggia la casa prima del coprifuoco").
NON Main Menu. NON modellare.
Gate: `docs/gates/10-systems.md` + test names.

---

## PHASE ui-main-menu

Tu fai SOLO il Main Menu.
OBBLIGO Skill tool `real-world-design` mode=game. Vietato inventare UXML a mano come primo passo. Vietato saltare Variant Studio / mock HTML + Playwright.
Flusso: tokens (palette GDD + preset lookdev) → 3-4 varianti HTML con layout distinti → screenshot gallery 1440x900 `screenshots/040-ui-main-menu-variants.png` → **MOSTRA ALL'UTENTE E ATTENDI LA SCELTA (STOP OBBLIGATORIO)** → solo dopo la scelta: `ui-transpiler.mjs` → UXML/USS + UIDocument + PanelSettings.
Scena MainMenu **build index 0**. Sfondo: screenshot lookdev o camera sul livello con Volume. Spawn FP nel livello = FAIL.
Gate: mock HTML su disco + UXML + PNG + `docs/gates/11-ui-main-menu.md`.

---

## PHASE ui-hud

Tu fai SOLO HUD. Skill `real-world-design` mode=game OBBLIGATORIA.
REGOLA SCELTA UTENTE TASSATIVA: È VIETATO auto-generare l'HUD senza varianti. Mantieni i token di stile consolidati nel Main Menu (`ui/tokens.css`), ma devi SEMPRE creare 3-4 varianti di layout diverse (es. diegetico, barre angolari survival, bottom-bar compatta, minimal immersivo) in Variant Studio.
Screenshot gallery 1440x900 `screenshots/041-ui-hud-variants.png` → **MOSTRA ALL'UTENTE E ATTENDI LA SCELTA (STOP OBBLIGATORIO)**.
Solo dopo la scelta dell'utente: `ui-transpiler.mjs` → UXML/USS + PanelSettings.
Vitali, obiettivo testuale visibile, prompt `[E]`, orologio se nel GDD. IMGUI = FAIL.
Screenshot Play Mode `screenshots/041-ui-hud.png`. Gate `docs/gates/11-ui-hud.md`. Mock HTML mancante = FAIL.

---

## PHASE ui-pause

Tu fai SOLO Pause. Skill `real-world-design` obbligatoria.
REGOLA SCELTA UTENTE TASSATIVA: Mantieni i token del Main Menu, ma genera 3-4 varianti di layout (sidebar laterale, modale centrale, registro/libro diegetico, minimal).
Screenshot gallery `screenshots/042-ui-pause-variants.png` → **MOSTRA ALL'UTENTE E ATTENDI LA SCELTA (STOP OBBLIGATORIO)**.
Solo dopo la scelta: transpiler UXML + controller (Esc, timeScale 0, Riprendi / Menu).
Screenshot `screenshots/042-ui-pause.png`. Gate `docs/gates/11-ui-pause.md`.

---

## PHASE ui-gameover

Tu fai SOLO Game Over / Victory. Skill `real-world-design` obbligatoria.
REGOLA SCELTA UTENTE TASSATIVA: Mantieni i token del Main Menu, ma genera 3-4 varianti (pergamena/certificato, epitaffio scuro, statistiche dettagliate, cinematico).
Screenshot gallery `screenshots/043-ui-gameover-variants.png` → **MOSTRA ALL'UTENTE E ATTENDI LA SCELTA (STOP OBBLIGATORIO)**.
Solo dopo la scelta: transpiler UXML + pulsante Riprova/Menu.
Screenshot `screenshots/043-ui-gameover.png`. Gate `docs/gates/11-ui-gameover.md`.

---

## PHASE juice (VFX + Audio + Game Feel)

Tu fai SOLO VFX, SFX CC0, hit-stop/shake. Leggi `vfx.md`, `audio-pipeline.md`, `juice.md`.
1. `execute_code`: `return GDS.VFX.CreateAll();` (+ Cartoon FX Free se `assetStore: yes`).
2. Collega: dust ai passi, pickup all'interact, hit al danno + hit-stop 3 frame + `CinemachineImpulseSource`, sparkle al win.
3. `fetch-cc0-audio.ps1 -ProjectPath PROJECT`; `AudioManager.cs` compilato 0 errori; istanza in `MainGame.unity`; passi/porte/UI click collegati.
4. Lint 0. Screenshot Play Mode durante un hit/pickup `screenshots/060-juice.png`.
5. NON dire "il gioco è finito".
Gate: `docs/gates/12-juice.md` + `Assets/_Game/Prefabs/VFX/` + `Assets/_Game/Audio/SFX/` popolate + console 0 errori + `lint:`.

---

## PHASE playtest

Tu fai SOLO QA. Leggi `playtest.md`, `scene-lint.md`.
1. `GDS.SceneLint.RunJson()` → `issues: 0` (altrimenti FAIL, non fixare tu: elenca).
2. Play Mode reale. WASD (MCP o TerminalMCP). Screenshot. Console 0 errori.
FAIL se dallo screenshot non si capisce l'obiettivo (manca testo HUD / prompt / menu).
FAIL se in Game View ci sono primitives Unity visibili (cubo/capsula default) o scena piatta senza Volume.
Scrivi `docs/playtest.md` e `docs/gates/13-playtest.md`.
NON inventare test verdi. Incolla job_id / output / lint JSON.

---

## PHASE slice

Tu fai SOLO il recap. Leggi tutti i `docs/gates/*.md`.
Se uno è rosso, NON dichiarare slice fatta. Elenca i rossi.
Gate: `docs/gates/14-slice.md`.

---

## Fine fase

`session-mode: continuous`: aggiorna GAME_TASKS.md + GAME_CONTEXT.md, il parent lancia la fase successiva.
`session-mode: hard-stop`: aggiorna GAME_TASKS.md + GAME_CONTEXT.md, stampa il banner in `session-cuts.md`, **FERMA**. Max 3 level-build (o hero-asset) nella stessa chat, poi STOP anche se la lista non e finita.
