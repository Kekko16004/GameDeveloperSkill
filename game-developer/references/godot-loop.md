# Godot loop — `engine: godot` (minimal)

Rare path: kept small on purpose. Same GDD, workers, contract, gates; no GDS deterministic layer yet, so the bar is met with files + headless runs. Not verified by this skill on a real project: the first project worker records what works in its gate (`engine_gap:`) and fixes this page.

## Requirements

- Godot 4.3+ (`godot` on PATH or `config.json` `paths.godot`), `godot --headless --version` answers.
- Optional editor MCP: if the project has an MCP addon under `addons/` (the launch skill's `project_scan.py` lists `mcp_addons`), use its tools for scene edits and screenshots; otherwise work on files.

## Bridge (adapter verbs, [engines.md](engines.md))

| verb | how |
|---|---|
| ping | `godot --headless --path PROJECT --quit` exit 0 + `project.godot` `config/features` |
| build | a worker script `tools/gds_build.gd` (EditorScript or `-s` SceneTree script) reads the same blueprint JSON and writes `.tscn` (CSGBox3D for greybox, instanced `.glb` scenes for kit pieces) |
| lint | `godot --headless --path PROJECT --check-only -s <script>` per script + a scene scan script (nodes below kill Y, missing resources) → `{"issues":N}` |
| shot | `godot --path PROJECT --write-movie captures/x.png --quit-after N <scene>` (needs a display; Xvfb on Linux) |
| test | GUT (`addons/gut`) headless: `godot --headless -s addons/gut/gut_cmdln.gd -gexit` |
| lock | one editor, one headless writer at a time (`Saved/gds-godot.lock`, same JSON as `ncli lock`) |

## Phase notes

- Y up, meters. 2D: TileMapLayer + Kenney 2D/itch CC0 tilesets.
- UI: designer mock → Control scene (`.tscn`) built by script; themes in a `Theme` resource. The user still picks a variant per screen.
- Systems in GDScript, one verb = script + GUT test.
