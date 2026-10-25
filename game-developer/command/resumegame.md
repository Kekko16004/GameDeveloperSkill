---
description: Resume after a crash / closed client from GAME_CONTEXT.md and keep the wave scheduler running to the slice.
---

Call Skill tool `game-developer` FIRST.

1. Find GAME_CONTEXT.md + GAME_TASKS.md (or GDD.md projectPath). Read `DECISIONI.md` FIRST (+ `launch/00-intenzioni.md` and "Decisioni prese" in `launch/TODO.md` if present: never reopen what is settled), then them + `docs/gates/` names/status. `engine:` from GDD.md picks the bridge (engines.md). For art phases also `art/blueprints/PLAN.md` and `art/kit-catalog.json` (`suggestedModule`, `notes` only).
2. Every `[/]` row = interrupted: gate PASS on disk → `[x]`; else if `docs/progress/<PHASE>-<TASK>.md` exists → relaunch that worker with `RIPRENDI da PROGRESS`; otherwise back to `[ ]`. Stale locks (Unity `PROJECT/Temp/gds-unity.lock`, Nucleon `PROJECT/Saved/gds-nucleon.lock`) older than 10 min are removed.
   - `[WAIT-USER-ASSET]`: check the destination (e.g. `art/exports/<asset>.glb` > 5 KB) → `[x]`, `asset_ready: true`, continue (import-art + rebuild blueprint).
3. New `launch/fg/waves/*-sintesi.md` since the last `docs/gates/plan-wNN.md` → write the gate plan with the approved proposals only, show the rest in one line each (launch-link.md §5).
4. Restart the wave scheduler (workers.md): launch every ready task with disjoint OWNS in one message, background, refill slots as they close. Contract in every prompt (DECISIONI, OWNS, DO / DO NOT, PROGRESS, REPORT).
5. Verify gate files on disk: `lint: {"issues":0}` for scene phases; level-build needs blueprint JSON + build JSON + PNG; hero-asset needs blender-*.png + GLB; lookdev needs the preset evidence + PNG; UI needs designer mock HTML. Report vs brief mismatch = FAIL, re-run.
6. Update GAME_TASKS.md + GAME_CONTEXT.md after every close; owner decisions → DECISIONI.md; iteration gate PASS → `gate_link.py check`, `apply-status --write`, `todo --run` (launch-link.md §6); never edit `launch/` otherwise. Every 10 `[x]` since the last checkpoint: checkpoint worker.
7. Keep going until the slice (all gates PASS) or until nothing is runnable; then report `[!]` rows with reasons.

Forbidden: bpy modelling, http://localhost:9876/mcp, gen3d outside the GDD tier/budget, wall-by-wall placement, skip designer, implementing phases yourself.
