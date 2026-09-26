# GDD Interview — thorough, adaptive, in blocks

**The interview is where quality is decided.** Every later worker reads only `GDD.md`: anything vague here becomes a guess later (cubes, wrong camera, wrong mood). So:

- **Ask a lot.** Group questions in blocks of 5-10 so the user answers in few turns, but never skip a topic because it "seems obvious".
- **Adaptive.** If the user's pitch already answers something, show it as *inferred* for confirmation instead of asking again. If an answer is vague ("un gioco figo", "normale"), ask a follow-up with 2-4 concrete options and a recommendation.
- **Offer defaults.** Every question has a recommended answer; "ok consigliati" locks the defaults for a whole block.
- **Follow-ups are mandatory when**: the genre is unknown, the style is ambiguous (toon vs low-poly vs realistic), the world type is unclear, the win/fail is missing, or the scope is bigger than a slice.
- Write answers to `GDD.md` as you go (`status: draft`). No Unity, Unreal, Blender, Voxel or UI until `status: locked`.

## Block A — The game (always first)

1. **One-liner + references**: premise in one sentence + 2-3 named reference games (and *what* to take from each: feel, look, loop).
2. **Genre** (row of [genres.md](genres.md)); hybrid → primary + secondary.
3. **Core loop (30 s)** and **session loop (10 min)**: what the player repeats; what makes a session end well.
4. **Player verbs** (short list: move, jump, interact, attack, dash, build...). For each: key/button and how it should *feel* (snappy, heavy, floaty).
5. **Win / fail** conditions and what happens after (retry, checkpoint, run over).
6. **Slice scope**: 1 world/level, 1 enemy or obstacle type, 1 clear objective, expected play time (5-15 min).
7. **Progression in the slice**: none | upgrades | inventory/crafting | XP. Save/load needed?
8. **Enemies / NPCs**: types, behaviour (patrol, chase, ranged, stealth), count on screen. Dialogue?

## Block B — Look & world

9. **Style** (row of [styles.md](styles.md)): `lowpoly` | `toon` | `stylized` | `voxel` | `realistic` | `2d-pixel`. Show 1 reference image per option if the user hesitates. `realistic` → engine Unreal 5.8 (see Q13).
10. **World type** (decides the build phase, [world-gen.md](world-gen.md) + [environments.md](environments.md)): open terrain | island | village/town | city streets | dungeon | cave | interior | space/sci-fi base | voxel world | arena | 2D levels. Size (small 100 m / medium 300 m / large 500 m+) and **one landmark** the player can navigate by.
11. **Mood & time of day** → lookdev preset ([lookdev.md](lookdev.md)): day, sunset, night, torch-lit, overcast, pastel, sci-fi cold; weather (fog, rain, snow) if any.
12. **Palette**: 4-6 hex colours + 1 dominant material (wood, stone, metal, plastic, neon). Offer 3 palettes if the user has none.
13. **Camera**: first-person | third-person | top-down | isometric | side (2D). FOV/distance feel.

## Block C — Presentation

14. **UI screens** (built with real-world-design, the user picks among 3-4 variants for EACH screen): Main Menu, HUD (vitals, objective text, prompt `[E]`, minimap?), Pause, Game Over / Victory, plus inventory/crafting/dialogue if the loop needs them. Tone of UI (diegetic, minimal, chunky, elegant).
15. **Audio**: ambience loop, music mood (calm, tense, epic), SFX for each verb; voice lines no/yes (TTS).
16. **Game feel extras**: hit-stop, camera shake, particles on every action, screen effects (vignette on damage). Default: yes to all, subtle.

## Block D — Production (mandatory, decides tools and cost)

17. **Engine & tool stack** ([tool-stack.md](tool-stack.md)): default Unity 6 URP (lowpoly/toon/stylized/voxel/2D) or Unreal 5.8 (realistic). Confirm the stack table once; no renegotiation per prop.
18. **Session mode**: `continuous` (Claude Code / Kilo with subagents) | `hard-stop` (Antigravity / single chat, `/resumegame`).
19. **Who makes the 3D assets**: `agent-full` | `user-provided` (agent writes `art/ASSET_MANIFEST.md`) | `hybrid`.
20. **Generative 3D tier + budget** ([gen3d.md](gen3d.md)): `none` (default) | `local` (Modly, ≥ 8 GB VRAM) | `meshy` | `tripo` | `hyper3d`; `gen3dBudgetCredits`, `gen3dMaxAssets`.
21. **Asset sources**: Asset Store free packs yes/no (Synty Starter, Cartoon FX Free); Fab/Megascans (`fab.enabled`, realistic only); user's own library path.
22. **Hardware**: GPU + VRAM (decides SSAO, shadow distance, Lumen software vs off, gen3d local).
23. **Target platform & performance**: PC only | + WebGL | + mobile; target FPS (60 default).
24. **Look extras**: toon shader yes/no, outline yes/no, HDRI sky name or none, post intensity (subtle / strong).

## Lock

- Recap as a table: **Declared** vs **Inferred** (inferred rows in bold so the user can correct them).
- For `user-provided`/`hybrid`: preview the asset manifest.
- Correction → update and show the recap again. Approved → `status: locked`, then the project phase.

`GDD.md` must contain: `genre`, `style`, `engine`, `world`, `worldSize`, `camera`, `lookdev`, `palette`, `verbs`, `win`, `fail`, `enemies`, `ui`, `session-mode`, `assets`, `gen3d`, `gen3dBudgetCredits`, `gen3dMaxAssets`, `assetStore`, `fab`, `gpu`, `vram`, `platform`, `toon`, `outline`, `hdri`.
