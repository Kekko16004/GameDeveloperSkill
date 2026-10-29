# Nucleon Engine: bugs and gaps found by the skill (first list 2026-10-21, re-checked 2026-10-29)

These came up while really building things with the skill. First round: the editor built from `main@d8e49bc`, Linux, Xvfb,
llvmpipe (the demo in `docs/samples/nucleon-glade-*.jpg` and the `ncli.py` tests). Second round (2026-10-29): the editor built from
`quality/q1@8e847b7d` on Windows 11, Direct3D 12, RTX 5060, run on a hidden desktop through `ncli` on a scratch project; every item
below was re-read in the engine source of that revision (file:line are for it) and, where it can be seen, run.
Nothing has been changed in the engine repository. The fixes belong there and follow its workflow (one branch + PR per stage).
The fix plan is in `tools/nucleon-bench`: benchmark, report, then `EXECUTION-PLAN.md` with the briefs K1-K5.

**Re-checked against the frozen game build `game-build-20261029` (`d241aa27`, NucleonEngine main) on 2026-10-29**, by reading the source of that revision
(not by running): D1, D2 and the natives-file lag of D4 are fixed there (marked below); every other item was not touched by the commits since `8e847b7d`
as far as the log shows (first-person kit, NUI/DUI on CEF, gameplay framework, render thread, MCP growth to 49 tools, view parity fixes), so it stays open.

Status at a glance (2026-10-29, before that re-check): **open** A1 (not reproduced on D3D12 with a simple test, not closed), A2, A3, A4, A5, A6, B1-B6, C1, C2, D1-D4, M1, M2; **mostly fixed** A7.
New since the first list: D1-D4 (found by the real-editor test of 2026-10-29).

## D. Found on 2026-10-29 (quality/q1, D3D12)

### D1. `Raycast` fails in any level that has an `instances` entity with a collider. HIGH, **fixed in `d241aa27`** (source read, not run)
`entityOfBody` in `resources/lua/nc/natives/world.lua` now handles the `{bodies = ...}` table of an instances entity. The ncli lint still sets such colliders to `none` for its probe (harmless).
- **Seen:** `Raycast(from, to)` raises `attempt to index a boolean value (local 'b')` as soon as the level has an `instances` entity whose
  collision is not `none`. `ncli lint --play` (a probe script made of `Raycast` calls) timed out because of it; ncli now sets such entities'
  collision to `none` for the probe and restores it (so a lint still works), but every game script that raycasts is broken.
- **Cause:** `resources/lua/nc/scene.lua:1284` sets `entity.body = made > 0 and true or nil` for instances (a boolean: how many colliders
  were made), while `resources/lua/nc/natives/world.lua:24-25` (`entityOfBody`, called from `Raycast` at world.lua:63) does
  `local b = rawget(rec, "body"); if b and b.getId then ...` and indexes the `true`.
- **Repro:** `entity_add` type `instances` (any model, a few `transforms`, collision left at its default), Play, run a script that calls
  `Raycast(vec3(0,0,10), vec3(0,0,-10))`. Fix: `type(b) == "table" and b.getId` in `entityOfBody` (or keep the body list of instances in
  another field).

### D2. `entity_add` type `instances` defaults to `collision = "mesh"`, which the runtime does not support. MEDIUM, **default fixed in `d241aa27`** (schema says default `box`; an explicit `mesh` still warns on every Play)
`editor/src/mcp/mcp_tools.cpp:1420` (`e->collision = "mesh"`, schema text at 1310 "default mesh") but `resources/lua/nc/scene.lua:1239-1241` turns
it into a box and logs `entity 'X': collision = 'mesh' is not supported for instances, a box is used` on **every Play** and every packaged start
(seen in `Saved/Logs/game.log`). The default should be `box` (or the editor should say so). The skill writes `box` / `none` explicitly.

### D3. The Material document's big preview is blank in a window shot (D3D12). MEDIUM
`NC_EDITOR_MATERIAL=<file> NC_EDITOR_SCREENSHOT=...` (also with `NC_EDITOR_SHOT_EXTRA_FRAMES=300`, visible or hidden desktop): the left preview
area is empty (no sphere, no background gradient) while the strip of model spheres under it renders. The preview image is
`ImGui::Image(s.target->getTexture())` at `editor/src/materials/materialeditor.cpp` ~2393 (a `RenderTarget` of its own). `nc_mat.py check` measures the strip
instead, so a pass means "the models render", not "the material looks right".

