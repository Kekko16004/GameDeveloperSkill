# Nucleon Engine: bugs and gaps found by the skill (2026-10-21, revised after reading the code)

These came up while really building things with the skill: the editor was built from `main@d8e49bc` and run on Linux under
Xvfb with llvmpipe. Two things were built: the demo in `docs/samples/nucleon-glade-*.jpg` and the `ncli.py` tests.
The first version was revised with a code review of the engine; each item marks what that review confirmed and what it ruled out.
Nothing has been changed in the engine repository. The fixes belong there and follow its workflow (one branch + PR per stage).
The fix plan is in `tools/nucleon-bench`: benchmark, report, then `EXECUTION-PLAN.md` with the briefs K1-K5 and those of
the measured causes.

## A. Rendering

### A1. Small repeated models drawn wrong or not at all: it is the **GPU-driven** path. HIGH
- **Reproduction:** a level with about 200 copies of `tree_single_A.gltf` (KayKit Medieval Hexagon, 95 vertices, one
  material with `baseColorTexture`) and 40 copies of `trees_A_medium.gltf` (same texture), plus fences, houses and props.
- **Seen:** brown, see-through trees (`docs/samples/nucleon-bug-instancing.jpg`). From the second camera they are not drawn
  at all (only their shadows), and the fence and mushrooms have the wrong colour.
- **Isolation on HEAD (2026-10-21, same camera, `docs/samples/nucleon-bug-a1-isolation.jpg`):**

  | run | result |
  |---|---|
  | default (`gpuDriven=true`, 19 classes) | trees missing (their shadows are there), fence brown/grey, mushroom grey; some houses appear and disappear from run to run |
  | **`NC_GPU_DRIVEN=0`**, instancing **on** (`gpuDriven=false`, 10776 instanced items) | **all correct**: trees, orange fence, red mushroom, tower |
  | `NC_EDITOR_VIEWMODE=basecolor` | same defect: it is geometry or texture sampling, not lighting |
  | `NC_GD_COUNT=0` (no draw-indirect-count) | same defect |
  | `NC_PREPASS_MASKED=0` | same defect |

  **So: the CPU instance classes and the instanced shaders are fine. The defect is in the GPU-driven draw (OpenGL, llvmpipe;
  D3D12/Vulkan not tried).** The shadows are right, so the GPU-driven culling and shadow pass see the trees; what is wrong is
  the forward / G-buffer draw of the classes.
- **Ruled out by reading the code:**
  - the class key: it already covers textures, every material parameter, fade/fadeInvert, the alpha mode and every vertex and
    index stream (`glmodern_scene.inc:473-523`, `glmodern.cpp:5561`);
  - a LOD cross-fade: a 95-vertex tree has no LOD (`lodMinTriangles = 256`, `cooker.h:29`).
- **Remaining candidates:**
  1. the UV/colour stream bound for the class (`gdBindStreams` / `gdRecordGbufClass` against what `forwardPipeline` expects).
     A uniform brown is one texel sampled every time.
  2. an object-wide `crossFade` stuck below 1 (`glscenemodel.cpp` ~5535, the streaming / HLOD fade-in) that `ncCoverage` turns
     into discarded fragments.

  The GPU-driven draws are recorded after the CPU forward objects (`glmodern.cpp` ~10577).
- **Brief:** K1 in `tools/nucleon-bench/briefs.json` (branch `fix/a1-instanced-material`).

### A2. `NC_INSTANCING=0` turns off much more than instancing: confirmed, docs only. MEDIUM
It turns off (`glmodern.cpp:191`):
- CPU instancing;
- GPU-driven (`glmodern_gpudriven.inc:763`);
- the retained scene;
- GPU LOD;
- pre-skinning;
- foliage (no other draw path);
- ISM sets;
- the mesh particles of the effects, which disappear **without a message** (`glfxextras.cpp:576`).

