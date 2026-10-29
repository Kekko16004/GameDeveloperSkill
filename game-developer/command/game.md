---
description: Idea to playable slice. Parent only, always continuous, every ready task in parallel (wave scheduler).
---

Call Skill tool `game-developer` FIRST. Never Read `references/*.md` from the game project cwd.

You are PARENT only. For: $ARGUMENTS

1. Follow workers.md (contract + "Scheduler a ondate") + pipeline.md + engines.md from the skill payload.
2. GDD interview (gdd-interview.md): **Q0 engine first, the user's choice, final** (unity | nucleon | unreal | godot). Then blocks A-E, one turn per block, adaptive follow-ups, defaults offered. Settled choices → DECISIONI.md. Lock before anything else; collect every later user choice you can at the lock.
3. Always continuous: after the lock, chain workers until the slice. Never print stop banners, never ask for a new chat. The only waits: the single UI-variants question (all screens at once) and real blockers.
4. Do not implement yourself. Claude Code: `Agent` tool, `subagent_type: "general-purpose"`, background; launch EVERY ready task with disjoint OWNS in ONE message (max `parallel.maxWorkers`), refill each freed slot at once. 9 context lines (ENGINE=<Q0>), SKILL=absolute skill dir. Every 10 `[x]`: checkpoint worker. `[!]` after 2 retries: skip, continue with what does not depend on it.
5. Bridge = the engine row of engines.md: Unity CLI `unity command gds_*` · Nucleon `python SKILL/scripts/ncli.py` (ping/build/lint/shot/play-test/lock; never load the MCP schemas in workers) · Unreal 5.8 MCP + gds_ue.py · Godot headless. Worlds/levels = JSON specs built by the deterministic layer; placing walls one by one = FAIL. Every scene-touching gate needs `lint: {"issues":0}`. Editor work only under the lock.
6. Art = ONE family. Hero props = Blender MCP native tools (Poly Pizza → Poly Haven → Sketchfab CC0 → gen3d tier from GDD only). No execute_blender_code modelling (only wipe + sanitize). Forbidden http://localhost:9876/mcp — use uvx mcp-for-blender stdio. GLB <15KB = FAIL.
7. Look = lookdev preset before any UI/playtest screenshot. Flat grey scene = FAIL. Art review scores the screenshots: average ≥ 4 or fix list → rebuild.
8. UI: Skill `designer` required; route `ui-route` from the GDD (concept images | direct | both, asked at Q14 only when an image tool is reachable, ToolSearch `generate-image`) passed to workers as `UI_ROUTE=`; variants of all screens in parallel, one question to the user, then engine transpiler (Unity ui-transpiler.mjs, Nucleon: none, the HTML mock becomes the NUI page; html2rml.py only for legacy RmlUi). Hand-written UXML/RML first = FAIL.
9. Claiming a building without `art/blueprints/<name>.json` + `docs/lint/build-<name>.json` = FAIL. Claiming Blender without `screenshots/blender-*.png` = FAIL.

Crash or closed client = `/resumegame` (resumes the scheduler from disk).
