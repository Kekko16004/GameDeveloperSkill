---
description: Resume from GAME_CONTEXT.md. hard-stop = one macrotask then STOP; continuous = keep chaining. New chat.
---

Call Skill tool `game-developer` FIRST.

1. Find GAME_CONTEXT.md + GAME_TASKS.md (or GDD.md projectPath). Read `DECISIONI.md` FIRST (+ `launch/00-intenzioni.md` and "Decisioni prese" in `launch/TODO.md` if present: never reopen what is settled), then them + `docs/gates/` names/status. For art phases also `art/blueprints/PLAN.md` and `art/kit-catalog.json` (`suggestedModule`, `notes` only).
2. Any `[/]` row = interrupted run: gate PASS on disk → `[x]`; else if `docs/progress/<PHASE>-<TASK>.md` exists → relaunch that worker with `RIPRENDI da PROGRESS`; otherwise back to `[ ]` (remove `PROJECT/Temp/gds-unity.lock` if it holds it). Then the work is the first `[ ]` whose `Dipende` tasks are all `[x]` (skip `[!]` and what depends on it).
   - **Se il task è un `[WAIT-USER-ASSET]`**: Controlla la cartella di destinazione (es: `art/exports/<asset_name>.glb`). Se il file è presente (> 5KB), segnalo come `[x]` completato, aggiorna `GAME_CONTEXT.md` (`asset_ready: true`) e procedi al task successivo (import-art + rebuild blueprint).
3. Launch ONE worker for that phase only (workers.md block + contract: DECISIONI, OWNS, DO / DO NOT, PROGRESS, REPORT; Claude Code: `Agent` `general-purpose`). New `launch/fg/waves/*-sintesi.md` since the last `docs/gates/plan-wNN.md` → write the gate plan with the approved proposals only, show the rest in one line each (launch-link.md §5). Set `Inizio`, then `Durata` at close.
4. Verify gate files on disk: `lint: {"issues":0}` for scene phases; level-build needs blueprint JSON + build JSON + PNG; hero-asset needs blender-*.png + GLB; lookdev needs LookDev_<preset>.asset + PNG; UI needs real-world-design mock HTML.
5. Check the report against the brief (mismatch = FAIL, re-run). Update GAME_TASKS.md + GAME_CONTEXT.md; owner decisions → DECISIONI.md; iteration gate PASS → `gate_link.py check`, `apply-status --write`, `todo --run` (launch-link.md §6); never edit `launch/` otherwise.
6. If 10 tasks closed since the last `docs/gates/checkpoint-*.md`: run the checkpoint worker first (task-decomposition.md).
7. hard-stop: print HARD STOP banner and stop. continuous: launch the next worker. Never declare slice PASS unless this macrotask IS slice and all gates are PASS.

Forbidden: bpy modelling, http://localhost:9876/mcp, gen3d outside the GDD tier/budget, wall-by-wall placement, skip DesignerSkill, implement 3 phases yourself.
