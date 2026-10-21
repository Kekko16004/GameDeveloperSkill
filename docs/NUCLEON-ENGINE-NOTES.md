# Nucleon Engine — bug e lacune trovati dalla skill (2026-10-21)

Trovati costruendo davvero con la skill (editor compilato da `main@d8e49bc`, Linux, Xvfb, llvmpipe) la demo
`docs/samples/nucleon-glade-*.jpg` e i test di `ncli.py`. Ogni voce ha la riproduzione e cosa ho misurato; dove dico
"ipotesi" non l'ho verificato nel codice. Ordine: impatto sul fare giochi belli e veloci.
Niente è stato cambiato nel repository dell'engine: le correzioni vanno fatte lì con il suo flusso (un branch + PR per tappa).

## A. Rendering

### A1. Modelli piccoli ripetuti disegnati con il materiale sbagliato (marroni, semitrasparenti) — ALTA
- **Riproduzione:** livello con ~200 copie di `tree_single_A.gltf` (KayKit Medieval Hexagon, 95 vertici, un materiale con
  `baseColorTexture`) + 40 copie di `trees_A_medium.gltf` (900 vertici, stesso materiale e stessa texture).
- **Visto:** i 200 alberi singoli sono coni marroni piatti e semitrasparenti (si vedono le case dietro), i 40 boschetti sono giusti.
  Foto: `docs/samples/nucleon-bug-instancing.jpg` (sinistra: default, destra: `NC_INSTANCING=0`).
- **Escluso:** mipmap (`import.mipmaps=false` non cambia), compressione texture (`NC_NO_TEXTURE_COMPRESSION=1`), pool texture,
  retained scene (`NC_RETAINED_SCENE=0` non cambia). Con `NC_INSTANCING=0` tutti gli alberi sono giusti.
- **Statistiche** (`Lighting.getStats()`, stessa vista): con instancing `gpuDriven=true`, `gdClasses=14`, `gdIndirectDraws=53`,
  `instanceBatches=6`, `instancedItems=21450`, `drawCalls=128` (844 senza batch); con `NC_INSTANCING=0` anche `gpuDriven=false` e
  `retainedItems=0`.
- **Ipotesi:** nel percorso GPU-driven/instanced "il materiale viene dal draw block del primo elemento" (LIGHTING.md "Instancing"): la
  classe non distingue qualcosa che questi elementi hanno diverso (fade/dither del LOD, binding della texture), oppure il fade di un
  elemento in transizione LOD viene applicato a tutta la classe (spiegherebbe la semitrasparenza).
- **Effetto:** qualunque foresta o set di prop ripetuti (il caso tipico di un gioco) esce sbagliato con le impostazioni di default.

### A2. `NC_INSTANCING=0` spegne anche GPU-driven, retained scene e foliage — MEDIA
Il nome dice "instancing", ma con lo switch spariscono anche l'erba (foliage) e il percorso GPU-driven. Serve uno switch per ogni
meccanismo, oppure la documentazione deve dirlo.

