# Nucleon core: requirements, coordinates, rules (every Nucleon worker)

Hub: [../nucleon-loop.md](../nucleon-loop.md).

## 1. Requirements (doctor checks them)

- `NucleonEditor` (+ `Nucleon` next to it, same build): `config.json` `paths.nucleon` (folder or exe) or env `NUCLEON_EDITOR`. The game build is the frozen one in `C:\TempNucleon\game\bin\` (see the top). A page on CEF (`IsWebBrowserAvailable()`) needs `libcef.dll`, `nc_cef_helper.exe` and the `.pak` files next to the exe: they are in that folder.
- Python 3.9+ (ncli is standard library only).
- Next to the editor: `Nucleon` (the runtime) and, on Windows, `nc_desktop_run.exe`: ncli uses it so **no engine window ever opens on the desktop you work on** (see §2).
- Project made by the editor or headless: `python SKILL/scripts/ncli.py --exe <editor> exe new-project <folder> --template third-person` (templates: `empty`, `first-person`, `third-person`, `top-down`; exit 0, prints `Project created`).


## 3. Coordinates (the trap)

- MCP tools, ncli, GDS specs, natives: **Z up**, meters, X east, Y north, rotation `[pitch, roll, yaw]` degrees, yaw 0 faces +Y.
- `.nclevel` / `.ncactor` files, `run_lua`, the legacy Lua API, `nc.*` modules, `NC_EDITOR_CAMERA`: **engine Y up** (`native (x,y,z) = (-engine.x, engine.z, engine.y)`).
- The `nucleon://docs/editor-guide` resource still says "+Y is up": stale (engine notes B3), ignore it (the tools speak Z up).
- Camera / light rotations are `[pitch, roll, yaw]`: a camera at `pos` looking at `target` has pitch `atan2(dz, hypot(dx, dy))`, yaw `atan2(-dx, dy)` (counter-clockwise seen from above): `camera add --target` and a spec `cameras[].target` compute it.
- Box shapes: centred on `position`; `width` = X, `depth` = Y, `height` = Z (verified with `entity_get` bounds).
- If `ping` reports `upAxis: y`, stop: the owner set Editor Preferences > Appearance > Coordinates to Y; ask before changing it.


## 10. Rules

- A test editor always runs with `--pref-dir <scratch>` (never the owner's `%APPDATA%/Nucleon`) and on the hidden desktop (default).
- Editor open with HTTP on = the owner's editor: never `stdio` on the same project at the same time (two editors, one level file).
- Every run of the engine is under the lock, **per run, not per round**: the run commands take it themselves; your own script that starts the engine goes through `ncli locked --owner O -- ...`. Never `lock acquire` and then leave it for the next hour: it ends after its max hold. Every ncli command has a watchdog (`--max-seconds`, default 1800, exit 124) and every child has a time limit. A `serve` session is yours alone (`--as NAME`); never play-test on, edit through or stop one you did not start. JSON specs, Lua scripts, mocks are written in parallel outside the lock.
- Save before closing a stdio run; never write `.nclevel` by hand while the editor has the level open (the editor overwrites it on save).
- `run_lua` (engine coordinates, not undoable) only for things no tool covers; prefer specs + natives.
- Engine bugs found during a run: write them in the gate (`engine_issues:`) with the repro; the Nucleon repo has its own workflow (do not patch the engine from a game worker).
