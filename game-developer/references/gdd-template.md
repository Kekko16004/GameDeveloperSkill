# GDD template

Write this file at `<game-root>/GDD.md`.

```markdown
---
status: draft
genre: action-adventure   # row of genres.md
engine: unity             # Q0, the user's choice: unity | nucleon | unreal | godot (engines.md)
style: lowpoly            # lowpoly | toon | stylized | voxel | realistic | 2d-pixel (styles.md)
world: terrain            # terrain | island | village | city | dungeon | cave | interior | scifi | voxel | arena | 2d
worldSize: medium         # small 100 m | medium 300 m | large 500 m+
landmark: ""              # one thing the player navigates by
camera: third
platform: pc              # pc | pc+webgl | pc+mobile
targetFps: 60
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
ui: designer
ui-route: direct          # Q14: concept | direct | both (concept = immagini per TUTTE le schermate, scelta in Variant Studio solo tra immagini, poi replica HTML della scelta; per-ruolo = un round per ruolo con 3-4 immagini)
audio: kenney-cc0
blender-mcp: uvx-stdio-9876
parallel: 6               # Q18: max workers at once (editor work is always one driver, engines.md lock)
asset-strategy: agent-full # agent-full | user-provided | hybrid
forbid: bpy-modelling, sloyd, blockbench, dust3d, wall-by-wall placement

## Hardware, budget, look (Q20–Q24)
gpu: GTX 1660 Super       # from the user
vram: 6                   # GB
gen3d: none               # none | local (Modly, ≥8 GB) | meshy | tripo | hyper3d
gen3dBudgetCredits: 0     # only for meshy/tripo
gen3dMaxAssets: 0         # hero props allowed through gen3d (default 5 when a tier is on)
assetStore: no            # yes → Synty Starter / Cartoon FX Free / Unity Particle Pack allowed
lookdev: stylized-day     # stylized-day | stylized-sunset | dungeon-torch | night-moon | pastel-bright | scifi-cold | toon-bright | realistic-overcast | realistic-golden
toon: no                  # Delt06 URP toon shader package
outline: no               # CristianQiu URP outline package
hdri: none                # Poly Haven HDRI id for the skybox, or none
fab: no                   # yes = FabCLI library allowed (realistic)
worldSpec: art/world/<name>.json   # GDS.World spec when world is procedural

## Quality baseline (Q25–Q31, quality-baseline.md)
a11y-essential: remap-kb-pad+restore, text-size, reduced-motion   # always, not asked
ui-essential: fades<=0.5s-skippable, hover+focus-every-button      # always, not asked
a11y: [high-contrast, one-hand, colourblind-symbols, hold-toggle, relax]   # Q25, default all
notifications: short+one-at-a-time   # Q26: short+one-at-a-time | full-sentences
sharedNumbers: single-source+check   # Q27: yes (recommended) | no
onboarding: tutorial<=4+first-hints+progressive   # Q28; tutorialVerb: <verb>; alwaysAvailable: <verb>
languages: [en, it]                  # Q29; CJK/AR → font fallback + RTL tasks
stringTable: Assets/_Game/Localization/strings.csv   # key,context,max_chars,<lang...>
playtestKit: telemetry-csv+fresh-profile+tester-readme   # Q30; return channel: <email|discord|form>
sold: yes                            # will it be sold / on a store page
storeCapture: yes                    # Q31; default yes when sold: yes
feelBaseline: docs/tests/feel-baseline.json   # written by the feel-baseline phase
decisions: DECISIONI.md              # every owner decision, dated; workers read it first

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
