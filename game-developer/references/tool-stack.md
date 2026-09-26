# Tool stack — default for the whole game

Ask this in GDD (question 17). One answer covers **every later worker**. Do not re-litigate per prop. Q20–Q24 (gen3d tier + budget, asset store, GPU, look preset) complete it.

Recommended (free, unlimited, already wired):

| Job | Tool | Why this one |
|---|---|---|
| Engine | Unity 6 URP (6000.x) for lowpoly/toon/stylized/voxel/2D; Unreal 5.8 for realistic ([styles.md](styles.md)) | One engine per game |
| Editor bridge | Unity CLI + Pipeline (`unity command gds_*`, `eval`, tests, play, screenshots); CoplayDev MCP secondary; Unreal MCP (5.8) | Fast, JSON, few tokens ([unity-cli.md](unity-cli.md), [unreal-loop.md](unreal-loop.md)) |
| World | `GDS.World` spec (terrain / island / dungeon / cave / voxel) | Seeded, rebuildable ([world-gen.md](world-gen.md)) |
| Deterministic layer | `Assets/_Game/Editor/GDS/*` ([gds-editor.md](gds-editor.md)) | Buildings from JSON, lint, lookdev, characters, VFX — no LLM eyeballing |
| Buildings / rooms | blueprint JSON → `GDS.LevelBuilder` (kit) / `GDS.PB` (ProBuilder shells) | One call per building; pivot-agnostic; door/window gaps without CSG |
| Modular look | **One** family: Kenney zips **or** KayKit GitHub **or** Quaternius MegaKit Standard **or** Synty POLYGON Starter (Asset Store, Q21) | Same palette, snap |
| Missing hero prop | Blender MCP: Poly Pizza → Poly Haven models → Sketchfab CC0 → gen3d tier (Q20) | Native tools, normalize metres, sanitize block only |
| Look | `GDS.LookDev.Apply(<Q11 preset>)` + palette; optional toon (Delt06) / outline (CristianQiu) | Sun, fog, skybox/HDRI, ACES, bloom, AO, vignette in one call |
| Characters | KayKit / Kenney Animated / Quaternius UBC + UAL → `GDS.Characters` | Humanoid, Animator, CharacterController from code |
| Enemies / AI | skill `initialize-ai-navigation` + `NavMeshAgent` | Already installed |
| VFX | `GDS.VFX` + `manage_vfx` (+ Cartoon FX Free if Q21 yes) | Stylized prefabs from code |
| Voxel games | VoxelAI MCP | Only if GDD style=voxel |
| UI | `real-world-design` → UI Toolkit | Mock HTML first, always |
| Audio | Kenney Audio CC0 + `AudioManager` | [audio-pipeline.md](audio-pipeline.md) |
| QA | `GDS.SceneLint` (issues 0) + Unity Play Mode + TerminalMCP WASD | Numbers, then real input |
| Blender client | `uvx mcp-for-blender` stdio → TCP `9876` | **Not** `http://localhost:9876/mcp` |

Optional, chosen once in Q20 (never mid-pipeline):

| Tier | Needs | Use |
|---|---|---|
| `local` (Modly: Hunyuan3D-2mini / TripoSG / TRELLIS2) | NVIDIA ≥ 8 GB VRAM | hero props offline |
| `meshy` / `tripo` | API key in MCP env + credit budget | CoplayDev `generate_model` |
| `hyper3d` | key in Blender MCP addon | `generate_hyper3d_model_via_*` |

Never (unless user overrides in GDD and has the hardware/licence):

- `execute_blender_code` cubes / bevel / boolean "handmade"
- placing walls/floors one by one with `manage_gameobject`, or ProBuilder MCP face-index edits for rooms
- Sloyd Guest, Blockbench / Dust3D (extra app, no gain)
- Quaternius Pro/Source paid zips, paid Asset Store packs, Fantasy Kingdom assets in a shipped build (non-commercial EULA)
- Mix two kit families in one room
- Unity official MCP / Unity AI (paywalled after 14 days) — CoplayDev covers it

Alternatives if CoplayDev is missing a tool: IvanMurzak Unity-MCP (Apache, extensions Terrain / Navigation / Splines / Timeline / ProBuilder) or AnkleBreaker unity-mcp-server (268 tools incl. terrain, NavMesh, CSG, Shader Graph; attribution licence). Do not run two Unity MCP plugins in the same project.

User may pick family + optional tiers. That lock is `GDD.md` → `## Tool stack`.
