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

## Nucleon: `ncli lint --play` (the same gate, measured with Raycast in Play)

`python SKILL/scripts/ncli.py lint --play --write docs/lint/scene-lint.json` writes
`{"issues":0,"belowKillZ":0,"duplicates":0,"floating":0,"underground":0,"noGround":0,"primitives":0,"missingAsset":0,"logErrors":0,"mode":"play",...}`.
`Content/Scripts/gds_probe.lua` (copied by `ncli setup`; the project copy stays byte-identical to `templates/nucleon/Content/Scripts/gds_probe.lua`) measures every model / actor / shape that is not the ground:

| Type | Meaning |
|---|---|
| `floating` | the first surface under the centre of the bottom is more than `--tol` (5 cm) lower, and the ground around is lower too, and nothing holds the object (below) |
| `underground` | the top is under the ground around it, or more than half of the height is sunk (ground = median of 4 rays just outside the footprint) |
| `noGround` | nothing at all under the object or around it: over the void / off the terrain. `--allow-void` only for levels that really float (space, sky islands); never to hide probe failures |

- **Through solids**: a ray that starts inside a collider hits it at the start point (engine behaviour). The probe gets the bottom of every solid from ncli (`zlo`) and starts the next ray just under it (0.25 m steps when it is not known), at most 64 rays: a 9-storey block or a 3 m wall is crossed in one or two rays.
- **The ground**: every terrain, plus the entities whose name matches `--ground-names` (default `ground|floor|terrain|landscape|road|path`) as a word (start, after `_` / a digit, or a CamelCase part: `R1_road_051`, `flatA1_floor`, `MainFloor`; not `playground_sandbox`, `underground_box`, `footpath`) and **at ground level only**: a ground-named slab with another solid standing under it (the walls of the storey below, the legs of a deck) is an upper floor and is checked like any other piece (`warnings.upperFloors`). A ground entity above the top of the object being checked is passed through (a balcony over a bench is not the bench's ground); the terrain never is (a buried box is `underground`). Two ground slabs overlapping in their bounds (road strips down a slope, a floor on its plinth) are not storeys.
- **Room parts are checked against their room, not the ground.** ncli reads the blueprint of each `BP_<name>` folder (`art/blueprints/<name>.json`, the same `nc_gds.room_parts` the builder used; without a blueprint, the builder's names `<room>_floor`, `<room>_ceiling`, `<room>_wall<N|S|E|W><i>`, kit `<room>_floor<i>_<j>` / `_corner<k>`): a **lintel** (a wall segment that starts above the room floor: over a door or a window) or a **ceiling** has nothing under its centre by construction, so it is held when it touches a grounded part of the **same** room. A room **floor** is never held by its own walls: a room that floats is reported once, at its floor.
- **Held by what it rests on / attached**: a floating object whose bottom is at the top of (or inside) a grounded solid with an overlapping footprint is held (`restsOn`: a roof on posts, a deck on legs, a runway on columns; the centre ray misses the posts); one whose top is at the bottom of a grounded solid `hangsFrom` it (a trolley under its beam, washing under the line); any other non-room piece touching a grounded solid on a side is `attached` (a sign on a post, a flag on a pole), and so is a room floor touching a grounded solid of another room or building (a mezzanine office against the hall wall). A gap is never held: a trolley 20 cm under its beam floats. Grounded = terrain, ground entities and every probed object without a problem, **unless all it stands on floats** (a crate on a floating pallet: the pallet is reported, not the crate). `warnings.held` counts them by rule, `warnings.heldSample` names a few.
- Prove the gate is not blind before trusting a 0 on a new kind of level: add a box 1 m up in open air, one in a room touching nothing, one fully under the terrain and one past the terrain edge (`entity_add`, not saved), lint, remove: 4 more issues (2 `floating`, 1 `underground`, 1 `noGround`), then back to the count before. Test names must not be ground names (`ZZ_test_floor` would be ground and never probed): `ZZ_test_buried` is fine.
- Floating lines name what the centre ray hit (`"on"`), so the fix is readable: `{"gap":0.2,"name":"crane_trolley","on":"crane_cable"}` = raise the trolley to its beam, not lower it onto the cable.
- Cost: one Play of ~10-15 s for 3000 shapes (DayM greybox, 2026-10-24: 324 false `noGround` before this rule set, 0 false positives after, 6 real defects left).
