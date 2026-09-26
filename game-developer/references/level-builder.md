# Level builder — blueprint JSON → building in one call

Why: "one kit piece per worker" never finishes a house; per-face ProBuilder MCP edits drift. The agent writes a **blueprint** (data), `GDS.LevelBuilder` assembles it (code). Pivot-agnostic: every piece is aligned by its measured bounds, so Kenney / KayKit / Quaternius / Synty all snap.

## Flow (worker `level-build`)

1. `GDS.KitCatalog.BuildJson(kitFolder)` → read `art/kit-catalog.json`. Pick files for roles `floor wall wallDoor wallWindow corner roof stair`. Check `suggestedModule` (Kenney castle/dungeon ≈ 1.0–4.0, KayKit ≈ 2–4). If `notes` says the kit is not metric → `SetImportScale` once.
2. Write `art/blueprints/<name>.json` (schema below). One file per building / room / area.
3. `return GDS.LevelBuilder.BuildFromFile("art/blueprints/<name>.json");` → read result: `pieces`, `missingRoles`, `warnings`.
4. `GDS.SceneLint.RunJson(autoFix:true)` → then `RunJson()` must say `issues: 0` (includes `overlappingWalls: 0`, `overlappingFloors: 0`).
5. Screenshot `screenshots/02x-build-<name>.png`. Gate quotes both JSONs.

## Schema

```json
{
  "name": "House_A",
  "group": "Level/Buildings",
  "origin": { "x": 0, "y": 0, "z": 12 },
  "rotY": 0,
  "mode": "kit",
  "kitRoot": "Assets/_Game/Art/Kits/kenney/kenney_castle-kit",
  "module": 4.0,
  "wallHeight": 3.0,
  "wallThickness": 0.2,
  "roles": [
    { "role": "floor",      "file": "floor.fbx" },
    { "role": "wall",       "file": "wall.fbx" },
    { "role": "wallDoor",   "file": "wall_doorway.fbx" },
    { "role": "wallWindow", "file": "wall_window.fbx" },
    { "role": "corner",     "file": "column.fbx" },
    { "role": "roof",       "file": "roof.fbx" }
  ],
  "cellsX": 3, "cellsZ": 2, "floors": 1,
  "openings": [
    { "side": "S", "index": 1, "floor": 0, "type": "door" },
    { "side": "N", "index": 0, "floor": 0, "type": "window" },
    { "side": "E", "index": 1, "floor": 0, "type": "none" }
  ],
  "roof": "kit",
  "corners": true,
  "material": "Assets/_Game/Art/Materials/Mat_Palette_2.mat",
  "prefabOut": "Assets/_Game/Prefabs/Buildings/House_A.prefab",
  "props": [
    { "file": "table.fbx", "name": "prop_table", "x": 6, "y": 0, "z": 4, "rotY": 90, "snap": true, "collider": "box" },
    { "file": "chair.fbx", "x": 5.2, "z": 4, "rotY": 90 },
    { "file": "prop_medieval_war_chest.glb", "x": 1, "z": 1, "collider": "convex" }
  ],
  "scatter": [
    { "file": "tree_pineTallA.fbx", "count": 25, "minX": -30, "maxX": 30, "minZ": -30, "maxZ": 30, "minDist": 3, "seed": 7, "avoidRadius": 14, "scaleMin": 0.9, "scaleMax": 1.3 },
    { "file": "rock_largeA.fbx", "count": 8, "minX": -30, "maxX": 30, "minZ": -30, "maxZ": 30, "minDist": 5, "seed": 3, "avoidRadius": 14 }
  ]
}
```

- `mode`: `kit` (modular pieces) | `probuilder` (real ProBuilder slabs + segmented walls, door/window gaps, flat or gable roof, palette materials) | `primitives` (greybox only) | `props` (no shell: props/fences/scatter only).
- **Composite plans** — `volumes: [{x, z, cellsX, cellsZ, floors, roof}]` (metres offsets, multiples of `module`) instead of `cellsX/cellsZ/floors`. Overlapping/adjacent volumes make L / T / U plans: walls buried in another wing are dropped, shared boundaries stay open (add `partitions` for interior walls), floors/roofs deduplicated, taller wings keep their upper walls. `openings[].volume` selects the wing.
- **Interior** — `partitions: [{volume, floor, x0, z0, x1, z1, door}]` (metres, `door` = 0..1 along the wall or -1), `stairs: [{file, x, z, rotY, floor}]` (kit `stair` role if `file` empty), `floorHoles: [{volume, cellX, cellZ, floor}]` for the stair well.
- **Wall attachments** — `attach: [{file, volume, side, index, floor, y, outward, along, rotY}]`: lanterns, signs, awnings, flower boxes, banners, pipes — placed on the wall segment, facing outward. This is the cheap detail layer that makes kit houses read as real.
- **Fences** — `fences: [{file, points: [{x,z}...], pieceLength, postFile}]`: kit fence pieces along a polyline, stretched to close gaps, snapped to ground.
- `props[].collider`: `box | convex | mesh | none` — `mesh` = exact static MeshCollider, use it for Blender-generated buildings (`file: "building_inn_hero"`).
- `scatter[].avoidPoints`: extra keep-out centres (other buildings) with `avoidPointRadius`.
- `origin` = building corner (min X, min Z). Cells grow +X / +Z. `rotY` rotates the finished building.
- `openings.side`: `S` (z=origin), `N`, `W` (x=origin), `E`. `index` = cell along that side. `type`: `door | window | none` (gap).
- `roof`: `kit` (roof role per cell; falls back to floor tiles) | `flat` | `none` | `gable` (probuilder mode).
- `props.file`: file name or path; searched under `Assets/_Game/Art` (kits **and** `art/exports` imports). `snap` raycasts to the surface below (tables inside rooms land on the floor tile, not the slab). Coordinates are relative to `origin`.
- `scatter`: seeded, min distance, keeps `avoidRadius` around the origin free, raycasts each instance to the ground — nothing floats.
- `prefabOut`: optional, saves the assembled building as a prefab.
- `wallOwner`: `auto` (default) | `self` | `neighbour` | `off` — who builds a wall line / slab shared with another blueprint (see below). `off` = legacy, builds everything (lint will flag duplicates).
- `omit`: `["N", "v1:E", "W2", "floor", "roof"]` — wall runs (`[v<volume>:]<side>[<index>]`) or parts this blueprint never builds; the neighbour on that line owns it.
- `neighbours`: optional explicit list of blueprint files to share with; default = every blueprint in the same folder with the same `group`.
- `groundGap` (0.02): a plain ground (e.g. greybox `Ground` cube, top at Y=0) coplanar with this blueprint's floors is lowered by this much, so floors sit on it without z-fighting. 0 = off.

