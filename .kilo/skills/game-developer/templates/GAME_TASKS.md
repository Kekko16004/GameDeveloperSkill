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

## 2. Modellazione 3D Atomica (Blender / Voxel / CC0)
*Nota: Un prop per riga. Vietato raggruppare.*
| ID | Categoria | Descrizione Atomica Task | File Target / Destinazione | Verifica / Evidenza | Stato | Note |
|---|---|---|---|---|---|---|
| TASK-010 | Blender | Modellazione struttura esterna mura casa (`house_walls`) | `art/exports/house_walls.glb` | PNG `screenshots/blender-house_walls.png` + GLB >15KB | [ ] | Mesh mura |
| TASK-011 | Blender | Modellazione tetto a falde e travi in legno (`house_roof`) | `art/exports/house_roof.glb` | PNG `screenshots/blender-house_roof.png` + GLB >15KB | [ ] | Mesh tetto |
| TASK-012 | Blender | Modellazione porta legno battente pivot su cardine (`door_leaf`) | `art/exports/door_leaf.glb` | PNG `screenshots/blender-door_leaf.png` + GLB >15KB | [ ] | Pivot X=0, Y=0 |
| TASK-013 | Blender | Modellazione maniglia/chiavistello ferro battuto (`door_handle`) | `art/exports/door_handle.glb` | PNG `screenshots/blender-door_handle.png` + GLB >15KB | [ ] | Dettaglio |
| TASK-014 | Blender | Modellazione tavolo rustico in legno per interni (`table_rustic`) | `art/exports/table_rustic.glb` | PNG `screenshots/blender-table_rustic.png` + GLB >15KB | [ ] | Arredo |
| TASK-015 | Blender | Modellazione sedia in legno coordinata (`chair_rustic`) | `art/exports/chair_rustic.glb` | PNG `screenshots/blender-chair_rustic.png` + GLB >15KB | [ ] | Arredo |
| TASK-016 | CC0/Mesh | Reperimento/Modellazione barile esterno (`barrel_wood`) | `art/exports/barrel_wood.glb` | PNG `screenshots/blender-barrel_wood.png` + GLB >15KB | [ ] | Prop esterno |

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
