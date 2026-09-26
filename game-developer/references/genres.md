# Genres — recipes so "any game" starts from a known shape

Task-decomposition picks ONE row from GDD Q1-Q5 + Q9 and writes it into `GAME_CONTEXT.md` (`genre:`). The row decides camera, controller, world source, core systems and the tests the systems worker must write. Unknown genre → the closest row + the difference as extra tasks.

| genre | camera (Cinemachine) | controller | world | core systems (one task + one test each) | extra skills |
|---|---|---|---|---|---|
| **3D platformer** | third-person follow, 6-8 m | CharacterController, coyote time 0.1 s, jump buffer 0.1 s, variable jump | blueprints `mode: probuilder` platforms + `terrain` backdrop | checkpoints, collectibles, moving platforms, death plane | — |
| **Action-adventure / soulslike-lite** | third-person orbit + lock-on | CC + dodge roll (i-frames) + stamina | `terrain` + `flat.village` or `dungeon` | melee combo (anim events), enemy FSM chase/attack, health/stamina, hit-stop | initialize-ai-navigation |
| **FPS / shooter** | first-person, FOV 75-90 | CC + sprint/crouch, hitscan or projectile | `dungeon` (kit) or blueprints arena | weapon (fire rate, ammo, reload), enemy AI with NavMesh + cover points, damage numbers | initialize-ai-navigation, physics diagnosis |
| **Survival / crafting** | first- or third-person | CC + interact raycast | `terrain`/`island` + scatter resources | gather → inventory (grid) → craft recipes (ScriptableObjects) → build placement, day/night, hunger | ui-uitk (inventory) |
| **Voxel sandbox** | first-person | CC on `VoxelWorld` | `voxel` | dig/place (VoxelInteractor), hotbar UI, block drops, save chunks diff | — |
| **Top-down / twin-stick / ARPG** | top-down 50-60°, 18-25 m | Rigidbody or CC, aim to mouse on ground plane | `dungeon` or `cave`, `layout.json` for spawns | waves/spawner, loot table, XP/level-up choice, projectile pooling | initialize-ai-navigation |
| **Roguelite** | top-down or third-person | as above | `dungeon` with new `seed` per run | run state, room clear → door unlock, upgrades draft, meta-currency | — |
| **Racing / arcade driving** | chase cam with speed FOV | WheelCollider or arcade raycast car | `terrain` + spline road (flat strip) or blueprint track | lap/checkpoint order, timer, boost, AI racers on waypoints | — |
| **Puzzle / physics** | fixed or orbit | click/drag or CC | blueprints rooms | puzzle state machine, pressure plates/triggers, undo, level select | physics diagnosis |
| **Horror / exploration** | first-person, head bob low | CC slow, flashlight | blueprints interior + `cave` | interact/inspect, doors/keys, enemy stalker (NavMesh + sight/hearing), sanity/audio cues | audio-setup-mixers |
| **Tower defense / strategy-lite** | top-down RTS cam (pan/zoom) | none (cursor) | `terrain` flat + blueprint path | grid placement, path waves, tower targeting, economy | — |
| **2D platformer / pixel** | 2D orthographic, pixel perfect | Rigidbody2D + custom collision | Tilemap (RuleTiles) | same as 3D platformer in 2D | 2d-pixel-perfect, tilemap-*, sprite-editor |
| **Multiplayer (any above)** | — | Netcode for GameObjects | same | lobby/session, spawn, sync transform/anim, host migration off | setup-multiplayer-services |

## Controller rules

- Always the Input System (`Move`, `Look`, `Jump`, `Interact`, `Pause` + genre verbs). Never `Input.GetAxis`.
- Feel numbers live in a ScriptableObject (`PlayerTuning.asset`) so juice/playtest can tune without code changes.
- Every verb has a test (`Verb_DoesX`) run with `unity command run_tests` (or `unity test <project> --mode EditMode`).

## Scope guard

Vertical slice = 1 world + 1 enemy type (or obstacle) + 1 objective + menu/HUD/pause/gameover. The genre row lists what the slice needs, not the full game.
