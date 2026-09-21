# Art pipeline — kits + ProBuilder + Poly Pizza. Never bpy cubes.

AI `execute_blender_code` modelling is banned. It drifts, floats pivots, leaks light. A playable slice uses pieces that already exist.

## Rank (first that fits)

| Rank | Tool | Cost | Use for | Never for |
|---|---|---|---|---|
| **1** | **Kenney packs** (per-kit zip, or local All-in-1 if you bought it) | $0 per pack / All-in-1 is $19.95 local-only | Modular walls, floors, furniture, props, same palette | Mixing with KayKit in one room |
| **2** | **Unity ProBuilder** (`manage_probuilder`) | $0 | Rooms, corridors, stairs, ramps, collision shell | Hero props, characters |
| **3** | **KayKit Standard** (GitHub) | $0 CC0 | Stylized dungeon/village/chars if GDD picked this family | EXTRA/SOURCE paid folders |
| **4** | **Quaternius MegaKit Standard** (itch $0) | $0 CC0, ~60–70% of pack | Sci-fi / village / city / nature / fantasy props when Kenney is thin | Pro/Source zips ($9.99+) |
| **5** | **Poly Pizza via Blender MCP** | $0, key in addon | One missing prop/character, normalize to Geometra metres | Levels, dioramas, 50k scans |
| **X** | bpy modelling, Sloyd Guest, Meshy, Tripo, Rodin, Hunyuan, TRELLIS, Blockbench, Dust3D | paid / VRAM / extra app | — | Default path |

Blockbench and Dust3D are skipped: extra install, no MCP in this stack, ProBuilder already covers grid rooms and kits cover props.

Hunyuan3D 2.1 / TRELLIS: 16–29GB VRAM, blob meshes, Hunyuan licence can exclude EU. Addon stays **disabled**.

## Beta-ready checklist

1. Scale 1u = 1m (Poly Pizza: `normalize_size` + `target_size`).
2. Pivot on the ground (`Y=0`). Walls: corner. Props: center-bottom.
3. Box/Capsule collider — not a dense render mesh.
4. No cameras/lights in the file.
5. Snap 1m / 2m / 4m for env. Props may sit off-grid.
6. **One family** per slice: Kenney **or** KayKit **or** Quaternius Standard. Poly Pizza props may dress that family if the look matches (low-poly, similar saturation). Photoreal Poly Pizza next to Kenney = FAIL.

## Per-genre default

| GDD | Family | Shell |
|---|---|---|
| Medieval / dungeon | Kenney Dungeon+Castle+Furniture; or KayKit Dungeon; or Quaternius Medieval Village **Standard** | ProBuilder |
| Sci-fi / space | Kenney Modular Space; KayKit Space Base; Quaternius Sci-Fi MegaKit **Standard** | ProBuilder |
| City | Kenney City Suburban; Quaternius Downtown City **Standard** | ProBuilder |
| Pirate | Kenney Pirate | ProBuilder |
| Interior | Kenney Furniture | ProBuilder |
| Nature extra | Quaternius Stylized Nature **Standard** | — |
| Fantasy props | Quaternius Fantasy Props **Standard** | — |

Fetch: `scripts/fetch-cc0-kits.ps1`. If `paths.kenneyAllInOne` exists, copy from that folder instead of re-downloading zips.

## Worker routing

```
GDD asset row
  ├─ env room/wall/stair     → greybox ProBuilder, then kit-dress tiles
  ├─ prop in kit             → kit-dress
  ├─ prop missing in kit     → blender-asset = Poly Pizza import (NOT bpy cubes)
  ├─ character in KayKit     → kit-dress
  └─ voxel GDD               → voxel worker
```

Do not spawn blender-asset for a Kenney crate. Do not `execute_blender_code` a mesh.

## Slice evidence

≥3 dressed pieces in `art/exports/` or `Assets/_Game/Art/`, each with ledger source (`kenney`/`kaykit`/`quaternius-standard`/`probuilder`/`polypizza`) + `screenshots/030-import-$ID.png` + collider.

Poly Pizza rows also need `screenshots/blender-$ID-2-import.png` + finale (not the old 5-step bevel protocol).
