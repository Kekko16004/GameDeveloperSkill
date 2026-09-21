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
4. For blender: require `blender-$ID-1-blockout.png` through `-4-mats.png` PLUS finale. Read step 2 and finale. Cube / empty / one dump PNG → FAIL retry.
5. For playtest: Read the Play Mode PNG. If no HUD text / no menu / unreadable goal → FAIL.

Template empty: `status: FAIL` + `missing:`.
