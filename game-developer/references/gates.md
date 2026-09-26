# Gate files

Path: `<game>/docs/gates/<id>.md`

```
phase: level-build
status: PASS
blueprint: art/blueprints/house_a.json
build: {"status":"PASS","pieces":38,"props":6,"scattered":25,"missingRoles":[],"warnings":[]}
lint: {"issues":0,"buried":0,"floating":0,"noGround":0,"noCollider":0,"pinkMaterial":0,"nonUrpShader":0}
evidence:
  - screenshots/020-build-house_a.png
```

Hero asset:

```
phase: hero-prop_relic
status: PASS
source: polypizza|polyhaven|sketchfab-cc0|meshy|tripo|hyper3d|local-modly
credits_used: 0
evidence:
  - screenshots/blender-prop_relic.png
  - art/exports/prop_relic.glb
polycount: 1240
bytes: 48211
lint: {"issues":0}
```

Parent after each worker:

1. File exists?
2. `status: PASS`?
3. Every evidence path exists on disk?
4. **Any phase that touches the scene** (greybox, world-gen, level-build, hero-asset, import-art, lookdev, characters, juice, playtest): a `lint:` line with `"issues":0` from `gds_lint` (`GDS.SceneLint.RunJson()`) is mandatory. Missing or > 0 → FAIL retry (`gds_lint --autofix true` first). The PNG is read only for style coherence, never to judge placement.
5. For level-build: `build:` JSON with `missingRoles: []` + `art/blueprints/<name>.json` on disk + `docs/lint/build-<name>.json`. Cubes visible in the PNG after a `mode: kit` build → FAIL.
6. For hero-asset: ledger `source:` one of the allowed tiers (gen3d only if GDD Q20 allows and `credits_used` ≤ budget). Require `blender-$ID.png` + GLB > 15 KB. Cube / empty / bpy-modelled mesh → FAIL retry.
7. For lookdev: `applied` must contain `volume` and `camera-post`; `Assets/_Game/Settings/LookDev_<preset>.asset` exists; PNG shows fog/bloom/shadows (not a flat grey scene).
8. For characters: `BuildController` JSON `status: PASS`, prefab path, `screenshots/050-characters.png` with the character in walk.
9. For world-gen: `docs/lint/world-<name>.json` `status: PASS`, `warnings: []`, `art/world/<name>.json` on disk, review PNGs.
10. For art-review: 7 scores with evidence, average ≥ 4 and none < 3, or a fix list naming spec files. Scores without the PNG paths → FAIL.
11. For playtest: Read the Play Mode PNG. If no HUD text / no menu / unreadable goal → FAIL. Unity primitives visible or no Volume → FAIL.

Template empty: `status: FAIL` + `missing:`.
