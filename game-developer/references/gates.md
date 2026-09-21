# Gate files

Path: `<game>/docs/gates/<id>.md`

```
phase: blender-prop_crate
status: PASS
evidence:
  - screenshots/blender-prop_crate.png
  - art/exports/prop_crate.glb
polycount: 1240
bytes: 48211
```

Parent after each worker:

1. File exists?
2. `status: PASS`?
3. Every evidence path exists on disk?
4. For kit-dress: require `screenshots/030-import-$ID.png` + prefab + ledger `source: kenney|kaykit|quaternius-standard`. Read the PNG. Floating mesh / no collider → FAIL retry.
5. For blender/polypizza: ledger `source: polypizza`. Require `blender-$ID-2-import.png` + finale `blender-$ID.png` + GLB. Read both. Cube / empty / bpy-modelled mesh → FAIL retry.
6. For playtest: Read the Play Mode PNG. If no HUD text / no menu / unreadable goal → FAIL. Primitives-only with empty Art folder → FAIL.

Template empty: `status: FAIL` + `missing:`.
