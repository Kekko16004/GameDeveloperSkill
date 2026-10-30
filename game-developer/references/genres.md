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

## FPS / shooter on Nucleon (engine features, not Lua re-implementations)

The engine has the first-person kit; the systems worker writes only the game's rules on top ([nucleon/first-person.md](nucleon/first-person.md), engine doc `docs/engine/FIRST_PERSON.md`):

| piece | use | never |
|---|---|---|
| look | `GetLookDelta()` in the pawn's `OnTick` (raw mouse, stick curve included), `SetMouseSensitivity` with the CS number, `SetLookSettings` on the options page | `GetActionVector("Look") * lookSpeed` (what the template pawn still does), own sensitivity maths |
| movement | `SetCharacterMovement{acceleration = 5.5, airAcceleration = 12, ...}` (Source ground and air strafing), `SetCharacterCrouching`, `SetCharacterWalking`, `MoveCharacter` with the wished speed (CS 250 u/s = 6.35 m/s) | own acceleration / friction / crouch code |
| arms + weapon | an actor as view model: `SetEntityViewModel(arms, true, 60)`, `SetViewModelOffset(arms, pos, rot)` every frame for bob, sway, recoil, ADS, `SetViewModelFov` | the weapon parented to the camera by hand |
| hitscan and hit maps | `Raycast` / `RaycastAll` (penetration) / `SphereCast*` with `{ignore = {pawn, arms}, layers = ...}`; damage multiplier by `hit.component` (the zone: Head / Torso / Legs collision components of the target actor), impact fx and sound by `hit.surface` (rule 6 below), ragdoll force by `hit.bone` | distance or name guessing for the zone, one ray per body part |
| teams, kills, respawn, bots | `nc.framework` natives (teams, score, kills / deaths, `SetRespawnRules`), `nc.abilities` (health, ammo, cooldown as attributes / effects), `nc.ai` (perception, State Trees) | a bespoke state machine, unless the module fails its first GDS test: then log `engine_issues:` and fall back |
| HUD, menus | NUI web page (`UI/index.html`: crosshair, ammo, health in `#hud`, `SendNUIMessage` from the weapon script) | RmlUi for a new game |

Tests of the row: a GDS test shoots the target actor's head and torso from the pawn (`t.check(hit.component == "Head")`), one for the view model offset (`GetViewModelSettings`), one for crouch height and ground speed; then `lint --play` and a shot of the view model.

### FPS hard rules (from a real first-person playthrough; each one fails the gate, [gates.md](gates.md) item 28)

1. **View model judged in the engine**, from the game camera, never from Blender previews (they hide clipping, scale and hand placement).
2. **Every clip checked at its closest frame** (draw, fire peak, reload, inspect) with a shot from the game camera, for near-plane clipping of weapon or arms. Reason: a clip that looks fine at rest cuts through the camera at its peak.
3. **ADS sight picture checked**: one shot per weapon, sights or optic on the crosshair line, nothing covering the target, FOV change sensible.
4. **One-handed or two-handed on purpose per weapon type** (pistol, SMG, rifle, shotgun...), written in the weapon spec; the hands then follow it (no free hand floating off the weapon).
5. **Delayed sway when turning**: a spring-damper driven by the look delta (frame-rate independent: scale by `dt`, or substep), not a weapon nailed to the screen centre. It must be **visible** in a shot taken mid-turn and settle without wobble when the look stops. GDS test: apply a look delta, the offset leaves rest by a stated minimum and returns within N s, the same at two frame rates.
6. **Impacts follow the material** (`hit.surface`): no ricochet streaks on concrete or stone (dust and chips), sparks only on metal; **tracers end at the hit point** (at max range on a miss), never through the surface.

## Controller rules

- Always the Input System (`Move`, `Look`, `Jump`, `Interact`, `Pause` + genre verbs). Never `Input.GetAxis`.
- Feel numbers live in a ScriptableObject (`PlayerTuning.asset`) so juice/playtest can tune without code changes.
- Every verb has a test (`Verb_DoesX`) run with `unity command run_tests` (or `unity test <project> --mode EditMode`).

## Scope guard

Vertical slice = 1 world + 1 enemy type (or obstacle) + 1 objective + menu/HUD/pause/gameover. The genre row lists what the slice needs, not the full game.
