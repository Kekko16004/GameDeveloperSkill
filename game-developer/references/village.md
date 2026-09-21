# Village — world layout in one call

`GDS.Village.BuildFromFile("art/blueprints/village_a.json")` builds: terrain (Perlin hills, flat centre, 2 slope-blended layers), roads (slabs or kit tiles), plaza with props, **lots along every road with buildings facing the street** (Blender-generated FBX or LevelBuilder blueprints, weighted random), fences with a gate in front of each lot, street props (lanterns alternating sides, barrels with jitter), and an outer forest/rock ring that avoids roads and lots. Sample: `docs/samples/unity-village-aerial.png`.

Template: `templates/blueprints/village_example.json`.

```json
{
  "name": "Hamlet", "group": "Level/Village", "origin": {"x":0,"y":0,"z":0}, "seed": 7,
  "terrain": { "enabled": true, "size": 220, "height": 14, "noiseScale": 0.018, "flattenRadius": 50, "layers": ["#6B8E4E", "#8A7B5C"] },
  "roads": [ { "points": [{"x":-60,"z":0},{"x":60,"z":0}], "width": 5 }, { "points": [{"x":0,"z":-50},{"x":0,"z":50}], "width": 4 } ],
  "roadMaterial": "Assets/_Game/Art/Materials/Mat_Palette_3.mat", "roadFile": "",
  "plaza": { "x": 0, "z": 0, "w": 18, "d": 18, "enabled": true },
  "lots": { "spacing": 16, "setback": 3, "minDistFromPlaza": 10, "gate": 2.2, "bothSides": true },
  "buildings": [
    { "file": "building_cottage_a", "weight": 3, "collider": "mesh" },
    { "file": "building_inn_hero",  "weight": 1, "collider": "mesh" },
    { "blueprint": "art/blueprints/house_kit_a.json", "weight": 2 }
  ],
  "streetProps": [ { "file": "lantern", "every": 12, "offset": 3.2, "alternate": true, "faceRoad": true } ],
  "plazaProps":  [ { "file": "well", "x": 0, "z": 0 } ],
  "fenceFile": "fence",
  "scatter": [ { "file": "tree_pineTallA", "count": 140, "radius": 95, "minDist": 4, "avoidVillageRadius": 52 } ]
}
```

- Terrain: flat area (y = 0) inside `flattenRadius`, hills outside; `TerrainCollider` included; URP terrain material when URP is active. Disable for interior-only games.
- Roads/plaza get URP/Lit slabs (or `roadFile` kit tiles). Names start with `road`/`plaza` → SceneLint treats them as environment.
- Lots: every `spacing` metres on both sides; a lot is skipped if it overlaps the plaza, another lot or a road. Buildings face the road: their `S` side (door) toward the street.
- `buildings[]`: `file` = FBX/GLB in `Assets/_Game/Art` (Blender generator output or kit building), `blueprint` = LevelBuilder JSON (kit or ProBuilder shell; it is rebuilt per lot with rotation). `weight` = pick probability.
- Result JSON: `{ buildings, roads, streetProps, fencePieces, scattered, terrain, warnings }` → `docs/lint/village-<name>.json`.

## Protocol (worker `village`)

1. Buildings first: 2–4 Blender specs (`art/specs/*.json`) → `gds-building.ps1` each, or kit blueprints in `art/blueprints/`.
2. Write `art/blueprints/village_<name>.json` from the GDD map (roads = the GDD's paths; plaza = the hub; hero building weight 1, cottages weight 3).
3. `return GDS.Village.BuildFromFile(...)` → `buildings` ≥ 6 for a slice, `warnings` empty (missing files are listed there).
4. `return GDS.SceneLint.RunJson(autoFix:true)` then `RunJson()` → `issues: 0`.
5. `GDS.LookDev.Apply(<GDD preset>)`, then screenshot aerial + street level: `screenshots/025-village-aerial.png`, `screenshots/026-village-street.png`.
6. Player spawn on the plaza; NavMesh bake later (characters phase).

Rules: one call rebuilds the whole village (same `name`), never hand-edit lots. Interiors: give each building blueprint its own `props`, or make the hero building's interior with the Blender `interior` block. Dungeons/interiors-only games skip this phase and use `GDS.PB.Room` blueprints.
