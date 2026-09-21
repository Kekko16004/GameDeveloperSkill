# Decomposizione Task Atomici (Anti-Pigrizia)

La causa principale per cui gli agenti LLM chiudono frettolosamente lo sviluppo di un gioco (*"ho creato 3 script e un cubo, gioco completato"*) è l'assenza di granularità forzata nei task.

Quando un task è formulato a livello macro (es. *"crea casa medievale e arredamento"*), il modello converge al minimo sforzo consentito.
**Regola Fondamentale:** È TASSATIVAMENTE VIETATO creare task raggruppati o generici.

---

## I 6 Livelli di Decomposizione Obbligatoria

Ogni elemento del GDD (ambiente, oggetto interattivo, NPC, prop, meccanica) deve essere esploso in `GAME_TASKS.md` attraverso i seguenti livelli atomici:

### Livello 1: Mesh 3D Singola (Blender / Voxel / CC0)
- Un solo prop per riga.
- Mai *"crea mobili"*. Sempre:
  - `TASK-XXX`: Modella sedia in legno (`chair.glb`)
  - `TASK-XXX`: Modella tavolo da pranzo (`table.glb`)
  - `TASK-XXX`: Modella porta singola con cardine (`door_leaf.glb`)
  - `TASK-XXX`: Modella maniglia ferro (`door_handle.glb`)
- Evidenza richiesta: File `.glb` > 15KB + screenshot viewport `.png`.

### Livello 2: Importazione e Materiali Unity
- Setup importazione URP Lit, scala 1u=1m.
- Generazione materiali e assegnazione texture/colori da palette GDD.
- Evidenza richiesta: File `.mat` e prefab/asset importato in `Assets/_Game/Art/`.

### Livello 3: Creazione Prefab & Setup Collider
- Creazione prefab dedicato con gerarchia pulita.
- Aggiunta Collider appropriati (MeshCollider non-convex solo per statici, BoxCollider/CapsuleCollider per trigger e props fisici).
- Aggiunta Rigidbody se prop dinamico.
- Evidenza richiesta: Prefab salvato in `Assets/_Game/Prefabs/`.

### Livello 4: Allestimento Scena (Scene Placement a Coordinate Precise)
- Nessun posizionamento casuale. Ogni istanziazione deve avere coordinate (X, Y, Z) esplicite nel task.
- Esempi:
  - `TASK-XXX`: Posiziona `House.prefab` a coordinate (0, 0, 15)
  - `TASK-XXX`: Posiziona `TableRustic.prefab` all'interno della casa a (1.5, 0, 16.5)
  - `TASK-XXX`: Posiziona 2x `ChairRustic.prefab` orientate verso il tavolo
  - `TASK-XXX`: Posiziona 3 barili esterni lungo il muro perimetrale a (-3.2, 0, 13.5)
- Evidenza richiesta: GameObject presente nella gerarchia della scena `MainGame.unity`.

### Livello 5: Scripting Gameplay & Interazioni Atomiche
- Singola responsabilità: uno script fa una sola cosa.
- Chi possiede lo script deve essere definito prima della scrittura del codice.
- Interfacce standard (es. `IInteractable`).
- Esempi:
  - `TASK-XXX`: Crea interfaccia `IInteractable.cs`
  - `TASK-XXX`: Crea script `DoorInteractable.cs` con rotazione slerp
  - `TASK-XXX`: Assegna `DoorInteractable` a `Door.prefab`
  - `TASK-XXX`: Aggiungi Raycast centrale su `PlayerController.cs` per rilevare `IInteractable`
- Evidenza richiesta: Script compilato con 0 errori in Unity Console (`read_console`).

### Livello 6: UI Hook & Feedback Visivo
- Mostrare a schermo cosa sta succedendo.
- Esempi:
  - `TASK-XXX`: Crea prompt visivo `[E] Apri Porta` in UI Toolkit HUD
  - `TASK-XXX`: Collega visibilità del prompt al Raycast del player
- Evidenza richiesta: Prompt visibile a schermo durante il Playtest.

### Livello 7: QA Playtest Atomico
- Screenshot Play Mode che dimostri il funzionamento della specifica feature.
- Evidenza richiesta: PNG in `screenshots/` con prova visiva inconfutabile.

---

## Ciclo di Vita di un Task in `GAME_TASKS.md`
1. Il parent / orchestratore seleziona il primo task con stato `[ ]`.
2. Imposta lo stato a `[/]` prima di iniziare l'operazione.
3. Lancia il worker dedicato o esegue il comando.
4. Esegue il controllo del gate (verifica che il file o l'output esista su disco).
5. Se il controllo passa, aggiorna a `[x]` e aggiunge il riferimento all'evidenza.
6. Se fallisce, imposta a `[!]`, logga l'errore e ritenta (max 2 volte).
7. Aggiorna `GAME_CONTEXT.md` con i progressi.
