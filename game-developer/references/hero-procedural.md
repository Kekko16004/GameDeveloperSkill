# Hero props: procedural Blender build (default path, every engine)

A hero prop (a unique object no kit has: a medal, a clock, a statue, a weapon, a sign, a machine) is **built by a deterministic
Python script run by headless Blender**, not by MCP clicks, not downloaded, not generated. The owner approved this path on
2026-10-24 after two tests (an airborne medal: shield, parachute, brick crate; a Louis XV bracket clock: violin case in painted
red lacquer, rococo ormolu, enamel dial, console): both built from one reference picture in minutes, imported and placed in
Nucleon with `ncli`. Libraries (Poly Pizza / Poly Haven / Sketchfab) and gen3d are now the fallback, only when the owner asks or
the object is organic (people, animals, faces) where a script cannot reach the quality.

## The loop

```
reference picture (owner) ─► read it: proportions in px -> meters, parts list, materials, palette
   ─► PROJECT/Tools/<asset>_build.py  (imports SKILL/scripts/blender/hero_kit.py)
   ─► blender -b -P Tools/<asset>_build.py -- art/exports/<Asset>.glb art/preview/<asset>     (5-15 s)
   ─► Read the preview PNGs next to the reference ─► list the differences ─► fix the script ─► rebuild  (2-4 rounds)
   ─► engine import + placement + engine screenshot ─► gate
```

Blender: `config.json paths.blender` (`C:\Program Files\Blender Foundation\Blender 5.1\blender.exe`). No MCP, no open Blender,
no socket: `blender -b` is the tool. The script is the source of the asset: commit it, rebuild it, never patch the GLB.

## hero_kit (`scripts/blender/hero_kit.py`)

The script puts the kit on `sys.path` (`HERO_KIT_DIR` env, default `~/.claude/skills/game-developer/scripts/blender`) and uses:

| Helper | Does |
|---|---|
| `args()`, `reset()` | `[out.glb, preview_prefix]` after `--`; empty factory scene |
| `material(name, rgb, metallic, rough, coat, image, emission)` | Principled, glTF friendly (linear colours) |
| `image_from_rgb(name, numpy_rgb, png)` | procedural texture (paint, patterns) saved as PNG, embedded in the GLB |
| `frame(pos, yaw, roll, pitch, scale)` / `local(x, y, z, angle, scale, mirror)` | ornament frames on a front surface (local X right, Y up, Z toward the viewer) |
| `slab(name, rings, z0, z1, mat, bevel, matrix)` | prism from a convex outline or an outer + inner ring, bmesh bevel on the top edge |
| `offset(poly, d)`, `rounded_rect`, `circle` | 2D outlines (inset keeps the vertex count, so rings bridge) |
| `loft(name, rings, mat, uv_scale)` + `superellipse(w, d, n)` + `smooth_profile(keys, z)` | bodies swept from a silhouette table `(z, half width, half depth)`: vases, cases, bottles, columns, consoles; UVs in meters |
| `tube(name, pts, r, mat, radii)`, `ring_tube` | mouldings, wires, ropes, bezels, tapering per point |
| `polar_disk(name, R, mat, height(rn, a))` | dials, domes, coins, shells, bosses |
| `text(name, body, size, mat, font, matrix)` | engraved / printed letters as geometry (`C:/Windows/Fonts/timesbd.ttf` ...) |
| `leaf`, `scroll` (C / S Euler-spiral), `shell`, `cluster(style=spray|cartouche|flame|corner)` | ornament: acanthus, rocaille, finials, crests (seeded) |
| `join_by_material()` | one object per material = one draw per material in the engine |
| `stats()`, `export_glb(path)`, `preview(prefix, target, dist, views)` | triangle count, GLB (Y up), EEVEE PNGs (Standard view transform) |

Examples to start from: `templates/blender/hero/medal_build.py` (flat badge: layered slabs, relief dome, bricks, tubes) and
`templates/blender/hero/clock_build.py` (lofted body, painted texture, dial text, ornament clusters, console).

## Conventions (the engine import depends on them)

- Meters, **Z up, front toward -Y, pivot at the base** (the lowest point at z = 0). Real size unless the GDD says otherwise.
- Nucleon: the GLB arrives Z up with the front toward -Y; to face a PlayerStart at the origin looking +Y, place it with
  `rotation [0, 0, 180]`. A wall-hung prop: its back plane at Blender +Y goes against the wall.
- Few materials (5-8), joined by material; previews with `preview()` front + three quarter + a detail view.
- Triangle budget: badge / small prop < 50k, ornate showpiece < 500k (the clock: 409k, 13 MB with its texture; Nucleon cooks
  meshes over 32 MB itself). Drop `segs` / `rings` / cluster `density` for game props seen from afar.

## Lessons (each cost a round)

1. **Never curve bevel / curve fill for outlines**: sharp tips (shield point) make metre-long spikes. Use `slab` (bmesh).
2. **Fan caps from the centre** (`bmesh.ops.poke`): ngon caps triangulate into slivers that render as black stripes.
3. Colours: the first guess is always too light and too saturated. Compare with the reference and darken (linear values: enamel
   0.02-0.05, lacquer red via a texture ~ sRGB 0.70/0.16/0.08, gold metallic 1 rough 0.28 colour 0.80/0.56/0.24). No metallic on
   cloth/paint (it reads as cream plastic). Preview with the **Standard** view transform, not AgX/Filmic.
4. Relief (badges, coins): flatten the depth (scale Z 0.5-0.6), sit the base of the relief just under the field surface.
5. Ornament must follow the surface: leaves along an edge point along it (angle 90 ± 15 in the edge frame), not outward like a
   hedge; ornament clusters must not cover the focal part (dial, face, emblem).
6. Printed detail at the right scale: numerals ~30 % of the dial radius, bold serif; painted motifs 1-3 cm (`uv_scale` meters).
7. Check every preview against the reference **side by side** and write the differences down before changing code; stop when
   the silhouette, proportions, palette and the 3-4 signature details match.
8. Engine screenshots of the templates are over-exposed (white walls, pale enamel): judge colours in Blender, judge placement,
   scale and orientation in the engine; lookdev of the level is the lookdev worker's job.

## Engine step

- **Nucleon** ([nucleon-loop.md](nucleon-loop.md)): `ncli call asset_import '{"sources":["<abs>/art/exports/<Asset>.glb"],"folder":"Content/Models/Hero"}'`
  → a spec `art/blueprints/<asset>_showcase.json` (`pieces` row with `rotation [0,0,180]`, a pedestal or wall `shapes` row, a point
  light) → `ncli build <spec> --save current` → `ncli shot docs/screens/<asset>_engine.png --pos ... --target ...`.
  In a game: the `pieces` row goes into the right level blueprint instead.
- **Unity**: GLB to `Assets/_Game/Art/Hero/`, `props` row of the blueprint, `GDS.LevelBuilder` rebuild + lint.
- **Unreal / Godot**: import the GLB with the engine's importer, same placement rule.

## Gate (`docs/gates/07-hero-<ID>.md`)

`Tools/<asset>_build.py` + `art/exports/<Asset>.glb` + `art/preview/<asset>_*.png` (with the reference beside them in the gate
text: what matches, what was simplified) + `STATS` line + engine import JSON + engine screenshot + ledger row
`source: procedural (Tools/<asset>_build.py)`. GLB < 15 KB = FAIL (a cube).
