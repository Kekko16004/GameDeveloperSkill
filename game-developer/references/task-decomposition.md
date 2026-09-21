# Decomposizione Task Atomici (Anti-Pigrizia)

La causa principale per cui gli agenti LLM chiudono frettolosamente lo sviluppo di un gioco (*"ho creato 3 script e un cubo, gioco completato"*) è l'assenza di granularità forzata nei task.

Quando un task è formulato a livello macro (es. *"crea casa medievale e arredamento"*), il modello converge al minimo sforzo consentito.
**Regola Fondamentale:** È TASSATIVAMENTE VIETATO creare task raggruppati o generici.

---

## I 6 Livelli di Decomposizione Obbligatoria

Ogni elemento del GDD (ambiente, oggetto interattivo, NPC, prop, meccanica) deve essere esploso in `GAME_TASKS.md` attraverso i seguenti livelli atomici:

### Livello 1: Blueprint (edifici / stanze / aree) e hero asset
- **Un task per blueprint**, non per pezzo. Il blueprint contiene shell + prop interni + scatter esterno ([level-builder.md](level-builder.md)).
  - `TASK-XXX`: BP-house_a — casa 3x2 celle, 1 piano, porta S1, finestra N0, tetto kit, interni: tavolo, 2 sedie, baule; origine (0,0,12) rot 0 (source=kenney)
  - `TASK-XXX`: BP-courtyard — scatter 25 alberi + 8 rocce, avoidRadius 14 (source=kenney nature)
  - `TASK-XXX`: BP-keep — mode probuilder 3x2 celle 2 piani gable, materiale Mat_Palette_2
- **Un task per hero asset** (solo ciò che nessun kit ha):
  - `TASK-XXX`: HERO-prop_relic — Poly Pizza "ancient relic" → se assente tier gen3d GDD (max 1 credito-run)
- Mai *"crea mobili"*, mai *"piazza muro 1..40"*, mai *"modella in Blender la cassa"* se il kit ce l'ha.
- Evidenza blueprint: `art/blueprints/<name>.json` + `docs/lint/build-<name>.json` PASS + `screenshots/020-build-<name>.png` + lint 0.
- Evidenza hero: GLB > 15KB + `blender-<id>.png` + riga ledger + rebuild blueprint.

### Livello 2: Importazione e Materiali Unity
- Setup importazione URP Lit, scala 1u=1m.
- Generazione materiali e assegnazione texture/colori da palette GDD.
- Evidenza richiesta: File `.mat` e prefab/asset importato in `Assets/_Game/Art/`.

### Livello 3: Creazione Prefab & Setup Collider
- Creazione prefab dedicato con gerarchia pulita.
- Aggiunta Collider appropriati (MeshCollider non-convex solo per statici, BoxCollider/CapsuleCollider per trigger e props fisici).
- Aggiunta Rigidbody se prop dinamico.
- Evidenza richiesta: Prefab salvato in `Assets/_Game/Prefabs/`.

### Livello 4: Allestimento Scena (coordinate nel blueprint, non nella chat)
- Le coordinate stanno in `art/blueprints/PLAN.md` (origine/rotazione di ogni blueprint sulla griglia 4 m) e nelle righe `props`/`scatter` dei JSON (relative all'origine del blueprint).
- Il piazzamento lo esegue `GDS.LevelBuilder` (allineamento per bounds + raycast a terra); il gate e `GDS.SceneLint` `issues: 0`.
- Esempi PLAN.md:
  - `BP-house_a | origin (0,0,12) | rotY 0 | 3x2 | ingresso verso S`
  - `BP-keep | origin (20,0,0) | rotY 90 | 3x2 x2 piani`
- Evidenza richiesta: `docs/lint/build-<name>.json` + `docs/lint/scene-lint.json` con `issues: 0`.

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

## Gestione Asset 3D Forniti dall'Utente (User-Provided Asset Protocol)

Se nel GDD è stato impostato `asset-strategy: user-provided` oppure `hybrid`:

1. **Generazione Immediata del Manifesto (`art/ASSET_MANIFEST.md`)**:
   L'agente genera la lista completa degli asset necessari prima di iniziare lo sviluppo, specificando:
   - **Cartella di destinazione**: `art/exports/` (o cartella scelta nel progetto).
   - **Nome file obbligatorio**: es. `building_house.glb`, `prop_chest.glb`.
   - **Dimensioni stimate (X, Y, Z)** in metri (scala 1u=1m).
   - **Vincolo di Pivot**: base a terra $Y=0$ (Unity Y-up), centro $X=0, Z=0$. Se il pivot e sbagliato non importa: il builder allinea per bounds.
   - **Formato**: `.glb` (raccomandato per materiali PBR) o `.fbx`.

2. **Formulazione dei Task in `GAME_TASKS.md`**:
   - `TASK-XXX: [WAIT-USER-ASSET] Fornitura prop_nome.glb da parte dell'utente in art/exports/`
   - `TASK-YYY: Verifica presenza e validazione metrica prop_nome.glb`
   - `TASK-ZZZ: Importazione e creazione Prefab Unity da prop_nome.glb`

3. **Ripresa con `/resumegame` ("Ho messo i modelli")**:
   Quando l'utente inserisce i file e notifica l'agente o lancia `/resumegame`:
   - L'agente scansiona la cartella: `Test-Path "art/exports/prop_nome.glb"`.
   - Se il file esiste, valida la dimensione (> 5KB) e l'integrità.
   - Segna il task `[x]`, aggiorna `GAME_CONTEXT.md` come `asset_ready: true`.
   - Procede immediatamente alla creazione dei materiali URP, Prefabs e allestimento della scena.

---

## Ciclo di Vita di un Task in `GAME_TASKS.md`
1. Il parent / orchestratore seleziona il primo task con stato `[ ]`.
2. Imposta lo stato a `[/]` prima di iniziare l'operazione.
3. Lancia il worker dedicato o esegue il comando.
4. Esegue il controllo del gate (verifica che il file o l'output esista su disco).
5. Se il controllo passa, aggiorna a `[x]` e aggiunge il riferimento all'evidenza.
6. Se fallisce, imposta a `[!]`, logga l'errore e ritenta (max 2 volte).
7. Aggiorna `GAME_CONTEXT.md` con i progressi.
