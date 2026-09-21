# Poly Pizza — native Blender MCP library (~10.6k low-poly GLB)

Free. CC0 or CC-BY. One self-contained `.glb` per model. Lighter than Sketchfab. **This is how Blender is used** when Kenney/KayKit miss a piece.

Key lives in Blender addon prefs and `BLENDERMCP_POLYPIZZA_API_KEY` (installer). Get one at https://poly.pizza/settings/api — never commit it into markdown.

## Step 0 Obbligatorio: Wipe Scena Preventivo

Prima di qualsiasi ricerca o download, pulisci completamente la scena Blender:
```python
import bpy
for obj in list(bpy.data.objects): bpy.data.objects.remove(obj, do_unlink=True)
for mesh in list(bpy.data.meshes): bpy.data.meshes.remove(mesh, do_unlink=True)
```
Mai scaricare un nuovo asset sopra oggetti residui di task precedenti!

## Worker calls

```
search_polypizza_models
  query: short English noun ("wooden barrel", "oak chair")
  licence: "CC0" first, else omit
  category: Furniture & Decor | Buildings | People & Characters | Weapons | Nature | Transport | Food & Drink | Clutter | Objects | Animals | Scenes & Levels | Other
  animated: true only for characters that must move
  limit: 8

download_polypizza_model
  model_id: from search
  normalize_size: true
  target_size: Geometra metres (largest axis)
```

Download writes `polypizza_attribution`, `polypizza_id`, `polypizza_licence` on the root object. Copy those into `ASSET-LEDGER.md`.

## Filters

- Reject scenes/dioramas, 20k+ tris, photogrammetry, NC licences.
- One object per `$ASSET_ID`.
- Cloudflare on `static.poly.pizza` can block datacenter IPs. Retry on this machine (residential). If still HTML: FAIL the worker, do not cube.

## Fast-Track Batch (Fino a 3 modelli per run)

Essendo modelli già pronti da scaricare, **non effettuare 5 step né screenshot intermedi**.
Un singolo worker o sessione può processare in sequenza **fino a 3 modelli Poly Pizza** alla volta:
1. `execute_blender_code`: Wipe scena
2. `search_polypizza_models` + `download_polypizza_model`
3. Sanitize (pivot base Y=0, rimozione luci/camere) + `export_scene` (`art/exports/$ASSET_ID.glb`)
4. **1 solo screenshot finale**: `screenshots/blender-$ASSET_ID.png`
5. Aggiorna riga `ASSET-LEDGER.md`

## Not a level kit

Poly Pizza pieces do **not** snap to a 4m grid. Use them as props/characters. Walls/floors stay Kenney/ProBuilder.
