# GAME_CONTEXT — Snapshot Globale di Progetto

> **Scopo:** Questo file è la "memoria centrale" del gioco. Contiene ogni dettaglio su gameplay, game loop, architettura, script, chi possiede tali script, mappa degli oggetti nella scena e locazione fisica dei file. Permette a qualsiasi istanza o nuovo thread (tramite `/resumegame`) di riprendere all'istante senza perdita di contesto né allucinazioni.

---

## 1. Identità e Visione del Gioco
- **Titolo Gioco:** `[Nome Gioco da GDD]`
- **Pitch (One-Liner):** `[Descrizione del gioco in una frase]`
- **Genere:** `[es. 3D Action Adventure / Survival / Puzzle]`
- **Target Audience & Mood:** `[es. Atmosferico, medievale low-poly, ritmo calmo ma teso]`
- **Stile Visivo & Palette:** `[es. Low-poly stilizzato, URP Lit, palette: #2c3e50, #8e44ad, #f39c12]`
- **Scala Mondo:** `1 unità Unity = 1 metro reale`

### Core Game Loop
1. **Loop dei 30 Secondi:** `[Cosa fa il giocatore istante per istante: es. Esplora l'ambiente, cerca porte/oggetti interattivi, raccoglie risorse]`
2. **Loop dei 3 Minuti:** `[Obiettivo a medio termine: es. Trova la chiave per la casa padronale, sblocca la porta, raccoglie l'artefatto]`
3. **Loop di Livello (Macro):** `[Ciclo completo della vertical slice: Start dal Main Menu -> Esplorazione villaggio -> Risoluzione puzzle/porta -> Condizione di Vittoria]`

### Condizioni di Vittoria e Sconfitta
- **Condizione Vittoria (Win):** `[es. Raggiungi la casa, apri la porta chiusa e raccogli l'artefatto prima dello scadere del tempo]`
- **Condizione Sconfitta (Fail):** `[es. Timer azzerato oppure caduta fuori dall'arena]`

### Controlli & Input
- **Movimento:** `WASD` / Stick Sinistro
- **Visuale / Telecamera:** `Mouse Delta` / Stick Destro
- **Interazione Verbo Primario:** `[E]` / Tasto Azione (Apri porte, esamina oggetti, raccogli)
- **Pausa Menù:** `[Esc]` (Congela il gioco tramite `Time.timeScale = 0`)

---

## 2. Architettura Tecnica & Setup Engine
- **Engine:** Unity `[6000.x]` URP (stile realistico: Unreal 5.8, vedi unreal-loop.md)
- **Percorso Assoluto Progetto:** `[Path cartella Unity sul disco]`
- **Build Settings:** `Index 0` `Assets/_Game/Scenes/MainMenu.unity` (obbligatorio) · `Index 1` `Assets/_Game/Scenes/MainGame.unity`
- **Ponte Unity:** Unity CLI (`unity command gds_*`, `eval`, `run_tests`) primario; CoplayDev unity-mcp solo fallback
- **Art:** famiglia `[kenney|kaykit|quaternius|synty]` in `art/cc0/` + `art/kit-catalog.json`; hero prop via Blender MCP (`uvx mcp-for-blender` stdio); gen3d solo se il GDD lo permette
- **Look:** preset `[gds_lookdev preset]`, palette `[hex...]`
- **Git:** repo nel progetto, commit di checkpoint ogni 10 task (vedi task-decomposition.md)

---

## 3. Registro Script C# — Chi fa Cosa & Component Mapping
*Nota: Ogni script compilato deve essere censito qui con scopo, chi lo possiede e dipendenze.*

