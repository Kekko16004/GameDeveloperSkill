# Unity editor loop (CoplayDev MCP)

Load `unity-mcp-orchestrator` if that skill is installed. This file is the game-slice overlay.

Package git URL: `https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity`

## Preflight

Read `mcpforunity://editor/state`. Wait until `ready_for_tools` and not compiling. If Safe Mode / compile errors: fix scripts first.

`batch_execute` for 2+ independent creates (max 25).

## Greybox scene

```
manage_scene(action="create", name="Slice", path="Assets/_Game/Scenes/")
```

Ground: scaled cube or ProBuilder plane at y=0. Player empty + CharacterController (or Rigidbody kinematic) + camera per GDD.

**Input System** (not old Input): Actions `Move` (Vector2 WASD), `Look`, `Jump`, `Interact`, `Pause`. Generate C# class. Player reads that asset — never `Input.GetAxis("Horizontal")`.

## Scripts

1. `create_script` under `Assets/_Game/Scripts/`
2. Poll editor state until not compiling
3. `read_console(types=["error"], include_stacktrace=true)`
4. Only then `manage_gameobject` add component

## Tests — mandatory per verb

Put tests in `Assets/_Game/Scripts/Tests/` assembly (`Editor` or PlayMode).

For `move`:

- EditMode: PlayerController applies a known input vector and transform.position.x increases
- or PlayMode: enter play, inject input, assert position delta after 0.5s

For `jump` / `interact` / `win` / `pause`: one test each, named `Verb_DoesX`.

Run them in the same turn you add the verb:

```
run_tests(mode="EditMode")   # MCP
```

or `unity test <project> --mode EditMode --format json`

Red test = fix before art. Do not skip with “will test later”.

## Play Mode probe (feel)

After tests pass:

1. Screenshot Game view → copy to `screenshots/`
2. Enter Play Mode
3. If MCP can send input, send WASD for ~1s, screenshot again
4. Else: TerminalMCP `screen` + `input` on the Game window **only as fallback**
5. `read_console` errors
6. Exit Play Mode

Write results into `docs/playtest.md`.

## Import art

Copy `art/exports/*.glb` → `Assets/_Game/Art/`. Scale 1, generate colliders (box/convex), no cameras/lights from the file (strip if present). Prefab in `Prefabs/`.

## Camera & Post-Processing
Cinemachine follow/third-person/top-down da GDD. Aggiungere `CinemachineImpulseSource` sul player o su eventi di impatto per il camera shake. Creare un GameObject `Global_Volume` con Bloom, Color Adjustments e Vignette per rifinire lo stile visivo. `manage_camera screenshot` con `include_image=true`, `max_resolution=512`, poi salvare copia in `screenshots/`.

## ProBuilder — geometria di livello (default greybox)
Usa `manage_probuilder` (vedi [probuilder-levels.md](probuilder-levels.md)), non bpy.
- ping → create_shape Cube/Plane/Stair/Door allineati al Geometra (parete 4×3×0.2, porta 1×2.2).
- get_mesh_info include=faces prima di extrude/delete (indici instabili).
- center_pivot, validate_mesh, screenshot.
- Kit Kenney/KayKit vestono le facce; ProBuilder può restare come collision.

## VFX Graph & Feedback Visivo
VFX Graph viene orchestrato direttamente dai componenti C# creati dall'agente:
- Aggiungere componente `VisualEffect` a prefab di impatti, proiettili, scie o polvere dei passi.
- Pilotare i parametri esposti a runtime: `vfx.SetFloat("SpawnRate", ...)`, `vfx.SetVector3("ImpactPoint", ...)`, `vfx.SendEvent("OnHit")`.
- Combinare VFX Graph con hit-stop e audio procedurale generato per il massimo impatto visivo.

## Console & Stabilità
Dopo ogni modifica di script o scena: `read_console` con filtri error e warning. Zero errori per procedere. Mai toccare file YAML di scena quando l'Editor è attivo.
