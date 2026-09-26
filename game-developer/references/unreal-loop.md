# Unreal loop — `style: realistic`

Used only when the GDD locks `style: realistic` and `engine: unreal` (see [styles.md](styles.md)). Everything else in the pipeline (GDD, gates, workers, art review, UI choice by the user) stays the same; the tools change.

## Requirements (doctor checks them)

- **Unreal Engine 5.8+** (Epic Launcher). The official MCP server does not exist before 5.8. Installed here today: UE 5.4 only → the worker stops and asks the user to install 5.8 (≈ 60 GB), or proposes `style: stylized` in Unity.
- GPU: see the hardware table in styles.md. GTX 1660 Super 6 GB = software Lumen, scalability High, small levels.
- Claude Code: `/plugin install unreal-engine-skills-for-claude-code@claude-plugins-official` (Epic's `unreal-mcp` skill). Other hosts: point them at the same MCP URL.

## Editor MCP (first-party, free)

1. Project: `Edit > Plugins` → enable **Unreal MCP** (`ModelContextProtocol`) and **All Toolsets** (`AllToolsets`) + **Python Editor Script Plugin**. Restart.
2. `Edit > Editor Preferences > General > Model Context Protocol` → **Auto Start Server**. Default `http://127.0.0.1:8000/mcp` (HTTP only, loopback, no auth — never port-forward).
3. Output Log: `ModelContextProtocol.GenerateClientConfig ClaudeCode` (or `Codex`, `Gemini`, `Cursor`, `All`). Launch the agent from the folder with the `.uproject`. Boot order: **Editor first, agent second.**
4. Tools are in tool-search mode: `list_toolsets` → `describe_toolset <name>` → `call_tool`. Load only the toolset you need (actors, materials, Niagara, Sequencer, widgets, screenshots, PIE control, logs, automation tests, Python). `ModelContextProtocol.RefreshTools` after adding tools.
5. Smoke test before any work: list actors (read-only), spawn one named actor, Ctrl+Z works. If undo fails, stop.

## Deterministic layer: `templates/unreal/gds_ue.py`

Copy it to `<Project>/Content/Python/gds_ue.py` (worker `project` does it). Then through the Python tool:

| Call | Does | Gate |
|---|---|---|
| `gds_ue.lookdev("realistic-overcast")` | directional sun (atmosphere sun), SkyAtmosphere, real-time SkyLight, VolumetricCloud, ExponentialHeightFog (volumetric), unbound PostProcessVolume | `applied` JSON |
| `gds_ue.lint(autofix=True, write_to="docs/lint/ue-lint.json")` | buried/floating static meshes by line trace (cm) | `issues: 0` |
| `gds_ue.shot("gds/035-lookdev.png")` | high-res viewport screenshot | PNG |
| `gds_ue.import_folder(fab_dir, "/Game/_Game/Megascans/<name>")` | batch-import a FabCLI download, no dialogs | count |
| `python gds_ue.py heightmap art/world/height.png 1009 42` | 16-bit heightmap (runs outside UE) → Landscape > Import from File | PNG |

Presets: `realistic-overcast`, `realistic-golden`, `realistic-noon`, `realistic-night`. The script is written against the documented API and not yet run on 5.8 here: the first worker records any mismatch in its gate and fixes the script, not the scene.

## Assets (realistic)

1. **Megascans / Fab**: free for Unreal projects. In-editor: Fab window (drag into level). Headless: FabCLI (`fab.enabled: true`, `fabcli download <uid> -o <fab.library_path>`) + `gds_ue.import_folder`.
2. **Poly Haven** (CC0) models, HDRIs, textures: `scripts/polyhaven.mjs` or the Blender MCP.
3. Characters: MetaHuman (free, in-editor) or Quaternius UBC retargeted; animations from the UE sample packs.
4. One family: Megascans + Poly Haven mix well (both photogrammetry); do not add low-poly kits.

## World (realistic)

- Landscape from `gds_ue.py heightmap` (or Landscape sculpt tools), material with layer auto-blend by slope/height (Megascans surfaces).
- Scatter with **PCG** (built-in): a PCG Volume + graph `Surface Sampler → Density Filter (slope/height) → Static Mesh Spawner` with Megascans foliage. One graph per biome; seed exposed. Generate, then `gds_ue.lint`.
- Buildings: modular Megascans/Fab kits or Blender `gds_building.py` export (realistic materials swapped in UE).

## Phases mapping

| Unity phase | Unreal equivalent |
|---|---|
| project | new project from **Third Person / First Person** template (C++ not required), plugins above, `Content/Python/gds_ue.py` |
| greybox | template map trimmed + BSP/cube blockout, PIE test via MCP PIE toolset |
| world-gen | heightmap → Landscape + PCG scatter |
| level-build | modular kit placement by Python from the same blueprint JSON idea (grid, snapped); Fab kits |
| lookdev | `gds_ue.lookdev(preset)` + Lumen/VSM check in Project Settings |
| characters | template character / MetaHuman + State Tree for enemies |
| systems | Blueprints (MCP Blueprint toolset) or C++; automation tests via the tests toolset |
| ui | real-world-design (user picks a variant) → UMG widget built with the widget toolset |
| juice | Niagara toolset, MetaSounds |
| playtest / art review | PIE + screenshots toolset + `gds_ue.lint` + [art-direction.md](art-direction.md) |

Third-party alternatives (only if 5.8 is impossible): chongdashu/unreal-mcp, flopperam/unreal-engine-mcp — experimental, extra C++ plugin build, weaker coverage.
