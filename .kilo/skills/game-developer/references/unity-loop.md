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

Ground: cube `[size,0.2,size]` at `y=-0.1` so the **top face is Y=0** (a cube *at* y=0 buries every prop by half its height — this was the root cause of "leggermente sottoterra"). Rooms via `GDS.PB.Room` / blueprints, never wall by wall. Player empty + CharacterController + camera per GDD (`manage_camera`).

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

## execute_code (the tool this skill leans on)

Group `scripting_ext`. Body = C# method body with UnityEngine + UnityEditor. Always `return GDS.X.Y(...);` so JSON comes back:

```
return GDS.LevelBuilder.BuildFromFile("art/blueprints/house_a.json");
return GDS.SceneLint.RunJson(autoFix:true);
return GDS.LookDev.Apply("stylized-day");
```

If the group is hidden: `manage_tools` enable `scripting_ext`. If the MCP build lacks it: `execute_menu_item` on `GDS/...` and read `docs/lint/*.json`.

## Import art

Copy `art/exports/*.glb` → `Assets/_Game/Art/Exports/`. Scale 1, no cameras/lights from the file (strip if present). Then reference the file in a blueprint `props` row and rebuild — the builder adds the collider and snaps it. Prefab in `Prefabs/` only for things spawned at runtime.

## Camera & Post-Processing
Cinemachine follow/third-person/top-down da GDD via `manage_camera`. `CinemachineImpulseSource` sul player o su eventi di impatto per il camera shake (juice). Il `Global_Volume` (Bloom, ACES, Color Adjustments, Vignette, White Balance), sole, fog, skybox, SSAO e qualità URP li crea `GDS.LookDev.Apply(<preset GDD>)` — fine-tune con `manage_graphics` (`volume_set_effect`, `skybox_set_fog`, `feature_add`), mai a mano nello YAML. `manage_camera screenshot` con `include_image=true`, `max_resolution=512`, poi salvare copia in `screenshots/`.

## ProBuilder — geometria di livello
`GDS.PB.Room / Tower / Stairs / Arch` o blueprint `mode: probuilder` (vedi [probuilder-levels.md](probuilder-levels.md)), non bpy, non `manage_probuilder` face-by-face per le stanze.
- `manage_probuilder` solo per ritocchi (bevel, materiale per faccia, subdivide) su UNA mesh: `get_mesh_info include=faces` prima, `validate_mesh` dopo, poi `GDS.SceneLint.RunJson()`.
- Kit vestono le shell; ProBuilder resta come collision + look con materiale palette.

## VFX & Feedback Visivo
`GDS.VFX.CreateAll()` produce i prefab base (dust/hit/pickup/torch/smoke/sparkle); `manage_vfx` per tuning, trail e line renderer; Cartoon FX Free se il GDD lo consente. VFX Graph solo per effetti GPU massivi, orchestrato dai componenti C#:
- Aggiungere componente `VisualEffect` a prefab di impatti, proiettili, scie o polvere dei passi.
- Pilotare i parametri esposti a runtime: `vfx.SetFloat("SpawnRate", ...)`, `vfx.SetVector3("ImpactPoint", ...)`, `vfx.SendEvent("OnHit")`.
- Combinare VFX Graph con hit-stop e audio procedurale generato per il massimo impatto visivo.

## Console & Stabilità
Dopo ogni modifica di script o scena: `read_console` con filtri error e warning. Zero errori per procedere. Mai toccare file YAML di scena quando l'Editor è attivo.