The separate switches already exist: `NC_GPU_DRIVEN`, `NC_RETAINED_SCENE`, `NC_FOLIAGE_GPU`, `NC_GPU_INSTANCES`. What is missing
is the note in LIGHTING.md "Instancing" (and a log line for the particles). K2.

### A3. Foliage with models: partly superseded. HIGH for games
Since 16 October these exist: the `instances` entity (ISM/HISM, `docs/rendering/INSTANCES.md`), "Convert Selection to
Instances" and Tools > Optimize Level for Streaming. A tree kit does not have to become thousands of entities any more. But:
- all of it is "built, never run";
- instances stay out of the retained scene and GPU LOD.

What is really missing is COMPETITOR_PLAN 2.3: foliage types painted with a brush that use models with LODs. K5. The skill
should use `instances` for repeated props once they have been run.

### A4. Forest: high frame times and hitches. Correct summary, to be measured on a GPU
From `docs/performance/PERFORMANCE.md`:
- ForestDemo GPU 23-30 ms against a 14 ms target;
- `World stream: load cell` 190-260 ms, `HLOD proxies` 60 ms;
- the wave 1 fixes are "not run".

The causes are measured by the `tools/nucleon-bench` bench (H4 shadows, H5 LOD, H6 foliage, H7 GI, H9 pixel/CPU bound).

### A5. Hidden shapes still collide: intended (as in UE), docs only. LOW
The collider is created without looking at `visible` (`resources/lua/nc/scene.lua` ~1150). The option already exists:
Details > Physics > Collision: None (`collision = "none"`, PHYSICS.md:239). It was the skill that hid the templates' Ground;
`nc_world.py attach` now removes it. One line in PHYSICS.md (K2).

### A6. Profiler counters with dangling names: garbage in the report, crash on exit. MEDIUM (new, 2026-10-21)
- **Garbage:** the `NC_PROFILE_REPORT` report prints a `misc:` line with unreadable names (`����U 1.249 ms (max 59.965)`).
  Some `ncprof::Counter`s are registered with a `name` that points to memory that has already been freed or reused.
- **Crash:** with `NC_PROFILE_REPORT` on and the report not yet complete (`NC_PROFILE_REPORT_FRAMES` not reached), calling
  `os.exit()` from Lua (or any `exit()` that runs the C++ exit handlers) crashes. Backtrace:
  `__strlen_evex <- ncprof::CounterWindow::read() <- Report::write() <- Report::~Report() <- __run_exit_handlers <- os_exit`
  (`engine/src/core/profiling/profiler.cpp` ~286 and ~525). `strlen` runs on those same names.
- **Fix:** counters copy their name (`std::string`) or get static names; `Report` writes from an explicit shutdown, not from a
  static destructor.
- The bench closes with the engine's `exit()`, which does not trigger it.

### A7. `makeSrgbCopy` reads textures back from the GPU after every restream. HIGH candidate for the Megascans drops (to be measured)
`glmodern.cpp` ~2900-2960: an uncompressed colour texture gets a GPU readback (full stall), then a second sRGB texture, when:
- it has no mip levels;
- or the device lacks `Caps::srgbViewsRgba8`;
- or `NC_SRGB_VIEW=0`.

This happens on its first draw **and again after every restream to another size**, which is exactly what happens when you walk
up to an asset and its mips go up. On llvmpipe a single readback took 53 ms in one frame (counter
`modern: srgb copies (readback)`). The bench measures it (H1, config `srgb-readback`, and the counter in the report). The fix
is in brief H1: sRGB format at upload, never a readback on the render thread.

## B. Editor MCP

### B1. `capture_viewport` does not wait for everything. HIGH for automated QA
It only calls `Scene::finishLoading()` (`scene.cpp:1573`), which links the pending models; the heavy models are cooked inside
that load. It does **not** wait for:
- texture streaming;
- world partition cells and HLOD;
- the preparation of virtualized geometry and GPU sets;
- reimports.

