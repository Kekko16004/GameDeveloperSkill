---
description: Idea to playable slice. Parent only. continuous = chain workers; hard-stop = one macrotask per chat.
---

Call Skill tool `game-developer` FIRST. Never Read `references/*.md` from the Unity cwd.

You are PARENT only. For: $ARGUMENTS

1. Follow workers.md + pipeline.md + session-cuts.md from the skill payload.
2. GDD interview: all 19 questions (tool stack, session mode, asset strategy, gen3d tier + credit budget, asset store, GPU/VRAM, look preset). Lock before anything else.
3. Se session-mode e hard-stop: dopo GDD lock fai ONE macrotask (project OR greybox OR kit-fetch OR one level-build blueprint OR hero-asset batch OR lookdev OR characters OR one UI screen), poi HARD STOP banner. Se continuous (con subagents): incatena i worker senza fermarti; la memoria e su disco (GAME_CONTEXT, blueprints, kit-catalog, docs/lint).
4. Do not implement yourself. Task general, 8 context lines, SKILL=absolute skill dir.
5. Levels = blueprint JSON → `GDS.LevelBuilder` / `GDS.PB` via CoplayDev `execute_code`. Placing walls one by one with manage_gameobject = FAIL. Every scene-touching gate needs `lint: {"issues":0}` from `GDS.SceneLint`.
6. Art = ONE family (Kenney/KayKit/Quaternius Standard/Synty Starter if GDD allows). Hero props = Blender MCP native tools (Poly Pizza → Poly Haven models → Sketchfab CC0 → gen3d tier from GDD only). Vietato execute_blender_code per modellare (solo wipe + sanitize). Forbidden http://localhost:9876/mcp — use uvx blender-mcp stdio. GLB <15KB = FAIL.
7. Look = `GDS.LookDev.Apply(<GDD preset>)` before any UI/playtest screenshot. Flat grey scene = FAIL.
8. UI: Skill `real-world-design` required. Hand-written UXML first = FAIL.
9. Claiming a building without `art/blueprints/<name>.json` + `docs/lint/build-<name>.json` = FAIL. Claiming Blender without `screenshots/blender-*.png` = FAIL.
10. In modalita hard-stop, se l'utente dice procedi dopo HARD STOP: rifiuta e indica /resumegame in chat nuova. In modalita continuous, procedi normalmente.

Resume = `/resumegame`.
