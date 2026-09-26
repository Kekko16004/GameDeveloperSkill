# Unity editor loop

Bridge: **Unity CLI + Pipeline** ([unity-cli.md](unity-cli.md)). CoplayDev MCP only where unity-cli.md says so. Examples below use `unity command`; with CoplayDev the same GDS call goes through `execute_code: return GDS.X.Y(...);`.

## Preflight

`unity status` → `ready`, `unity command gds_ping` → JSON. Compile errors = Safe Mode: fix the C#, restart, never edit YAML.

## Greybox scene

```
unity command create_scene --path Assets/_Game/Scenes/Slice.unity
```

Ground: its **top face is Y = 0** (cube `[size,0.2,size]` at `y=-0.1`, or a `GDS.World` terrain / dungeon). A cube *at* y=0 buries every prop by half its height — the historical cause of "leggermente sottoterra". Rooms via `GDS.PB.Room` / blueprints, never wall by wall. Player: CharacterController + camera per GDD (Cinemachine).

**Input System** only: actions `Move`, `Look`, `Jump`, `Interact`, `Pause` (+ genre verbs from [genres.md](genres.md)). Never `Input.GetAxis`.

## Scripts

1. `unity command create_script` (or write the file under `Assets/_Game/Scripts/`)
2. `unity command recompile` → poll `recompile_status` until `completed`
3. `unity command console` → 0 errors
4. `unity command attach_script` / `add_component`

## Tests — one per verb

Tests in `Assets/_Game/Scripts/Tests/` (EditMode or PlayMode assembly), named `Verb_DoesX` (`Move_ChangesPosition`, `Jump_LeavesGround`, `Interact_OpensDoor`, `Pause_StopsTime`).

```
unity command run_tests        # then test_status
unity test <P> --mode EditMode --format json    # exit 8 = failed tests, other non-zero = infrastructure
```

Red test = fix before art. No "will test later".

## Play Mode probe

1. `unity command gds_shot --out screenshots/<n>-game.png` (Main Camera)
2. `unity command editor_play` → wait 2 s → `unity command capture_game_view` (or `screenshot --output`)
3. Input: PlayMode test that injects input (preferred, deterministic) or TerminalMCP `input` on the Game window (fallback)
4. `unity command console` errors → `editor_stop`

Results in `docs/playtest.md`.

## GDS layer

```
unity command gds_build --blueprint art/blueprints/house_a.json
unity command gds_world --spec art/world/overworld.json
unity command gds_lint --autofix true      # then again without autofix → issues 0
unity command gds_lookdev --preset stylized-day
```

## Import art

Copy `art/exports/*.glb` → `Assets/_Game/Art/Exports/`. Scale 1, no cameras/lights from the file. Reference the file in a blueprint `props` row (or world `scatter`) and rebuild — the builder adds the collider and snaps it. Prefabs only for runtime spawns.

## Camera & post

Cinemachine follow / third-person / top-down from the GDD; `CinemachineImpulseSource` for shake. Sun, fog, sky, Global Volume (ACES, bloom, color, vignette), SSAO, URP quality: `gds_lookdev`. Fine-tune with `unity command set_lighting_settings` / `set_quality_settings` or `eval`, never the YAML.

## ProBuilder

`GDS.PB.Room / Tower / Stairs / Arch` or blueprint `mode: probuilder` ([probuilder-levels.md](probuilder-levels.md)). No face-by-face editing for rooms.

## VFX

`unity command gds_vfx` creates dust/hit/pickup/torch/smoke/sparkle prefabs; Cartoon FX Free if the GDD allows. VFX Graph only for massive GPU effects, driven from C# (`SetFloat`, `SendEvent`).

## Console

After every script or scene change: `unity command console` → 0 errors to continue.
