# Blender — importer + sanitizer (no bpy modelling)

Blender does **not** build rooms or hero meshes from Python. That path produced cubes, floating pivots and seams.

Order: kit on disk → Poly Pizza MCP → sanitize → export GLB. See [blender-mcp.md](blender-mcp.md) and [art-pipeline.md](art-pipeline.md).

## When to open Blender

1. Ledger `source: polypizza` — kit miss, need one low-poly GLB.
2. Kit/Poly Pizza piece pivot off by >5cm — sanitize only.
3. Never: walls, floors, stairs (ProBuilder), crates that Kenney already has, Hunyuan/Rodin blobs.

## Import (native tools only)

```
blender_get_addon_status
blender_get_polypizza_status          # must be enabled
blender_search_polypizza_models(query, licence="CC0", limit=8)
# pick lowest-tri CC0 match that is ONE object, not a diorama
blender_download_polypizza_model(model_id, normalize_size=true, target_size=<Geometra metres>)
blender_get_scene_info
blender_get_viewport_screenshot  → screenshots/blender-$ID-2-import.png
```

Prefer `licence=CC0`. CC-BY only if CC0 empty; write attribution in `ASSET-LEDGER.md`. Skip CC-BY-NC.

If search returns junk (photogrammetry, 80k tris, whole rooms): do not download. Fall back to Kenney/KayKit or ProBuilder. Do not `execute_blender_code` a cube.

Poly Haven: **textures on the imported mesh** (`set_texture`) if the GLB is untextured. Never HDRI on game-asset materials (HDRI as scene skybox is fine — LookDev handles it).

## Sanitize (the only allowed execute_blender_code)

Paste this **once**, then screenshot, then `blender_export_scene`. No extra modelling.

```python
import bpy
if bpy.context.object and bpy.context.object.mode != "OBJECT":
    bpy.ops.object.mode_set(mode="OBJECT")
for obj in list(bpy.data.objects):
    if obj.type in ("LIGHT", "CAMERA"):
        bpy.data.objects.remove(obj, do_unlink=True)
mesh_objects = [o for o in bpy.data.objects if o.type == "MESH"]
for obj in mesh_objects:
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
if mesh_objects:
    min_x = min(obj.bound_box[i][0] + obj.location.x for obj in mesh_objects for i in range(8))
    max_x = max(obj.bound_box[i][0] + obj.location.x for obj in mesh_objects for i in range(8))
    min_y = min(obj.bound_box[i][1] + obj.location.y for obj in mesh_objects for i in range(8))
    max_y = max(obj.bound_box[i][1] + obj.location.y for obj in mesh_objects for i in range(8))
    min_z = min(obj.bound_box[i][2] + obj.location.z for obj in mesh_objects for i in range(8))
    # props: center-bottom. walls: set pivot_mode corner in worker if ledger role=env
    target = ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0, min_z)
    bpy.context.scene.cursor.location = target
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")
    for obj in mesh_objects:
        obj.location = (0.0, 0.0, 0.0)
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
```

Export: `blender_export_scene(filepath=PROJECT/art/exports/$ID.glb, format=glb, object_names=[imported roots])`.

## Not in this skill

- Blockbench / Dust3D: extra app, no gain over ProBuilder + kits + Poly Pizza.
- Hunyuan3D / TRELLIS / Rodin: 16–29GB VRAM, blob topology, Hunyuan community licence excludes EU/UK. Leave disabled.
- Modelling a crate with bevel modifiers in bpy: FAIL.
