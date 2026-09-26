# World generation — `GDS.World`

One seeded JSON → a whole world in one call. Same seed + same spec = same world, so a worker fixes the **spec** and rebuilds; it never patches the scene by hand.

```
unity command gds_world --spec art/world/<name>.json            # CLI (primary)
unity command eval "return GDS.World.BuildFromFile(\"art/world/<name>.json\");"
execute_code: return GDS.World.BuildFromFile("art/world/<name>.json");   # CoplayDev fallback
```

Result (also written to `docs/lint/world-<name>.json`): `status`, `rooms`, `cells`, `scattered`, `props`, `chunks`, `water`, `spawn`, `goal`, `villages`, `warnings`. `PlayerSpawn` (and `spawn_goal` for dungeon/cave) are placed; an existing `Player` is moved to the spawn.

Examples ship in `templates/world/` and are copied to `art/world/example_*.json` by `install-gds-editor.ps1`.

## Which mode

| GDD world (Q8) | mode | Notes |
|---|---|---|
| Open nature, hills, mountains, survival, exploration | `terrain` | Unity Terrain: warped fBm + ridged mountains + thermal erosion, height/slope layers, water, kit scatter |
| Island, archipelago, coast | `island` | `terrain` + radial falloff into the sea (`seaLevel` auto 0.12) |
| Village / town in a landscape | `terrain` + `flat[].village` | Flat spot + `GDS.Village` on top (village terrain disabled automatically) |
| Dungeon, crypt, roguelite floors, base interiors | `dungeon` | Rooms + corridors on a grid; kit tiles (`floorFile`/`wallFile`) or merged meshes; `art/world/<name>.layout.json` with room centres for enemies/loot |
| Cave, mine, grotto | `cave` | Cellular automata, largest region kept, jittered organic walls, optional ceiling |
| Minecraft-like, destructible, building game | `voxel` | `GDS.VoxelWorld` runtime: chunks, greedy meshing, caves, trees, water, streaming, `VoxelInteractor` dig/place |
| Hand-authored level (arena, house, street) | — | Not world-gen: `GDS.LevelBuilder` blueprints |

Worlds and blueprints compose: build the world first, then level-build blueprints with `origin` on a flat spot, then `GDS.SceneLint`.

## Schema

```jsonc
{
  "name": "Overworld", "mode": "terrain|island|dungeon|cave|voxel", "seed": 42, "spawn": true,
  "terrain": {                     // terrain + island
    "size": 400, "height": 60, "resolution": 513,   // metres; heightmap 2^n+1
    "scale": 0.006, "octaves": 5, "warp": 1.5,      // lower scale = bigger features; warp 0-3 = organic coasts/valleys
    "mountains": 0.45, "erosion": 20,               // ridged peaks weight; thermal erosion iterations
    "seaLevel": 0.12, "islandFalloff": 0.55,        // 0..1 of height; 0 = no water
    "flat": [ { "x": 0, "z": 0, "r": 35, "village": "art/blueprints/village_a.json" } ]
  },
  "layers": [                      // later layers override earlier ones; texture = Poly Haven PBR if you have it
    { "name": "sand", "color": "#D6C38E", "maxHeight": 0.15 },
    { "name": "grass", "color": "#6B8E4E", "maxSlope": 28, "texture": "Assets/_Game/Art/Terrain/grass_diff.png", "normal": "...", "tile": 8 },
    { "name": "rock", "color": "#7D7872", "minSlope": 28 },
    { "name": "snow", "color": "#EEF1F4", "minHeight": 0.82 }
  ],
  "scatter": [                     // names from art/kit-catalog.json
    { "file": "tree_pineRoundA", "count": 250, "minHeight": 0.16, "maxHeight": 0.7, "maxSlope": 25,
      "minDist": 5, "clusters": 0.5, "scaleMin": 0.85, "scaleMax": 1.25, "collider": "trunk|box|convex|mesh|none", "alignToSlope": false }
  ],
  "grid": {                        // dungeon + cave
    "cell": 4, "wallHeight": 4, "width": 26, "depth": 26,
    "rooms": 9, "minRoom": 3, "maxRoom": 6, "corridorWidth": 1,       // dungeon
    "fill": 0.46, "smooth": 5, "jitter": 0.7,                           // cave
    "floorFile": "floor_tile", "wallFile": "wall", "floorMaterial": "", "wallMaterial": "",
    "floorColor": "#4E4945", "wallColor": "#6A635C", "ceiling": false,
    "wallProps": [ { "file": "torch_wall", "every": 5 } ],
    "roomProps": [ { "file": "chest", "perRoom": 1, "collider": "box" } ]
  },
  "voxel": {
    "chunkSize": 16, "height": 64, "baseHeight": 20, "heightAmp": 20, "scale": 0.018, "octaves": 4, "mountains": 0.55,
    "seaLevel": 17, "snowLine": 44, "caves": true, "caveThreshold": 0.64, "treeChance": 0.012,
    "viewRadiusChunks": 5, "editorRadiusChunks": 3, "stream": true, "interact": true,
    "palette": ["", "#6AAA4A", "#866043"]          // optional hex per Block id (Air, Grass, Dirt, Stone, Sand, Water, Wood, Leaves, Snow, Gravel, Planks, Brick)
  }
}
```

## Rules

- **Kit dungeon**: set `cell` to the kit module size from `art/kit-catalog.json` (`suggestedModule`), then `floorFile`/`wallFile`. Without them the builder makes merged meshes with palette materials (fine for toon/low-poly greybox, not for the final look of a kit-family game).
- **Scatter before props**: world scatter is the vegetation layer; hero props and buildings come later from blueprints.
- **Fog scales itself**: `GDS.LookDev.Apply` thins fog on terrains > 150 m, so run lookdev after the world.
- **Dark worlds need light**: `dungeon`/`cave` + `dungeon-torch` without `wallProps` torches (or `GDS.VFX.AttachTorches`) is a black screen = FAIL at the art review.
- **Voxel**: the VoxelWorld streams around `target` (the Player) at runtime; in the editor it bakes `editorRadiusChunks` for screenshots/lint. Game systems use `world.SetBlock`, `world.GetBlock`, `world.RaycastBlock`, `world.SpawnPoint`. Hotbar keys 1-9 in `VoxelInteractor`. Up to 16 block types (palette texture 16x4).
- Gate: `status: PASS`, `warnings` reviewed (missing kit names = fix the spec), `gds_lint` → `issues: 0`, `gds_sheet` screenshots.

## Unreal

Realistic worlds go to Unreal ([unreal-loop.md](unreal-loop.md)): Landscape + PCG graphs + Megascans are better than anything we would generate here. The spec above is Unity-only.
