# Engines — the user picks, the skill adapts

**The engine is the user's choice, always.** It is the first question of the GDD (Q0) and nothing overrides it: not the style, not the genre, not the hardware. The skill gives facts (what each engine does well for this game, what it costs), never picks. Default order offered: the owner's usual engine from `config.json` `engines.preferred` (first entry), then the others.

| engine | use it for (the skill's notes, not a rule) | bridge | deterministic layer | loop |
|---|---|---|---|---|
| `unity` | everything; strongest kit/CC0 pipeline, 2D, voxel, WebGL/mobile | Unity CLI `unity command gds_*` (+ CoplayDev MCP fallback) | `templates/Editor/GDS` + `Runtime/GDS` | [unity-loop.md](unity-loop.md), [unity-cli.md](unity-cli.md) |
| `nucleon` | 3D PC games, Lua gameplay, modern lighting (Lumen/Nanite-like), HTML/CSS UI, text assets git can diff | `scripts/ncli.py` → editor MCP (HTTP or stdio) | `ncli build` specs + `templates/nucleon` (test harness) | [nucleon-loop.md](nucleon-loop.md) |
| `unreal` | photoreal, Megascans/Fab, big landscapes | Unreal 5.8 MCP (first-party) + `gds_ue.py` | `templates/unreal/gds_ue.py` | [unreal-loop.md](unreal-loop.md) |
| `godot` | small 2D/3D, web export, open source | a Godot MCP addon if the project has one, else files + `godot --headless` | none yet (specs written as `.tscn` by script) | [godot-loop.md](godot-loop.md) (minimal) |

## The adapter contract (what every engine must give a worker)

Every phase in [workers.md](workers.md) talks to the engine only through these eight verbs. A worker reads the row of its `ENGINE=` and never mixes rows.

| verb | unity | nucleon | unreal | godot |
|---|---|---|---|---|
| **ping** | `unity command gds_ping` | `ncli ping` (`state`: the raw editor state) | MCP `list_toolsets` + `gds_ue` import | `godot --headless --version` |
| **build** (spec → scene) | `gds_build` / `gds_world` / `gds_village` | `ncli build spec.json` / `cycle` (+ `exe run-lua` world scripts; `entity add` for one-offs; cameras, `instances`, render flags in the spec) | `gds_ue` + PCG | script writes `.tscn` |
| **lint** → `{"issues":0}` | `gds_lint` | `ncli lint --write docs/lint/scene-lint.json` | `gds_ue.lint` | `godot --headless --check-only` + scene scan |
| **shot** | `gds_shot` / `screenshot` | `ncli shot` / `camera shot NAME out.png` | `gds_ue.shot` | `--write-movie` frame / viewport capture |
| **test** | `run_tests` (EditMode/PlayMode) | `NC_GDS_TEST=1` + `ncli play-test --expect "GDS-TEST DONE ... fail=0"`; on a package `ncli run-game <dir> --gds-test` | automation tests toolset | GUT / `godot --headless -s` |
| **play** | `editor_play` | `ncli play-test` | PIE toolset | `godot --headless` run |
| **lock** | `scripts/unity-lock.ps1` | per run, automatic (`ncli locked`; [nucleon/bridge.md](nucleon/bridge.md)) | one MCP client (same rule) | one editor |
| **package** (only if asked) | Unity build | `ncli exe package --config Development\|Shipping` + `run-game` | UAT | `godot --export-release` |

## Optimization row (loop: [optimization.md](optimization.md))

Measure with vsync off in the real scene, moving, top preset, native resolution; same walk every time.

| step | unity | nucleon | unreal | godot |
|---|---|---|---|---|
| **vsync off** | `QualitySettings.vsyncCount = 0`, `Application.targetFrameRate = -1` | `ncli bench` does it (`NC_D3D12_VSYNC=0`, upscaler off) | `t.MaxFPS 0`, `r.VSync 0` | `DisplayServer.window_set_vsync_mode(VSYNC_DISABLED)`, `Engine.max_fps = 0` |
| **measure** (p50/p95/p99, CPU/GPU) | `FrameTimingManager` (CPU/GPU frame time) in a PlayMode test over the fixed walk | `ncli bench --view ... \| --path f.json` (compares with `docs/bench/<name>.baseline.json`) | `stat unit` + `stat gpu` over the walk, or an Unreal Insights trace | monitors `TIME_PROCESS`, `RENDER_*`; `RenderingServer.viewport_get_measured_render_time_cpu/gpu` |
| **attribute** (which pass or system) | Profiler (CPU) + Frame Debugger / RenderDoc (GPU, draw calls) | `ncli profile` (passes, GPU timings), `tools/nucleon-bench`, [nucleon/perf.md](nucleon/perf.md) | `ProfileGPU`, Insights, `stat scenerendering` | Visual Profiler, `--print-fps`, monitors |
| **scene counts** | Stats window / `UnityStats` | `ncli memory`, the `scene:` line of `lint` | `stat rhi`, `stat memory` | monitors `RENDER_TOTAL_DRAW_CALLS_IN_FRAME` |

Only the Nucleon row has been run by the skill; the Unity, Unreal and Godot rows are the engines' documented commands, **not run here**: the first worker that uses one fixes this table if it is wrong.

Gates are identical across engines: the same `docs/gates/NN-*.md`, the same `lint:` line, the same evidence rules. "Engine X does not support Y" is written in the gate as `engine_gap:` with the workaround; it never silently lowers the bar.

## Style is independent of the engine

`style:` picks assets, look and art-review focus ([styles.md](styles.md)); the engine renders it. Known limits the skill tells the user once, at Q0, without deciding for them:

- `realistic` on Unity URP = stylized-realistic; Nucleon modern lighting and Unreal go further.
- `2d-pixel`: Unity (2D URP) or Godot; Nucleon and Unreal are 3D-first.
- `voxel`: Unity has `GDS.VoxelWorld`; elsewhere voxel meshes come from VoxelAI/Blender as models.
- WebGL / mobile target: Unity or Godot.

## What changes per engine in the pipeline

Nothing in the order of phases, the contract, the parallel scheduler or the gates. Per engine only: the bridge commands, the language of `systems` (C# / Lua natives / Blueprint-C++ / GDScript), the UI target (UI Toolkit UXML / web page on CEF (NUI; RmlUi legacy) / UMG / Control scenes) and the asset import step.