### A3. Il foliage non accetta modelli (solo carte, billboard, forme procedurali) — ALTA per i giochi
Gli alberi di un kit (glTF) devono diventare entità del livello: migliaia di entità invece di istanze del foliage (come HISM / Foliage
Tool in Unreal o il terrain detail di Unity). È già scritto in COMPETITOR_PLAN 2.3 ("Not done: foliage types that use models with
LODs"). Per la skill è la lacuna più grande sui mondi naturali.

### A4. Foresta: frame alto e scatti (dal repository, non rimisurato qui: qui non c'è una GPU)
Da `docs/performance/PERFORMANCE.md`: ForestDemo GPU 23-30 ms contro un obiettivo di 14 ms (RTX 5060, High); scatti del main thread
`World stream: load cell` 190-260 ms e `HLOD proxies` 60 ms; molte correzioni della "wave 1" sono "built, not run" e vanno provate su
Windows; le passate d'ombra disegnano ogni chunk del terreno visibile in ogni cascata (niente culling per cascata); niente ombre
oltre la distanza degli impostor. Con llvmpipe i ms non valgono (qui `cpuEndMs` ~700 ms = attesa del rasterizzatore software).
Il gate di performance della skill (`ncli play-test --fps N`) va fatto girare sulla GPU vera.

### A5. Hidden shapes still collide — LOW
`visible = false` hides a shape but leaves its collider (the template's hidden `Ground` box stayed a floor under the landscape).
If that's intended, it needs a separate "collision off" option and a mention in the docs.

## B. Editor MCP (the way an agent drives the editor)

### B1. `capture_viewport` doesn't wait for models still being imported/cooked — HIGH for automated QA
After deleting `Saved/DDC` (or changing an import setting) the screenshots come out **without the houses** (only their shadows) or
without the trees, even though the tool calls `finishLoading()`. The wait has to include the cook of virtualized meshes and the
reimports, or the result needs a `pending: n` field.

### B2. `scene_list` filters by `type: "terrain"` but the type is called `landscape` — MEDIUM
`entityTypeName(EntityType::Terrain)` returns "Landscape", while the tool's enum offers "terrain": the filter never finds anything.

### B3. The `nucleon://docs/editor-guide` resource says "+Y is up" and rotation (X, Y, Z) — MEDIUM
The tools work in Z up with `[pitch, roll, yaw]` (MCP.md): an agent that reads the guide gets the axes wrong.

### B4. Things the MCP can't do (an agent has to edit files with the editor closed) — HIGH
Create/sculpt/paint a landscape, foliage, water, fog volume, post-process volume, particles/effects, decals (`entity_add` only covers
empty, light, shape, playerstart, reflection_capture, audio*, folder, model, actor); the level's `lighting` table (post process, fog,
sky); Project Settings; Game View on/off (no command id); importing settings for an asset (`import` in AssetDatabase.json).
The skill works around this with headless Lua scripts and level patches, but every patch requires closing the editor.

### B5. `capture_viewport` captures at the size of the viewport — MEDIUM
In a 1600×900 window the image is 859×796; there's no way to ask for 1920×1080 (store, trailer). An offscreen render at a chosen
resolution is needed.

### B6. In Play In Editor `TakeScreenshot` captures the whole editor window — MEDIUM
For the game view, the skill has to hand off to MCP `capture_viewport` (gds_capture.lua handshake).

## C. Lua API / natives

### C1. Native registry with the wrong arity — MEDIUM
- `SetAnimationParameter(entity, name, value)`: `value` is documented "leave it out to fire a trigger" but has `optional: false`.
- The trailing `...` parameters are marked required: `TriggerEvent`, `TriggerServerEvent`, `TriggerClientEvent`, `CallOnServer`,
  `CallOnOwner`, `CallOnAll`, `SendNetworkMessage`, `SendNetworkMessageToPlayer`.

Effect: `NATIVES.md`, the LuaLS annotations and the Blueprint nodes show wrong arities. (The skill corrects them in its snapshot,
`ncli api-refresh`.)

### C2. `GetFrameTime` is capped at 0.1 s — LOW
Below 10 fps every frame reads 100 ms: perf measurements read "100 ms" instead of the real value. Documenting it is enough.

## Suggestions to get to UE / Unity / Godot level for an agent
1. MCP tools for landscape (create/import heightmap/paint layer/foliage) and for the level's `lighting` table.
2. `capture_viewport` with resolution, view mode "game" (no icons/grid) and wait for full loading.
3. Foliage with models + LOD + impostors (A3) and the A1 fix: forests made of kit models, cheap.
4. A "scene stats" tool (draw calls, instancing, GPU ms per pass) to make performance gates automatic.
5. A headless test runner (`-run-tests`) that runs Content/Scripts in Play without a window and returns an exit code.
