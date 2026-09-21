# Juice (after verbs work)

Do not add juice before movement tests are green. Details: [vfx.md](vfx.md), [audio-pipeline.md](audio-pipeline.md).

- `GDS.VFX.CreateAll()` → dust on footsteps, pickup on interact, hit on damage, sparkle on win, torch on lamps (`AttachTorches`)
- CC0 SFX (Kenney) on jump/interact/win required if those verbs exist; footsteps via `AudioManager`
- Hit-stop 2–4 frames on damage (`Time.timeScale = 0.05f` for 0.05 s real time)
- Camera shake tiny (Cinemachine impulse via `manage_camera`), never earthquake
- UI click sound on every button (`AudioManager.PlayUI`)
- Pause already a verb: Esc → timeScale 0 + pause UI

Keep it cheap. ≤ 60 particles per effect. No music bed required for the slice (ambient loop optional).
