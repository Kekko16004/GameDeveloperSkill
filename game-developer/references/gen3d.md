# Generative 3D — optional tier, chosen ONCE in the GDD (Q16), hero props only

Kits + Poly Pizza + Poly Haven cover 90 % of a slice. Generative 3D is for the 10 %: the unique relic, the boss, the weird machine. Never for walls, floors, crates, trees. Never more than `gen3d.maxAssets` per slice (default 5).

| Tier (`GDD.md → gen3d:`) | Cost | Needs | How the worker calls it | Quality / notes |
|---|---|---|---|---|
| `none` (default) | $0 | — | Poly Pizza / Poly Haven / Sketchfab CC0 only | fine for stylized slices |
| `local` | $0 | NVIDIA ≥ 8 GB VRAM (6 GB = shape only, slow) | **Modly** desktop app (`https://github.com/lightningpixel/modly`, open source, offline; extensions Hunyuan3D-2mini / TripoSG / TRELLIS2). User generates from a reference image → GLB → `art/exports/`. Agent writes the prompt + reference image request, then imports via **import-art** | untextured or baked PBR, 20–60 k tris → decimate in Blender sanitize block; style mismatch risk next to Kenney |
| `meshy` | paid credits (free tier exists, ~200 credits/mo) | `MESHY_API_KEY` in the CoplayDev MCP env | CoplayDev `generate_model provider=meshy prompt=... ` → imports into `Assets/_Game/Art/Generated/` | best text→3D for stylized props; ask for "low poly, flat colors, game asset, single object, no base" |
| `tripo` | paid credits (free tier) | `TRIPO_API_KEY` in MCP env | CoplayDev `generate_model provider=tripo` | fast, decent topology |
| `hyper3d` | free trial key in Blender MCP addon (limited) / paid | Blender MCP addon → Hyper3D Rodin enabled | `generate_hyper3d_model_via_text` / `via_images` → `poll_rodin_job_status` → `import_generated_asset` → sanitize → `export_scene` | PBR, good geometry; slow |
| `hunyuan-cloud` | free HF space quota | browser (TerminalMCP) | HF space Hunyuan3D-2.1 → download GLB → `art/exports/` | manual, EU licence check |

## Rules (all tiers)

1. Budget lives in `GDD.md`: `gen3d: meshy`, `gen3dBudgetCredits: 400`, `gen3dMaxAssets: 5`. The worker reads it and stops at the cap. It reports credits used in the gate.
2. Prompt template: `"<object>, low poly stylized game asset, flat colors, single object centered, no floor, no background, front view"` + the GDD palette words. Image-to-3D beats text-to-3D: if the user gives a reference image, use it.
3. Post-process is mandatory: Blender sanitize block (remove lights/cameras, pivot at base Y=0, `normalize_size` to the Geometra size, decimate > 15 k tris to ~5 k), export GLB to `art/exports/<id>.glb`, ledger `source: meshy|tripo|hyper3d|local-modly|hunyuan`.
4. Style coherence: generated PBR next to flat Kenney = FAIL. Either convert the generated material to a flat palette color (`ApplyPalette` + assign) or use the generated prop only as the hero in its own spotlight.
5. Interview Q16 is mandatory. If the user has no key and no GPU → `none`, and the agent never suggests buying credits mid-pipeline.