### D4. Small things
- `NucleonEditor -optimize-level ... -dry-run` prints `written: <level>` although nothing is written (`editor/src/world/levelopt.cpp` ~1015; the dry run returns at 853).
- (fixed in `d241aa27`: the file has 622 natives, the same as the built registry) `docs/api/lua/natives.json` of the engine lagged behind the sources: the five Camera natives (`SetActiveCamera`, `GetActiveCamera`, `GetCameraEntities`,
  `GetCameraEntityLens`, `SetCameraEntityLens`, `resources/lua/nc/natives/render.lua:326-368`) are in the build and not in the committed dump / NATIVES.md
  (404 natives in the registry of the built editor, 399 in the file). `ncli api-refresh --from-editor` reads the live registry.
- `build` of a spec entry the MCP refuses (e.g. `render_flags.cast_shadow` on a shape, `render_flags` on a camera) still adds the entity "with default values"
  (the error text says so): the engine adds first and validates the optional fields after. The skill now drops those keys with a warning; a failed entry still leaves
  a default entity in the level (seen with `shape.color` as a hex string: it must be `[r, g, b]`).

## A. Rendering

### A1. Small repeated models drawn wrong or not at all: the **GPU-driven** path. HIGH (OpenGL, llvmpipe; not reproduced on D3D12 with untextured boxes)
- **Reproduction (2026-10-21, OpenGL, llvmpipe):** about 200 copies of `tree_single_A.gltf` (KayKit Medieval Hexagon, 95 vertices, one
  material with `baseColorTexture`) and 40 copies of `trees_A_medium.gltf` (same texture), plus fences, houses and props.
- **Seen:** brown, see-through trees (`docs/samples/nucleon-bug-instancing.jpg`). From the second camera they are not drawn
  at all (only their shadows), and the fence and mushrooms have the wrong colour.
- **Isolation (same camera, `docs/samples/nucleon-bug-a1-isolation.jpg`):**

  | run | result |
  |---|---|
  | default (`gpuDriven=true`, 19 classes) | trees missing (their shadows are there), fence brown/grey, mushroom grey; some houses appear and disappear from run to run |
  | **`NC_GPU_DRIVEN=0`**, instancing **on** (`gpuDriven=false`, 10776 instanced items) | **all correct** |
  | `NC_EDITOR_VIEWMODE=basecolor` | same defect: it is geometry or texture sampling, not lighting |
  | `NC_GD_COUNT=0` (no draw-indirect-count) | same defect |
  | `NC_PREPASS_MASKED=0` | same defect |

  The CPU instance classes and the instanced shaders are fine; the defect is in the GPU-driven draw (the shadows are right: culling and
  the shadow pass see the trees; the forward / G-buffer draw of the classes is wrong).
- **Ruled out by reading the code:** the class key (it covers textures, every material parameter, fade, alpha mode and the vertex / index
  streams: `glmodern_scene.inc:473-523`, `glmodern.cpp:5561`); a LOD cross-fade (a 95-vertex tree has no LOD, `lodMinTriangles = 256`).
- **Remaining candidates:** the UV / colour stream bound for the class (`gdBindStreams` / `gdRecordGbufClass` against `forwardPipeline`); an object-wide
  `crossFade` stuck below 1 (`glscenemodel.cpp` ~5535) that `ncCoverage` turns into discarded fragments.
- **Brief:** K1 in `tools/nucleon-bench/briefs.json` (branch `fix/a1-instanced-material`).
- **2026-10-29, D3D12 (RTX 5060), `quality/q1@8e847b7d`:** 300 copies of an untextured model (`Box.glb`, scattered by `ncli build`) draw identically with the default path and with `NC_GPU_DRIVEN=0` (two screenshots compared): **not reproduced** here. The original needs small *textured* models (the KayKit trees), so this is not conclusive: re-run it with the kit through `tools/nucleon-bench` H8 before closing K1. `NC_GPU_DRIVEN=0` stays the workaround on OpenGL; for repeated props prefer `instances` (but D1 / D2).

