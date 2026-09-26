# Art direction — reference board + scored screenshot review

Gates prove the scene is *correct* (lint 0, tests green). This loop proves it looks *good*. It runs as `PHASE art-review` after lookdev, after juice and before the slice. Worker = fresh eyes: it only sees the board, the rubric and the PNGs.

## 1. Reference board (once, in task-decomposition)

`art/reference/BOARD.md` + 4-8 images in `art/reference/`:

- 2-3 shots of the named reference games from GDD Q1 (web image search, store pages, press kits). Save the file, note the URL.
- 1 palette strip (GDD hex) and 1 lighting reference for the lookdev preset.
- One line per image: *what to copy* (e.g. "silhouette density of trees on the horizon", "warm key + cold fill", "outline weight 2 px").
- No image generation required (zero cost). If the user gives images, they win.

## 2. Shots (deterministic)

```
unity command gds_sheet --prefix screenshots/review/<phase>
```

→ `game`, `aerial`, `orbit1`, `orbit5`, `hero` PNGs from the real render (URP post included). Unreal: `gds_ue.shot` + PIE screenshot toolset.

## 3. Rubric (score 1-5, write the evidence)

| # | Criterion | 5 = | 1 = |
|---|---|---|---|
| R1 | Readability | objective/path obvious in the game shot in 2 s | cannot tell where to go |
| R2 | Silhouette & scale | varied heights, player scale right (door 2.1 m) | flat field of same-size objects |
| R3 | Palette coherence | matches GDD palette ±, one accent colour | default grey / rainbow |
| R4 | Lighting & mood | key/fill/rim, shadows, fog depth match the board | flat, black or blown out |
| R5 | Density & composition | foreground/mid/background layers, clusters + negative space | empty plane or uniform noise |
| R6 | Style consistency | one family, one shading model (styles.md row) | mixed kits, PBR next to flat |
| R7 | Polish | no z-fighting, seams, floating/buried props, pink, stretched textures | visible defects |

**PASS = every criterion ≥ 3 and average ≥ 4.** Otherwise write a fix list.

## 4. Fix list → spec, never the scene

Each fix names the file and the change, so the next worker rebuilds deterministically:

```
R5 2/5 terrain.scatter tree_pineRoundA count 250→500, clusters 0.5→0.65 (art/world/overworld.json)
R3 2/5 pines teal vs GDD greens: gds_recolor kit nature leafsDark #3D7A3A, leafsGreen #5E9E3A
R4 2/5 lookdev stylized-day → stylized-sunset; add GDS.VFX.AttachTorches("lantern")
R2 3/5 blueprint house_a floors 1→2, add attach lanterns ×2 (art/blueprints/house_a.json)
```

The parent re-runs the owning phase(s) with the fix list, then art-review again. Max 2 loops, then report the scores to the user honestly.

## Gate

`docs/gates/15-art-review.md`: board path, PNG list, the 7 scores with one-line evidence each, average, PASS/FAIL, fix list.
