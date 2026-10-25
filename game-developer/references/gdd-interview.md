# GDD Interview — thorough, adaptive, in blocks

**The interview is where quality is decided.** Every later worker reads only `GDD.md`: anything vague here becomes a guess later (cubes, wrong camera, wrong mood). So:

- **Ask a lot.** Group questions in blocks of 5-10 so the user answers in few turns, but never skip a topic because it "seems obvious".
- **Adaptive.** If the user's pitch already answers something, show it as *inferred* for confirmation instead of asking again. If an answer is vague ("un gioco figo", "normale"), ask a follow-up with 2-4 concrete options and a recommendation.
- **Offer defaults.** Every question has a recommended answer; "ok consigliati" locks the defaults for a whole block.
- **Follow-ups are mandatory when**: the genre is unknown, the style is ambiguous (toon vs low-poly vs realistic), the world type is unclear, the win/fail is missing, or the scope is bigger than a slice.
- Write answers to `GDD.md` as you go (`status: draft`). No engine, Blender, Voxel or UI work until `status: locked`.
- **Ask in one turn per block** (the whole block at once, defaults shown): the user answers 5-10 questions per message, the interview is 4-6 turns, not 30.

## Q0 — Engine (always the very first question, the user decides)

0. **Engine**: `unity` | `nucleon` | `unreal` | `godot` ([engines.md](engines.md)). Offer `config.json` `engines.preferred[0]` as the default and say in one line each what it means for *this* pitch (facts, not a pick). The answer is final: style, genre and hardware never change it; a known limit (e.g. 2D pixel on Nucleon) is said once and the user decides. Write `engine:` to `GDD.md` and `DECISIONI.md` at once.

## Block A — The game

1. **One-liner + references**: premise in one sentence + 2-3 named reference games (and *what* to take from each: feel, look, loop).
2. **Genre** (row of [genres.md](genres.md)); hybrid → primary + secondary.
3. **Core loop (30 s)** and **session loop (10 min)**: what the player repeats; what makes a session end well.
4. **Player verbs** (short list: move, jump, interact, attack, dash, build...). For each: key/button and how it should *feel* (snappy, heavy, floaty).
5. **Win / fail** conditions and what happens after (retry, checkpoint, run over).
6. **Slice scope**: 1 world/level, 1 enemy or obstacle type, 1 clear objective, expected play time (5-15 min).
7. **Progression in the slice**: none | upgrades | inventory/crafting | XP. Save/load needed?
8. **Enemies / NPCs**: types, behaviour (patrol, chase, ranged, stealth), count on screen. Dialogue?

## Block B — Look & world

9. **Style** (row of [styles.md](styles.md)): `lowpoly` | `toon` | `stylized` | `voxel` | `realistic` | `2d-pixel`. Show 1 reference image per option if the user hesitates. The style never changes the engine chosen at Q0 ([engines.md](engines.md) "Style is independent of the engine").
10. **World type** (decides the build phase, [world-gen.md](world-gen.md) + [environments.md](environments.md)): open terrain | island | village/town | city streets | dungeon | cave | interior | space/sci-fi base | voxel world | arena | 2D levels. Size (small 100 m / medium 300 m / large 500 m+) and **one landmark** the player can navigate by.
11. **Mood & time of day** → lookdev preset ([lookdev.md](lookdev.md)): day, sunset, night, torch-lit, overcast, pastel, sci-fi cold; weather (fog, rain, snow) if any.
12. **Palette**: 4-6 hex colours + 1 dominant material (wood, stone, metal, plastic, neon). Offer 3 palettes if the user has none.
13. **Camera**: first-person | third-person | top-down | isometric | side (2D). FOV/distance feel.

## Block C — Presentation

