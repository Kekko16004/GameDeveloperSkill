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
| **ping** | `unity command gds_ping` | `ncli ping` | MCP `list_toolsets` + `gds_ue` import | `godot --headless --version` |
| **build** (spec → scene) | `gds_build` / `gds_world` / `gds_village` | `ncli build spec.json` (+ `exe run-lua` world scripts) | `gds_ue` + PCG | script writes `.tscn` |
| **lint** → `{"issues":0}` | `gds_lint` | `ncli lint --write docs/lint/scene-lint.json` | `gds_ue.lint` | `godot --headless --check-only` + scene scan |
| **shot** | `gds_shot` / `screenshot` | `ncli shot` | `gds_ue.shot` | `--write-movie` frame / viewport capture |
| **test** | `run_tests` (EditMode/PlayMode) | `NC_GDS_TEST=1` + `ncli play-test --expect "GDS-TEST DONE ... fail=0"` | automation tests toolset | GUT / `godot --headless -s` |
| **play** | `editor_play` | `ncli play-test` | PIE toolset | `godot --headless` run |
| **lock** | `scripts/unity-lock.ps1` | `ncli lock` | one MCP client (same rule) | one editor |
| **package** (only if asked) | Unity build | `ncli exe package` | UAT | `godot --export-release` |

Gates are identical across engines: the same `docs/gates/NN-*.md`, the same `lint:` line, the same evidence rules. "Engine X does not support Y" is written in the gate as `engine_gap:` with the workaround; it never silently lowers the bar.

## Style is independent of the engine

`style:` picks assets, look and art-review focus ([styles.md](styles.md)); the engine renders it. Known limits the skill tells the user once, at Q0, without deciding for them:

- `realistic` on Unity URP = stylized-realistic; Nucleon modern lighting and Unreal go further.
- `2d-pixel`: Unity (2D URP) or Godot; Nucleon and Unreal are 3D-first.
- `voxel`: Unity has `GDS.VoxelWorld`; elsewhere voxel meshes come from VoxelAI/Blender as models.
- WebGL / mobile target: Unity or Godot.

## What changes per engine in the pipeline

Nothing in the order of phases, the contract, the parallel scheduler or the gates. Per engine only: the bridge commands, the language of `systems` (C# / Lua natives / Blueprint-C++ / GDScript), the UI target (UI Toolkit UXML / RmlUi RML / UMG / Control scenes) and the asset import step.
