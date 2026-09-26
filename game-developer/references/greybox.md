# Greybox

Art comes later. First: a level that already **plays**, built the same way the final level will be built (blueprints), so level-build replaces it in place instead of leaving cubes behind. Do not call the slice done here. Do not open Blender. Do not fetch kits yet. Do not build Main Menu.

1. Create scene `Assets/_Game/Scenes/Slice.unity` (fresh, avoid default-object name clashes)
2. Ground: Unity Cube named `Ground`, scale `[size, 0.2, size]`, position `[0, -0.1, 0]` → **top face at Y = 0** (never a cube at y=0: that buries everything 10 cm). Keep its BoxCollider. Size from GDD (~20–40 m).
3. Rooms / buildings: read `art/blueprints/PLAN.md` (from task-decomposition). For each entry, either
   - `unity command eval`: `return GDS.PB.Room(new Vector3(x,0,z), w, 3, d, "S:1", null, "<name>");` (ProBuilder shell, door gap, colliders), or
   - write `art/blueprints/<name>.json` with `"mode": "primitives"` (or `"probuilder"`) and `return GDS.LevelBuilder.BuildFromFile(...)`.
   Same `name` as the final blueprint → level-build rebuilds in place later. Never place walls one by one.
4. Player at (0, 1, 0), CharacterController (height 1.8, radius 0.4), Input System Move
5. Camera from GDD (third: behind; top-down: orthographic height) via `manage_camera`
6. Win trigger (empty box + flag) even if art is a cube
7. Write `PlayerController` + `PlayerMovementTests`
8. Run tests
9. Lint: `return GDS.SceneLint.RunJson(autoFix:true);` then `return GDS.SceneLint.RunJson();` → `issues: 0`
10. Play Mode screenshot `screenshots/010-greybox-play.png`
11. `read_console` clean

Do not model in Blender. Do not download kits until this gate is green.
