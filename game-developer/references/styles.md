# Styles — one decision that routes assets, look and gates

The GDD `style:` (Q9) is locked once and every worker reads it. A style is a bundle, not an adjective: it picks the asset family, the lookdev preset, the shaders and what the art review measures. **It does not pick the engine**: the engine is the user's answer to Q0 ([engines.md](engines.md)); the columns below say how each engine renders the style.

| style | assets (one family) | Unity URP | Nucleon | Unreal 5.8 | art review focus |
|---|---|---|---|---|---|
| `lowpoly` | Kenney / KayKit / Quaternius / Synty Starter | URP Lit flat palette, `stylized-*` / `pastel-bright` | modern lighting, `nc_mat.py auto --style lowpoly` (shared materials, foliage model + wind on plants), low bloom | Lumen, flat materials | silhouette, palette coherence, no default grey |
| `toon` | same kits, or Blender buildings with palette | Delt06 toon + CristianQiu outline, `toon-bright` | `nc_mat.py auto --style toon` (rougher, low specular) + strong key light; bands/outline through a material graph only if the lookdev worker proves it (`engine_gap:` otherwise) | toon post material | clean shadow bands, outlines readable, saturated but not neon |
| `stylized` | kits + Poly Haven textures on terrain, hand-picked hero props | URP Lit textured, volumetric optional | modern lighting, landscape paint layers, volumetric fog, `nc_mat.py --style stylized` (clear coat / cloth / foliage where named) | Lumen + PCG foliage | lighting mood, depth (fog), texture scale |
| `voxel` | `GDS.VoxelWorld` (Unity) or VoxelAI/Blender voxel models | palette texture, SSAO | voxel models as `.glb`, palette material | voxel meshes, Nanite off | block scale 1 m, chunk seams, no z-fighting |
| `realistic` | Fab / Megascans, Poly Haven | `realistic-*` presets = stylized-realistic | Lumen-like GI, traced reflections, Nanite-like meshes; `nc_mat.py --style realistic` (ORM packing, detail normals, triplanar rocks, parallax ground, glass/water/skin models) | Lumen, Nanite, VSM, TSR | scale, material realism, GI, no floating assets |
| `2d-pixel` | Kenney 2D, itch CC0 tilesets | URP 2D, `2d-pixel-perfect`, tilemaps | not 3D-first: say so at Q0 | not recommended | pixel grid, no filtering, readable sprites |

Mixing is allowed only inside the row (a toon game can use low-poly kits; a low-poly game cannot use Megascans).

## Engine notes per style (facts to tell the user at Q0, never a pick)

- Unreal 5.8 ships a free first-party MCP server and Megascans are free for Unreal projects.
- Nucleon renders `realistic`/`stylized` with modern lighting (Lumen/Nanite-like) and its assets are text files the agent edits directly; `.glb` kits import as they are.
- Unity has the widest CC0 kit tooling here (`GDS.*` C# layer), 2D, voxel runtime, WebGL/mobile.

## Hardware gate (Q22)

The hardware sets quality settings, never the engine.

| GPU / VRAM | realistic (Unreal / Nucleon modern) | toon/lowpoly/voxel |
|---|---|---|
| ≥ 8 GB, RTX | Lumen HW, Nanite, VSM | everything on |
| 6 GB GTX (e.g. 1660 Super) | Lumen **software**, Nanite on, VSM on, TSR 66 %, scalability High not Epic; keep levels small | everything on, SSAO ok |
| ≤ 4 GB | say it will be slow; offer `stylized` or Nucleon `classic` lighting (the user decides) | SSAO off, shadow distance 50 |

## Style → first files

- `lowpoly` / `toon` / `stylized`: [art-pipeline.md](art-pipeline.md), [lookdev.md](lookdev.md), [level-builder.md](level-builder.md), [world-gen.md](world-gen.md)
- `voxel`: [world-gen.md](world-gen.md) (mode `voxel`), [voxelai.md](voxelai.md) for hero models
- Engine loop first: [unity-loop.md](unity-loop.md) · [nucleon-loop.md](nucleon-loop.md) · [unreal-loop.md](unreal-loop.md) · [godot-loop.md](godot-loop.md)
- `2d-pixel`: Unity skills `2d-pixel-perfect`, `tilemap-palette-create`, `tilemap-ruletile-createempty`, `sprite-editor`, `manage-sprite-atlas`