### A2. `NC_INSTANCING=0` turns off much more than instancing. MEDIUM, docs only, **still open**
`engine/src/renderer/pipeline/glmodern.cpp:229-231` sets `instancing = false`, which also turns off GPU-driven, the retained scene, GPU LOD,
pre-skinning, foliage (no other draw path), ISM sets and the mesh particles of the effects (silently). The separate switches exist
(`NC_GPU_DRIVEN`, `NC_RETAINED_SCENE`, `NC_FOLIAGE_GPU`, `NC_GPU_INSTANCES`). `docs/rendering/LIGHTING.md` "Instancing" (line 775) still describes only
the instancing itself. K2.

### A3. Foliage with models. HIGH for games, partly superseded
The `instances` entity (ISM/HISM, `docs/rendering/INSTANCES.md`), "Convert Selection to Instances" and Tools > Optimize Level for Streaming exist, and
the skill now builds `instances` groups (`ncli build` `instances` / `performance.auto_group`; checked in the editor 2026-10-29: groups are created with up to
100000 transforms, `wind`, `cull_distance`, `cast_shadows`, collision `none|box|capsule`; **but see D1 and D2**). Missing: COMPETITOR_PLAN 2.3, foliage types
painted with a brush that use models with LODs (K5). Instances stay out of the retained scene and GPU LOD.

### A4. Forest: high frame times and hitches. To be measured on a GPU
From `docs/performance/PERFORMANCE.md`: ForestDemo GPU 23-30 ms against a 14 ms target; `World stream: load cell` 190-260 ms. Measured by
`tools/nucleon-bench` (H4 shadows, H5 LOD, H6 foliage, H7 GI, H9 pixel/CPU bound). Not re-run on 2026-10-29.

### A5. Hidden shapes still collide: intended (as in UE), docs only. LOW, **still open**
`addStaticCollision` (`resources/lua/nc/scene.lua:1288-1295`) never looks at `visible`; `collision = "none"` is the switch. There is now also the render
flag `hiddenInGame` (docs/engine/RENDER_FLAGS.md): it hides the object in Play, and it still collides. One line in PHYSICS.md (K2).

### A6. Profiler counters with dangling names. MEDIUM, **still open**
`ncprof::Counter(const char* name, ...)` still stores the pointer (`engine/src/core/profiling/profiler.h:143`), so a counter registered with a
temporary name prints garbage in the `NC_PROFILE_REPORT` `misc:` line, and with `NC_PROFILE_REPORT` on, `exit()` before the report is complete
crashes in `CounterWindow::read() <- Report::~Report()` (`profiler.cpp`). Fix: copy the name (`std::string`), write the report from an explicit shutdown.
(The new MCP `profile_capture` / `ncli profile` ran without it on 2026-10-29: the counter means came back with sane names.)

### A7. `makeSrgbCopy` GPU readback after every restream. **Mostly fixed**
`engine/src/renderer/pipeline/glmodern.cpp:3604-3660`: with `NC_SRGB_VIEW=1` (the default) and `Caps::srgbViewsRgba8` an uncompressed colour texture with mip
levels gets an sRGB **view**, no readback. The readback path remains for textures without mips, devices without the cap and `NC_SRGB_VIEW=0`.

### M1. Material system: models that were never run
`nc_mat.py check` renders each model in the Material document with models on and with `NC_MATERIAL_MODELS=0`. 2026-10-24 (OpenGL, llvmpipe): Car Paint,
Cloth, Single Layer Water, Preintegrated Skin render; Two Sided Foliage equals the fallback (no light from behind).
**Glass / Acrylic: suspect, still there on D3D12 (2026-10-29):** the Glass and Acrylic tiles of the model strip are empty circles (no highlight, no
Fresnel rim) while Default Lit, Clear Coat, Car Paint, Cloth, Subsurface, Skin, Hair, Eye, Foliage, Water and Unlit draw; Thin Film is nearly black. Check it
in a scene (`:world`) before any glass ships. A real-GPU art review is still needed (and see D3).

### M2. Opening a material marks it unsaved. LOW, **still open**
`NC_EDITOR_MATERIAL=<file>`: the tab is marked modified (`leaf •`, "1 unsaved" in the status bar) with no edit made (seen again on 2026-10-29): the model
preset / the feature cards write their values back on open. Closing it asks "save changes?".

