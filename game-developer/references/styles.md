# Styles — one decision that routes engine, assets, look and gates

The GDD `style:` (Q7) is locked once and every worker reads it. A style is a bundle, not an adjective: it picks the engine, the asset family, the lookdev preset, the shaders and what the art review measures.

| style | engine | assets (one family) | look | shaders / post | art review focus |
|---|---|---|---|---|---|
| `lowpoly` | Unity URP | Kenney / KayKit / Quaternius / Synty Starter | `stylized-day` / `stylized-sunset` / `pastel-bright` | URP Lit, flat palette materials, SSAO, bloom low | silhouette, palette coherence, no default grey |
| `toon` | Unity URP | same kits, or Blender buildings with palette | `toon-bright` (+ any stylized preset) | Delt06 toon shader + CristianQiu outline (`-WithToonShader -WithOutline`), `GDS.LookDev.ConvertMaterials` | clean shadow bands, outlines readable, saturated but not neon |
| `stylized` | Unity URP | kits + Poly Haven textures on terrain, hand-picked hero props | `stylized-*`, `realistic-golden` | URP Lit with textures, volumetric light optional | lighting mood, depth (fog), texture scale |
| `voxel` | Unity URP | `GDS.VoxelWorld` + VoxelAI hero models | `stylized-day` / `night-moon` | palette texture, SSAO on | block scale 1 m, chunk seams, no z-fighting |
| `realistic` | **Unreal 5.8** | Fab / Megascans (free in UE), Poly Haven | `realistic-overcast` / `realistic-golden` equivalents in UE | Lumen, Nanite, Virtual Shadow Maps, Exposure/TSR | scale, material realism, GI, no floating assets |
| `2d-pixel` | Unity URP 2D | Kenney 2D, itch CC0 tilesets | 2D lights | Unity skills `2d-pixel-perfect`, `tilemap-*`, `sprite-editor` | pixel grid, no filtering, readable sprites |

Mixing is allowed only inside the row (a toon game can use low-poly kits; a low-poly game cannot use Megascans).

## Why realistic → Unreal

- UE 5.8 ships a free first-party MCP server (Unreal MCP + All Toolsets) and Epic's Claude Code plugin (`/plugin install unreal-engine-skills-for-claude-code@claude-plugins-official`).
- Megascans on Fab are free for Unreal projects; Lumen/Nanite give real GI and dense geometry that URP cannot match on the same budget.
- Unity URP can still do `realistic-*` presets for a stylized-realistic look; it is the fallback when UE 5.8 is not installed or the GPU cannot run it.

## Hardware gate (Q22)

| GPU / VRAM | realistic in UE 5.8 | toon/lowpoly/voxel in Unity |
|---|---|---|
| ≥ 8 GB, RTX | Lumen HW, Nanite, VSM | everything on |
| 6 GB GTX (e.g. 1660 Super) | Lumen **software**, Nanite on, VSM on, TSR 66 %, scalability High not Epic; keep levels small | everything on, SSAO ok |
| ≤ 4 GB | not recommended: propose `stylized` in Unity | SSAO off, shadow distance 50 |

## Style → first files

- `lowpoly` / `toon` / `stylized`: [art-pipeline.md](art-pipeline.md), [lookdev.md](lookdev.md), [level-builder.md](level-builder.md), [world-gen.md](world-gen.md)
- `voxel`: [world-gen.md](world-gen.md) (mode `voxel`), [voxelai.md](voxelai.md) for hero models
- `realistic`: [unreal-loop.md](unreal-loop.md)
- `2d-pixel`: Unity skills `2d-pixel-perfect`, `tilemap-palette-create`, `tilemap-ruletile-createempty`, `sprite-editor`, `manage-sprite-atlas`
