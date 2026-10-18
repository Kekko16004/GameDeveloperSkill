# Report — <PHASE>:<TASK-id>

> Fixed format: the worker's final message IS this block (also saved as the gate's last section). The parent compares it with the brief: an item of the brief missing from "Fatto" or "Aperto", work outside the DO fence not listed under "Deviazioni", or a "Fatto" item without an evidence path = FAIL, re-run with `GATE ROSSO:` + the mismatch.

status: PASS | FAIL | PARTIAL
brief: <one line copied from the prompt>
gate: docs/gates/<id>.md
progress: docs/progress/<PHASE>-<TASK-id>.md

## Fatto (one line per brief item, each with evidence on disk)
| # | brief item | result | evidence |
|---|---|---|---|
| 1 | <item> | done | `docs/lint/build-x.json`, `screenshots/020-build-x.png` |
| 2 | <item> | done | test `Interact_OpensDoor` green, job `a1b2c3` |

## Deviazioni (anything not exactly as briefed, or outside DO; "none" if none)
- none

## Scelte di design (any design choice that differs from the brief; "none" if none)
| what | why | decided_by |
|---|---|---|
| <e.g. warning at 40 % instead of 35 %> | <it fired too late in the timed run> | implementer |
`decided_by: owner (<source: brief date / chat date / D-NNN>)` only when the source exists. Never attribute a choice to the owner without it.

## Proposte (optional: "Riapre la decisione: D-NNN — prove — proposta"; never implemented here)
- none

## Aperto (brief items not done, with the reason and what is needed)
- none

## File cambiati (every file written; owned = listed in OWNS)
| file | owned | action |
|---|---|---|
| Assets/_Game/Scripts/Interaction/DoorInteractable.cs | yes | created |

## Stop sui file (files it did NOT write because not owned or changed since read)
- none

## Numeri (JSON from the deterministic calls, pasted, not described)
lint: {"issues":0}
tests: {"passed":14,"failed":0}
feel: {"baseline":"docs/tests/feel-baseline.json","worse":[]}
