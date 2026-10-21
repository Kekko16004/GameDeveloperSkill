# Nucleon loop — `engine: nucleon`

Used when the user picks Nucleon in the GDD (Q0, [engines.md](engines.md)). The pipeline (GDD, workers, contract, gates, art review, UI picked by the user, design review) does not change; the tools do. Nucleon is a C++17 engine with a UE5-like editor, Lua games (the **natives**, PascalCase, FiveM-style), RmlUi game UI (HTML/CSS), Jolt physics, landscape/foliage/water, Lumen/Nanite-like renderer on D3D12/Vulkan/OpenGL, and an MCP server built into the editor. Engine docs live in the engine repo: `docs/editor/MCP.md`, `docs/api/NATIVES.md`, `docs/engine/*.md`, `docs/manual/README.md`.

Verified on 2026-10-21 against the editor built from `main@d8e49bc` (Linux, Xvfb, llvmpipe), every command below on real projects: build / cycle / cache, kit rooms from a catalog (pieces measured, rotations checked against `entity_get` bounds), worlds (island, village 22 lots, dungeon 6 rooms, the glade demo `docs/samples/nucleon-glade-*.jpg`), `lint --play` (planted floating / buried / stacked / off-the-edge objects: found, zero false positives on 275 objects), `serve`, `tools-check`, `lua-check` (0 false positives on the engine's samples), `affected`, `capture` (+GIF), telemetry, perf, bisect. Not run here: Windows, D3D12, the HTTP transport with the owner's editor. Engine bugs found on the way: [docs/NUCLEON-ENGINE-NOTES.md](../../docs/NUCLEON-ENGINE-NOTES.md) (A1: small repeated models drawn with a wrong material, workaround `NC_INSTANCING=0`).

## 1. Requirements (doctor checks them)

- `NucleonEditor` (+ `Nucleon` next to it, same build): `config.json` `paths.nucleon` (folder or exe) or env `NUCLEON_EDITOR`.
- Python 3.9+ (ncli is standard library only).
- Project made by the editor or headless: `python SKILL/scripts/ncli.py --exe <editor> exe new-project <folder> --template third-person` (templates: `empty`, `first-person`, `third-person`, `top-down`; exit 0, prints `Project created`).

## 2. The bridge: `scripts/ncli.py` (primary, token-cheap)

`ncli.py` **is an MCP client** of the editor's built-in server (JSON-RPC `tools/call`, batches): same tools, same undo history. Workers **never** register the MCP in their own context (24 tool schemas, one call per entity, base64 images in chat): they run `ncli.py`, one JSON line per step, PNGs on disk. Registering the MCP directly (`ncli mcp-config`) is for interactive sessions with the owner.

| Transport | When | How |
|---|---|---|
| HTTP | the owner has the editor open (normal case) | Editor Preferences > AI > **Enable Server** (port 47420). ncli reads port + token from `editor-settings.lua` (`NC_EDITOR_PREF_DIR` or the user folder `Nucleon/Editor`). One connection at a time: that is what the lock is for. |
| stdio | no editor open, CI, worker on its own copy | `--stdio <NucleonEditor> --project <dir>`: starts `--mcp-stdio` for one command, closes it. **Unsaved changes are lost**: pass `--save current` to `build`, or call `save`. Linux headless: under `xvfb-run`. |

| Command | Does | Gate evidence |
|---|---|---|
| `ping` | project, level, entity count, unsaved, Play state, up axis (warns if Y) | first line of every Nucleon gate |
| `build spec.json [--save current]` | GDS blueprint → entities in ONE JSON-RPC batch under folder `BP_<name>`; rebuild in place; **skipped when spec + catalog + builder are unchanged** (`--force`) | `docs/lint/build-<name>.json` `{"status":"PASS","entities":N,"byType":...,"specHash":...}` |
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
| `log --since N` · `save` | read_log (errors), save_scene | — |
| `lock acquire|release --owner PHASE:TASK` | one editor driver at a time (`PROJECT/Saved/gds-nucleon.lock`, stale after 10 min) | — |
| `exe compile-blueprints|package|run-lua|migrate|new-project <project>` | headless editor (no MCP, no window): Blueprints → Lua, pak build, Lua tool scripts | `{"ok":true,...}` |
| `setup <project>` | copies the test harness, example spec, skill folders, `.gitignore` lines (phase project) | `{"ok":true,"copied":[...]}` |
| `exe new-project <dir> --template T` | headless project, **without the template's starter shapes** (`--starter` keeps them) | `{"ok":true}` |
| `mcp-config` | `claude mcp add nucleon ...` lines (stdio / HTTP) for an **interactive** session | — |

Raw MCP (only interactive, or for a tool ncli does not wrap): `editor_state`, `scene_list`, `entity_get/modify/add/remove`, `scene_select`, `asset_search`, `asset_import`, `list_commands`/`run_command` (`edit.undo`, `file.save`, `play.play_in_editor`, `tools.build_reflection_captures`, ...), `get/set_input_mapping`, documents, `play_control`, `read_log`, `viewport_camera`, `capture_viewport`, `run_lua`, `migrate_project`, `save_scene`. Every edit is undoable (`run_command edit.undo`); nothing is on disk before `save_scene`.

## 3. Coordinates (the trap)

- MCP tools, ncli, GDS specs, natives: **Z up**, meters, X east, Y north, rotation `[pitch, roll, yaw]` degrees, yaw 0 faces +Y.
- `.nclevel` / `.ncactor` files, `run_lua`, the legacy Lua API, `nc.*` modules, `NC_EDITOR_CAMERA`: **engine Y up** (`native (x,y,z) = (-engine.x, engine.z, engine.y)`).
- The `nucleon://docs/editor-guide` resource still says "+Y is up": stale, ignore it (the tools speak Z up).
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
 "lights":[{"type":"point","position":[4,3,2.5],"intensity":400,"range":8}],
 "playerStart":{"position":[4,-3,0],"yaw":0}}
