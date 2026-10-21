# Sollumz 2.9 internals (per casi che `sz_fivem` non copre)

Ricavato dal sorgente Sollumz v2.9.0 (GitHub Sollumz/Sollumz). Il package si chiama `sollumz` o
`bl_ext.<repo>.sollumz`: usa `sz.szm("modulo")` per importare i sottomoduli senza indovinare il nome.

## `obj.sollum_type` (enum `sollumz_properties.SollumType`)
| Valore | Uso |
|---|---|
| `sollumz_drawable` | radice .ydr (empty o armatura) |
| `sollumz_drawable_model` | mesh con LOD (`obj.sz_lods.get_lod(LODLevel.HIGH).mesh`) |
| `sollumz_drawable_dictionary` | radice .ydd |
| `sollumz_fragment` | radice .yft (armatura) |
| `sollumz_light` | luce embedded (`light.data.sollum_type` = `sollumz_light_point/spot/capsule`) |
| `sollumz_bound_composite` | radice collisione |
| `sollumz_bound_geometrybvh` / `sollumz_bound_geometry` | contenitore poly (BVH) / geometria (fragment) |
| `sollumz_bound_box/sphere/capsule/cylinder/disc/plane` | primitive |
| `sollumz_bound_poly_box/sphere/capsule/cylinder/triangle` | poly dentro BVH (`triangle` = "Bound Poly Mesh") |
| `sollumz_clip_dictionary` > `sollumz_clips` > `sollumz_clip`; `sollumz_animations` > `sollumz_animation` | YCD |

Materiali: `mat.sollum_type` = `sollumz_material_shader` | `sollumz_material_collision`; `mat.shader_properties.filename`
(es. `normal_spec.sps`); nodi immagine chiamati come il sampler (`DiffuseSampler`...), `node.texture_properties.embedded`;
nodi parametro (`SzShaderNodeParameter`) chiamati come il parametro, `node.set(i, v)`.
Nome texture = nome file immagine senza estensione (minuscolo). Immagine HD: `img.sz_is_hd`.

## Proprieta' principali
- Drawable: `obj.drawable_properties.lod_dist_high/med/low/vlow`.
- Ossi: `bone.bone_properties.tag` (0 per la radice, altrimenti hash del nome; `use_manual_tag`/`manual_tag`),
  `bone.bone_properties.flags_enum = {"RotX","RotY","RotZ","TransX","TransY","TransZ","ScaleX",...}`,
  `bone.sollumz_use_physics`, `bone.group_properties.strength/...` (fragment).
- Collisioni: `obj.composite_flags1/2.<flag>` (bool), `mat.collision_properties.collision_index`,
  `obj.child_properties.mass` (fragment), `scene.sz_default_flag_preset_name`.
- Luci: `light.light_properties.intensity/falloff/falloff_exponent/cone_*_angle/corona_*/flashiness`,
  `light.time_flags.total` (stringa, 24 bit), `light.light_flags.<flag>`; colore = `light.color`.
- YTYP: `scene.ytyps` (collezione), `ytyp.new_archetype(ArchetypeType.BASE)`, `arch.asset` (aggiorna nome/tipo/
  physics dict), `arch.flags.total` (stringa), `arch.special_attribute` (nome enum, es. `IS_NORMAL_DOOR`),
  `arch.texture_dictionary`, `arch.clip_dictionary`, `arch.lod_dist`, `arch.hd_texture_dist`, `arch.extensions`.
- YTD: `scene.sz_txds.new_texture_dictionary(name)`, `txd.new_texture(image)`, `txd.new_source()`.
- YCD: `clip.clip_properties.hash/name/duration/animations[].animation/start_frame/end_frame/tags/properties`;
  `anim.animation_properties.hash/action/target_id/target_id_type` ("ARMATURE" | "CAMERA" | "MATERIAL");
  UV: `mat.animation_tracks.uv0/uv1` (righe matrice 2x3) o `mat.animation_tracks.uv_transforms`.
  Tracce ossa supportate: `pose.bones["x"].location`, `.rotation_quaternion`, `.scale` (non euler!).

## Operatori utili (`bpy.ops.sollumz.*`)
| Operatore | Uso |
|---|---|
| `export_assets(directory=..., direct_export=True, use_custom_settings=True, target_formats={'NATIVE','CWXML'}, target_versions={'GEN8','GEN9'}, limit_to_selected=True, export_ytyps=True, export_ytds=True, export_ymaps=False, apply_transforms=False)` | export headless |
| `import_assets(directory=..., files=[{"name": "x.ydr"}])` | import (.ydr/.yft/.ydd/.ybn/.ytd/.ytyp/.ymap/.xml) |
| `converttodrawable`, `converttodrawablemodel`, `createdrawable`, `createdrawabledict` | conversione (usa selezione + scene props `create_seperate_drawables`, `auto_create_embedded_col`, `center_drawable_to_selection`) |
| `createshadermaterial(shader_index=i)`, `change_shader`, `autoconvertmaterials`, `setallembedded`, `setallmatembedded` | materiali (indice nella lista `ydr.shader_materials.shadermats`) |
| `converttocomposite`, `createbound`, `createpolygonbound`, `createcollisionmaterial`, `load_flag_preset(name=...)` | collisioni |
| `create_light`, `auto_lod`, `extract_lods`, `copy_lod`, `set_lod_level` | luci/LOD |
| `createfragment`, `createbonesatobjects`, `calculate_mass`, `setmass` | fragment |
| `create_clip_dictionary`, `create_clip`, `create_animation`, `clip_recalculate_uv_hash`, `uv_sprite_sheet_anim`, `uv_transform_add` | animazioni |
| `createytyp`, `createarchetype`, `createarchetypefromselected`, `export_ytyp_io` | ytyp |
| `txd_create`, `txd_create_texture`, `txd_add_textures_from_dds`, `export_ytd` | ytd |
| `map_add_obj_as_entity`, `map_auto_assign_unassigned`, `map_calculate_extents`, `export_ymap` | mappe |
| `find_missing_textures`, `color_attrs_add_missing`, `uv_maps_add_missing`, `uv_maps_rename_by_order` | riparazioni |

Molti operatori leggono la selezione/oggetto attivo e proprieta' di scena: in headless prepara selezione e
`view_layer.objects.active`, oppure chiama le funzioni sottostanti (`tools.drawablehelper`, `tools.boundhelper`,
`ydr.shader_materials.create_shader`) come fa `sz_fivem`.

## Gotcha scoperti testando (gia' gestiti in `sz_fivem`)
- In background `obj.bound_box` e `matrix_world` non si aggiornano dopo modifiche: usa vertici reali e
  `view_layer.update()` (altrimenti collisioni/bbox spostati).
- Per modelli legati a ossi con COPY_TRANSFORMS la geometria e' nello spazio dell'osso: per bbox/hull usa la
  `matrix_world` valutata (`obj.evaluated_get(depsgraph)`).
- Nel fragment l'osso radice deve avere `sollumz_use_physics` altrimenti la sua collisione viene scartata.
- `flashiness` e' un enum di stringhe (`CONSTANT`, `CANDLE`...).
- Hash clip UV = joaat(nome modello) + indice materiale + 1: il drawable deve esistere prima di creare il clip.
- Export YCD: sempre `.ycd.xml`, nella cartella di export radice (non in gen8/gen9).
