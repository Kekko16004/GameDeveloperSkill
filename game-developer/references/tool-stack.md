# Tool stack — default for the whole game

Ask this in GDD (question 13). One answer covers **every later worker**. Do not re-litigate per prop.

Recommended (free, unlimited, already wired):

| Job | Tool | Why this one |
|---|---|---|
| Engine | Unity 6 URP + CoplayDev MCP | Live scene, scripts, tests, ProBuilder |
| Rooms / stairs / collision | `manage_probuilder` | Grid snap, no export, no seams |
| Modular look (walls, furniture, chars) | **One** family: Kenney zips **or** KayKit GitHub **or** Quaternius MegaKit **Standard** | CC0, commercial, snap |
| Missing single prop | Blender MCP **Poly Pizza** (`search` + `download` + `export_scene`) | Native tools, normalize metres |
| Pivot / lights strip | Blender sanitize block only | Not modelling |
| Voxel games | VoxelAI MCP | Only if GDD style=voxel |
| UI | `real-world-design` → UI Toolkit | Mock HTML first |
| Audio | Kenney Audio CC0 + `AudioManager` | [audio-pipeline.md](audio-pipeline.md) via `fetch-cc0-audio.ps1` |
| QA | Unity Play Mode + TerminalMCP WASD | Real input |
| Blender client | `uvx blender-mcp` stdio → TCP `9876` | **Not** `http://localhost:9876/mcp` |

Never (unless user overrides in GDD and has the hardware/licence):

- `execute_blender_code` cubes / bevel / boolean “handmade”
- Sloyd Guest, Meshy, Tripo, Rodin
- Hunyuan3D / TRELLIS (VRAM + licence)
- Blockbench / Dust3D (extra app, no gain)
- Quaternius Pro/Source paid zips
- Mix Kenney + KayKit in one room
- Kenney All-in-1 purchase in-pipeline (use only if already on disk)

User may pick family + optional Poly Pizza fill. That lock is `GDD.md` → `## Tool stack`.
