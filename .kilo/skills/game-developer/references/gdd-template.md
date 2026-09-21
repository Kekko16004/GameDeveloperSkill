# GDD template

Write this file at `<game-root>/GDD.md`.

```markdown
---
status: draft
engine: unity
style: low-poly
camera: third
scale: 1u=1m
slice: 1 level, 1 enemy, 1 win
phase: gdd
projectPath: ""
verbs:
  - move
  - pause
  - win
---

# <Title>

## Intent
<one liner>

## References
- Game A — why
- Game B — why

## Loop
Every 30s the player: ...

## Win / fail
Win: ...
Fail: ...

## Camera / controls
Camera: ...
Move: WASD
Look: mouse
Pause: Esc
Extras: ...

## Palette
- #......
Material: wood

## UI
- HUD: ...
- Pause: ...

## Assets (slice)
| id | role | source plan |
|---|---|---|
| player | pawn | voxel or blender or kenney |
| ground | floor | primitive then texture |

## Out of scope
...
```
