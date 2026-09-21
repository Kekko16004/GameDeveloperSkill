---
description: Resume one macrotask from GAME_CONTEXT.md then HARD STOP. New chat only.
---

Call Skill tool `game-developer` FIRST.

This chat does EXACTLY one macrotask then HARD STOP (session-cuts.md). Never finish the whole game here.

1. Find GAME_CONTEXT.md + GAME_TASKS.md (or GDD.md projectPath).
2. Read them. First `[ ]` task is the only work.
   - **Se il task è un `[WAIT-USER-ASSET]`**: Controlla la cartella di destinazione (es: `art/exports/<asset_name>.glb`). Se il file è presente (> 5KB), segnalo come `[x]` completato, aggiorna `GAME_CONTEXT.md` (`asset_ready: true`) e procedi al task successivo di importazione/allestimento scena.
3. Launch ONE Task general worker for that phase only.
4. Verify gate files + screenshots on disk. Kit-dress needs 030-import PNG + collider. Poly Pizza needs blender-*-2-import.png + finale. UI needs real-world-design mock HTML.
5. Update GAME_TASKS.md + GAME_CONTEXT.md.
6. Print HARD STOP banner. Do not start the next task. Do not declare slice PASS unless this macrotask IS slice and all gates are PASS.

Forbidden: bpy modelling, http://localhost:9876/mcp, Hunyuan, skip DesignerSkill, implement 3 phases yourself.