## B. Editor MCP (27 tools at `8e847b7d`, 49 in the frozen build, 52 at `quality/q1@a58cb429`)

New at `a58cb429` (`scripts/data/nucleon-mcp-tools.json`): `weather` (get / set / clear / strike; scope level, project, live), `destruction` (fracture, info, make_actor, make_cloth_actor; state, damage, break, set_health, ray, explode, cloth_wind in Play), `memory_stats` (memory by tag, load timeline); `animation_state` got `bone`, `bone2`, `map`, `pelvis`, `position`, `section`, `slot`, `source`; `entity_add/modify` `render_flags` now has `receive_shadow`, `custom_depth_stencil`, `lighting_channels` and `cast_shadow` on shapes; the light object has `lighting_channels`.

New in the frozen build (22 tools, `scripts/data/nucleon-mcp-tools.json`): `anim_graph`, `animation_state`, `asset_read`, `asset_write`, `blueprint_graph`, `build`, `foliage`, `fx_asset`, `gameplay_assets`, `gameplay_state`, `input_bindings`, `landscape`, `levels`, `lighting_get`, `lighting_set`, `material_graph`, `natives_search`, `open_level`, `play_test`, `save_games`, `sequence`, `web_ui`; `entity_add` / `entity_modify` gained `decal`, `fx`, `ui_surface`. B4 below is largely answered. Tried by the skill: `play_test`, `web_ui` (`status`).

New since the first list: `profile_capture`, `camera_pilot`, `material_domain`; `entity_add` / `entity_modify` gained `wind`, `transforms`,
`cull_distance`, `cast_shadows`, `collision` (instances), `camera`, `render_flags`, `post_volume`; types `instances`, `camera`, `post_volume`.
`ncli` wraps every tool (`tools-check` compares them with `scripts/data/nucleon-mcp-tools.json`).

### B1. `capture_viewport` does not wait for everything. HIGH for automated QA, **still open**
It only calls `Scene::finishLoading()` (`editor/src/mcp/mcp_tools.cpp` ~2120). It does not wait for texture streaming, world cells and HLOD,
virtualized geometry, GPU sets or reimports; `Scene::loadingPending()` is not used and the result has no `pending` field. Right after the editor starts the
first call can answer "not visible" (ncli retries). K3.

### B2. Type names in the MCP schema. MEDIUM, **still open**
`entityTypeName(Terrain)` is "Landscape" (`editor/src/scene/scene.cpp:141`) while the `scene_list` enum offers `terrain` (`mcp_tools.cpp:1138`); the enum also
leaves out Water, Fog Volume, Decal, Effect, Post Process Volume, Camera and Instances (the filter accepts them, `ncli entities --type instances|water|camera|"post process volume"` works). K2.

### B3. The editor guide (`editor/src/mcp/mcp.cpp:94`) says "+Y is up", rotation (X, Y, Z). MEDIUM, **still open**
It should say Z up, `[pitch, roll, yaw]` (the tools themselves are Z up). K2.

### B4. What the MCP cannot do. HIGH, **mostly answered in the frozen build** (landscape, foliage, `lighting_get/set`, `levels`, `input_bindings`, `asset_read/write`, `build` jobs); the text below is the 8e847b7d state
Still missing in the frozen build: Project Settings values, import settings, Game View, `entity_modify` fields of water / fog / particles.
Reachable with `run_command` (112 ids): Add > Effects, Post Process and Navigation Volumes, Level Streaming Volume, Build GI / Navigation / HLOD /
Reflection Captures, Optimize Level for Streaming, Package Project, the Play modes. Now also in the MCP: post volumes with blendables, camera entities, render flags,
the Material Domain. Real gaps: sculpting and painting the landscape, foliage, the level's `lighting` table, Project Settings values, import settings, sublevels
(Level Streaming), Game View (no command id), the `entity_modify` fields of water, fog, decal and particles. `run_lua` changes the world but is neither
saved nor undoable. K4 (with a `scene_stats` tool). The skill authors those through Lua tool scripts (`ncli exe run-lua`) or by writing the level with the editor closed.

