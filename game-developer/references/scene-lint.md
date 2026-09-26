# Scene lint — the gate is a JSON, not an opinion

`GDS.SceneLint.RunJson()` writes `docs/lint/scene-lint.json`:

```json
{ "scene": "Slice", "checkedObjects": 143, "issues": 0,
  "buried": 0, "floating": 0, "noGround": 0, "noCollider": 0, "pinkMaterial": 0, "nonUrpShader": 0, "emptyMesh": 0, "outOfBounds": 0,
  "overlappingWalls": 0, "overlappingFloors": 0,
  "list": [ { "type": "buried", "obj": "Level/Props/prop_barrel_3", "value": -0.12, "fix": "raise by 0.120 m (surface: floor_1_0)", "isFixed": false } ] }
```

| Type | Meaning | Auto-fix |
|---|---|---|
| `buried` | bounds.min.y is below the surface under the object by > 2 cm | yes (raise) |
| `floating` | bounds.min.y is above the surface by > 5 cm | yes (lower) |
| `noGround` | nothing with a collider under the object (ground without collider, or object outside the level) | no — fix the ground / move the object |
| `noCollider` | no Collider in the hierarchy | yes (BoxCollider from bounds) |
| `pinkMaterial` | null material / error shader | no — assign URP/Lit or run the URP material converter |
| `nonUrpShader` | Standard / Legacy shader on a URP project | no — `Window > Rendering > Render Pipeline Converter` or `manage_material` |
| `emptyMesh` | MeshFilter with no mesh | no — delete or reimport |
| `outOfBounds` | > 500 m from origin | no |
| `overlappingWalls` | two parallel wall pieces interpenetrating in thickness (centre-lines closer than mean thickness), overlapping > 50 % of the shorter length and > 50 % of the lower height = same wall built twice (z-fighting, doors to align twice). Corner contacts and wainscots ignored | no — fix the blueprint (`omit` / `wallOwner`) and rebuild both blueprints; hand-made walls: delete one |
| `overlappingFloors` | two horizontal slabs (slab_/floor_/ground/roof/ceiling/terrain/lawn/plaza/road) with coplanar top or bottom faces (±5 mm) overlapping > 50 % of the smaller = doubled floor / ceiling, or ground coplanar with a room floor | no — rebuild the blueprints (builder clips slabs, lowers a plain ground by `groundGap`) or lower the ground 2 cm |

Environment shells (names matching ground/floor/wall/room/roof/stair/pb_/env_… or big static colliders) skip the ground test. Player / camera / lights / UI are skipped.

## Protocol (every worker that touches the scene)

1. `return GDS.SceneLint.RunJson(autoFix:true);`
2. `return GDS.SceneLint.RunJson();` → must return `"issues": 0`.
3. Paste the JSON summary line into the gate file. Screenshot after, not instead.

Parent: a gate without a lint JSON line, or with `issues > 0`, is FAIL. No exceptions for "it looks fine in the screenshot".

Single object: `GDS.SceneLint.SnapToGround("prop_barrel_3")`.
