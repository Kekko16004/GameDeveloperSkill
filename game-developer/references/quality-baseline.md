# Quality baseline — what must exist from the start

Asked in GDD Block E ([gdd-interview.md](gdd-interview.md)), turned into tasks by [task-decomposition.md](task-decomposition.md). **ESSENTIAL** = always in the slice, not asked (only shown in the recap). Everything else is a question with a recommended default: the owner can say no, and a "no" goes into `DECISIONI.md` so nobody proposes it again.

Why: on Buffet Panic! every item below was bolted on late (gates 39-52), each one touching screens that were already done. Built in at the start, each one is a single task.

## 1. Accessibility

| Item | Status | Default | Notes |
|---|---|---|---|
| Key remapping, keyboard **and** pad, with "Restore defaults" | ESSENTIAL | — | Input System rebinding, saved in the settings file; the HUD prompts read the current binding, never a hard-coded key |
| Text size (100 / 125 / 150 %) | ESSENTIAL | — | one scale on the root UI; every screen checked at 150 % |
| Reduced motion (shake, flashes, zoom punches off or ×0.3) | ESSENTIAL | — | juice reads one flag |
| High contrast | optional | yes | dark plate behind HUD text, outlines; never colour-only warnings |
| One-hand preset | optional | yes if the core verb needs two hands | a remap preset, not a separate control scheme |
| Colour-blind symbols | optional | yes | shape/icon next to every colour state ("HOT" not only red) |
| Hold / toggle for every held input | optional | yes | |
| Relax / assist mode | optional | yes for skill-heavy games | e.g. no fail timer; label it plainly, never shame |
| First-launch accessibility screen | optional | yes when any optional item is on | 3-4 toggles + "more in Options" |

Gate: a test per essential item (rebind saved and restored, text scale applied, reduced-motion flag read by juice) + screenshots of every screen at 150 %.

## 2. UI quality

| Item | Status | Default |
|---|---|---|
| Scene transitions: fade ≤ 0.5 s, skippable (any key), never blocking input longer | ESSENTIAL | — |
| Hover **and** focus state on every button (mouse, keyboard, pad): scale ~1.05 or outline/brighter fill, ~0.1 s, hand cursor | ESSENTIAL | — |
| Short notifications: icon + 2-3 words; the full sentence only the first time | optional | yes |
| One notice at a time (queue, no stacking on top of the HUD) | optional | yes |
| Single source of truth for every number shown on more than one screen (score, money, tips, quota) + a consistency check | recommended | yes |

Single source of truth: one getter per number (e.g. `RunStats.Tips`), every screen reads it; a test or editor check compares the values each screen shows in the same state. Buffet Panic! had three screens counting tips three ways (gate 50).

## 3. Onboarding

Default yes, asked.
- Tutorial ≤ 4 steps, the core verb only; it never blocks the second-best verb (make it available from the start).
- Contextual first-time hints for everything else, shown once, at the first real occasion, saved per profile.
- Progressive disclosure on dense screens (shop, upgrades, van, inventory): items appear a few at a time across the first runs.

## 4. Localization from day 1

Asked: how many languages, which (default: EN + the owner's language; 8+ if the game targets Steam worldwide).
- One string table `Assets/_Game/Localization/strings.csv`: `key,context,max_chars,<lang1>,<lang2>,...`. `context` says where it appears; `max_chars` is the UI limit.
- **No hard-coded strings** in UXML, C# or prefabs. A check (`loc_check`) reports: missing per language, placeholder mismatches (`{0}`), duplicates, rows over `max_chars`, string literals in UI code.
- Font fallbacks planned up front: CJK (ZH/JA/KO) and Arabic (RTL, shaping) in the fallback chain; one screen per script checked by screenshot. Unity: skill `localization` + `optimize-text-mesh-pro`.
- Owner's language list = a decision: it goes into `DECISIONI.md` and is never reopened.

## 5. Playtest kit

Default yes.
- **Telemetry CSV**, opt-in (asked on first launch), local file only (`Application.persistentDataPath/telemetry/*.csv`), one row per level/floor: time, result, deaths/drops, score, key events. No network.
- **Demo / fresh-profile build variant**: its own company/product name or save folder, so it never reads or writes the developer's saves and PlayerPrefs.
- **Tester README** from [templates/TESTER_README.md](../templates/TESTER_README.md): install, controls, what to observe, how to send the telemetry, 10 questions.

## 6. Store-capture tool

Optional; default yes when the GDD says the game will be sold.
- Editor-only (`Assets/_Game/Editor/Capture/`), never in the build.
- HUD modes: `full` / `minimal` / `none`; input prompts hidden in every mode except `full`.
- Fixed seeds and real systems for the set-up (see "Catture fedeli alle regole" in [playtest.md](playtest.md)).
- Outputs: store-size screenshots (1920x1080, plus the sizes the store asks for), GIF frame sequences (PNG numbered) in `captures/<date>/`, never in `Temp/` or `Library/`.
- Every output has a sidecar `captures/<date>/manifest.json`: file, seed, scene, HUD mode, how it was produced.

## 7. Discoverability (every screen and feature has a way in)

ESSENTIAL from the first menu, checked again after every redesign ([design-review.md](design-review.md) §2).
- Every screen, shop, unlockable, cosmetic and upgrade has at least one entry point the player can find, and the screen map grades it **evidente / trovabile / nascosta**. Anything **nascosta** is either on purpose (`hidden-ok` + the decision) or a bug.
- Important features get **two** entry points, or one entry the game shows the first time it matters (contextual hint). A single entry point is fragile: one redesign and the feature is gone.
- **Orphaned-feature check** after any change to menus, shops, flow or progression: `design_review.py screens --before` on the screen map. Buffet Panic!: the most liked shop screen of the game stopped opening in a real run after the van was redesigned; only the full screen map of wave 9 found it.
- One door per screen where possible; the same screen reached from three places with three different layouts confuses more than it helps.
