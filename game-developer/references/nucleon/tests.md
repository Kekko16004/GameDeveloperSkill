# Nucleon tests: the GDS harness (every worker that writes or runs a test)

## 6. Tests: `templates/nucleon/Content/Scripts/gds_test.lua`

Copied by `ncli setup` (phase project). Off unless `NC_GDS_TEST` is set. Each verb test: `Content/Scripts/test_<verb>.lua` with `exports.gds_test:Register(name, function(t) ... end)`; helpers `t.hold(key, s)` / `t.tap(key)` (real input via `SimulateKey`), `t.wait`, `t.waitFor`, `t.check`, `t.near`, `t.pawn()`, `t.shot(name)`. Log lines: `GDS-TEST <name> PASS|FAIL: <reason>`, then `GDS-TEST DONE pass=N fail=M`.

- In the editor: `NC_GDS_TEST=1` in the editor's environment (stdio run: export it before ncli), then `ncli play-test --seconds 60 --expect "GDS-TEST DONE pass=<N> fail=0"`.
- Packaged: `ncli run-game <Packaged/win64> --gds-test` (the same as `NC_GDS_TEST=1 NC_GDS_TEST_EXIT=1 NC_GDS_TEST_OUT=captures/test <game exe>` on the hidden desktop) → exit code 0/3 + the `GDS-TEST` lines + screenshots. Package with `--config Development` for tests: Debug / Development have the F8 console and the game's prints in `Saved/Logs/game.log`, **Shipping logs errors only** (a Shipping run can pass a test and show nothing).
- In the editor `play-test` the project is not packaged: collision, assets and scripts are the editor's; a bug that only shows in the pak (a missing dependency: `exe package` prints `Unresolved reference` warnings) needs `run-game`.
- Bug fixes: `Tools/gds/test_bug_template.lua` → `Content/Scripts/test_bug_<key>.lua`, FAIL before the fix, PASS after (workers.md iterate-gate 1b); `gds_bisect.py` finds the commit that broke a test.
- The engine has its own functional test framework too (`nc.test`: `describe/it/expect`, `t.holdKey`, `t.waitUntil`, screenshots; MCP `play_test` with inline `steps` or a script, `NucleonEditor -test <project> <script.lua>`; docs/editor/PLAYTEST.md): `ncli call play_test '{"steps":[{"op":"wait_frames","frames":60},{"op":"assert","lua":"GetEntityPosition(GetPlayerPawn(GetLocalPlayer())).z > 0","message":"..."}]}'` ran here (PASS), the rest of that framework is unverified. Keep the GDS harness as the gate evidence (`GDS-TEST` lines, `run-game`); `play_test` is for quick asserts and input injection in the open editor.
- Performance: `t.perf("walk", 10, "W")` in a test + `ncli play-test --fps <targetFps>` → p50/p95/p99 per run, FAIL over budget (GPU only; llvmpipe numbers mean nothing).
- Telemetry (opt-in): `gds_telemetry.lua` + `scripts/telemetry_report.py` (playtest.md).
- Feel baseline (playtest.md): the same harness measures the core verb in the real level (distance, time to apex, stop distance) and prints it with `t.feel({...})` (one `GDS-FEEL {json}` line); the worker stores it in `docs/tests/feel-baseline.json`.
