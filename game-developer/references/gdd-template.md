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
levels: blueprint+gds   # blueprint JSON → GDS.LevelBuilder (kit) / GDS.PB (ProBuilder shells)
family: kenney          # kenney | kaykit | quaternius-standard | synty-starter (needs assetStore: yes) — pick ONE
fill: polypizza         # hero props: polypizza → polyhaven-models → sketchfab-cc0 → gen3d tier
blender: import-sanitize-only
ui: real-world-design
audio: kenney-cc0
blender-mcp: uvx-stdio-9876
session-mode: continuous # continuous (Claude Code / Kilo con subagents) | hard-stop (Antigravity monochat)
asset-strategy: agent-full # agent-full | user-provided | hybrid
forbid: bpy-modelling, sloyd, blockbench, dust3d, wall-by-wall placement

## Hardware, budget, look (Q16–Q19)
gpu: GTX 1660 Super       # from the user
vram: 6                   # GB
gen3d: none               # none | local (Modly, ≥8 GB) | meshy | tripo | hyper3d
gen3dBudgetCredits: 0     # only for meshy/tripo
gen3dMaxAssets: 0         # hero props allowed through gen3d (default 5 when a tier is on)
assetStore: no            # yes → Synty Starter / Cartoon FX Free / Unity Particle Pack allowed
lookdev: stylized-day     # stylized-day | stylized-sunset | dungeon-torch | night-moon | pastel-bright | scifi-cold
toon: no                  # Delt06 URP toon shader package
outline: no               # CristianQiu URP outline package
hdri: none                # Poly Haven HDRI id for the skybox, or none

## Art
genre-kit: dungeon|medieval|scifi|city|pirate|interior|prototype
production: kits          # kits | kits+polypizza | voxel | user-provided
manifest: art/ASSET_MANIFEST.md # Generato obbligatoriamente se asset-strategy != agent-full

## Assets (slice)
| id | role | source |
|---|---|---|
| char_player | pawn | kaykit-adventurers OR kenney-animated (GDS.Characters) |
| BP-house_a | blueprint | kenney castle roles floor/wall/wallDoor/roof + props |
| BP-courtyard | blueprint | scatter kenney nature |
| prop_relic | hero | polypizza → gen3d tier if none |

## Out of scope
...
```
