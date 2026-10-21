# Pipeline Python: spec JSON e API `sz_fivem`

Due livelli:
1. **Spec JSON + `build_from_spec.py`** - copre il 90% dei casi senza scrivere codice Blender.
2. **API `sz_fivem`** - per tutto il resto (modellazione procedurale, casi speciali), dallo stesso Python.

## 1. Spec JSON

```jsonc
{
  "output": "build/myrp_pack",          // cartella output (relativa al file spec)
  "ytyp": "myrp_pack",                   // nome del .ytyp (un ytyp per risorsa va benissimo)
  "formats": ["NATIVE", "CWXML"],        // NATIVE se PyMateria c'e' (Windows), CWXML sempre (fallback/ispezione)
  "versions": ["GEN8", "GEN9"],          // GEN8 = FiveM classico (stream/), GEN9 = Enhanced (stream_enhanced/)
  "vertex_color": [1, 0, 0, 1],          // default Color 1 (esterni rosso, interni [0,1,0,1])
  "reset_scene": true,                   // svuota la scena prima di costruire
  "save_blend": true,
  "export_even_with_errors": false,      // l'audit blocca l'export se ci sono errori
  "resource": { "name": "myrp_pack", "path": "build/myrp_pack/resource", "cwconv": null },
  "assets": [ { ... }, ... ]
}
```

### Campi comuni a ogni asset

| Campo | Valori | Note |
|---|---|---|
| `name` | `myrp_xxx` | nome modello/archetipo/file |
| `type` | `static` `dynamic` `animated` `uv_scroll` `dui` `light` `door` `fragment` | sceglie il builder e i flag di default |
| `source` | `{"file": "models/x.glb", "objects": [...], "scale": 1.0}` / `{"objects": ["NomeInScena"]}` / `{"primitive": "cube|cylinder|plane", "size": [x,y,z], "location": [..]}` | glb/gltf/fbx/obj/blend; le mesh importate vengono unite in una |
| `origin` | `"BOTTOM_CENTER"` (default per static) / `"CENTER"` / `[x,y,z]` | pivot in gioco |
| `vertex_color` | `[r,g,b,a]` | sovrascrive il default globale |
| `material` | vedi sotto | |
| `collision` | `{"mode": "box|boxes|hull|mesh", "material": "WOOD_SOLID_MEDIUM", "boxes": [[min],[max]]..., "source": {...}}` / `null` | `null` = nessuna collisione |
| `lods` | `"auto"` | decimate 50/25/10% + distanze 25%/50%/75%/100% di `lod_dist` |
| `lod_distances` | `[high, med, low, vlow]` | metri |
| `lod_dist` | `100` | distanza a cui l'archetipo sparisce |
| `flags` | `["static"]`, `["dynamic"]`, ... | nomi in [archetypes-ytyp.md](archetypes-ytyp.md); default per tipo |
| `special` | `none`, `door`, `street_light`, `clock`... | special attribute |
| `texture_dictionary` | `myrp_xxx_txd` | se le texture NON sono embedded: crea il .ytd e lo collega all'archetipo |
| `lights` | lista di kwargs di `sz.add_light` | luci embedded |

### `material`

```jsonc
// shader esplicito (consigliato)
{ "shader": "normal_spec", "embedded": true,
  "textures": { "diffuse": "textures/myrp_x_d.png", "normal": "textures/myrp_x_n.png", "spec": "textures/myrp_x_s.png" },
  "params": { "bumpiness": 1.0, "specularIntensityMult": 0.5 } }
// conversione automatica dei materiali Principled del file importato (default se "material" manca)
{ "convert_existing": true, "shader": null, "embedded": true }   // shader null = auto (default/normal/spec/normal_spec)
// multi-materiale: per nome del materiale importato
{ "slots": { "Metal": { "shader": "normal_spec", "textures": {...} }, "Glass": { "shader": "glass", "textures": {...} } } }
// schermo DUI
{ "shader": "emissive", "embedded": false, "dui": true, "textures": { "diffuse": "textures/myrp_tv_screen.png" } }
```
Alias texture: `diffuse|albedo|color`, `normal|bump`, `spec|specular`, `tint|palette`, `detail`, `env`, `height`, oppure
il nome reale del sampler (`DiffuseSampler`...). PNG/TGA/JPG vengono convertiti in DDS automaticamente.

