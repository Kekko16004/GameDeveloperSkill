# Nucleon loop — `engine: nucleon`

Used when the user picks Nucleon in the GDD (Q0, [../engines.md](../engines.md)). The pipeline does not change; the tools do. Nucleon is a C++17 engine with a UE5-like editor, Lua games (the **natives**, PascalCase, FiveM-style), a web game UI (HTML/CSS/JS on CEF), Jolt physics, landscape/foliage/water, a Lumen/Nanite-like renderer on D3D12/Vulkan/OpenGL and an MCP server built into the editor. Engine docs live in the engine repo: `docs/editor/MCP.md`, `docs/api/NATIVES.md`, `docs/engine/*.md`, `docs/editor/PLAYTEST.md`, `docs/manual/README.md`.

**This file is only the index.** A worker reads the files its phase needs (`config/phases.json` lists them per phase; `python scripts/context_budget.py --reads <phase> --engine nucleon`):

| File | What is in it | Read it when |
|---|---|---|
| [nucleon/core.md](nucleon/core.md) | requirements, coordinates (Z up trap), rules | every Nucleon worker |
| [nucleon/bridge.md](nucleon/bridge.md) | `ncli.py`: transport, hidden desktop, locks, build / lint / shot / play-test / bench / playthrough / entity / run-game | the worker runs the engine |
| [nucleon/bridge-extra.md](nucleon/bridge-extra.md) | camera, post volumes, weather, destruction, memory, raw MCP tools, snapshot gotcha | you need one of those |
| [nucleon/spec.md](nucleon/spec.md) | spec format, kit catalog, worlds (`nc_world.py`), look file | level-build, world-gen, greybox, village, lookdev |
| [nucleon/gameplay.md](nucleon/gameplay.md) | natives, gameplay framework, player start, Blueprint, input, saves | systems, characters |
| [nucleon/first-person.md](nucleon/first-person.md) | the engine first-person kit (view model, look, Source-like movement, hit zones) | **only a first-person game** |
| [nucleon/gameplay-extra.md](nucleon/gameplay-extra.md) | level streaming, weather, destruction and cloth, animation extras | only if the GDD asks |
| [nucleon/tests.md](nucleon/tests.md) | the GDS harness, `play-test`, `run-game`, perf and feel | every worker that tests |
| [nucleon/ui.md](nucleon/ui.md) | NUI web page UI | ui-* phases |
| [nucleon/look.md](nucleon/look.md) | lighting, post, materials (`nc_mat.py`) | lookdev, art review |
| [nucleon/perf.md](nucleon/perf.md) | `tools/nucleon-bench`, engine gaps | optimization ([../optimization.md](../optimization.md)) |
| [nucleon/status.md](nucleon/status.md) | which engine build, what was verified, what never ran | project phase, doctor |

**Old section numbers** (other files and code comments cite them): §1 §3 §10 = nucleon/core.md; §2 = nucleon/bridge.md (+ bridge-extra.md); §4 §4b = nucleon/spec.md; §5 = nucleon/gameplay.md (first-person kit: nucleon/first-person.md; streaming, weather, destruction: nucleon/gameplay-extra.md); §6 (6b, 6c) = nucleon/tests.md; §7 = nucleon/ui.md; §8 §8a = nucleon/look.md; §8b = nucleon/perf.md; §9 = below.

## 9. Phase mapping

| Phase | Nucleon |
|---|---|
| project | `exe new-project` (template from the genre: first-person / third-person / top-down) or attach; `ncli setup PROJECT` (harness, example spec, folders, `.gitignore`); HTTP server on (owner, once) or stdio; `ping` + `lint` JSON + `play-test` with `test_move.lua`; `git init` |
| greybox | spec with rooms/shapes → `build` → `lint` → `play-test` with `test_move.lua` green |
| world-gen | `nc_world.py build` → `exe run-lua` → `attach` → `build _world_<name>.json` → `lint --play` (§4b) |
| level-build | blueprint JSON (kit roles / kit rooms / `scatter`) → `cycle` (one worker per blueprint, JSON written in parallel, `cycle` takes the lock itself) |
| hero-asset | [hero-procedural.md](hero-procedural.md): `blender -b -P Tools/<asset>_build.py` (hero_kit) → GLB → `call asset_import '{"sources":[...],"folder":"Content/Models/Hero"}'` → `pieces` row with `rotation [0,0,180]` (front toward the player) → `build --save current` → `shot` |
| lookdev | `nc_mat.py auto` + `assign` (§8a) + `check` on the new models → `art/look/<name>.json` from the board → `nc_world.py look` → shots in Game View (`NC_EDITOR_GAME_VIEW=1` on the editor) → art review |
| characters | template pawn (`Content/Actors/Player.ncactor`, Character Movement, animation graph `.ncanim`); FPS: look from `GetLookDelta`, Source movement params, view model arms, hit-zone collision components (§5); enemies: navigation volume + `BuildNavigationMesh` / behavior trees (`nc.behavior`), or `nc.ai` (§5) |
| systems | `Content/Scripts/<system>.lua` + actor scripts + `test_<verb>.lua`; Blueprint only if the GDD says so; weapons = rules in Lua over `Raycast*` hit zones / surfaces + view model + `nc.abilities` or plain attributes, never a re-made raycast, recoil camera, crouch or acceleration (§5) |
| ui-* | §7 (web page: restyle `UI/index.html`, `nc-menu.css` variables, HUD in `#hud`) |
| juice | effects `.ncfx` / particles entities, `PlaySound*` natives, `ShakeCamera` |
| playtest | `lua-check` + `play-test` (all tests, `--fps`) + `lint --play` + shots; packaged run with `run-game --gds-test`; `capture` for the store |
| build (only if asked) | `exe package <project> --config Development --platform win64 --out Packaged/win64 --report size.json` + `run-game Packaged/win64 --gds-test` (tests), then `--config Shipping` for the release; no 32-bit player |
