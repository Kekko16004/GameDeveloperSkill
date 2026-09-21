# Sloyd — NOT the default path

User asked to integrate https://app.sloyd.ai/. Research (pricing page 2026, API docs, live app) says **Sloyd cannot feed a whole game for free**.

## What Sloyd actually is

Two products:

1. **Web app** (`app.sloyd.ai`) — Template Editor (parametric, human-authored topology) + Text/Image-to-3D.
2. **HTTP API** (`https://api.sloyd.ai/api`) — prepaid credits, separate from the web plan. Min buy **$12**.

Unity plugin exists (`https://app.sloyd.ai/plugins/unity/sloyd-unity-bridge.zip`) and lands files in `Assets/SloydModels/`. Plugin access is a **Plus/Pro** feature.

## Guest plan (the only $0 tier)

From https://www.sloyd.ai/pricing :

| Limit | Guest |
|---|---|
| AI 3D generation | **1 per day** |
| Template editor | unlimited **in-browser preview** |
| Downloads | **community models only** |
| License | **personal-use** (not commercial) |
| Plugins (Unity/Blender) | **no** |
| Commercial game | **no** |

That is a demo, not a pipeline. One prop per day cannot dress a slice. Personal-use forbids shipping a commercial game.

Plus = $15/mo (unlimited gens, commercial, plugins). Pro = $50/mo. API = extra prepaid credits.

## Skill rule

- **Do not** open Sloyd, do not drive the browser, do not call the API as part of `/game`.
- **Do not** treat Guest community GLBs as kit replacements (mixed style + personal license).
- If the **user** has Plus/Pro **and** explicitly says "use Sloyd for this prop":
  1. Prefer Template Editor (parametric) over text-to-3D (geometry is frozen after generate).
  2. Game Dev preset: Low Poly (~10k tris, 512 tex) for props; never Ultra/500k.
  3. Export **GLB**. Copy to `art/exports/$ID.glb`. Ledger `source: sloyd`.
  4. Sanitize pivot in Blender if `Y≠0`. BoxCollider in Unity.
  5. Screenshot `screenshots/sloyd-$ID.png`.
- Text-to-3D blobs, glass/chrome, thin wires, faces: skip. Use a Kenney/KayKit piece instead.

Community library at https://www.sloyd.ai/free-3d-models is **CC BY 4.0** (attribution required, mixed quality, not modular-grid). Not a substitute for Kenney.

## Why kits win

Sloyd parametric templates are the good part (clean UV, LOD sliders) — and they sit behind a paywall for export. Kenney/KayKit already give you that topology, for free, with matching palettes and 1m snap, unlimited commercial copies.
