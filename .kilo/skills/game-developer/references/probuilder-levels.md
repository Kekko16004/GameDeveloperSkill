# ProBuilder levels — native Unity geometry, driven from C#, not from face indices

Package: `com.unity.probuilder` (≥ 6.1.2 on Unity 6000.5+, installer sets it). Two ways to use it:

| Way | When | Reliability |
|---|---|---|
| **`GDS.PB` / blueprint `mode: probuilder`** ([level-builder.md](level-builder.md)) | rooms, corridors, buildings, towers, stairs, arches, collision shells | deterministic: one call, colliders + static flags + material set |
| `manage_probuilder` (CoplayDev MCP) | small touch-ups: `bevel_edges`, `set_face_material`, `subdivide`, `extrude_faces` on one mesh; `validate_mesh` / `repair_mesh` | face indices change after every edit → read `get_mesh_info include=faces` first, one edit per call |

Never build a room by chaining `create_shape` + `delete_faces` + `extrude_faces` by index. That is how the agent gives up and drops a cube.

## Why this instead of Blender walls

- Snap is Unity grid. Geometra `1m / 2m / 4m` is exact. No FBX axis flip.
- Colliders come with the mesh (`GDS.PB.Finish` adds MeshCollider). No import scale `0.01`.
- UV unwrap for lightmaps is built in.
- Zero export. The shell CAN stay as the final collision + look with a palette material; kits dress on top.

## Recipes

```
// 12 x 8 m hall, 3 m high, door on south segment 1, window north segment 0, stone palette
return GDS.PB.Room(new Vector3(0,0,0), 12, 3, 8, "S:1,N:0:window", "Assets/_Game/Art/Materials/Mat_Palette_1.mat", "Hall");

// two-floor keep with gable roof (blueprint)
{ "name":"Keep","mode":"probuilder","origin":{"x":20,"y":0,"z":0},"cellsX":3,"cellsZ":2,"floors":2,
  "openings":[{"side":"S","index":1,"type":"door"},{"side":"E","index":0,"floor":1,"type":"window"}],
  "roof":"gable","material":"Assets/_Game/Art/Materials/Mat_Palette_2.mat" }

// round tower, stairs, arch
GDS.PB.Tower(new Vector3(30,0,0), 3f, 9f, 8, mat);
GDS.PB.Stairs(new Vector3(4,0,0), 2f, 3f, 4f, 10, 90f, mat);
GDS.PB.Arch(new Vector3(6,0,0), 1.2f, 2.4f, 0.4f, 0f, mat);
```

Doors/windows are legs + lintel/sill boxes (no CSG). Corridors = a room with `openings` on both ends. Multi-room = several blueprints sharing wall lines on the 4 m grid (PLAN.md decides).

## Hard rules

- Every shell gets a palette material (`GDS.LookDev.ApplyPalette`) — grey default is only for greybox.
- After any `manage_probuilder` edit: `validate_mesh`, then `GDS.SceneLint.RunJson()`.
- `set_pivot` is unreliable; the builder never depends on pivots.
- Never export ProBuilder to Blender "to make it pretty". Dress with kits, light with LookDev.
