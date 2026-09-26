# Unity CLI — the primary bridge to the Editor

Official `unity` CLI (beta, `1.0.0-beta.10`+) + the project's **Pipeline** package (`com.unity.pipeline`, added by `install-gds-editor.ps1`). It talks to the **open Editor** in 200-600 ms, no recompile, no domain reload, and returns JSON. Full reference: Unity's own skill `unity-cli` (installed by `npx skills add Unity-Technologies/skills`) — read its `references/integration-advanced.md` when a command is missing here.

Why primary: no MCP tool schemas in context (the MCP bridges cost ~20k+ tokens of schema per session), one shell call per action, and the GDS layer is registered as real commands.

## Preflight (every worker that touches Unity)

```
unity status --format json                       # instance with state "ready" (GUI Editor)
unity command gds_ping --project-path <P>        # {"gds":..,"probuilder":true,"urp":true,"pipeline":true}
```

- No instance: ask the user whether Unity is open (a sandbox can hide it) — or start a headless one: `"<editor>\Unity.exe" -batchmode -projectPath <P> -logFile editor.log` **without `-quit`** (it stays resident; `unity status` does not list it, `unity command` still works).
- Connection refused while an Editor is open → **Safe Mode** (compile errors): `unity pipeline list`, fix C#, restart. Never hand-edit `.unity`/`.prefab` YAML while an Editor is reachable.
- Several Editors open → always `--project-path <P>`.

## The GDS commands (registered with `[CliCommand]`)

| Command | Wraps |
|---|---|
| `unity command gds_world --spec art/world/<n>.json` | `GDS.World.BuildFromFile` (terrain / island / dungeon / cave / voxel) |
| `unity command gds_build --blueprint art/blueprints/<n>.json` | `GDS.LevelBuilder.BuildFromFile` |
| `unity command gds_village --spec art/blueprints/village_<n>.json` | `GDS.Village.BuildFromFile` |
| `unity command gds_lint --autofix true` | `GDS.SceneLint.RunJson` — gate `issues: 0` |
| `unity command gds_lookdev --preset <p> [--hdri <asset>]` | `GDS.LookDev.Apply` |
| `unity command gds_palette --colors "#..,#.."` | `GDS.LookDev.ApplyPalette` |
| `unity command gds_catalog --folder Assets/_Game/Art/Kits/<f>/<pack>` | `GDS.KitCatalog.BuildJson` |
| `unity command gds_kit_scale --folder <kit> --scale <catalog suggestedScale>` | `GDS.KitCatalog.SetImportScale` (relative, batched reimport; rebuild the catalog after) |
| `unity command gds_recolor --folder <kit> --material <name from catalog materials> --hex "#RRGGBB"` | `GDS.LookDev.Recolor` (palette coherence without touching source files) |
| `unity command gds_vfx` | `GDS.VFX.CreateAll` |
| `unity command gds_shot --out screenshots/x.png --view game\|aerial\|hero\|orbitN` | `GDS.Shots.Capture` (real URP render, works headless) |
| `unity command gds_sheet --prefix screenshots/review/<phase>` | 5 review shots for [art-direction.md](art-direction.md) |

Add `--result-only` to get just the JSON.

**Time budget**: `eval` / `eval_file` have a 5 s server-side main-thread budget ("Main thread operation timed out after 5000ms"). Anything long (reimports, big worlds, bakes) goes through a registered `gds_*` command (dispatcher budget) or a built-in with `job`/`--detach`. Never loop `eval` over hundreds of assets.

**Argument names**: GDS command args never reuse global CLI flags (`--color`, `--format`, `--timeout`, `--json`, `--quiet`, `--verbose`, `--proxy`): the CLI eats them before the Editor sees them. Anything else in the GDS API: `unity command eval "return GDS.Characters.ListClips();"` (method body, `return` a value; no `using`/class declarations) or `unity command eval_file snippet.cs`.

## Built-in commands worth knowing (Pipeline 0.7)

Discover with `unity command --format json` (162 in 0.7). The ones the pipeline uses:

- **Scripts**: `create_script` → `recompile` → poll `recompile_status` until `completed` → `console` (errors) → `attach_script`.
- **Scenes**: `create_scene`, `open_scene --path`, `save_scene`, `save_all`, `add_scene_to_build`, `get_scene_hierarchy`, `find_gameobjects`.
- **Play**: `editor_play`, `editor_pause`, `editor_stop`, `capture_game_view`, `capture_scene_view`, `screenshot --output x.png`.
- **Tests**: `run_tests` → `test_status`; CI-style `unity test <P> --mode EditMode --format json` (exit 8 = tests failed).
- **Packages**: `package_add`, `package_list`, `package_resolve`, `package_status`.
- **Bakes**: `bake_navmesh_surfaces`, `bake_lighting`, `navmesh_bake_status`.
- **Settings**: `get/set_quality_settings`, `get/set_lighting_settings`, `get/set_physics_settings`, `set_player_settings`, `set_tags_layers`.
- **Batch**: `batch --operations '[...]' --transactional true` for many small edits in one round-trip.

## Lifecycle (project phase)

```
unity auth status --format json          # loggedIn; "stale" session is fine for local work
unity license status --format json
unity editors --installed --format json
unity templates list --editor <ver> --format json      # real ids: com.unity.template.urp-blank (3D URP), com.unity.template.universal-2d
unity projects create "<Name>" --path "<parent>" --editor-version <ver> --template com.unity.template.urp-blank --non-interactive --format json
powershell -File <SKILL>\scripts\install-gds-editor.ps1 -ProjectPath "<parent>\<Name>"   # GDS + packages + unity pipeline install
unity open "<parent>\<Name>"
```

`--path` is the parent folder; the name is the first positional. Ignore the cloud-org warning (local project).

## When to use CoplayDev MCP instead

CoplayDev `unity-mcp` stays installed as a secondary bridge for: `manage_ui` UI Toolkit helpers, `manage_vfx` fine tuning, `generate_model` (Meshy/Tripo gen3d tier), and hosts without a shell. Same GDS calls via `execute_code: return GDS.X.Y(...);`. Never run both bridges on the same edit.
