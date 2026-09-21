# GAME_TASKS — Registro Task Atomici

> **Regola Anti-Pigrizia:** Vietati task aggregati (es. "modelli 3D", "sistema interazioni"). Ogni singola mesh, importazione, prefab, collider, script, posizionamento coordinate, hook UI e test deve avere un proprio ID e una propria riga. Un task è `[x]` solo con evidenza fisica verificata su disco (file GLB >15KB, PNG viewport, C# compilato con 0 errori, test verde o screenshot Play Mode).

## Stato Globale
- **Totale Task:** 0
- **Completati:** 0 (0%)
- **In Corso:** 0
- **Da Fare:** 0
- **Bloccati:** 0
- **Ultimo Checkpoint:** Nessuno

---

## Legenda Stati
- `[ ]` DA FARE (Pianificato, requisiti pronti)
- `[/]` IN CORSO (Worker attivo, file in modifica)
- `[x]` COMPLETATO (Verificato su disco con evidenza in `docs/gates/` o screenshot)
- `[!]` BLOCCATO (Errore compilazione, asset mancante, richiede intervento)

---

## 1. Scaffold & Setup Scena Base
| ID | Categoria | Descrizione Atomica Task | File Target / Destinazione | Verifica / Evidenza | Stato | Note |
|---|---|---|---|---|---|---|
| TASK-001 | Setup | Setup cartelle progetto (`Assets/_Game/{Scripts,Art,Prefabs,Scenes,UI}`) | `Assets/_Game/` | Cartelle su disco | [ ] | Base |
| TASK-002 | Setup | Creazione scena principale `MainGame.unity` con Lighting URP base | `Assets/_Game/Scenes/MainGame.unity` | File scena esistente | [ ] | Scena level |
| TASK-003 | Greybox | Creazione pavimento arena (plane 20x20m con BoxCollider) | `Assets/_Game/Scenes/MainGame.unity` | GameObject `Ground` | [ ] | Greybox |
| TASK-004 | Greybox | Setup CharacterController + script `PlayerController.cs` | `Assets/_Game/Scripts/PlayerController.cs` | Compilazione 0 errori | [ ] | Movimento |
| TASK-005 | Test | Test suite movimento player (`PlayerMovementTests.cs`) | `Assets/_Game/Tests/PlayerMovementTests.cs` | Unity Test Runner verde | [ ] | QA test |
| TASK-006 | QA | Screenshot greybox in Play Mode | `screenshots/010-greybox-play.png` | PNG su disco | [ ] | Gate greybox |

---

## 2. Kit CC0 (default) — un pezzo per riga
*Nota: source=kenney|kaykit. Blender solo se il kit non ha il pezzo.*
| ID | Categoria | Descrizione Atomica Task | File Target / Destinazione | Verifica / Evidenza | Stato | Note |
|---|---|---|---|---|---|---|
| TASK-009 | KitFetch | Download pack genere GDD (`fetch-cc0-kits.ps1`) | `art/cc0/` | Zip unzippato su disco | [ ] | Una famiglia |
| TASK-010 | Kit | Dress mura / tile pavimento da kit (`env_wall_a`) | `art/exports/env_wall_a.glb` | PNG `screenshots/030-import-env_wall_a.png` + collider | [ ] | source=kenney |
| TASK-011 | Kit | Dress tetto o modulo tetto kit (`env_roof`) | `art/exports/env_roof.glb` | PNG `screenshots/030-import-env_roof.png` | [ ] | source=kenney |
| TASK-012 | Kit | Dress porta battente kit (`door_leaf`) | `art/exports/door_leaf.glb` | PNG `screenshots/030-import-door_leaf.png` + pivot cardine | [ ] | source=kenney |
| TASK-013 | Kit | Dress tavolo kit furniture (`table_rustic`) | `art/exports/table_rustic.glb` | PNG `screenshots/030-import-table_rustic.png` | [ ] | source=kenney |
| TASK-014 | Kit | Dress sedia kit (`chair_rustic`) | `art/exports/chair_rustic.glb` | PNG `screenshots/030-import-chair_rustic.png` | [ ] | source=kenney |
| TASK-015 | Kit | Dress barile kit (`barrel_wood`) | `art/exports/barrel_wood.glb` | PNG `screenshots/030-import-barrel_wood.png` | [ ] | source=kenney |
| TASK-016 | PolyPizza | (OPZIONALE) Prop assente dal kit, import MCP | `art/exports/hero_relic.glb` | PNG `blender-hero_relic-2-import.png` + GLB | [ ] | source=polypizza |

---

## 3. Importazione Unity, Prefab & Collider
| ID | Categoria | Descrizione Atomica Task | File Target / Destinazione | Verifica / Evidenza | Stato | Note |
|---|---|---|---|---|---|---|
| TASK-020 | Import | Importazione GLB mura e tetto in Unity con materiali URP Lit | `Assets/_Game/Art/Props/House/` | Asset .mat e texture | [ ] | Scale 1u=1m |
| TASK-021 | Prefab | Creazione prefab `House.prefab` con MeshCollider statici | `Assets/_Game/Prefabs/House.prefab` | Prefab valido in Assets | [ ] | Static geometry |
| TASK-022 | Prefab | Creazione prefab `Door.prefab` (anta + maniglia + BoxCollider trigger) | `Assets/_Game/Prefabs/Door.prefab` | Prefab valido con trigger | [ ] | Interattivo |
| TASK-023 | Prefab | Creazione prefab `TableRustic.prefab` e `ChairRustic.prefab` | `Assets/_Game/Prefabs/Furniture/` | Prefab con BoxCollider | [ ] | Arredo |
| TASK-024 | Prefab | Creazione prefab `Barrel.prefab` con Rigidbody/Collider | `Assets/_Game/Prefabs/Props/` | Prefab con fisica | [ ] | Prop |

---

## 4. Allestimento e Posizionamento Scena (Level Dressing)
| ID | Categoria | Descrizione Atomica Task | Coordinate / Parent | Verifica / Evidenza | Stato | Note |
|---|---|---|---|---|---|---|
| TASK-030 | Scena | Istanziazione `House.prefab` nell'arena a coordinate (0, 0, 15) | Pos: (0, 0, 15) Rot: (0, 0, 0) | GameObject presente in scena | [ ] | Edificio principale |
| TASK-031 | Scena | Istanziazione `Door.prefab` nel vano porta della casa | Pos locale porta casa | Cerniera allineata al muro | [ ] | Cardine funzionante |
| TASK-032 | Scena | Posizionamento `TableRustic.prefab` all'interno della casa | Pos: (1.5, 0, 16.5) | Contatto piano terra verificato | [ ] | Interno |
| TASK-033 | Scena | Posizionamento 2x `ChairRustic.prefab` attorno al tavolo | Pos: (1.5, 0, 15.8) e (1.5, 0, 17.2) | Orientate verso tavolo | [ ] | Interno |
| TASK-034 | Scena | Posizionamento 3x `Barrel.prefab` all'esterno lungo il muro nord | Pos: (-3.2, 0, 13.5), (-3.2, 0, 14.3) | Scatter esterno | [ ] | Props esterni |

---

## 5. Scripting Gameplay, Interazioni e Verbi GDD
| ID | Categoria | Descrizione Atomica Task | File Script / Componente | Verifica / Evidenza | Stato | Note |
|---|---|---|---|---|---|---|
| TASK-040 | Script | Creazione interfaccia interazione `IInteractable.cs` | `Assets/_Game/Scripts/Interactions/IInteractable.cs` | Compilazione C# 0 errori | [ ] | Core interface |
| TASK-041 | Script | Creazione script `DoorInteractable.cs` (apri/chiudi, anim slerp, audio hook) | `Assets/_Game/Scripts/Interactions/DoorInteractable.cs` | Compilazione C# 0 errori | [ ] | Gestione porta |
| TASK-042 | Hook | Assegnazione componente `DoorInteractable` a `Door.prefab` | `Door.prefab` inspector | Componente collegato | [ ] | Setup prefab |
| TASK-043 | Script | Implementazione Raycast/Trigger interazione su `PlayerController` | `PlayerController.cs` | Rilevamento `IInteractable` | [ ] | Input [E] |
| TASK-044 | Test | Test automatico apertura porta (`DoorInteractionTests.cs`) | `Assets/_Game/Tests/DoorInteractionTests.cs` | Test runner PASS | [ ] | Unit/Play test |

---

## 6. UI Toolkit, HUD e Menù
| ID | Categoria | Descrizione Atomica Task | File Target | Verifica / Evidenza | Stato | Note |
|---|---|---|---|---|---|---|
| TASK-050 | UI | Scena `MainMenu.unity` con UI Toolkit, bottone Gioca ed Esci | `Assets/_Game/Scenes/MainMenu.unity` | Build Index 0 + Screenshot | [ ] | Obbligatorio |
| TASK-051 | UI | HUD in-game UXML/USS con indicatore obiettivo testuale | `Assets/_Game/UI/HUD.uxml` | UIDocument in `MainGame` | [ ] | Obiettivo a video |
| TASK-052 | UI | Prompt interazione contestuale `[E] Apri Porta` a centro schermo | `Assets/_Game/UI/HUD.uxml` | Appare solo in prossimità | [ ] | Feedback visivo |
| TASK-053 | UI | Menù Pausa con tasto Esc, riprendi e ritorno al menù | `Assets/_Game/UI/PauseMenu.uxml` | Time.timeScale = 0 | [ ] | Pausa |
| TASK-054 | UI | Schermata Vittoria / GameOver con pulsante Riprova | `Assets/_Game/UI/GameOverMenu.uxml` | Trigger fine partita | [ ] | Win/Fail |

---

## 7. QA, Playtest & Vertical Slice Gate
| ID | Categoria | Descrizione Atomica Task | File Output / Evidenza | Criterio Accettazione | Stato | Note |
|---|---|---|---|---|---|---|
| TASK-060 | QA | Esecuzione Playtest interazione completa in Play Mode | `screenshots/025-door-interaction.png` | Porta aperta + prompt [E] | [ ] | Funzionale |
| TASK-061 | QA | Screenshot gameplay completo con HUD e modelli finali | `screenshots/050-vertical-slice.png` | Nessun cubo visibile, HUD chiaro | [ ] | Qualità visiva |
| TASK-062 | Slice | Verifica finale tutti i gate e redazione report slice | `docs/gates/12-slice.md` | Tutti i gate PASS | [ ] | Chiusura |
