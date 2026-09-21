# VFX — particles, feedback, juice that ships

Order of preference (all $0):

1. `GDS.VFX.CreateAll()` — six stylized prefabs from code (`dust`, `hit`, `pickup`, `torch`+light, `smoke`, `sparkle`) in `Assets/_Game/Prefabs/VFX/`. Zero downloads, URP particle material.
2. **Cartoon FX Remaster Free** (Jean Moreno, Asset Store, free, URP) — 50+ stylized prefabs (explosions, magic, smoke). Requires Unity account; `Window > Package Manager > My Assets` after adding it on the store (TerminalMCP browser if headless). Only if the GDD allowed Asset Store (interview Q17).
3. **Kenney Particle Pack** (CC0 sprites) — `fetch-cc0-kits.ps1 -Genre vfx` → use as `_BaseMap` on the GDS particle material for custom shapes.
4. `manage_vfx` (CoplayDev) for tuning: `create_particle_system`, `set_particle_properties`, `create_trail_renderer`, `create_line_renderer`.
5. VFX Graph only for GPU-heavy effects (rain, embers ×10k). `Assets/_Game/VFX/` + `VisualEffect` component; drive via `SendEvent`.

## Wiring (worker `juice`)

| Event | Effect | Code |
|---|---|---|
| footstep on move | `VFX_dust` at feet every 0.4 s while `Speed > 0.5` | `Instantiate(dust, feet, Quaternion.identity)` + `AudioManager.PlayFootstep()` |
| interact / pickup | `VFX_pickup` at object | + UI prompt flash |
| damage / hit | `VFX_hit` + hit-stop 3 frames (`Time.timeScale = 0.05f` for 0.05 s real time) + Cinemachine impulse | `manage_camera` add `CinemachineImpulseSource` |
| torches / lamps | `GDS.VFX.AttachTorches("torch")` | after level-build |
| win | `VFX_sparkle` burst + UI |  |

Keep every effect ≤ 60 particles. Trail on projectiles via `manage_vfx create_trail_renderer`. No screen-filling explosions in the slice.

Gate `docs/gates/10-juice.md`: VFX prefabs listed, `screenshots/060-juice.png` captured during a hit/pickup (particles visible), console 0 errors.