14. **UI screens** (built with designer, the user picks among 3-4 variants for EACH screen): Main Menu, HUD (vitals, objective text, prompt `[E]`, minimap?), Pause, Game Over / Victory, plus inventory/crafting/dialogue if the loop needs them. Tone of UI (diegetic, minimal, chunky, elegant).
    **Route for the variants** (ask only when an image-generation tool is reachable: Canva `generate-image` and other claude.ai connectors are often deferred, so run ToolSearch `generate-image` first; none → `direct` without asking): `concept` (concept images from designer's detailed per-screen prompts, shown as variants, then the chosen one is rebuilt in HTML) | `direct` (HTML variants from the prompts, the usual way) | `both` (concept for Main Menu/HUD, direct for the rest). May use credits of that service. → `ui-route` in the GDD and DECISIONI.md.
15. **Audio**: ambience loop, music mood (calm, tense, epic), SFX for each verb; voice lines no/yes (TTS).
16. **Game feel extras**: hit-stop, camera shake, particles on every action, screen effects (vignette on damage). Default: yes to all, subtle.

## Block D — Production (mandatory, decides tools and cost)

17. **Tool stack** ([tool-stack.md](tool-stack.md)) for the engine of Q0: confirm the stack table once; no renegotiation per prop.
18. **Parallelism** (default from `config.json` `parallel.maxWorkers`, 6): how many workers at once on this machine (RAM/CPU; the editor itself is always one driver at a time). The run is always continuous: workers chain without stopping, memory on disk ([workers.md](workers.md) "Scheduler").
19. **Who makes the 3D assets**: `agent-full` | `user-provided` (agent writes `art/ASSET_MANIFEST.md`) | `hybrid`.
20. **Generative 3D tier + budget** ([gen3d.md](gen3d.md)): `none` (default) | `local` (Modly, ≥ 8 GB VRAM) | `meshy` | `tripo` | `hyper3d`; `gen3dBudgetCredits`, `gen3dMaxAssets`.
21. **Asset sources**: Asset Store free packs yes/no (Synty Starter, Cartoon FX Free); Fab/Megascans (`fab.enabled`, realistic only); user's own library path.
22. **Hardware**: GPU + VRAM (decides SSAO, shadow distance, Lumen software vs off, gen3d local).
23. **Target platform & performance**: PC only | + WebGL | + mobile; target FPS (60 default).
24. **Look extras**: toon shader yes/no, outline yes/no, HDRI sky name or none, post intensity (subtle / strong).

## Block E — Quality baseline (asked, with recommended defaults)

Detail and the "why" of each item: [quality-baseline.md](quality-baseline.md). Ask the whole block in one turn; "ok consigliati" takes every default. Tell the user first, as a statement (not a question): *"Always included: key remapping (keyboard + pad, restore defaults), text size, reduced motion, scene fades ≤ 0.5 s that can be skipped, hover/focus on every button."* Every "no" below goes into `DECISIONI.md` and is not proposed again.

25. **Accessibility extras** — which of these? High contrast · One-hand preset · Colour-blind symbols (icon next to every colour state) · Hold/toggle for held inputs · Relax/assist mode (e.g. no fail timer). *Recommended: all five; one-hand only if the core verb needs both hands at once; relax mode for skill-heavy or timed games.* Follow-up if relax = yes: what does it remove (timer, fail, damage)?
26. **Notifications** — short (icon + 2-3 words; full sentence only the first time) and one at a time? *Recommended: yes + yes.* Alternative: full sentences always (story-heavy games).
27. **Shared numbers** — numbers shown on several screens (score, money, quota): one source of truth + an automatic consistency check? *Recommended: yes* (cheap now, painful later).
28. **Onboarding** — (a) tutorial of ≤ 4 steps on the core verb, (b) first-time hints at the first real occasion, (c) dense screens (shop, upgrades, inventory) that reveal items gradually. *Recommended: a + b + c.* Follow-up: which verb is the tutorial about, and which verb must stay available from the start?
29. **Languages** — how many and which, at the slice/beta? *Recommended: EN + your language now, string table ready for more; 8+ (EN, ES, FR, DE, PT-BR, RU, ZH, JA, + AR/KO) if selling worldwide on Steam.* Any CJK or Arabic → font fallback + RTL tasks are added. Strings are never hard-coded either way.
30. **Playtest kit** — opt-in local telemetry CSV per level, a demo/fresh-profile build that never touches your saves, a tester README with 10 questions? *Recommended: yes to all three* when real testers are planned. Follow-up: how will testers send files back (email, Discord, form)?
31. **Store capture** — will the game be sold or shown on a store page? If yes: an Editor-only capture tool (HUD full / minimal / none, prompts hidden, fixed seeds, store-size screenshots + GIF frames). *Recommended: yes if sold; no for a jam/private prototype.*

After the lock, if `game-launch-strategist` is installed: offer the early market check once ([launch-link.md](launch-link.md) §10). Offered, not forced.

## Lock

- Recap as a table: **Declared** vs **Inferred** (inferred rows in bold so the user can correct them). Block E rows show the ESSENTIAL items as "always". **Pending user choices are collected here too**: anything later phases would stop for (asset manifest, Asset Store packs) is asked now, so the run after the lock needs the user only for the UI variant picks.
- For `user-provided`/`hybrid`: preview the asset manifest.
- Correction → update and show the recap again. Approved → `status: locked`, then the project phase.

`GDD.md` must contain: `genre`, `style`, `engine`, `world`, `worldSize`, `camera`, `lookdev`, `palette`, `verbs`, `win`, `fail`, `enemies`, `ui`, `parallel`, `assets`, `gen3d`, `gen3dBudgetCredits`, `gen3dMaxAssets`, `assetStore`, `fab`, `gpu`, `vram`, `platform`, `toon`, `outline`, `hdri`, `a11y`, `notifications`, `sharedNumbers`, `onboarding`, `languages`, `playtestKit`, `storeCapture`, `sold`.

At lock the parent writes every owner choice that closes a topic (languages, platforms, Block E "no"s, style) into `DECISIONI.md` with the date.