```

- Rooms: floor + four walls, one box per wall segment, door and window gaps cut by the builder (no CSG). Side `S` = min Y, `N` = max Y, `W` = min X, `E` = max X. Adjacent rooms share a wall: `omit` it on one of them.
- `pieces` / `scatter` take `.glb/.gltf/.fbx/.obj` models or `.ncactor` actors already in the project (`asset_search` / `asset_import` first: `call asset_import '{"sources":["/abs/art/exports/crate.glb"],"folder":"Content/Models/Kit"}'`).
- Greybox = rooms + shapes only; art = same `name` with `pieces` (kit) → rebuild in place.
- **Kit catalog** (`python SKILL/scripts/nc_gds.py catalog Content/Models/<Kit> --project . --out art/kit-catalog.json`): every glTF/GLB/OBJ measured offline (display bounds, pivot, size), a role guessed from the name (`wall`, `wallDoor`, `wallWindow`, `floor`, `corner`, `fence`, `roof`, `stairs`, `building`, `tree`, `rock`, `plant`, `light`, `container`, `furniture`, `prop`), the wall module. Then specs say `{"role": "container"}` or `{"piece": "barrel"}` instead of a path, and rooms say `"kit": {}`: floor tiles, wall modules along each side, door/window modules at the openings, corners; lengths snap to the module.
- **Kit scale**: `"kitScale": 6` in a spec scales a miniature kit (KayKit hex: a 0.9 m house) once, with bounds and placement scaled correctly (or set the asset's `import.scale` in `Config/AssetDatabase.json`).
- **On a generated world**: `"origin": [x, y, "ground"]` takes the height of the flat spot of `art/world/*.layout.json` under the origin (a hard-coded z is wrong as soon as the terrain changes; the lint catches it).

## 4b. Worlds and look: `scripts/nc_world.py`

`python SKILL/scripts/nc_world.py build art/world/<name>.json --project .` — Python generates, the engine writes:

| mode | output | then |
|---|---|---|
| `terrain` / `island` | heightmap (warped fBm + ridged), layers by height/slope (solid-colour PNGs from the palette), grass foliage, flat spots (`flat: [{x, y, r, spawn}]`), kit scatter at the **real** height (pivot-aware, `kitScale`), water for islands | `ncli exe run-lua Tools/gds_world_<name>.lua .` → `.land`; `nc_world.py attach . --name <name>` (editor closed: adds terrain + water, removes the template `Ground`); `ncli build art/blueprints/_world_<name>.json` |
| `dungeon` / `cave` | grid of rooms + corridors (MST + loops) or cellular cave; kit floor/wall pieces when the catalog has them, boxes otherwise; room props, torches | `ncli build ...` |
| `village` | plaza, bent roads, lots facing the road, kit houses (or `buildings` / greybox houses), fences, lamps, trees outside lots and roads | `ncli build ...` |

`reference` in the world JSON = numbers the worker measures on `art/reference/BOARD.md` (street width, lot size, relief, density, treeline, rooms...): the world follows the references, not the generator's defaults. Every mode writes `art/world/<name>.layout.json` (spawn, goal, rooms, lots, flats with their z) for the systems workers.

**Look**: `nc_world.py look . art/look/<name>.json` (editor closed) writes the level's `lighting` table (any `Lighting.set` / Post Process key: atmosphere, clouds, volumetric clouds, height fog, volumetric fog, light shafts, GI, bloom, exposure, tonemapper, SSAO, vignette...), the sun (azimuth / elevation / colour / intensity → `environment.sun` and the `Sun` entity) and ambient. Values come from the reference board; lessons from the glade demo: auto exposure + AgX + a strong warm height fog turn a sunny scene brown; for a stylized daytime start from `autoExposure=false, tonemapper="aces"`, sun 20-35°, height fog density ≤ 0.005 with `heightFogStart` 40+ (haze at the horizon only).
- Worlds: landscape (`.land`), foliage, water are authored with a Lua tool script run by `ncli exe run-lua Tools/make_world.lua <project>` (the engine's sample `samples/ThirdPersonDemo/Tools/make_world.lua` is the reference: `LandscapeNew`, `setHeightAt`, paint layers, foliage), seeded from `art/world/<name>.json`. The level then references the `.land` (`type = "terrain"`); after that ncli builds on top.

## 5. Gameplay = Lua natives (+ Blueprint when the owner wants graphs)

- Game rules: `Content/Scripts/*.lua` (each runs once at start, own environment, talk with `exports` / `TriggerEvent`). Actor behaviour: the actor's script with `OnBeginPlay`, `OnTick(dt)`, `OnTriggerEnter(other)`, ... (`entity` = the actor). Reference: `docs/api/NATIVES.md` (382 natives) and `docs/api/lua/natives.lua` for completion.
- One verb = one script + one test + one prompt (task-decomposition merge rule, same as Unity).
- Blueprint graphs (`.ncbp`) compile to Lua: after any change `ncli exe compile-blueprints <project>` → `0 failed`.
- Input: `Config/Input.lua` (actions, keyboard + pad bindings) — `call get_input_mapping` / `set_input_mapping`. Key remapping baseline item: `nc.input` rebinding.
- Saves: `nc.save` / natives `SaveData/LoadData` (owner saves: Contract 9 backup rule applies to `<user folder>/Nucleon/<project>/`).

## 6. Tests: `templates/nucleon/Content/Scripts/gds_test.lua`

Copied by `ncli setup` (phase project). Off unless `NC_GDS_TEST` is set. Each verb test: `Content/Scripts/test_<verb>.lua` with `exports.gds_test:Register(name, function(t) ... end)`; helpers `t.hold(key, s)` / `t.tap(key)` (real input via `SimulateKey`), `t.wait`, `t.waitFor`, `t.check`, `t.near`, `t.pawn()`, `t.shot(name)`. Log lines: `GDS-TEST <name> PASS|FAIL: <reason>`, then `GDS-TEST DONE pass=N fail=M`.

- In the editor: `NC_GDS_TEST=1` in the editor's environment (stdio run: export it before ncli), then `ncli play-test --seconds 60 --expect "GDS-TEST DONE pass=<N> fail=0"`.
- Packaged: `NC_GDS_TEST=1 NC_GDS_TEST_EXIT=1 NC_GDS_TEST_OUT=captures/test <game exe>` → exit code 0/3 + screenshots.
- Bug fixes: `Tools/gds/test_bug_template.lua` → `Content/Scripts/test_bug_<key>.lua`, FAIL before the fix, PASS after (workers.md iterate-gate 1b); `gds_bisect.py` finds the commit that broke a test.
- Performance: `t.perf("walk", 10, "W")` in a test + `ncli play-test --fps <targetFps>` → p50/p95/p99 per run, FAIL over budget (GPU only; llvmpipe numbers mean nothing).
- Telemetry (opt-in): `gds_telemetry.lua` + `scripts/telemetry_report.py` (playtest.md).
- Feel baseline (playtest.md): the same harness measures the core verb in the real level (distance, time to apex, stop distance) and prints it with `t.feel({...})` (one `GDS-FEEL {json}` line); the worker stores it in `docs/tests/feel-baseline.json`.

## 7. UI: real-world-design → RmlUi

Mock HTML (user picks a variant per screen, unchanged rule) → `python SKILL/scripts/html2rml.py mock.html PROJECT/UI/<screen>.rml --model <screen>` → `.rml` + `.rcss` + `.preview.lua`; it reports every change (`px→dp`, grid → flex wrap, shadows dropped, `href/onclick` dropped: bind buttons by id in Lua). Open it in the UI editor to check (`NC_EDITOR_UI_DOCUMENT=UI/<screen>.rml NC_EDITOR_SCREENSHOT=docs/screens/<screen>.png NucleonEditor <project>`). Show/bind with the natives of the Game UI category (`CreateUIModel`, documents shown by the game script, see the sample `Content/Scripts/game.lua`). Pause menu and options: the templates ship `nc.pause` and `UI/options.rml` (graphics options already wired): reuse them, restyle them, do not rebuild them.

## 8. Look

- Project lighting `graphics.lighting = "modern"` (Lumen-like GI, reflections, volumetric fog) for stylized/realistic; `classic` for very low-end targets.
- Post process and sky: the Post Process panel / `lighting` table of the level or `project.ncproject`; sun = the Directional Light flagged `atmosphere_sun`.
- Lookdev preset = a `lighting`+`environment` table written by the lookdev worker into the level (`call entity_modify` on the sun + Project Settings) and a `shot` per preset view; art review as for Unity ([art-direction.md](art-direction.md)).
- Software rendering (CI, Xvfb/llvmpipe) washes colours out: art review only on screenshots from the owner's GPU.

## 9. Phase mapping

| Phase | Nucleon |
|---|---|
| project | `exe new-project` (template from the genre: first-person / third-person / top-down) or attach; `ncli setup PROJECT` (harness, example spec, folders, `.gitignore`); HTTP server on (owner, once) or stdio; `ping` + `lint` JSON + `play-test` with `test_move.lua`; `git init` |
| greybox | spec with rooms/shapes → `build` → `lint` → `play-test` with `test_move.lua` green |
| world-gen | `nc_world.py build` → `exe run-lua` → `attach` → `build _world_<name>.json` → `lint --play` (§4b) |
| level-build | blueprint JSON (kit roles / kit rooms / `scatter`) → `cycle` (one worker per blueprint, JSON written in parallel, `cycle` takes the lock itself) |
| hero-asset | Blender MCP unchanged → GLB → `call asset_import '{"sources":[...],"folder":"Content/Models/Hero"}'` → `pieces` row |
| lookdev | `art/look/<name>.json` from the board → `nc_world.py look` → shots in Game View (`NC_EDITOR_GAME_VIEW=1` on the editor) → art review |
| characters | template pawn (`Content/Actors/Player.ncactor`, Character Movement, animation graph `.ncanim`); enemies: navigation volume + `BuildNavigationMesh` / behavior trees (`nc.behavior`) |
| systems | `Content/Scripts/<system>.lua` + actor scripts + `test_<verb>.lua`; Blueprint only if the GDD says so |
| ui-* | §7 |
| juice | effects `.ncfx` / particles entities, `PlaySound*` natives, `ShakeCamera` |
| playtest | `lua-check` + `play-test` (all tests, `--fps`) + `lint --play` + shots; packaged run with `NC_GDS_TEST_EXIT=1`; `capture` for the store |
| build (only if asked) | `exe package <project> --config Shipping --platform win64 --out Packaged/win64` |

## 10. Rules

- Editor open with HTTP on = the owner's editor: never `stdio` on the same project at the same time (two editors, one level file).
- Every ncli call that edits or plays goes between `lock acquire` / `lock release` (same rule as `unity-lock.ps1`); JSON specs, Lua scripts, mocks are written in parallel outside the lock.
- Save before closing a stdio run; never write `.nclevel` by hand while the editor has the level open (the editor overwrites it on save).
- `run_lua` (engine coordinates, not undoable) only for things no tool covers; prefer specs + natives.
- Engine bugs found during a run: write them in the gate (`engine_issues:`) with the repro; the Nucleon repo has its own workflow (do not patch the engine from a game worker).
