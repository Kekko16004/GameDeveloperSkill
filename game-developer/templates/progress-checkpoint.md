# Progress — systems:TASK-034

> Copy to `<game>/docs/progress/<PHASE>-<TASK-id>.md`. The worker writes it in its first minute and updates it after every step (not at the end). When it is (re)launched it reads this file FIRST and continues from "Prossimo passo"; it never restarts done steps. The parent deletes nothing: the file stays as the trail of the task.

worker: systems
task: TASK-034
brief: Interact verb (IInteractable + DoorInteractable + raycast + HUD prompt + test)
status: in-progress        # in-progress | blocked | done
started: 2026-10-17 14:20
updated: 2026-10-17 14:41
unity-lock: released       # held | released (if held when the worker dies, the parent removes Temp/gds-unity.lock)

## Fatto
- [x] 14:24 `Scripts/Interaction/IInteractable.cs` written
- [x] 14:31 `Scripts/Interaction/DoorInteractable.cs` written (slerp 0.25 s)
- [x] 14:38 recompile → console 0 (output in `docs/progress/systems-TASK-034.log`)

## Prossimo passo
- Add the raycast to `PlayerController.cs` (owned) at `Update()`, then `Tests/EditMode/InteractTests.cs`.

## Restano
- HUD prompt `[E] Apri` via string key `hud.prompt.open`
- run_tests → gate `docs/gates/10-systems.md`

## File toccati
| file | owned | sha1 when read | changed |
|---|---|---|---|
| Assets/_Game/Scripts/Interaction/IInteractable.cs | yes | new | created |
| Assets/_Game/Scripts/Interaction/DoorInteractable.cs | yes | new | created |
| Assets/_Game/Scripts/Player/PlayerController.cs | yes | 3f9a1c… | not yet |

## Bloccanti / domande
- none