### Per tipo

```jsonc
// animated: parti rigide legate a ossi + clip
{ "type": "animated", "name": "myrp_chest",
  "parts": { "root": { "source": {...}, "material": {...} },
             "lid":  { "source": {...}, "material": {...}, "pivot": [0, 0.3, 0.5], "parent": "root" } },
  "clip_dictionary": "myrp_chest_anims",
  "clips": [ { "name": "open",  "loop": false, "keys": { "lid": [[0, {"rot": [0,0,0]}], [30, {"rot": [-100,0,0]}]] } },
             { "name": "close", "keys": { "lid": [[0, {"rot": [-100,0,0]}], [30, {"rot": [0,0,0]}]] } } ],
  "auto_start": false,      // true -> flag Auto Start Anim (il clip con nome = nome modello parte da solo)
  "collision": { "mode": "hull", "material": "WOOD_SOLID_MEDIUM" } }
// keys: frame (30 fps) -> {"rot": [x,y,z] gradi euler XYZ (diventa quaternion), "loc": [x,y,z] relativa al pivot, "scale": [x,y,z]}

// uv_scroll
{ "type": "uv_scroll", "name": "myrp_sign", "source": {...},
  "material": { "shader": "emissive", "textures": {...} },          // shader con supporto UV anim!
  "uv": { "frames": 90, "du": 1.0, "dv": 0.0, "material_index": 0 } } // du/dv = quante "ripetizioni" in frames

// dui
{ "type": "dui", "name": "myrp_tv", "source": {...}, "material": { "...": "vedi sopra" },
  "texture_dictionary": "myrp_tv_txd", "screen_texture": "myrp_tv_screen", "screen_size": [1280, 720] }

// door
{ "type": "door", "name": "myrp_door_01", "kind": "swing|sliding|garage|sliding_vertical|barrier",
  "hinge": [x, y, z], "source": {...}, "material": {...}, "collision": { "material": "WOOD_SOLID_MEDIUM" } }

// fragment
{ "type": "fragment", "name": "myrp_sign_break",
  "parts": { "root": { "source": {...}, "collision": "box", "collision_material": "CONCRETE", "mass": 200 },
             "pole": { "source": {...}, "pivot": [0,0,0.1], "collision": "box", "mass": 20, "strength": 50 },
             "board": { "source": {...}, "pivot": [0,0,2.05], "parent": "pole", "mass": 5, "strength": -1 } } }
```

### Esecuzione e output

```bash
blender -b -P <skill>/scripts/build_from_spec.py -- spec.json
```
Output in `output/`: `_textures/*.dds`, `export/` (gen8/, gen9/, *.ycd.xml), `resource/`, `<ytyp>.blend`,
`build_report.json` (`audit` per asset, `written`, `resource.needs_conversion`). Se `audit` ha errori l'export non
parte: correggi la spec.

## 2. API `sz_fivem` <a id="api"></a>

```python
import sys; sys.path.append(r"<skill>/scripts"); import sz_fivem as sz
```

