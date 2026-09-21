---
description: Resume from GAME_CONTEXT.md. hard-stop = one macrotask then STOP; continuous = keep chaining. New chat.
---

Call Skill tool `game-developer` FIRST.

1. Find GAME_CONTEXT.md + GAME_TASKS.md (or GDD.md projectPath). Read them + `docs/gates/` names/status. For art phases also `art/blueprints/PLAN.md` and `art/kit-catalog.json` (`suggestedModule`, `notes` only).
2. First `[ ]` task is the work.
   - **Se il task è un `[WAIT-USER-ASSET]`**: Controlla la cartella di destinazione (es: `art/exports/<asset_name>.glb`). Se il file è presente (> 5KB), segnalo come `[x]` completato, aggiorna `GAME_CONTEXT.md` (`asset_ready: true`) e procedi al task successivo (import-art + rebuild blueprint).
3. Launch ONE Task general worker for that phase only (workers.md block).
4. Verify gate files on disk: `lint: {"issues":0}` for scene phases; level-build needs blueprint JSON + build JSON + PNG; hero-asset needs blender-*.png + GLB; lookdev needs LookDev_<preset>.asset + PNG; UI needs real-world-design mock HTML.
5. Update GAME_TASKS.md + GAME_CONTEXT.md.
6. hard-stop: print HARD STOP banner and stop. continuous: launch the next worker. Never declare slice PASS unless this macrotask IS slice and all gates are PASS.

Forbidden: bpy modelling, http://localhost:9876/mcp, gen3d outside the GDD tier/budget, wall-by-wall placement, skip DesignerSkill, implement 3 phases yourself.
