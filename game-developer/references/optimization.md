# Optimization loop (every engine, every genre)

One loop, used by the perf gate (`perf:` in [gates.md](gates.md) 25b), by any worker whose gate misses the budget and by the parent at every engine update. Commands per engine: [engines.md](engines.md) "Optimization row".

**Budget.** `targetFps` from the GDD (Q22) gives `1000/targetFps` ms (60 fps = 16.6 ms; p95, not the mean). Ask nothing. **The top quality preset at native resolution is the thing measured: never lower quality or resolution, never switch on an upscaler or frame generation to pass the gate** unless the owner chose it in `DECISIONI.md`.

**Loop**
1. **Measure** in the real scene, moving along the fixed walk (same camera or path every time), **vsync off**, no other engine process, GPU lock held. Keep p50/p95/p99 of the frame, CPU, GPU, Present, draw calls, instances. The first run of a scene is the stored baseline (`docs/bench/<name>.baseline.json`).
2. **Attribute**: CPU bound, GPU bound or Present/vsync bound; then which pass or system (shadows, GI, post, scripts, culling, streaming, physics, UI). A number with a warning (other engine run, refresh-locked, software renderer, too few frames) is not a measurement: repeat it.
3. **Fix the largest waste first**, in this order: (a) content waste (instances or triangles where the player cannot see or reach, duplicate materials, huge textures, lights without range) ; (b) game code (per-frame allocations, scans, scripts on every entity); (c) engine settings that lose no visible quality; (d) an engine problem: write `engine_gap:` with the repro and the numbers and let the parent route it, do not work around it silently.
4. **Remeasure after each fix** against the stored baseline: keep a fix only if the number moved; a fix that changes the picture needs the shot compared (look check) in the same gate.
5. **Stop** at the budget, or report what remains: the largest remaining cost, what was tried and the numbers. Update the baseline only for a measured improvement.

**Where it is wired.** `ncli bench` (Nucleon) is the measurement and reads the baseline; the parent reads the number and the `trusted` flag at every engine update and every scene gate, a worker's "faster" without numbers is not accepted. Gate fields: `perf:` (p95 vs budget), `scene: {instances, drawCalls, outOfReach}`. A missed budget is a FAIL with the attribution and the next fix, not an owner question.
