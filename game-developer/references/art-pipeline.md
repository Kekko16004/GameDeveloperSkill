# Art pipeline — blueprint + kits + ProBuilder + hero props. Never bpy cubes, never one wall at a time.

AI `execute_blender_code` modelling is banned. It drifts, floats pivots, leaks light. Hand-placing 40 kit walls via MCP calls never finishes either. A playable slice uses pieces that already exist, assembled by `GDS.LevelBuilder` from a JSON blueprint ([level-builder.md](level-builder.md)), then lit by `GDS.LookDev` ([lookdev.md](lookdev.md)).

## Rank (first that fits)

| Rank | Tool | Cost | Use for | Never for |
|---|---|---|---|---|
| **1** | **Blender building generator** (`gds-building.ps1`, spec JSON) | $0, seconds | Every exterior building that must look finished: houses, inns, tower-houses, shops, sheds | Curved towers (PB), furniture (kits) |
| **1b** | **Kit family** (Kenney zips / KayKit / Quaternius Standard / Synty Starter if Q21) via blueprint `mode: kit` + `attach` | $0 | Buildings in the kit's own style, furniture, props, fences, lanterns, trees, rocks | Mixing families in one room |
| **2** | **ProBuilder** via `GDS.PB` / blueprint `mode: probuilder` + palette material | $0 | Rooms, corridors, towers, stairs, arches, collision shell when the kit has no walls | Hero props, characters |
| **3** | **Poly Pizza / Poly Haven models / Sketchfab CC0** (Blender MCP, sanitize, export) | $0 | One missing prop/character; normalize to Geometra metres | Levels, dioramas, 50k scans next to Kenney |
| **4** | **gen3d tier from GDD Q20** (Modly local / Meshy / Tripo / Hyper3D) | $0 local or credits | ≤ `gen3dMaxAssets` unique hero props | Modular pieces, anything a kit has |
| **X** | bpy modelling, Sloyd, Blockbench, Dust3D, Unity primitives after greybox | — | — | Default path |

## Beta-ready checklist (enforced by SceneLint + LookDev, not by eye)

1. Scale 1u = 1m (`GDS.KitCatalog` reports; `SetImportScale` once per kit folder).
2. Pivot irrelevant: builder aligns by bounds. Lint flags anything > 2 cm buried / > 5 cm floating.
3. Box/Capsule collider on every prop (builder adds; lint flags).
4. No cameras/lights in the file (`Common.Spawn` strips).
5. Snap 1m / 2m / 4m for env via blueprint cells. Props may sit off-grid.
6. **One family** per slice. Hero CC0 props may dress it if low-poly and palette-matched.
7. Lookdev applied (Volume, fog, sun, skybox) before any UI/playtest screenshot.
8. Materials: URP/Lit or toon; no Standard/Legacy (lint flags `nonUrpShader`), no pink.

## Per-genre default

| GDD | Family (fetch-cc0-kits.ps1 -Genre) | Extras | Lookdev preset |
|---|---|---|---|
| Medieval / village | Kenney Castle + Furniture + Nature (`medieval`); or KayKit Medieval Hex; or Quaternius Medieval Village Standard | KayKit Adventurers (`characters`) | `stylized-day` / `stylized-sunset` |
| Dungeon | Kenney Modular Dungeon + Mini Dungeon (`dungeon`); or KayKit Dungeon Remastered | KayKit Skeletons | `dungeon-torch` |
| Sci-fi / space | Kenney Modular Space (`scifi`); KayKit Space Base; Quaternius Sci-Fi Standard | Kenney Animated Protagonists | `scifi-cold` |
| City | Kenney City Suburban (`city`); Quaternius Downtown Standard | Kenney Animated Survivors | `stylized-day` / `night-moon` |
| Pirate | Kenney Pirate (`pirate`) + Nature | Kenney Animated Retro | `stylized-sunset` |
| Interior | Kenney Furniture (`interior`); KayKit Furniture Bits | — | `pastel-bright` / `dungeon-torch` |
| Nature extra | Kenney Nature Kit (`nature`); Quaternius Stylized Nature Standard | — | — |
| Any stylized (Q21 yes) | Synty POLYGON Starter Pack | Cartoon FX Free | any |

Fetch: `scripts/fetch-cc0-kits.ps1`. If `paths.kenneyAllInOne` exists, copy from that folder instead of re-downloading zips.

## Worker routing

```
GDD asset row
  ├─ exterior building             → building-gen (Blender spec → FBX), placed by village or as a blueprint prop
  ├─ settlement / outdoor map      → village (roads, plaza, lots, terrain, forest)
  ├─ interior / dungeon / area     → level-build (blueprint: shell + partitions + interior props + attach)
  ├─ prop in kit                   → row in a blueprint `props` list
  ├─ prop missing in kit           → hero-asset (Poly Pizza → Poly Haven → Sketchfab → gen3d tier) then `props` row
  ├─ character                     → characters (KayKit / Kenney / Quaternius UAL)
  ├─ trees / rocks / clutter       → blueprint `scatter`
  └─ voxel GDD                     → voxel worker
```

Do not spawn hero-asset for a Kenney crate. Do not `execute_blender_code` a mesh. Do not `manage_gameobject` a wall.

## Slice evidence

≥ 2 blueprints (`art/blueprints/*.json` + `docs/lint/build-*.json` PASS) + hero rows in ledger with `screenshots/blender-$ID.png` + `docs/lint/scene-lint.json` `issues: 0` + `screenshots/035-lookdev.png`.
