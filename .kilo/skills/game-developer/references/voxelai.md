# VoxelAI

Path default: `C:\Users\FRANCY\Desktop\Dev Things\VoxelAIArtist`

## MCP

```
python "<VoxelAIArtist>\mcp_server" --workdir "<game>\art\voxel"
```

`--workdir` is the **only** write root. Global installer must **not** pin a single workdir for all games. After attach, prefer a per-project MCP launch or pass `--workdir` for this game.

Do not start the VoxelAI GUI if MCP tools answer.

## When

GDD `style: voxel` → primary for characters and props. Other styles → CC0/Blender first; Voxel only if asked.

## How

- `voxel_ai_status` before generate
- Prefer `voxel_ops` (local, free) for simple shapes
- `voxel_generate` only if AI is authenticated; on auth fail, fall back to ops + CC0 — do not block the slice
- `multi_part=true` so Unity gets separate meshes
- Humanoids: T-pose, `humanoid=true`, then `voxel_rig_auto`
- Export GLB → `art/exports/<id>.glb` (copy; workdir is `art/voxel`)
- `voxel_preview` ASCII + screenshot file

Y is up. Model sits on y=0.
