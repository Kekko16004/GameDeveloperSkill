# Greybox

Art comes later. First: a level made of primitives that already **plays**.
This phase MAY use cubes. Later Blender workers REPLACE visible cubes. Do not call the slice done here. Do not open Blender. Do not build Main Menu.

1. Create scene `Assets/_Game/Scenes/Slice.unity` (fresh, avoid default-object name clashes)
2. Ground at y=0, scale so the slice fits (~20–40 m)
3. Player at (0, 1, 0), CharacterController, Input System Move
4. Camera from GDD (third: behind; top-down: orthographic height)
5. One blocking volume (wall) so movement is visible
6. Win trigger (empty box + flag) even if art is a cube
7. Write `PlayerController` + `PlayerMovementTests`
8. Run tests
9. Play Mode screenshot `screenshots/010-greybox-play.png`
10. `read_console` clean

Unity: ProBuilder optional; cubes are enough. Godot: `CharacterBody3D` + `MeshInstance3D`.

Do not model in Blender until this gate is green.