### B5. `capture_viewport` only at the size of the panel. MEDIUM, **still open**
`max_width` can only scale down (`mcp_tools.cpp:2103-2110`, default 1024): the PNG is the panel size (1041x905 here) whatever you ask. Needs an offscreen
render at a chosen resolution. K3.

### B6. In PIE, `TakeScreenshot` reads the whole window. MEDIUM, **still open**
`resources/lua/nc/natives/game.lua:349-366` reads the window framebuffer (documented); a game-view-only capture is missing. The skill uses the
`gds_capture.lua` handshake.

## C. Lua API / natives

### C1. Missing optional parameters in the registry. MEDIUM, **still open**
A parameter is optional only if its type ends with `?` or it has a default (`resources/lua/nc/natives.lua:178-183`). Not marked: `value` of
`SetAnimationParameter`, the `...` of `TriggerEvent`, `TriggerServerEvent`, `TriggerClientEvent`, `CallOnServer`, `CallOnOwner`, `CallOnAll`,
`SendNetworkMessage`, `SendNetworkMessageToPlayer` (`ncli api-refresh` reports them under `registryFixes` and corrects its own snapshot). K2.

### C2. `GetFrameTime` is capped at 0.1 s only in Play In Editor. LOW, **still open**
`std::min(GLWin::getTimeStep(), 0.1f)` in `editor/src/app/editor.cpp:6626` (it moved from 6434); a packaged game has no cap. Document it in the
native's description (K2). The bench and `gds_telemetry` use `Async.now()`.

## E. Found on 2026-10-29 night (quality/q1 `a58cb429`, D3D12, run through the MCP)

### E1. `api-refresh --from-editor` reads the PROJECT's `nc/` folder, not the editor's own runtime modules. MEDIUM, skill gotcha, engine behaviour
`NucleonEditor -run-lua dump.lua <project>` with `NC_NATIVES_DUMP` makes the registry from `require("nc.natives")`, and that finds the project's `nc/` folder (the runtime
modules the editor copies in when it opens the project) before the embedded copy. A project last opened by an older editor gave 404 natives (the `8e847b7d`
registry) instead of 694, with no error; a fresh `exe new-project` folder (only `nc/ui`) writes nothing. `ncli api-refresh --from-editor` now needs `--project`, refuses a
project with no `nc/natives.lua` and warns when it is older than the editor. Suggested engine fix: the dump should use the embedded modules (as
`natives_registryJson` in `editor/src/play/play.cpp` already does for the Natives panel).

### E2. `destruction` details worth knowing. LOW
`damage` answers `ok:false` when the blow did not break the object (not an error); `explode` on already broken objects answers `hurt:0`; pieces of a destructible
placed with no collider under it fall forever (z -21 after 2 s in the test project). `weather strike` while the weather is off (edit mode, after `clear`) leaves
`flash=0`: turn the weather on first (`set`), the live flash works in Play.

### E3. Not looked at. MEDIUM
The pictures: rain, snow, wet ground, lightning, fracture pieces, cloth, shadow / lighting-channel flags, montages and IK were driven through the MCP and the
Lua state only; nobody has seen them on screen. The engine team wrote them without running them (docs say "never run").

## Priorities (= the order of the K briefs in EXECUTION-PLAN.md)
1. **D1**: `Raycast` + instances (a one-line fix, breaks every raycasting game that uses instances) and **K1 / A1** (check it with textured models on D3D12 first).
2. **K2**: small fixes in one PR: D2, D4, B2, B3, C1 + the doc notes A2, A5, C2.
3. **K3**: B1 + B5 + B6: wait for the whole load with a `pending` field, offscreen capture at a chosen resolution, a Game View command, a
   game-view-only capture. D3 (blank Material preview) with it.
4. **K4**: B4: MCP tools for landscape, foliage, the lighting table, sublevels and `scene_stats`.
5. **K5**: A3: a foliage brush with models and LODs on top of the ISM instances that already exist.
6. Then the H briefs that the bench confirms on the real GPU.

There is still no headless test runner that runs `Content/Scripts` in Play: `-run-lua` exists but does not run in Play. The skill uses
`ncli play-test` (editor with MCP) in the editor and `ncli run-game --gds-test` on a packaged game (the GDS harness reads `NC_GDS_TEST*`).
