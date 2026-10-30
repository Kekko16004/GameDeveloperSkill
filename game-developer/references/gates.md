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
12. **Feel regression** ([playtest.md](playtest.md) § Feel in scena reale): any gate touching physics, controller, tuning, colliders or the level scene must carry `feel: {"baseline":"docs/tests/feel-baseline.json","worse":[]}` from the suite run **in the real level**. `worse` not empty → FAIL unless `DECISIONI.md` has the owner's approval for that case. A feel sim in an empty test scene does not count.
13. **Captures**: every screenshot/clip used as evidence for playtest, focus group or store has a `produced:` label; a capture made by a helper that changed game state (timer held, score/tips added, events placed by hand) → FAIL, redo with a real seed or real systems.
14. **Evidence location**: any evidence path under `Temp/` or `Library/` → FAIL (Unity wipes them on close). Move it to `captures/`, `screenshots/` or `docs/`.
15. **Report vs brief** ([workers.md](workers.md) § Contratto): the gate ends with the fixed report; every DO item is in "Fatto" with a path or in "Aperto"; writes outside OWNS only under "Deviazioni"; a "stop sui file" is handled by the parent before the next worker. Mismatch → FAIL, re-run.
16. **DECISIONI**: a gate or report that lists as a problem, or changes, something settled in `DECISIONI.md` → that part is struck; repeated → FAIL.

### Iteration gates (after the slice: waves, owner notes) — [launch-link.md](launch-link.md) §7, [templates/gate.md](../templates/gate.md)

17. **Header**: `python SKILL/scripts/gate_link.py --project PROJECT check docs/gates/NN-*.md` ✅. Missing header, empty `risks`/`owner_try`, screenshot not on disk, a decision key in `closes` → FAIL.
18. **Real mechanic, normal play**: every fix is verified in the real scene in ordinary play, from every side/situation the player meets it (front / side / rear, standing / running, with and without the related perk/option), numbers before → after. Verified only in the reported case → FAIL.
19. **Screenshots and frames looked at**: each one cited with one line on what it shows; a screenshot that contradicts the text (or shows an old version) → FAIL or say so in the gate. An animation counts the same: the worker Reads its frames (first, middle, extreme, last) and writes what it sees; a clip that looks wrong is not done because the numeric checks pass ([art-direction.md](art-direction.md) §5).
20. **Saves**: any Play/exe session that can write saves or prefs has `saves: backup + restore identical` (hash check). Missing → FAIL.
21. **No unrequested builds**; **no test suites** when `DECISIONI.md` says the owner tests himself (compile 0, lint, deterministic checks and the real-scene feel sim stay).
22. **Design changes and attribution**: every difference from the brief is in `design_changes` with `decided_by`; "the owner asked" without a source → FAIL.
23. **Regression loop**: `risks` lists the gameplay risks the gate introduces (harder, slower, more UI, new interactions); the next wave or real test re-checks them.
24. **Orphans**: a gate that redesigns screens, menus, shops, flow or progression has the `design_review.py screens --before` result in the gate: nothing lost its entry point, or it was retired on purpose (`hidden-ok` + source).
25a. **Repro first**: every bug fix has `repro: {before: "FAIL <reason>", after: PASS}` from a test that reproduces it (workers.md iterate-gate 1b); a fix without a failing-then-passing test → FAIL.
25b. **Performance, from the first playable on** (every gate, not only iteration gates, never left to the end; the benchmark also runs at every engine update and the parent reads the number, loop in [optimization.md](optimization.md), Nucleon `ncli bench`): every gate with a playable scene has `perf:` (p95 vs `1000/targetFps`) measured on the real scene with vsync off ([playtest.md](playtest.md) "Budget di performance"), or `perf: skipped: software renderer` with the reason. "Playable" with no frame time in the gate → FAIL.
25. **Hand-off** (when `launch/` exists): after PASS the parent runs `gate_link.py apply-status --write` and `gate_link.py todo --run`; before a wave `gate_link.py since --out docs/design-review/changes-since-wNN.md`.

### Playability (every gate that touches the scene or the controls; found by a real first-person playthrough)

26. **Frames only where the player can go**: a scene gate carries `scene: {"instances":N,"drawCalls":N,"outOfReach":"<what is drawn there and why it is cheap or needed>"}`. Foliage, grass or detail in an unreachable area → FAIL ([level-builder.md](level-builder.md) Rules). Reason: that cost bought nothing the player sees.
27. **Every input really works**: each input of the controls table (GDD verbs, Q4) is tested through the real input path, not by calling the function: the mouse wheel and the number keys must both change the weapon (the active weapon changes, not just an animation), pause opens and closes, and so on. An input the harness cannot produce is an `engine_gap:` in the gate, never silently untested ([playtest.md](playtest.md) Verbi).
28. **First-person view models** (FPS genres): weapon and arms judged in the engine from the game camera, every clip checked at its closest frame for near-plane clipping, the ADS sight picture checked, one- or two-handed chosen per weapon type, visible delayed sway, impacts following the surface ([genres.md](genres.md) FPS hard rules). Blender previews do not count.
29. **Owner hand-off**: before the owner is told a build can be opened, the parent has run the playthrough checklist itself ([playtest.md](playtest.md) "Passeggiata del parent") and `docs/gates/playthrough-NN.md` exists. Workers' passing tests do not stand in for it → no hand-off.

Checkpoint (ogni 10 task, [task-decomposition.md](task-decomposition.md)):

```
phase: checkpoint-3
status: PASS
range: TASK-021..TASK-030
console: 0
tests: {"passed":14,"failed":0}
lint: {"issues":0}
feel: {"baseline":"docs/tests/feel-baseline.json","worse":[]}
scripts: {"todo":0,"notImplemented":0,"missingFromRegistry":0}
scene_map: docs/scene-map.md
commit: 3f2a91c
```

Gate with feel and report (any phase touching the core verb):

```
phase: systems
status: PASS
lint: {"issues":0}
tests: {"passed":22,"failed":0}
feel: {"baseline":"docs/tests/feel-baseline.json","cases":6,"worse":[]}
captures: captures/2026-10-17/manifest.json   # produced: seed:42, hud:none
report: (fixed block of templates/worker-report.md)
```

Template empty: `status: FAIL` + `missing:`.