| Funzione | Cosa fa |
|---|---|
| `env_report()` | versioni + disponibilita' NATIVE Gen8/Gen9 |
| `reset_scene()` | scena vuota, fps=30 |
| `check_asset_name(name)` | problemi di naming |
| `apply_transforms(obj, location=False)` | applica rot/scala (e posizione) |
| `set_origin(obj, "BOTTOM_CENTER"\|"CENTER"\|"POINT", point)` | pivot senza muovere la geometria |
| `ensure_uv_names(obj)` | `UVMap 0..n` |
| `paint_vertex_colors(obj, rgba, index=1)` | riempie `Color n` |
| `prepare_mesh(obj, vertex_rgba)` | tutto quanto sopra |
| `make_drawable(name, [meshes])` | Drawable (empty) + Drawable Model (LOD High); pivot = origine del primo oggetto |
| `add_lod(model, "MEDIUM", mesh)` / `auto_lods(model)` / `set_lod_distances(drawable, h, m, l, vl)` | LOD |
| `new_shader_material(shader)` / `set_shader_textures(mat, {...}, embedded)` / `set_shader_params(mat, **p)` / `assign_material(obj, mat)` | materiali Sollumz |
| `material(obj, shader, textures, embedded=True, **params)` | scorciatoia di quanto sopra |
| `convert_existing_materials(obj, shader=None)` | Principled BSDF -> Sollumz |
| `make_txd(name, images, source_objects)` | Texture Dictionary di scena -> `<name>.ytd` |
| `add_embedded_collision(drawable, mode, material, mesh=None, boxes=None)` | collisione embedded |
| `make_static_collision(name, meshes, material)` | `.ybn` statico in coordinate mondo |
| `add_light(drawable, kind, location, color, intensity, falloff, ..., flashiness, bone)` | luce embedded |
| `make_animated_drawable(name, {"root": {...}, "bone": {"mesh", "pivot", "parent"}})` | drawable-armatura per prop animati |
| `keyframe_bone(arm, bone, frame, rot_euler_deg, loc, scale)` | keyframe in quaternion |
| `record_action(target_id, name, fn)` | registra una Action pulita da una funzione di keyframe |
| `make_clip_dictionary(name)` / `add_clip(cd, clip, action, target, uv=False)` | YCD |
| `uv_scroll_action(mat, frames, du, dv)` | Action UV per scorrimento |
| `make_door(name, mesh, hinge, kind)` / `add_door_archetype(ytyp, door)` | porte |
| `make_fragment(name, parts)` / `set_bone_physics(arm_data, bone, use, strength)` | YFT |
| `get_or_make_ytyp(name)` / `add_archetype(ytyp, asset, flags, lod_dist, texture_dictionary, clip_dictionary, special)` | YTYP |
| `flags_value(*names)` | intero dei flag archetipo |
| `audit(root=None)` | errori/warning pre-export |
| `export(out_dir, objects, formats, versions)` | `sollumz.export_assets` senza UI |
| `szm("ydr.shader_materials")` | accesso diretto ai moduli Sollumz |

### Esempio: prop statico scritto a mano (MCP)

```python
import bpy, sz_fivem as sz
sz.reset_scene()
bpy.ops.import_scene.gltf(filepath=r"C:\proj\models\crate.glb")
obj = [o for o in bpy.context.selected_objects if o.type == "MESH"][0]
sz.prepare_mesh(obj)                                   # rot/scala, UVMap 0, Color 1 rosso
sz.set_origin(obj, "BOTTOM_CENTER")
sz.material(obj, "normal_spec", {"diffuse": r"C:\proj\build\_textures\myrp_crate_d.dds",
                                 "normal": r"...\myrp_crate_n.dds", "spec": r"...\myrp_crate_s.dds"})
d = sz.make_drawable("myrp_crate", [obj])
sz.add_embedded_collision(d, "box", material="WOOD_SOLID_MEDIUM")
y = sz.get_or_make_ytyp("myrp_pack")
sz.add_archetype(y, d, flags=("static",), lod_dist=120)
assert not sz.audit(d)["errors"]
sz.export(r"C:\proj\build\export", [d])
```

### Esempio: modellazione procedurale prima della conversione

Puoi costruire la geometria con `bmesh`/operatori (es. un tavolo da primitive), poi `prepare_mesh` +
`material` + `make_drawable`. Mantieni: unwrap UV (`bpy.ops.uv.smart_project()` o seam+unwrap), normali coerenti
(`bpy.ops.mesh.normals_make_consistent()`), niente facce doppie (`remove_doubles`), triangoli < budget.

### Script dopo la build

`make_resource.py` puo' essere rieseguito da solo (senza Blender) per rigenerare la risorsa da un export:
```bash
python make_resource.py build/x/export build/x/resource --name myrp_pack --spec spec.json --ytyp myrp_pack
```
