# ProBuilder levels — native Unity geometry

Package: `com.unity.probuilder` (installer already lists it). Tool: `manage_probuilder` on CoplayDev unity-mcp.

Use this for **rooms, corridors, stairs, ramps, platforms, blocking**. Do not model crates or characters here.

## Why this instead of Blender walls

- Snap is Unity grid. Geometra `1m / 2m / 4m` is exact. No FBX axis flip.
- Colliders come with the mesh. No import scale `0.01`.
- UV unwrap for lightmaps is built in.
- Zero export. The greybox CAN stay as the final collision shell; kits only dress the look.

## Greybox protocol (worker greybox)

After creating `Slice.unity`:

1. `manage_probuilder` ping. If missing: `manage_packages add_package package=com.unity.probuilder`, wait compile.
2. Ground: `create_shape` Plane or Cube, size `[tile*n, 0.2, tile*n]`, position `[0, -0.1, 0]` so top face is `Y=0`.
3. Walls: cubes `size [length, 3.0, 0.2]` on the 4m module. Door gap = `1.0 x 2.2`.
4. One stair if the GDD has verticality: `create_shape` Stair.
5. `center_pivot` or keep corner at min XZ. Freeze transform if you moved after create.
6. Player still uses CharacterController on a separate object. Do not ProBuilder-ize the player.
7. Screenshot `screenshots/010-greybox-play.png`.

Primitives (Unity Cube) are still allowed if ProBuilder ping fails. Prefer ProBuilder.

## Dressing (worker kit-dress)

ProBuilder stays as **collision + occlusion**. Kit tiles (Kenney floor/wall) are children snapped to the same grid. If a kit wall already has thickness, hide or delete the ProBuilder face behind it so you do not double-draw.

## Hard rules

- Face indices change after every edit. `get_mesh_info include=faces` before extrude/delete.
- `set_pivot` is unreliable; use `center_pivot` or Transform.
- After mesh edits: `validate_mesh`, then screenshot.
- Never export ProBuilder to Blender "to make it pretty". Dress with kits.
