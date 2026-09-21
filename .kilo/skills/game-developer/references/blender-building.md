# Blender building generator — real houses from a 20-line spec

`templates/blender/gds_building.py` is a deterministic procedural architect (pure bpy/bmesh, no addons, Blender 4.x/5.x). The LLM writes **what** (footprint volumes, style, doors, balconies); the script decides **how it looks**: wall thickness, plinth, cornices, timber beams, window frames + sills + mullions + shutters, door frame + planks + step + awning, gable/hip/flat roofs with overhang, fascia, ridge beam, chimneys, balconies with railings, interior slabs, partitions with door frames, stairs. Flat-shaded, bevelled, box-UV'd, 5–25 k tris, one mesh with 6–8 material slots, pivot at footprint corner on the ground, exported as **GLB + FBX**.

Samples: `docs/samples/blender-inn_hero.png`, `docs/samples/blender-mage_house.png`.

## Run

Headless (no MCP, no GUI — the robust path):
```
powershell -File SKILL/scripts/gds-building.ps1 -Spec PROJECT/art/specs/inn.json -ProjectPath PROJECT
```
→ `GDS_RESULT {"name","tris","materials","dims","glb","fbx","bytes","preview"}`; FBX/GLB copied to `Assets/_Game/Art/Exports/`, preview PNG in `screenshots/`.

Via Blender MCP (when the scene is already open, e.g. to add Poly Haven PBR materials first):
```
execute_blender_code:  exec(open(r"<SKILL>/templates/blender/gds_building.py", encoding="utf-8").read()); print(gds_build(r"<PROJECT>/art/specs/inn.json"))
```
This is the **only** allowed `execute_blender_code` beyond wipe/sanitize: a fixed generator, not freehand modelling.

## Spec

```json
{
  "name": "inn_hero",
  "style": "medieval",                       // medieval | fantasy | village | modern | scifi | dungeon
  "styleOverride": { "roof": "#5A6E8E", "shutters": false },   // any STYLES key
  "volumes": [
    { "x": 0,  "z": 0, "w": 10, "d": 7, "floors": 2, "roof": "gable", "ridgeAxis": "x" },
    { "x": 10, "z": 1, "w": 5,  "d": 5, "floors": 1, "roof": "hip" }
  ],
  "wallThickness": 0.3, "floorHeight": 3.0,
  "window": { "w": 1.1, "h": 1.4, "sill": 1.0, "spacing": 2.4, "margin": 1.0, "auto": true },
  "windowsOverride": [ { "volume": 0, "side": "N", "floor": 1, "count": 3 } ],
  "doors":      [ { "volume": 0, "side": "S", "t": 0.3, "awning": true } ],
  "balconies":  [ { "volume": 0, "side": "S", "floor": 1, "t": 0.7, "w": 3.0, "depth": 1.2 } ],
  "chimneys":   [ { "volume": 0, "x": 2.5, "z": 3.5 } ],
  "roof": { "pitch": 0.55, "overhang": 0.5, "thickness": 0.16 },
  "interior": {
    "partitions": [ { "volume": 0, "floor": 0, "from": [5, 0], "to": [5, 7], "door": 0.5 } ],
    "stairs": { "volume": 0, "x": 0.6, "z": 0.8, "rotY": 0 }
  },
  "materials": { "wall": "plaster_rough" },          // optional: existing Blender material names (Poly Haven via MCP)
  "textures":  { "roof": "C:/.../roof_tiles_diff_1k.jpg" },   // optional: image paths
  "export": "art/exports/building_inn_hero.glb",     // relative → PROJECT (gds-building.ps1) ; FBX exported next to it
  "preview": "screenshots/blender-building_inn_hero.png",
  "bevel": 0.012, "uvScale": 2.0
}
```

- Plan coordinates: `x` right, `z` depth, metres. Volumes overlap to make L / T / U plans; shared walls are trimmed automatically, floors/ceilings deduplicated.
- `side`: `S` (z = min, the street side by convention), `N`, `W`, `E`. `t` = 0..1 along that side.
- Windows are auto-spaced per wall (skipped where a door is); `windowsOverride` fixes a count per wall/floor (`"count": 0` = blind wall).
- Styles set palette + features: `beams` (timber corner/floor beams), `shutters`, `plinth` height, `stone_ground` (stone ground floor).
- Everything is 1 unit = 1 m. Door 1.2 × 2.3, window 1.1 × 1.4, floor 3.0: Geometra-compatible.

## In Unity

The exported FBX is a normal model: `props` row in a blueprint (`"collider": "mesh"`) or a `buildings[]` entry in a village spec (`"file": "building_inn_hero"`). Materials import as URP/Lit with the style colors (SceneLint auto-converts if the pipeline changed after import). Lint with `GDS.SceneLint.RunJson()` as always.

## Gate (`docs/gates/07-building-<name>.md`)

- `GDS_RESULT` JSON line (tris between 2 k and 40 k, `bytes` > 50 k)
- `screenshots/blender-building-<name>.png` (the Workbench preview) — parent reads it only for style coherence with the kit family
- `Assets/_Game/Art/Exports/building_<name>.fbx` present, then the blueprint/village rebuild + lint 0

## Limits (say them, do not hide them)

- Rectangular volumes only (compose several for complex plans). No curved walls, no towers: use `GDS.PB.Tower` in Unity or a kit piece.
- Interior detail = slabs, partitions, stairs, door frames. Furniture comes from kits via blueprint `props`.
- Textures are flat colors unless `textures`/`materials` are given (Poly Haven CC0 via Blender MCP `download_polyhaven_asset(textures)`, then `"materials": {"wall": "<material name>"}`).
