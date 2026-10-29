# Nucleon loop — `engine: nucleon`

Used when the user picks Nucleon in the GDD (Q0, [engines.md](engines.md)). The pipeline (GDD, workers, contract, gates, art review, UI picked by the user, design review) does not change; the tools do. Nucleon is a C++17 engine with a UE5-like editor, Lua games (the **natives**, PascalCase, FiveM-style), RmlUi game UI (HTML/CSS), Jolt physics, landscape/foliage/water, Lumen/Nanite-like renderer on D3D12/Vulkan/OpenGL, and an MCP server built into the editor. Engine docs live in the engine repo: `docs/editor/MCP.md`, `docs/api/NATIVES.md`, `docs/engine/*.md`, `docs/manual/README.md`.

Verified on 2026-10-29 against the editor built from `quality/q1@8e847b7d` (Windows 11, D3D12, RTX 5060; the editor always on a hidden Win32 desktop, preferences in a scratch folder), every command below on a real project made by `exe new-project`: `serve`, `ping`, `state`, `entities`, `entity get|set|add|rm|select`, `build` / `cycle` (rooms, `instances`, `performance.auto_group`, scatter, lights, cameras, player start), `lint` and `lint --play` (planted floating / buried objects found, objects buried under a new terrain found), `play-test` (also with the GDS harness: `GDS-TEST ... PASS`), `capture` (+GIF), `shot`, `camera`, `lua`, `lua-check` (+ `--engine-syntax`), `affected`, `profile`, `docs`, `input`, `import`, `resources`, `tools`, `tools-check`, `api-refresh`, `exe` (new-project, compile-blueprints, run-lua, migrate --dry-run, optimize-level --dry-run, package), `run-game --gds-test` on the packaged game, `nc_world.py` (island: build, `exe run-lua`, attach, look), `nc_mat.py` (presets, make, auto, check). Not run: Linux, Vulkan, the HTTP transport with an owner's editor, `exe hlod|build-gi|upgrade-ddc`. A1 (repeated textured models, GPU-driven path) did not reproduce on D3D12 with 300 untextured boxes: still open in the notes. `post` / `postVolumes` / `material domain` ran on `8e847b7d` (`post add`, `post set`, `material domain` read and write, a spec with `postVolumes`). Engine bugs found: [docs/NUCLEON-ENGINE-NOTES.md](../../docs/NUCLEON-ENGINE-NOTES.md) (read it before blaming the game: `Raycast` fails in a level with `instances` that have a collider, D1).

## 1. Requirements (doctor checks them)

- `NucleonEditor` (+ `Nucleon` next to it, same build): `config.json` `paths.nucleon` (folder or exe) or env `NUCLEON_EDITOR`.
- Python 3.9+ (ncli is standard library only).
- Next to the editor: `Nucleon` (the runtime) and, on Windows, `nc_desktop_run.exe`: ncli uses it so **no engine window ever opens on the desktop you work on** (see §2).
- Project made by the editor or headless: `python SKILL/scripts/ncli.py --exe <editor> exe new-project <folder> --template third-person` (templates: `empty`, `first-person`, `third-person`, `top-down`; exit 0, prints `Project created`).

## 2. The bridge: `scripts/ncli.py` (primary, token-cheap)

`ncli.py` **is an MCP client** of the editor's built-in server (JSON-RPC `tools/call`, batches): same tools, same undo history. Workers **never** register the MCP in their own context (27 tool schemas, one call per entity, base64 images in chat): they run `ncli.py`, one JSON line per step, PNGs on disk. Registering the MCP directly (`ncli mcp-config`) is for interactive sessions with the owner.

| Transport | When | How |
|---|---|---|
| HTTP | the owner has the editor open (normal case) | Editor Preferences > AI > **Enable Server** (port 47420). ncli reads port + token from `editor-settings.lua` (`NC_EDITOR_PREF_DIR` or the user folder `Nucleon/Editor`). One connection at a time: that is what the lock is for. |
| stdio | no editor open, CI, worker on its own copy | `--stdio <NucleonEditor> --project <dir>`: starts `--mcp-stdio` for one command, closes it. **Unsaved changes are lost**: pass `--save current` to `build`, or call `save`. Linux headless: under `xvfb-run`. Prefer `serve` (below): one editor for the whole session. |