## Shared walls & floors (one wall per line, one slab per spot)

Adjacent rooms / corridors are separate blueprints on the same 4 m grid, so their walls fall on the same line. `BuildFromFile` reads the other blueprints of the same folder + group (JSON only, never the scene; other blueprints' objects are never touched) and:

- **Walls** — a run collinear with a neighbour's (centre-lines closer than the mean thickness, same storey, overlap longer than a thickness) is built **once**. Owner: `omit` side loses → `wallOwner` self > auto > neighbour → taller `wallHeight` → blueprint `name` (ordinal, first wins). The owner cuts the openings of **both** sides into its wall (door > window) and takes the taller height; the other side skips that portion (splits a partial run) and keeps only its wainscot on its face. `none` = "no wall from me": facing the neighbour's door → that door; facing a plain wall → plain wall; `none` on both sides → gap. Corner/edge contacts ≤ thickness are normal.
- **Floors / ceilings** — floor vs floor and roof vs roof on the same level: the owner (same rule) keeps its slab, the other clips its own (kit tiles dropped when ≥ 50 % covered). A roof under another blueprint's floor on the same level is dropped (that floor is the ceiling). Overlaps < 0.25 m (eaves) are kept.
- **Order** — the result depends only on the JSONs, so build order does not matter. Only when you change openings / height / `wallOwner` / `omit` on a shared line, rebuild **both** blueprints of that line. After upgrading GDS, rebuild every blueprint once (old builds still carry full duplicate walls).
- Result JSON adds `sharedOwned`, `sharedSkipped`, `omitted`, `slabsClipped`, `groundLowered`, `sharedWith[]`. Warning "built by X, which is not in the scene yet" = build X.
- `rotY` not a multiple of 90 → no sharing (warning); lint reports the duplicates.
- Gate: `gds_lint` → `overlappingWalls: 0`, `overlappingFloors: 0`.

Result JSON: `{ status, pieces, props, scattered, boundsX/Y/Z, missingRoles[], warnings[] }`. `missingRoles` non-empty for `floor`/`wall` = FAIL → fix the roles, do **not** fall back to cubes.

## Which builder for which building

| Need | Use | Why |
|---|---|---|
| Exterior buildings that must look finished (village, town, inn, tower-house) | **Blender generator** ([blender-building.md](blender-building.md)) → FBX → `props`/village `buildings` | frames, trims, roofs, beams, balconies out of the box; one spec = one house |
| Buildings in a kit's own art style (Kenney/KayKit/Synty) | `mode: kit` + `attach` details | textures and silhouettes of the kit; interiors from kit props |
| Interiors, dungeons, corridors, collision shells | `mode: probuilder` (`GDS.PB.Room`) + kit props | exact gaps, palette materials, fast |
| Whole settlement | `GDS.Village` ([village.md](village.md)) | roads, lots, facing, terrain, fences, scatter |

## ProBuilder helpers (when the GDD wants rooms rather than kit walls)

```
GDS.PB.Room(new Vector3(0,0,0), 12, 3, 8, "S:1,E:0:window", "Assets/_Game/Art/Materials/Mat_Palette_1.mat", "Hall")
GDS.PB.Tower(new Vector3(20,0,0), 3f, 9f, 8, matPath)
GDS.PB.Stairs(new Vector3(4,0,0), 2f, 3f, 4f, 10, 90f, matPath)
GDS.PB.Arch(new Vector3(6,0,0), 1.2f, 2.4f, 0.4f, 0f, matPath)
```

Doors are made by splitting the wall into legs + lintel (no CSG, no face indices). ProBuilder shells stay as collision + look; dress with kit props on top.

## Rules

- One family per blueprint (`kitRoot`). Poly Pizza / Poly Haven / generated hero props go in `props`, never in `roles`.
- Never hand-place a wall via `manage_gameobject` after this exists. Edit the JSON, rebuild (same `name` replaces the old building).
- A blueprint with `cellsX*cellsZ*floors > 200` is a level, not a building: split.
- Store every blueprint in `art/blueprints/`. That folder **is** the level's memory for `/resumegame`.
