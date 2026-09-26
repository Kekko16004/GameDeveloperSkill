# Task decomposition — atomic by *deliverable*, not by click

Macro tasks ("make the village") make an agent stop early. Micro tasks ("place wall 17") burn tokens: 110+ rows, each with its own context load, prompt and gate. The rule is in between:

**One task = one verifiable deliverable = usually one deterministic call or one script+test.** Target **60-80 tasks** for a vertical slice (hard cap 90). Never a task without evidence on disk.

## Merge rules (what goes in ONE task)

| Merge into one task | Because |
|---|---|
| A whole building / room / area | one blueprint JSON → one `gds_build` → one lint |
| The whole procedural world (terrain + layers + scatter + water + spawn) | one `gds_world` call |
| Import + materials + collider + prefab of the same asset | the builder/import does all of it in one pass |
| Up to 3 hero props from the same source | hero-asset batch |
| Up to 5 Blender building specs | building-gen batch |
| A verb's script + its test + its prompt hook (`DoorInteractable` + `Interact_OpensDoor` + `[E] Apri`) | same worker, same compile, same test run |
| Small related settings (tags/layers + input actions + quality) | one project-setup task |
| Palette + lookdev preset + torches | one lookdev task |
| All SFX wiring for one system (door open/close/locked) | one audio task |

## Keep separate (never merge)

- Different gates: greybox ≠ world ≠ blueprint ≠ lookdev ≠ UI screen ≠ playtest.
- Each UI screen (the user picks a variant per screen).
- Each blueprint that another worker could build in parallel (max 3 at once).
- Anything with a `[WAIT-USER-ASSET]` or user choice.
- Each art-review pass.

## Typical slice budget (≈ 70)

| Block | Tasks |
|---|---|
| Setup (project, packages, GDS, input, scenes) | 4-5 |
| Reference board + world spec + PLAN | 2-3 |
| Greybox + movement test | 3 |
| Kit fetch + catalog | 2 |
| World-gen (1) + building-gen batches (1-2) | 2-4 |
| Blueprints (buildings/rooms/areas) | 6-12 |
| Hero props (batches of 3) | 2-4 |
| Lookdev + art review ×2 + fixes | 4-6 |
| Characters (player, 1-2 enemy types) + NavMesh | 3-4 |
| Systems (one verb/system = script + test + hook) | 10-15 |
| UI (4 screens + inventory/dialogue if any) | 4-6 |
| Audio + VFX + juice | 5-7 |
| Playtest + fixes + slice recap | 4-6 |

If the count goes above 90: merge by the table above. Below 50 for a normal slice: something macro slipped in — split it by deliverable.

## Row format (`GAME_TASKS.md`)

```
| TASK-021 | BP | BP-house_a — 3x2 cells, 1 floor, door S1, window N0, kit roof, interior table+2 chairs+chest, origin (0,0,12) | art/blueprints/house_a.json | build JSON + lint 0 + PNG | [ ] | kenney |
| TASK-034 | SYS | Interact: IInteractable + DoorInteractable (slerp) + raycast in PlayerController + HUD prompt [E] + test Interact_OpensDoor | Scripts/Interaction/* | test green + console 0 | [ ] | |
| TASK-040 | WORLD | Overworld terrain 400 m, seed 42, flat village spot (0,0,35), pines/oaks/rocks scatter | art/world/overworld.json | world JSON PASS + lint 0 + sheet | [ ] | |
```

The description carries every number the worker needs (sizes, origins, counts, names from the catalog), so the worker never re-reads the GDD for it.

## User-provided assets

`asset-strategy: user-provided | hybrid` → `art/ASSET_MANIFEST.md` (file name, folder `art/exports/`, size in metres, pivot at base, `.glb`/`.fbx`) and ONE row per asset: `[WAIT-USER-ASSET] prop_x.glb → validate + import + rebuild blueprints that use it`. On `/resumegame` "ho messo i modelli": check the file (> 5 KB), mark `[x]`, `asset_ready: true`, rebuild.

## Lifecycle

`[ ]` → `[/]` (worker running) → `[x]` with evidence path, or `[!]` with the error (max 2 retries). Update the counters in `GAME_TASKS.md` and the snapshot in `GAME_CONTEXT.md` after every task.

## Speed

- Independent tasks run in parallel (max 3 workers): blueprints, hero batches, UI mocks while systems compile.
- A worker may complete **consecutive tasks of the same phase** in one run (e.g. 3 blueprints of the same kit) when each still writes its own gate line.
- Deterministic calls return JSON: paste the JSON in the gate, never re-describe it.