`Scene::loadingPending()` exists (`scene.h:524`) but the tool does not use it, and the result has no `pending` field. K3.

### B2. Type names in the MCP schema. MEDIUM
`entityTypeName(Terrain)` returns "Landscape" (`scene.cpp:141`), while the enum offers `terrain` (`mcp_tools.cpp:774`,
MCP.md:116). The enum also leaves out Water, Fog Volume, Decal, Effect, Post Process Volume and Instances, even though the
comparison would accept them. K2.

### B3. The editor guide (`mcp.cpp:91`) says "+Y is up", rotation (X, Y, Z). MEDIUM
It should say Z up, `[pitch, roll, yaw]`. K2.

### B4. What the MCP cannot do: some of it is reachable with `run_command`. HIGH
- **Already reachable with `run_command`:**
  - Add > Effects (Water, Fog Volume, Decal, Particle Emitter);
  - Post Process Volume and Navigation Volume;
  - Build GI / Navigation / HLOD.
- **The real gaps:**
  - sculpting and painting the landscape;
  - foliage;
  - the level's `lighting` table;
  - Project Settings values (the commands only open the window);
  - import settings;
  - Game View (no command id);
  - the `entity_modify` fields of water, fog, decal, particles and post-process volumes.
- `run_lua` changes the world but does not save to the level and is not undoable. K4 (with a `scene_stats` tool).

### B5. `capture_viewport` only at the size of the panel. MEDIUM
The schema has `target` and `max_width`, and `max_width` can only scale down (`viewport.cpp:209`). It needs an offscreen
render at a chosen resolution. K3.

### B6. In PIE, `TakeScreenshot` reads the whole window. MEDIUM
`natives/game.lua:348` reads the whole window framebuffer, so in Play In Editor the shot includes the editor. This is
documented ("what the window shows"); what is missing is a capture of the game view only. K3. The skill uses the
`gds_capture.lua` handshake meanwhile.

## C. Lua API / natives

### C1. Missing optional parameters in the registry. MEDIUM
The registry marks a parameter optional only if its type ends with `?` or it has a default (`natives.lua:178-183`). These
have neither:
- the `value` of `SetAnimationParameter`;
- the `...` of `TriggerEvent`, `TriggerServerEvent`, `TriggerClientEvent`, `CallOnServer`, `CallOnOwner`, `CallOnAll`,
  `SendNetworkMessage` and `SendNetworkMessageToPlayer`.

Fix the definitions, then run `run-natives-docs.sh --update` (NATIVES.md, LuaLS, Blueprint nodes). K2. The skill corrects
its own snapshot meanwhile.

### C2. `GetFrameTime` is capped at 0.1 s only in Play In Editor. LOW
The cap is `std::min(GLWin::getTimeStep(), 0.1f)` in `editor.cpp:6434`; a packaged game has no cap. Document it in the
native's description (K2). The bench and `gds_telemetry` use `Async.now()`.

## Priorities (= the order of the K briefs in EXECUTION-PLAN.md)
1. **K1 / A1**: GPU-driven, the path is isolated (table above). It breaks any scene with repeated objects.
2. **K2**: small fixes in one PR: B2, B3, C1 + the doc notes A2, A5, C2.
3. **K3**: B1 + B5 + B6: wait for the whole load with a `pending` field, offscreen capture at a chosen resolution, a Game View
   command, a game-view-only capture.
4. **K4**: B4: MCP tools for landscape, foliage, the lighting table, the volume fields, and `scene_stats`
   (`Lighting.getStats()` can already be read through `run_lua`, but there is no dedicated tool).
5. **K5**: A3: a foliage brush with models and LODs on top of the ISM instances that already exist.
6. Then the H briefs that the bench confirms on the real GPU.

There is still no headless test runner that runs `Content/Scripts` in Play: `-run-lua` exists but does not run in Play.
The skill uses `ncli play-test` (the editor with MCP) meanwhile.