**Hidden desktop (Windows).** ncli starts every editor / game it needs (stdio, `exe`, `run-game`, `nc_mat.py check`) through `nc_desktop_run.exe --desktop ncli-<pid> -- <cmd>` with `NC_UNATTENDED=1`: the window lives on a hidden Win32 desktop, never on yours, and `--mcp-stdio` still works (stdin/stdout are inherited; the job kills the child with the launcher). Opt out: `--visible` / `NCLI_VISIBLE=1`; another wrapper: `--launcher "<prefix>"` (`""` = none). Global options before the command: `--pref-dir DIR` (**always give it in tests**: sets `NC_EDITOR_PREF_DIR`, so the owner's preferences, layouts and recent list stay untouched; with HTTP the token and port are read from it), `--env K=V` (repeatable, e.g. `--env NC_GDS_TEST=1`), `--exe`, `--project`. A test run on a GPU shared with other agents: take the machine's lock first (the editor itself is the heavy part, one at a time on a hard disk).

| Command | Does | Gate evidence |
|---|---|---|
| `ping` / `state` | project, level, entity count, unsaved, Play state, up axis (warns if Y) / the raw `editor_state` | first line of every Nucleon gate |
| `build spec.json [--save current]` | GDS blueprint → entities in ONE JSON-RPC batch under folder `BP_<name>`; rebuild in place; **skipped when spec + catalog + builder are unchanged** (`--force`; the cached answer carries `report`) | `docs/lint/build-<name>.json` `{"status":"PASS","entities":N,"byType":...,"specHash":...}` |
| `cycle spec.json --owner PHASE:TASK [--save current]` | the whole level task in one call: lock → build (cached) → lint → framed shot → unlock | one JSON: build + lint + PNG |
| `lint [--play] [--no-primitives] --write docs/lint/scene-lint.json` | below kill Z, duplicates, primitives after greybox, log errors; floating / underground: on bounds (flat ground) or **`--play`: measured in Play with Raycast on the real colliders** (terrain, slopes, stacked props, objects off the ground = `noGround`) | `{"issues":0,...,"mode":"play"}` |
| `serve` / `session-stop [--save]` | one editor (stdio) kept open for every later ncli call of the project: 5-10 s saved per command, the whole glade demo built + linted + shot in ~45 s | — |
| `lua-check [--strict]` | game Lua vs the engine API before any Play: unknown PascalCase calls (`did_you_mean`), native argument counts, syntax (`luac` if installed) | `{"issues":0}` |
| `affected` | tests touched by the files changed since the last checkpoint commit (`-- covers:` globs; a core file = all) | `NC_GDS_TEST=<list>` + `expect` |
| `tools-check` / `api-refresh --engine-repo` | the editor's MCP tools / the Lua API vs the snapshot this skill was verified with: added, removed, changed | diff JSON |
| `capture plan.json` | store / trailer shots and GIF frames in real Play (camera, keys, hidden HUD; rules untouched), `manifest.json` `produced: real-play` | PNG/GIF + manifest |
| `shot out.png --pos x,y,z --target x,y,z [--mode lit]` | camera + capture, PNG written by ncli | PNG path |
| `play-test --seconds 60 --expect "GDS-TEST DONE pass=N fail=0" --shot p.png` | Play, stops at the first `GDS-TEST DONE`, log errors, screenshot of the game, Stop | `{"status":"PASS",...}` |
| `batch calls.json` | any list `[{"tool","args"}]` in one round trip | ids |
| `call <tool> '<json>'` | one raw MCP tool (escape hatch) | — |
| `log --since N [--level i\|w\|E\|g] [--category C]` · `save` | read_log (levels: i info, w warning, E error, g engine), save_scene | — |
| `entities [--type T] [--name X] [--count]` | scene_list as short records (`--count` = by type) | — |
| `entity get\|set\|add\|rm\|select ...` | entity_get / entity_modify (`new_name` renames) / entity_add / entity_remove / scene_select: the whole entity schema (light, shape, `instances` + `transforms`, `wind`, `cull_distance`, `collision`, `camera`, `render_flags`, `player_start`, `audio_*`, `reflection`) | the entity, short |
| `camera list\|add\|pilot\|stop\|shot` | Camera entities: `camera add Hero --pos 0,-20,6 --target 0,0,2 --focal 35 --dof --fstop 2.8 --focus 20`; `camera shot Hero out.png` pilots it, captures, stops piloting | PNG + lens |
| `post list\|add\|set` · `material domain PATH` | Post Process Volumes (`post add Night --unbound --set bloom=true --blendable Content/Materials/PP_Outline.ncmat:0.8`) and the Material Domain of a `.ncmat` (`--domain postProcess --post-location afterTonemap`) | the entity / the domain |
| `assets [QUERY] [--type T]` · `import FILES --folder F [--place]` | asset_search / asset_import (models, textures, sounds; placed in the level on request) | — |
| `commands [QUERY]` · `command ID` | list_commands / run_command (112 ids: `edit.undo`, `file.save`, `add.landscape`, `add.effects_*`, `tools.build_navigation\|build_hlod\|build_gi\|build_reflection_captures\|optimize_level_for_streaming`, `file.package_project`, `play.*`) | — |
| `input get [--out f.lua]` · `input set f.lua` | get / set_input_mapping (`Config/Input.lua`) | — |
| `docs list\|switch\|open\|close` · `play start\|stop\|pause\|resume\|step` | documents (Level, Actor, Mesh, Preferences, Project Settings) and play_control | — |
| `lua 'code'\|@file.lua` | run_lua (ENGINE coordinates, 5 s, not undoable); errors come back as `{"ok":false,...}` | — |
| `profile start\|stop\|save [--path]` | profile_capture: CPU/GPU means, draws, GPU passes, a `.ncprof` under `Saved/Profiling` (**only when the owner allows profiling**) | — |
| `resources list\|read URI` · `tools [NAME]` | MCP resources (guide, `nucleon://lua-api/*.lua`, `nucleon://project/<path>`) and tools/list of the running editor | — |
| `lock acquire|release --owner PHASE:TASK` | one editor driver at a time (`PROJECT/Saved/gds-nucleon.lock`, stale after 10 min) | — |
| `exe <mode> ...` | headless editor (no MCP, hidden desktop): `new-project DIR --template T [--api d3d12] [--starter]`, `compile-blueprints P`, `package P --config Development --platform win64 --out DIR [--report r.json --strict --clean --geometry virtualized\|lod --key HEX]`, `run-lua SCRIPT P`, `migrate P [--dry-run]`, `hlod P LEVEL`, `build-gi P LEVEL [--quality high]`, `optimize-level P LEVEL [--dry-run --args "-cell 128 -min-group 8"]`, `upgrade-ddc [DIR]`, `raw --args "<any editor argument>"` | `{"ok":true,"code":0,"errors":[],"tail":[...]}` |
| `run-game GAME_DIR [--gds-test] [--seconds 60] [--allow-timeout]` | a **packaged** game from its own folder on the hidden desktop: exit code, `Saved/Logs/game.log` errors, `GDS-TEST` lines (`--gds-test` = `NC_GDS_TEST=1` + `NC_GDS_TEST_EXIT=1`: exit 0 all passed, 3 a failure), shots | `{"status":"PASS","gdsTest":["GDS-TEST DONE pass=1 fail=0"]}` |
| `setup <project>` | copies the test harness, example spec, skill folders, `.gitignore` lines (phase project) | `{"ok":true,"copied":[...]}` |
| `exe new-project <dir> --template T` | headless project, **without the template's starter shapes** (`--starter` keeps them) | `{"ok":true}` |
| `mcp-config` | `claude mcp add nucleon ...` lines (stdio / HTTP) for an **interactive** session | — |

Raw MCP: every tool has a command above, `call <tool> '<json>'` reaches any other (27 tools: `editor_state`, `scene_list`, `scene_select`, `entity_get/modify/add/remove`, `asset_search`, `asset_import`, `list_commands`, `run_command`, `get/set_input_mapping`, `list/switch/open/close_document`, `play_control`, `read_log`, `viewport_camera`, `capture_viewport`, `camera_pilot`, `run_lua`, `profile_capture`, `material_domain`, `migrate_project`, `save_scene`). Every edit is undoable (`command edit.undo`); nothing is on disk before `save`. Not covered by any MCP tool (use a spec, `lua`, a Lua tool script, or the headless modes): landscape sculpt / foliage painting, the level's `lighting` table (`nc_world.py look`), project settings, sublevels.

`capture_viewport` writes the viewport panel at its own size (`max_width` only shrinks); the first call right after the editor starts can say "not visible": ncli retries for 20 s.

## 3. Coordinates (the trap)

- MCP tools, ncli, GDS specs, natives: **Z up**, meters, X east, Y north, rotation `[pitch, roll, yaw]` degrees, yaw 0 faces +Y.
- `.nclevel` / `.ncactor` files, `run_lua`, the legacy Lua API, `nc.*` modules, `NC_EDITOR_CAMERA`: **engine Y up** (`native (x,y,z) = (-engine.x, engine.z, engine.y)`).
- The `nucleon://docs/editor-guide` resource still says "+Y is up": stale (engine notes B3), ignore it (the tools speak Z up).
- Camera / light rotations are `[pitch, roll, yaw]`: a camera at `pos` looking at `target` has pitch `atan2(dz, hypot(dx, dy))`, yaw `atan2(-dx, dy)` (counter-clockwise seen from above): `camera add --target` and a spec `cameras[].target` compute it.
- Box shapes: centred on `position`; `width` = X, `depth` = Y, `height` = Z (verified with `entity_get` bounds).
- If `ping` reports `upAxis: y`, stop: the owner set Editor Preferences > Appearance > Coordinates to Y; ask before changing it.

## 4. Deterministic layer for Nucleon

**Spec, not clicks.** A worker writes JSON, ncli builds it; the scene is never edited entity by entity.

`art/blueprints/<name>.json` (Nucleon flavour, example `templates/nucleon/specs/house_example.json`):

```json
{"name":"house_a","origin":[10,0,0],"yaw":0,"seed":7,
 "defaults":{"h":3,"wall":0.2,"wallColor":[0.8,0.78,0.72],"floorColor":[0.45,0.4,0.35]},
 "rooms":[{"name":"main","x":0,"y":0,"w":8,"d":6,"h":3,
           "doors":[{"side":"S","at":0.5,"width":1.2,"height":2.2}],
           "windows":[{"side":"E","at":0.5,"width":1.5,"sill":0.9,"height":2.0}],
           "ceiling":false,"omit":[]}],
 "pieces":[{"asset":"Content/Models/Crate.glb","position":[2,2,0],"rotation":[0,0,45],"scale":[1,1,1]}],
 "scatter":[{"name":"trees","assets":["Content/Models/Tree1.glb","Content/Models/Tree2.glb"],"count":30,
             "area":[-40,-40,40,40],"minDist":4,"scale":[0.8,1.3],"avoid":[[-2,-2,10,8]],"z":0}],
 "shapes":[{"name":"ramp","position":[0,-4,0.5],"shape":{"kind":"stairs","width":2,"depth":3,"height":1,"steps":6}}],
 "lights":[{"type":"point","position":[4,3,2.5],"intensity":60,"unit":"cd","range":8}],
 "cameras":[{"name":"Hero","position":[0,-12,6],"target":[4,3,1],"focalLength":35,"depthOfField":true,"fStop":2.8,"focusDistance":14}],
 "playerStart":{"position":[4,-3,0],"yaw":0}}
```

- Rooms: floor + four walls, one box per wall segment, door and window gaps cut by the builder (no CSG). Side `S` = min Y, `N` = max Y, `W` = min X, `E` = max X. Adjacent rooms share a wall: `omit` it on one of them.
- `pieces` / `scatter` take `.glb/.gltf/.fbx/.obj` models or `.ncactor` actors already in the project (`asset_search` / `asset_import` first: `call asset_import '{"sources":["/abs/art/exports/crate.glb"],"folder":"Content/Models/Kit"}'`).
- **Lights are in physical units** (`lightUnits = 2`): point / spot / rect / disc in candela (`"unit":"cd"`, or lumen), directional in lux, sky light a multiplier. 10 cd at 1 m is about a surface value of 1 at 0 EV, so an indoor lamp is 30-100 cd and `intensity: 400` is blown out (the old examples were). Fields: `type`, `position`, `rotation`, `color`, `intensity`, `unit`, `range`, `inner_cone`, `outer_cone`, `cast_shadows`, `atmosphere_sun` (the sun = a Directional Light flagged so).
- **Many repeated props = `instances`** (one entity, up to 100000 transforms, one draw path): `"instances":[{"name":"crate_field","asset":"Content/Models/Box.glb","collision":"none|box|capsule","cast_shadows":true,"cull_distance":0,"wind":"tree","transforms":[{"position":[8,0,0.5],"rotation":[0,0,30],"scale":0.6}]}]`, or `"performance":{"auto_group":true,"min_group":6}` to fold repeated models of `pieces` / `scatter` into groups. `collision` `mesh` is accepted but the runtime uses a box and logs a warning on every Play (engine notes D2): write `box`. Do not use instances for anything with identity (a pickup, a door): keep those as models / actors.
- **Cameras**: `"cameras":[{"name","position","target"|"rotation","fov"|"focalLength","depthOfField","fStop","focusDistance","manualExposure","ev100","defaultView"}]` (docs/engine/CAMERA.md: a plain camera has `fov`; a Cine camera has a physical lens: focal length, sensor, f-stop, focus distance). `defaultView: true` = the game starts through it; natives `SetActiveCamera`, `GetActiveCamera`, `GetCameraEntities`, `GetCameraEntityLens`, `SetCameraEntityLens` (a focus pull = a loop of `SetCameraEntityLens(cam, {focusDistance = d})`).
- **Render flags** on `shapes` / `pieces`: `"renderFlags":{"castShadow":false,"visibleInRayTracing":false,"affectGI":false,"hiddenInGame":true}` (docs/engine/RENDER_FLAGS.md; `castShadow` on models and instances only, `lightingChannels` is stored but not honoured yet). `hiddenInGame` = a marker or blocker that must exist in the editor and not in Play.
- **Post Process Volumes**: `"postVolumes":[{"name":"Night","position":[0,0,0],"size":[40,40,20],"unbound":false,"priority":1,"blendRadius":5,"weight":1,"settings":{"bloom":true,"exposure":-0.5},"blendables":[{"material":"Content/Materials/PP_Outline.ncmat","weight":0.8}]}]` (docs/rendering/POSTPROCESS.md; `settings` are the `Lighting` keys of the Post Process panel, `null` removes one; a blendable is a `.ncmat` whose domain is `postProcess`: `nc_mat.py make` a material, then `ncli material domain PATH --domain postProcess`; an `unbound` volume covers the whole level; a project-wide look is still `nc_world.py look`).
- Greybox = rooms + shapes only; art = same `name` with `pieces` (kit) → rebuild in place.
- **Kit catalog** (`python SKILL/scripts/nc_gds.py catalog Content/Models/<Kit> --project . --out art/kit-catalog.json`): every glTF/GLB/OBJ measured offline (display bounds, pivot, size), a role guessed from the name (`wall`, `wallDoor`, `wallWindow`, `floor`, `corner`, `fence`, `roof`, `stairs`, `building`, `tree`, `rock`, `plant`, `light`, `container`, `furniture`, `prop`), the wall module. Then specs say `{"role": "container"}` or `{"piece": "barrel"}` instead of a path, and rooms say `"kit": {}`: floor tiles, wall modules along each side, door/window modules at the openings, corners; lengths snap to the module.
- **Kit scale**: `"kitScale": 6` in a spec scales a miniature kit (KayKit hex: a 0.9 m house) once, with bounds and placement scaled correctly (or set the asset's `import.scale` in `Config/AssetDatabase.json`).
- **On a generated world**: `"origin": [x, y, "ground"]` takes the height of the flat spot of `art/world/*.layout.json` under the origin (a hard-coded z is wrong as soon as the terrain changes; the lint catches it).

## 4b. Worlds and look: `scripts/nc_world.py`

`python SKILL/scripts/nc_world.py build art/world/<name>.json --project .` — Python generates, the engine writes:

| mode | output | then |
|---|---|---|
| `terrain` / `island` | heightmap (warped fBm + ridged), layers by height/slope (solid-colour PNGs from the palette), grass foliage, flat spots (`flat: [{x, y, r, spawn}]`; `z` is accepted as another spelling of `y`), kit scatter at the **real** height (pivot-aware, `kitScale`), water for islands | `ncli exe run-lua Tools/gds_world_<name>.lua .` → `.land`; `nc_world.py attach . --name <name>` (editor closed: adds terrain + water, removes the template `Ground`); `ncli build art/blueprints/_world_<name>.json` |
| `dungeon` / `cave` | grid of rooms + corridors (MST + loops) or cellular cave; kit floor/wall pieces when the catalog has them, boxes otherwise; room props, torches | `ncli build ...` |
| `village` | plaza, bent roads, lots facing the road, kit houses (or `buildings` / greybox houses), fences, lamps, trees outside lots and roads | `ncli build ...` |

`reference` in the world JSON = numbers the worker measures on `art/reference/BOARD.md` (street width, lot size, relief, density, treeline, rooms...): the world follows the references, not the generator's defaults. Every mode writes `art/world/<name>.layout.json` (spawn, goal, rooms, lots, flats with their z) for the systems workers.

**Look**: `nc_world.py look . art/look/<name>.json` (editor closed) writes the level's `lighting` table (any `Lighting.set` / Post Process key: atmosphere, clouds, volumetric clouds, height fog, volumetric fog, light shafts, GI, bloom, exposure, tonemapper, SSAO, vignette...), the sun (azimuth / elevation / colour / intensity → `environment.sun` and the `Sun` entity) and ambient. Values come from the reference board; lessons from the glade demo: auto exposure + AgX + a strong warm height fog turn a sunny scene brown; for a stylized daytime start from `autoExposure=false, tonemapper="aces"`, sun 20-35°, height fog density ≤ 0.005 with `heightFogStart` 40+ (haze at the horizon only).
- Worlds: landscape (`.land`), foliage, water are authored with a Lua tool script run by `ncli exe run-lua Tools/make_world.lua <project>` (the engine's sample `samples/ThirdPersonDemo/Tools/make_world.lua` is the reference: `LandscapeNew`, `setHeightAt`, paint layers, foliage), seeded from `art/world/<name>.json`. The level then references the `.land` (`type = "terrain"`); after that ncli builds on top.

## 5. Gameplay = Lua natives (+ Blueprint when the owner wants graphs)

- Game rules: `Content/Scripts/*.lua` (each runs once at start, own environment, talk with `exports` / `TriggerEvent`). Actor behaviour: the actor's script with `OnBeginPlay`, `OnTick(dt)`, `OnTriggerEnter(other)`, ... (`entity` = the actor). Reference: `docs/api/NATIVES.md` (404 natives in 33 categories at `8e847b7d`) and `docs/api/lua/natives.lua` for completion; `ncli api-refresh --engine-repo <checkout> --from-editor` rewrites the snapshot ncli checks Lua against from the built editor's own registry (the committed `natives.json` of the engine can lag behind the sources).
- Natives are **Z up** (x east, y north, z up, rotations `vec3(pitch, roll, yaw)`); `GetEntity*` / `SetEntity*` take the entity numbers `scene_list` shows. Newer categories worth using: Camera (`SetActiveCamera`...), Sky (`GetSky*`/`SetSky*`, moon), Streaming (`LoadStreamLevel` ...), `GetEntityLevel`, `LoadLevelInstance`.
- **Player Start and game mode**: a `playerStart` entity in the spec is where the Default Pawn spawns (`startTag` for several; the feet position, check it does not overlap terrain: `lint --play` warns). The pawn and the rules come from `project.ncproject` `game = {defaultPawn, gameMode}` and the level's own `game` table; the templates already set them. Spawn point **inside the ground = the pawn never lands** (`GDS-TEST ... timeout waiting for the pawn on the ground`): after a terrain is attached, move or remove the template's old `PlayerStart`.
- **Level streaming** (engine docs `docs/engine/WORLD.md` "Level streaming", written but never run by the engine team): a persistent `.nclevel` lists `sublevels` (name, source, transform, `streaming = always|blueprint|volume`, ...) and `levelstreamingvolume` entities; runtime `nc.levels`; natives `LoadStreamLevel` and friends. There is no MCP tool for sublevels: author the `.nclevel` with the editor closed, or `command add.level_streaming_volume`; `command tools.optimize_level_for_streaming` / `exe optimize-level` turns a big flat level into instance groups + cells. Treat it as experimental and check it in Play.
- One verb = one script + one test + one prompt (task-decomposition merge rule, same as Unity).
- Blueprint graphs (`.ncbp`) compile to Lua: after any change `ncli exe compile-blueprints <project>` → `0 failed`.
- Input: `Config/Input.lua` (actions, keyboard + pad bindings) — `call get_input_mapping` / `set_input_mapping`. Key remapping baseline item: `nc.input` rebinding.
- Saves: `nc.save` / natives `SaveData/LoadData` (owner saves: Contract 9 backup rule applies to `<user folder>/Nucleon/<project>/`).

## 6. Tests: `templates/nucleon/Content/Scripts/gds_test.lua`

Copied by `ncli setup` (phase project). Off unless `NC_GDS_TEST` is set. Each verb test: `Content/Scripts/test_<verb>.lua` with `exports.gds_test:Register(name, function(t) ... end)`; helpers `t.hold(key, s)` / `t.tap(key)` (real input via `SimulateKey`), `t.wait`, `t.waitFor`, `t.check`, `t.near`, `t.pawn()`, `t.shot(name)`. Log lines: `GDS-TEST <name> PASS|FAIL: <reason>`, then `GDS-TEST DONE pass=N fail=M`.

- In the editor: `NC_GDS_TEST=1` in the editor's environment (stdio run: export it before ncli), then `ncli play-test --seconds 60 --expect "GDS-TEST DONE pass=<N> fail=0"`.
- Packaged: `ncli run-game <Packaged/win64> --gds-test` (the same as `NC_GDS_TEST=1 NC_GDS_TEST_EXIT=1 NC_GDS_TEST_OUT=captures/test <game exe>` on the hidden desktop) → exit code 0/3 + the `GDS-TEST` lines + screenshots. Package with `--config Development` for tests: Debug / Development have the F8 console and the game's prints in `Saved/Logs/game.log`, **Shipping logs errors only** (a Shipping run can pass a test and show nothing).
- In the editor `play-test` the project is not packaged: collision, assets and scripts are the editor's; a bug that only shows in the pak (a missing dependency: `exe package` prints `Unresolved reference` warnings) needs `run-game`.
- Bug fixes: `Tools/gds/test_bug_template.lua` → `Content/Scripts/test_bug_<key>.lua`, FAIL before the fix, PASS after (workers.md iterate-gate 1b); `gds_bisect.py` finds the commit that broke a test.
- Performance: `t.perf("walk", 10, "W")` in a test + `ncli play-test --fps <targetFps>` → p50/p95/p99 per run, FAIL over budget (GPU only; llvmpipe numbers mean nothing).
- Telemetry (opt-in): `gds_telemetry.lua` + `scripts/telemetry_report.py` (playtest.md).
- Feel baseline (playtest.md): the same harness measures the core verb in the real level (distance, time to apex, stop distance) and prints it with `t.feel({...})` (one `GDS-FEEL {json}` line); the worker stores it in `docs/tests/feel-baseline.json`.

## 7. UI: designer → RmlUi

Mock HTML (user picks a variant per screen, unchanged rule) → `python SKILL/scripts/html2rml.py mock.html PROJECT/UI/<screen>.rml --model <screen>` → `.rml` + `.rcss` + `.preview.lua`; it reports every change (`px→dp`, grid → flex wrap, shadows dropped, `href/onclick` dropped: bind buttons by id in Lua). Open it in the UI editor to check (`NC_EDITOR_UI_DOCUMENT=UI/<screen>.rml NC_EDITOR_SCREENSHOT=docs/screens/<screen>.png NucleonEditor <project>`). Show/bind with the natives of the Game UI category (`CreateUIModel`, documents shown by the game script, see the sample `Content/Scripts/game.lua`). Pause menu and options: the templates ship `nc.pause` and `UI/options.rml` (graphics options already wired): reuse them, restyle them, do not rebuild them.

## 8. Look

- Project lighting `graphics.lighting = "modern"` (Lumen-like GI, reflections, volumetric fog) for stylized/realistic; `classic` for very low-end targets.
- Post process and sky: the Post Process panel / `lighting` table of the level or `project.ncproject`; sun = the Directional Light flagged `atmosphere_sun`.
- Lookdev preset = a `lighting`+`environment` table written by the lookdev worker into the level (`call entity_modify` on the sun + Project Settings) and a `shot` per preset view; art review as for Unity ([art-direction.md](art-direction.md)).
- Software rendering (CI, Xvfb/llvmpipe) washes colours out: art review only on screenshots from the owner's GPU.

## 8a. Materials: `scripts/nc_mat.py` (the material system of 21 October 2026)
Nucleon has Unreal's shading models as presets of one Substrate-style slab (engine docs `docs/rendering/MATERIAL_SYSTEM.md`,
`MATERIALS.md`): Default Lit, Unlit, Subsurface, Preintegrated Skin, Clear Coat, Subsurface Profile (`.ncsss`), Two Sided Foliage,
Hair, Cloth, Eye, Single Layer Water, Thin Translucent, Glass/Acrylic, Car Paint, Thin Film; plus layers (`layers`, `layerStack`
of `.ncmatfunc` layer functions), World Position Offset / material wind, parallax, triplanar, detail normals, material domains
(post process, sky, fog, decal, light function, volume, UI) and parameter collections (`.ncmpc`). A kit left on its glTF material is
Default Lit everywhere: the lookdev worker gives every surface its model.
- `nc_mat.py auto --project P --catalog art/kit-catalog.json --style <GDD style> --name <kit>`: every glTF/GLB slot gets a role
  (material and texture names; on an **atlas** texture only the catalog role, never water/glass/emissive guessed from an asset
  name), shared `.ncmat` in `Content/Materials/Auto/<kit>/` (one per role and texture set: the renderer batches **per material**,
  so few materials = few draws), separate PBR maps packed into ORM (`realistic`), GLB images extracted, and the vegetation wind of
  the plants (`wind = {type = "tree"|"bush"|"grass"}`: weighted by height, the trunk base stays; never on hills, buildings, stumps).
- `nc_mat.py assign --project P --map art/materials/<kit>.map.json` (editor CLOSED, `session-stop` first): `materials` and `wind` on the
  level's model entities. Run it after every `build --save` that placed kit pieces (the MCP `entity_add` has no materials field).
- `nc_mat.py make <role> OUT.ncmat [--texture T] [--set k=v]` for one surface: `glass`, `frosted`, `ice`, `crystal`, `stained`,
  `water`/`ocean`/`pool`/`swamp` (Single Layer Water, the engine's Ocean/Lake/Pool/Swamp numbers), `carPaint`, `lacquer`, `painted`,
  `cloth`, `velvet`, `skin`, `wax`, `jade`, `marble`, `hair`, `eye`, `neon`, `screen`, `holo`, `film`, `foliage`, `grass`... (`presets`
  lists them with their keys). Big water surfaces stay the Water entity (its own pass); the material is for ponds, pools, troughs.
- `nc_mat.py check --project P --editor NucleonEditor <files>`: every NEW shading model is "written and built, never run" in the engine:
  the check renders the Material document with models on and with `NC_MATERIAL_MODELS=0` (on the hidden desktop), and fails a black, flat or unchanged preview. The D3D12 editor draws the big preview blank in a window shot (engine notes D3): the check then measures the strip of model spheres under it, so a pass means "the models render", not "this material looks right": look at the PNG.
  A failing model goes to the engine notes (`docs/NUCLEON-ENGINE-NOTES.md`) and the material falls back to `defaultLit` with the
  same textures: never ship a surface nobody saw.
- A material replaces the slot completely (textures too): `auto` copies the glTF's maps; a hand-made `.ncmat` must name its maps.
- Triplanar / parallax replace or displace the mesh UVs: only on tileable sets, never on a kit atlas.

Material graph nodes added on 2026-10-29 (engine docs `MATERIAL_GRAPH.md`): Two Sided Sign, Shadow Pass Switch, Per Instance Random (variation per instance of an `instances` entity without a texture), Scene Color, Distance To Nearest Surface. Post Process materials (domain `postProcess`) are applied by a Post Process Volume `blendables` list or by the level's Post Process panel.

## 8b. Performance diagnosis: `tools/nucleon-bench`
When `play-test --fps` fails on the real GPU, or the owner reports drops: don't guess. `bench.py grab-view` (the spot from the
open editor) → `bench.py run --only <H>` (one change per config against base: shadows, LOD, foliage, GI, texture and page
streaming, the GPU-driven paths, resolution) → `analyze` (REPORT.md with verdicts) → `plan` (EXECUTION-PLAN.md: briefs with a
ready-made prompt for Claude Code in the NucleonEngine repository). Engine bugs and the K1-K5 briefs:
`docs/NUCLEON-ENGINE-NOTES.md`. In the meantime the game works around them: `NC_GPU_DRIVEN=0` if repeated props come out wrong
(A1), `instances` for repeated props once they have been run. The bench has H10 (the material system: models, sets, offset,
layers, deferred models) to tell what the new materials cost.

## 9. Phase mapping

| Phase | Nucleon |
|---|---|
| project | `exe new-project` (template from the genre: first-person / third-person / top-down) or attach; `ncli setup PROJECT` (harness, example spec, folders, `.gitignore`); HTTP server on (owner, once) or stdio; `ping` + `lint` JSON + `play-test` with `test_move.lua`; `git init` |
| greybox | spec with rooms/shapes → `build` → `lint` → `play-test` with `test_move.lua` green |
| world-gen | `nc_world.py build` → `exe run-lua` → `attach` → `build _world_<name>.json` → `lint --play` (§4b) |
| level-build | blueprint JSON (kit roles / kit rooms / `scatter`) → `cycle` (one worker per blueprint, JSON written in parallel, `cycle` takes the lock itself) |
| hero-asset | [hero-procedural.md](hero-procedural.md): `blender -b -P Tools/<asset>_build.py` (hero_kit) → GLB → `call asset_import '{"sources":[...],"folder":"Content/Models/Hero"}'` → `pieces` row with `rotation [0,0,180]` (front toward the player) → `build --save current` → `shot` |
| lookdev | `nc_mat.py auto` + `assign` (§8a) + `check` on the new models → `art/look/<name>.json` from the board → `nc_world.py look` → shots in Game View (`NC_EDITOR_GAME_VIEW=1` on the editor) → art review |
| characters | template pawn (`Content/Actors/Player.ncactor`, Character Movement, animation graph `.ncanim`); enemies: navigation volume + `BuildNavigationMesh` / behavior trees (`nc.behavior`) |
| systems | `Content/Scripts/<system>.lua` + actor scripts + `test_<verb>.lua`; Blueprint only if the GDD says so |
| ui-* | §7 |
| juice | effects `.ncfx` / particles entities, `PlaySound*` natives, `ShakeCamera` |
| playtest | `lua-check` + `play-test` (all tests, `--fps`) + `lint --play` + shots; packaged run with `run-game --gds-test`; `capture` for the store |
| build (only if asked) | `exe package <project> --config Development --platform win64 --out Packaged/win64 --report size.json` + `run-game Packaged/win64 --gds-test` (tests), then `--config Shipping` for the release; no 32-bit player |

## 10. Rules

- A test editor always runs with `--pref-dir <scratch>` (never the owner's `%APPDATA%/Nucleon`) and on the hidden desktop (default).
- Editor open with HTTP on = the owner's editor: never `stdio` on the same project at the same time (two editors, one level file).
- Every ncli call that edits or plays goes between `lock acquire` / `lock release` (same rule as `unity-lock.ps1`); JSON specs, Lua scripts, mocks are written in parallel outside the lock.
- Save before closing a stdio run; never write `.nclevel` by hand while the editor has the level open (the editor overwrites it on save).
- `run_lua` (engine coordinates, not undoable) only for things no tool covers; prefer specs + natives.
- Engine bugs found during a run: write them in the gate (`engine_issues:`) with the repro; the Nucleon repo has its own workflow (do not patch the engine from a game worker).
