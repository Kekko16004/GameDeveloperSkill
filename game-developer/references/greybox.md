# Greybox

Art comes later. First: a level made of ProBuilder (or primitives) that already **plays**.
This phase MAY use cubes. Later **kit-dress** workers REPLACE visible cubes with Kenney/KayKit pieces. Do not call the slice done here. Do not open Blender. Do not fetch kits yet. Do not build Main Menu.

1. Create scene `Assets/_Game/Scenes/Slice.unity` (fresh, avoid default-object name clashes)
2. `manage_probuilder` ping. If ok: Plane/Cube ground so the walk surface is `Y=0`, walls on 4m module, door gap 1.0×2.2. See [probuilder-levels.md](probuilder-levels.md). If ping fails: Unity cubes.
3. Ground scale so the slice fits (~20–40 m)
4. Player at (0, 1, 0), CharacterController, Input System Move
5. Camera from GDD (third: behind; top-down: orthographic height)
6. One blocking volume (wall) so movement is visible
7. Win trigger (empty box + flag) even if art is a cube
8. Write `PlayerController` + `PlayerMovementTests`
9. Run tests
10. Play Mode screenshot `screenshots/010-greybox-play.png`
11. `read_console` clean

Do not model in Blender. Do not download kits until this gate is green.