| Script | Percorso File | Scopo / Logica | Chi ha questo Script (GameObject / Prefab) | Dipendenze / Serialized Fields | Eventi & Interfacce |
|---|---|---|---|---|---|
| `PlayerController` | `Assets/_Game/Scripts/PlayerController.cs` | Movimento WASD, gravità, raycast interazione centrale | `Player` (GameObject in scena / `Player.prefab`) | `CharacterController`, `Camera`, `interactDistance`, `interactionLayer` | Invoca `IInteractable.Interact()` |
| `IInteractable` | `Assets/_Game/Scripts/Interactions/IInteractable.cs` | Interfaccia per tutti gli elementi del mondo interattivi | Nessuno (Interface) | Nessuna | `string GetInteractionPrompt()`, `void Interact(GameObject user)` |
| `DoorInteractable` | `Assets/_Game/Scripts/Interactions/DoorInteractable.cs` | Gestisce apertura/chiusura cardine porta, rotazione slerp e SFX | `Door.prefab` (assegnato al cardine) | `Transform doorHinge`, `AudioSource`, `isOpen`, `openAngle` | Implementa `IInteractable` |
| `GameManager` | `Assets/_Game/Scripts/Core/GameManager.cs` | Gestione stato di gioco (Playing, Paused, Won, Lost) | `[GameController]` (GameObject persistente) | `HUDController`, `PauseMenuController` | Eventi `OnGameWin`, `OnGameFail` |
| `HUDController` | `Assets/_Game/Scripts/UI/HUDController.cs` | Aggiorna testo obiettivo a video e prompt `[E] Interagisci` | `UIDocument` in scena `MainGame` | `UIDocument`, `VisualElement promptLabel`, `VisualElement objectiveLabel` | Ascolta Raycast player |

---

## 4. Mappa della Scena — GENERATA
Non scrivere oggetti o coordinate a mano qui: invecchiano al primo rebuild. La mappa vera è `docs/scene-map.md`, rigenerata con `unity command gds_scene_map` a ogni checkpoint (o `eval "return GDS.SceneMap.WriteJson();"`). Le posizioni autoritative stanno nei JSON (`art/world/`, `art/blueprints/`, village spec).

---

## 5. File Manifest del Progetto (Locazione Fisica)
*Dizionario completo dei file generati per evitare dispersioni o duplicazioni.*

- **Script C#:**
  - `Assets/_Game/Scripts/PlayerController.cs`
  - `Assets/_Game/Scripts/Interactions/IInteractable.cs`
  - `Assets/_Game/Scripts/Interactions/DoorInteractable.cs`
  - `Assets/_Game/Scripts/Core/GameManager.cs`
  - `Assets/_Game/Scripts/UI/HUDController.cs`
- **Kit & GLB:**
  - `art/cc0/` (pack scaricati)
  - `art/exports/env_wall_a.glb`
  - `art/exports/door_leaf.glb`
  - `art/exports/table_rustic.glb`
  - `art/exports/chair_rustic.glb`
  - `art/exports/barrel_wood.glb`
- **Prefab Unity:**
  - `Assets/_Game/Prefabs/House.prefab`
  - `Assets/_Game/Prefabs/Door.prefab`
  - `Assets/_Game/Prefabs/Furniture/TableRustic.prefab`
  - `Assets/_Game/Prefabs/Furniture/ChairRustic.prefab`
  - `Assets/_Game/Prefabs/Props/Barrel.prefab`
- **Scene:**
  - `Assets/_Game/Scenes/MainMenu.unity`
  - `Assets/_Game/Scenes/MainGame.unity`
- **UI Toolkit:**
  - `Assets/_Game/UI/MainMenu.uxml` & `MainMenu.uss`
  - `Assets/_Game/UI/HUD.uxml` & `HUD.uss`
  - `Assets/_Game/UI/PauseMenu.uxml`
- **Gate e Verifiche:**
  - `docs/gates/` (contiene file di log e stato delle fasi)
  - `screenshots/` (contiene catture viewport Blender e Play Mode)

---

## 6. Decisioni (solo aggiunte in coda, una riga ciascuna, mai riscrivere le vecchie)
- `[YYYY-MM-DD HH:MM]` **Scaffold Iniziale:** Creata struttura directory `Assets/_Game/`.
- `[YYYY-MM-DD HH:MM]` **Greybox PASS:** Movimento base validato con test `PlayerMovementTests.cs`.
- `[YYYY-MM-DD HH:MM]` **Decisione Rendering:** Scelto URP Lit con palette desaturata per enfatizzare l'atmosfera rustica medievale.

---

## 7. Stato Attuale e Puntatore di Ripresa Immediata
- **Ultimo Task Completato:** `[ID es. TASK-006]`
- **Task Attuale in Esecuzione:** `[ID es. TASK-010]`
- **Prossimo Task Immediato:** `[ID es. TASK-011]`
- **Istruzione Esatta per chi riprende (`/resumegame`):**
  > Eseguire `TASK-010`: kit-dress `env_wall_a` da `art/cc0/`, copiare in `art/exports/`, prefab+collider, screenshot `screenshots/030-import-env_wall_a.png`, gate `docs/gates/07-kit-env_wall_a.md`.
