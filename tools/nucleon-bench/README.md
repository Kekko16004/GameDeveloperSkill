# Nucleon bench: from "low fps" to a fix plan for Claude Code

Measure a real scene on the real GPU, test one hypothesis at a time, and keep only the causes the numbers confirm. Then turn
them into ready-made briefs for Claude Code in the NucleonEngine repository.

```
scenes.json ──> bench.py run ──> results/<stamp>/  (CSV per frame, GPU passes, slowest frames, screenshots)
                                     │
                     bench.py analyze ──> REPORT.md + results.json (verdict H1..H9)
                                     │
                        bench.py plan ──> EXECUTION-PLAN.md (K1..K5 known + only the confirmed H*)
```

## 1. What it measures and why (hypotheses)

| | Hypothesis | Symptom it explains | One-change configs (each against `base`) |
|---|---|---|---|
| H1 | 8K texture mips uploaded with CPU copies | drops when you **get close** to Megascans | upload budget 512 MB, full pool, textures Low *(bound)*, uncompressed |
| H2 | Virtual geometry pages: 64 MB pool, per-frame budget | drops close up and when flying | everything resident, 512 MB pool, 64 loads/frame |
| H3 | The Nanite-like path costs more than the classic one | low fps that is always there with scans | `NC_VIRTUAL=0`, forward instead of the visibility buffer |
| H4 | Shadows (casters at full detail, cascades, wind) | low fps that is **always there** in a forest | shadows off *(bound)*, Low, classic VSM, GD plan off, no wind, wind ≤ 15 m |
| H5 | LOD not aggressive enough | fps rises a lot if you force LOD 3 | `NC_LOD_FORCE=3` *(bound)*, bias 2, GPU LOD |
| H6 | Overdraw from masked foliage | pixel bound with grass/leaves | foliage Low *(bound)*, masked pre-pass on/off |
| H7 | GI/Lumen with vegetation | high cost even when standing still | GI off *(bound)*, no vegetation in GI, SSR reflections |
| H8 | GPU-driven / instancing paths (bug A1) and their cost | brown or missing repeated objects | `NC_GPU_DRIVEN=0`, `NC_INSTANCING=0`, retained off, vgeo unified, occlusion (with screenshots) |
| H9 | Pixel bound or CPU/geometry bound? | which way to start | resolution 50 % |

*(bound)* = it switches a feature off to find out how much it costs. It is an upper bound, not a fix.
The rules for each verdict are in `configs.json` (`rule`) and in `bench.py` (`verdicts`). A hypothesis is confirmed only by
the numbers: a large measured gain, or a correlation between hitches and loads (pages/textures) in the same frames.

Three kinds of scenario (`scenes.json`, Z up like the natives):
- **view**: a fixed camera, the steady-state cost (low fps that never goes away);
- **fly**: a path at constant speed (streaming, LOD switches);
- **approach**: walking up to an asset from 60 to 2 m, twice. Run 1 is cold, run 2 is warm. If run 1 is much worse than
  run 2, the cause is streaming, not rendering.

## 2. How to run it (Windows, real GPU)

```powershell
# 1) the spots: open the editor on the project, put the camera where it drops, then
python tools\nucleon-bench\bench.py grab-view forest-dense --project D:\Games\ForestDemo
#    (or write scenes.json by hand: copy scenes.example.json)
# 2) the matrix: about 25 configs x 2 runs; 30-60 min. Do not use the PC (nc_desktop_run.exe hides the window if present)
python tools\nucleon-bench\bench.py run --engine D:\NucleonEngine\build-msvc\bin --project D:\Games\ForestDemo --scenes tools\nucleon-bench\scenes.json
#    only some hypotheses:  --only H1,H2   ·  quality: --quality Cinematic  ·  repeats: --repeat 3
# 3) report and plan
python tools\nucleon-bench\bench.py analyze tools\nucleon-bench\results\<stamp>
python tools\nucleon-bench\bench.py plan    tools\nucleon-bench\results\<stamp>
```

- `run` does not modify the project. It copies `zz_gds_bench.lua` into `Content/Scripts`, `Saved/gds-bench.lua` and
  `gds_bench_main.lua`, and removes all three at the end. Saves and the DDC go to `results/<stamp>/_save|_ddc`. The first,
  unmeasured run warms up the shader cache and the DDC (`--no-warm-run` skips it).
- Environment of every run: `NC_GPU_PROFILE=5` (GPU passes), `NC_PROFILE_REPORT` (the slowest frames with their CPU zones),
  vsync off, plus the config's `env`.
- **Projects with their own `main.lua`** that does not call `nc.game.run`: the bench script does not start. `run` reports it
  (`started: false`). Use a level of the project with `nc.game.run`, or the engine's benches
  `tests/bench/perf/gpu_driven.sh` and `gpu_foliage.sh`.
- On Linux, `--xvfb` checks only that the kit works: on llvmpipe the milliseconds mean nothing.

## 3. Reading REPORT.md

- **Base**: fps, p50/p95/p99/max, hitches every 10 s (a frame above max(2×p50, p50+10 ms)), GPU frame and the 4 most
  expensive passes for each scenario.
- **Verdicts**: CONFIRMED / REFUTED / not confirmed, with the numbers that decide it.
- **Each config against base**: the % change in p50 and in hitches for each scenario (negative = better).
- **Slowest frames**: the CPU zones of the worst frames (e.g. `World stream: load cell`, `Texture upload`).

## 4. The execution plan

`EXECUTION-PLAN.md` holds:
- **K1-K5**: the items already found (`docs/NUCLEON-ENGINE-NOTES.md`), placed first because they need no numbers.
  K1 = bug A1 (GPU-driven), K2 = the small fixes in one PR (B2, B3, C1 + notes A2, A5, C2), K3 = settled capture and resolution,
  K4 = the MCP world tools, K5 = foliage with models. `--no-known` leaves them out.
- **The confirmed H**, ordered by measured gain. Each one carries the numbers that confirm it, the engine files, the steps
  (with the Unreal reference), the acceptance criteria tied to re-running this bench, the branch, and the ready-made
  **prompt** to paste into Claude Code opened on the NucleonEngine repository.

The rules of the engine repository are included in every brief: one branch + PR for each brief, a switch back to the old code
for every change, verification with `tools/verify/windows.ps1 -Changed`, no GitHub Actions. "Done" = the bench re-run with
`--only <H>` on the same scene and the same GPU reaches the acceptance numbers.

## Files

- `bench.py` — run / analyze / plan / grab-view (standard library; Pillow optional, used for the screenshot diff)
- `gds_bench.lua` — the in-game driver: camera, CSV for each frame, markers in the log
- `configs.json` — the matrix: base + one change for each config, with each hypothesis' rule
- `briefs.json` — the briefs K1-K5 and H1-H9 that `plan` fills in with the numbers
- `scenes.example.json` — an example of the three kinds of scenario
