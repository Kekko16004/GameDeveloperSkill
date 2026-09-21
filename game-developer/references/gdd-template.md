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

## Tool stack (whole game)
levels: probuilder
family: kenney          # kenney | kaykit | quaternius-standard — pick ONE
fill: polypizza         # missing props via Blender MCP native tools
blender: import-sanitize-only
ui: real-world-design
audio: kenney-cc0
blender-mcp: uvx-stdio-9876
session-mode: hard-stop # hard-stop (consigliato su Antigravity monochat) | continuous (su Claude Code/Kilo con subagents)
asset-strategy: agent-full # agent-full | user-provided | hybrid
forbid: bpy-modelling, sloyd, hunyuan, trellis, meshy, blockbench, dust3d

## Art
genre-kit: dungeon|medieval|scifi|city|pirate|interior|prototype
production: kits          # kits | kits+polypizza | voxel | user-provided
manifest: art/ASSET_MANIFEST.md # Generato obbligatoriamente se asset-strategy != agent-full

## Assets (slice)
| id | role | source |
|---|---|---|
| player | pawn | kaykit-adventurers OR kenney |
| ground | floor | probuilder then kenney tile |
| wall_a | env | kenney modular |
| crate | prop | kenney (NOT blender) |

## Out of scope
...
```
