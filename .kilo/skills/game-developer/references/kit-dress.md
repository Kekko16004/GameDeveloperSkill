# Kit-dress → superseded by level-build (blueprints)

The "one kit piece per worker" phase is retired: a house needs 30–60 pieces and never got finished, and hand placement buried props. It is replaced by:

- **level-build**: one blueprint JSON per building/area → `GDS.LevelBuilder.BuildFromFile` assembles shell + interior `props` + outdoor `scatter` in one call, pivot-agnostic, colliders included. See [level-builder.md](level-builder.md).
- **SceneLint**: `issues: 0` gate instead of "the parent reads the PNG". See [scene-lint.md](scene-lint.md).

## Single extra prop after a build (the only manual case)

Add a row to the blueprint's `props` and rebuild (same `name` → replaced in place):

```json
{ "file": "barrel.fbx", "name": "prop_barrel_4", "x": 2.5, "z": 1.0, "rotY": 30, "snap": true, "collider": "box" }
```

Or, for a one-off outside any blueprint: `manage_gameobject` create from prefab, then `return GDS.SceneLint.SnapToGround("prop_barrel_4");` and `GDS.SceneLint.RunJson()`.

## Anti-slop (still valid)

- One Kenney **or** one KayKit **or** one Quaternius **or** Synty pack family per slice.
- One import scale per pack folder (`GDS.KitCatalog.SetImportScale`), never per piece.
- Do not generate a "better" crate in Blender when the kit has `crate`.
- Do not drop a photoreal Poly Haven scan next to Kenney without flattening its material to the palette.
