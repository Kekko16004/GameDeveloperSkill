"""
sz_fivem.py - helper deterministici Blender + Sollumz per asset FiveM.

Testato con: Blender 5.2.2 LTS (anche headless / come modulo bpy) + Sollumz 2.9.0 (szio 1.3.x).
Funziona anche con Blender 4.2+ (Sollumz 2.9 richiede >= 4.2).

COME CARICARLO
- Blender MCP / console Python / script:
      import sys; sys.path.append(r"<cartella skill>/scripts"); import sz_fivem as sz
      import importlib; importlib.reload(sz)   # dopo modifiche
- Headless:
      blender -b -P build_script.py      (build_script fa sys.path.append + import sz_fivem)

FILOSOFIA
- Ogni funzione crea la struttura che Sollumz si aspetta (sollum_type, gerarchia, proprieta').
- Nessuna dipendenza dalla UI: niente bpy.ops che richiedano viewport (tranne l'export, che
  funziona anche in background).
- Unita': 1 unita' Blender = 1 metro. Z su. Il "fronte" del prop e' -Y (convenzione GTA: il player
  lo guarda da -Y verso +Y); l'origine dell'oggetto = punto di appoggio/pivot nel gioco.
"""
from __future__ import annotations

import importlib
import json
import math
import os
import re
from pathlib import Path
from typing import Iterable, Optional, Sequence

import bpy
from mathutils import Matrix, Vector

# --------------------------------------------------------------------------------------------
# Accesso al package Sollumz (il nome cambia: "sollumz", "bl_ext.user_default.sollumz",
# "bl_ext.repo_sollumz_org.sollumz", "bl_ext.<repo>.sollumz_dev", ...)
# --------------------------------------------------------------------------------------------
_SZ_PKG: Optional[str] = None


def sz_pkg() -> str:
    """Nome del package Python dell'addon Sollumz abilitato."""
    global _SZ_PKG
    if _SZ_PKG:
        return _SZ_PKG
    candidates = [k for k in bpy.context.preferences.addons.keys() if "sollumz" in k.lower()]
    for name in candidates:
        try:
            importlib.import_module(name + ".sollumz_properties")
            _SZ_PKG = name
            return name
        except Exception:
            continue
    raise RuntimeError(
        "Sollumz non e' abilitato. Installa Sollumz 2.9+ (Preferences > Get Extensions, repo "
        "https://repo.sollumz.org/) e abilitalo, poi riprova."
    )


def szm(module: str):
    """Importa un sottomodulo di Sollumz, es. szm('ydr.shader_materials')."""
    return importlib.import_module(f"{sz_pkg()}.{module}")


def _props():
    return szm("sollumz_properties")


def ST():
    """Enum SollumType di Sollumz."""
    return _props().SollumType


# --------------------------------------------------------------------------------------------
# Ambiente
# --------------------------------------------------------------------------------------------
def env_report(print_it: bool = True) -> dict:
    """Versioni di Blender/Sollumz/szio e disponibilita' dell'export binario nativo (PyMateria)."""
    info = {"blender": bpy.app.version_string}
    try:
        pkg = sz_pkg()
        mod = importlib.import_module(pkg)
        ver = getattr(mod, "bl_info", {}).get("version")
        if ver is None:
            try:
                ver = szm("meta").sollumz_version()
            except Exception:
                ver = "?"
        info["sollumz_pkg"] = pkg
        info["sollumz_version"] = ".".join(map(str, ver)) if isinstance(ver, tuple) else str(ver)
    except Exception as e:  # noqa: BLE001
        info["sollumz_error"] = str(e)
    try:
        import szio  # noqa: F401
        from szio.gta5 import AssetFormat, AssetTarget, AssetVersion, is_provider_available
        info["szio"] = getattr(szio, "__version__", "installed")
        info["native_gen8"] = is_provider_available(AssetTarget(AssetFormat.NATIVE, AssetVersion.GEN8))
        info["native_gen9"] = is_provider_available(AssetTarget(AssetFormat.NATIVE, AssetVersion.GEN9))
        info["cwxml"] = is_provider_available(AssetTarget(AssetFormat.CWXML, AssetVersion.GEN8))
    except Exception as e:  # noqa: BLE001
        info["szio_error"] = str(e)
    if print_it:
        print(json.dumps(info, indent=2))
    return info


def reset_scene(keep_ytyps: bool = False):
    """Svuota la scena (oggetti, mesh, materiali, immagini orfane, azioni, armature, luci)."""
    if bpy.context.mode != "OBJECT" and bpy.context.object is not None:
        bpy.ops.object.mode_set(mode="OBJECT")
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures, bpy.data.actions,
                 bpy.data.lights, bpy.data.images):
        for block in list(coll):
            if block.users == 0 or coll is not bpy.data.images:
                coll.remove(block)
    sc = bpy.context.scene
    if not keep_ytyps and hasattr(sc, "ytyps"):
        sc.ytyps.clear()
    if hasattr(sc, "sz_txds"):
        sc.sz_txds.texture_dictionaries.clear()
    sc.render.fps = 30  # le animazioni GTA sono a 30 fps
    sc.render.fps_base = 1.0


# --------------------------------------------------------------------------------------------
# Naming
# --------------------------------------------------------------------------------------------
_NAME_RE = re.compile(r"^[a-z0-9_]+$")


def check_asset_name(name: str) -> list[str]:
    """Regole nome asset: minuscolo, [a-z0-9_], max 63 caratteri, niente collisioni con prefissi vanilla."""
    problems = []
    if not _NAME_RE.match(name):
        problems.append(f"'{name}': usa solo a-z 0-9 _ (minuscolo, niente spazi/punti/trattini)")
    if len(name) > 63:
        problems.append(f"'{name}': troppo lungo ({len(name)} > 63)")
    if re.match(r"^(prop_|v_|p_|des_|hei_|xm_|ba_|ch_|h4_|tr_|sm_|vw_|bkr_|ex_|gr_|imp_|sr_|xs_)", name):
        problems.append(f"'{name}': prefisso usato dai file vanilla, rischio di sovrascrivere un asset del gioco. "
                        "Usa un prefisso tuo (es. 'myrp_')")
    return problems


# --------------------------------------------------------------------------------------------
# Preparazione mesh
# --------------------------------------------------------------------------------------------
def _select_only(objs: Iterable[bpy.types.Object], active: Optional[bpy.types.Object] = None):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    objs = list(objs)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or (objs[0] if objs else None)


def apply_transforms(obj: bpy.types.Object, location: bool = False, rotation: bool = True, scale: bool = True):
    """Applica rotazione/scala (e opzionalmente posizione) ai dati mesh."""
    _select_only([obj])
    bpy.ops.object.transform_apply(location=location, rotation=rotation, scale=scale)


def set_origin(obj: bpy.types.Object, mode: str = "BOTTOM_CENTER", point: Optional[Sequence[float]] = None):
    """
    Sposta l'origine (= pivot in gioco) senza muovere la geometria nel mondo.
    mode: 'BOTTOM_CENTER' (prop appoggiati a terra, default), 'CENTER' (bbox), 'POINT' (usa `point`,
    coordinate mondo: cerniere di porte, perni di leve, ecc.)
    """
    mw = obj.matrix_world
    corners = [mw @ v.co for v in obj.data.vertices]  # non usare obj.bound_box: in headless resta vecchio
    mn = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    mx = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    if mode == "BOTTOM_CENTER":
        target = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    elif mode == "CENTER":
        target = (mn + mx) / 2
    elif mode == "POINT":
        assert point is not None, "mode='POINT' richiede point=(x,y,z)"
        target = Vector(point)
    else:
        raise ValueError(mode)
    offset_local = mw.inverted() @ target
    obj.data.transform(Matrix.Translation(-offset_local))
    obj.matrix_world = mw @ Matrix.Translation(offset_local)
    return target


def ensure_uv_names(obj: bpy.types.Object):
    """Rinomina le UV in 'UVMap 0', 'UVMap 1', ... (convenzione Sollumz obbligatoria)."""
    me = obj.data
    if not me.uv_layers:
        raise RuntimeError(f"'{obj.name}' non ha UV map: fai l'unwrap prima di convertire.")
    for i, uv in enumerate(me.uv_layers):
        uv.name = f"UVMap {i}"


def paint_vertex_colors(obj: bpy.types.Object, rgba: Sequence[float] = (1.0, 0.0, 0.0, 1.0),
                        index: int = 1, overwrite: bool = True):
    """
    Riempie l'attributo 'Color <index>' (Face Corner, Byte Color).
    Default prop esterno: Color 1 = rosso pieno (R = luce ambiente naturale/cielo).
    Prop d'interni (MLO): (0,1,0,1). Prop usato ovunque: (1,1,0,1) e' un compromesso accettabile.
    Vestiti ped: Color 1 = #FF8000 (1,0.5,0,1), Color 2 = (0,0,0,0).
    """
    me = obj.data
    name = f"Color {index}"
    attr = me.color_attributes.get(name)
    if attr is not None and (attr.domain != "CORNER" or attr.data_type != "BYTE_COLOR"):
        me.color_attributes.remove(attr)
        attr = None
    if attr is None:
        attr = me.color_attributes.new(name=name, type="BYTE_COLOR", domain="CORNER")
        overwrite = True
    if overwrite:
        flat = list(rgba) * len(attr.data)
        attr.data.foreach_set("color_srgb", flat)
    me.color_attributes.active_color = attr
    me.color_attributes.render_color_index = me.color_attributes.find(name)
    return attr


def set_tint_column(obj: bpy.types.Object, column: int = 0, index: int = 1):
    """Shader *_tnt: imposta il canale Blu di 'Color <index>' = colonna della palette (0-255), mantenendo R/G/A.
    (shader trees_*_tnt usano Color 2 -> index=2)."""
    me = obj.data
    attr = me.color_attributes.get(f"Color {index}") or paint_vertex_colors(obj, (1, 0, 0, 1), index)
    n = len(attr.data)
    vals = [0.0] * (n * 4)
    attr.data.foreach_get("color_srgb", vals)
    for i in range(n):
        vals[i * 4 + 2] = column / 255.0
    attr.data.foreach_set("color_srgb", vals)


def prepare_mesh(obj: bpy.types.Object, vertex_rgba: Optional[Sequence[float]] = (1.0, 0.0, 0.0, 1.0),
                 apply_rot_scale: bool = True):
    """Prepara una mesh "sorgente": applica rot/scala, UV map rinominate, Color 1 dipinto, normali ok."""
    if obj.type != "MESH":
        raise TypeError(f"{obj.name} non e' una mesh")
    if apply_rot_scale:
        apply_transforms(obj, location=False)
    ensure_uv_names(obj)
    if vertex_rgba is not None:
        paint_vertex_colors(obj, vertex_rgba, 1, overwrite=("Color 1" not in obj.data.color_attributes))
    # niente modificatori non applicati: Sollumz esporta la mesh valutata, ma meglio esplicito
    return obj


def apply_modifiers(obj: bpy.types.Object):
    _select_only([obj])
    for m in list(obj.modifiers):
        if m.type == "ARMATURE":
            continue
        bpy.ops.object.modifier_apply(modifier=m.name)


# --------------------------------------------------------------------------------------------
# Drawable (.ydr)
# --------------------------------------------------------------------------------------------
def make_drawable(name: str, meshes: Sequence[bpy.types.Object], keep_world_position: bool = False) -> bpy.types.Object:
    """
    Crea un Drawable (empty, sollum_type DRAWABLE) con le mesh come Drawable Models (LOD High).
    L'origine del Drawable = origine mondo (0,0,0) se keep_world_position=False: le mesh vengono
    traslate in modo che il loro pivot (origine del primo oggetto) finisca in (0,0,0).
    """
    for p in check_asset_name(name):
        print("[sz_fivem][WARN]", p)
    dh = szm("tools.drawablehelper")
    meshes = list(meshes)
    if not keep_world_position:
        pivot = meshes[0].matrix_world.translation.copy()
        for m in meshes:
            m.matrix_world.translation -= pivot
    drawable = dh.convert_objs_to_single_drawable(meshes)
    drawable.name = name
    for m in meshes:
        if not m.name.endswith(".model"):
            m.name = f"{m.name}.model"
    return drawable


def add_lod(model_obj: bpy.types.Object, lod: str, mesh: bpy.types.Mesh | bpy.types.Object | None):
    """Assegna una mesh a un LOD: lod in {'HIGH','MEDIUM','LOW','VERYLOW'} (VERYHIGH solo veicoli)."""
    LOD = _props().LODLevel
    level = {"VERYHIGH": LOD.VERYHIGH, "HIGH": LOD.HIGH, "MEDIUM": LOD.MEDIUM, "LOW": LOD.LOW,
             "VERYLOW": LOD.VERYLOW}[lod.upper()]
    if isinstance(mesh, bpy.types.Object):
        src = mesh
        mesh = mesh.data
        bpy.data.objects.remove(src, do_unlink=True)
    model_obj.sz_lods.get_lod(level).mesh = mesh


def auto_lods(model_obj: bpy.types.Object, ratios=(("MEDIUM", 0.5), ("LOW", 0.25), ("VERYLOW", 0.1))):
    """Genera LOD con Decimate (collapse) partendo dal LOD High. Controlla sempre il risultato a occhio."""
    high = model_obj.data
    for lod, ratio in ratios:
        tmp = bpy.data.objects.new("tmp_lod", high.copy())
        bpy.context.collection.objects.link(tmp)
        mod = tmp.modifiers.new("dec", "DECIMATE")
        mod.ratio = ratio
        _select_only([tmp])
        bpy.ops.object.modifier_apply(modifier=mod.name)
        me = tmp.data
        me.name = f"{model_obj.name}.{lod.lower()}"
        bpy.data.objects.remove(tmp, do_unlink=True)
        add_lod(model_obj, lod, me)
    model_obj.sz_lods.active_lod_level = _props().LODLevel.HIGH


def set_lod_distances(drawable: bpy.types.Object, high=25.0, med=50.0, low=100.0, vlow=200.0):
    """Distanze (m) fino a cui si usa ciascun LOD del drawable. Default Sollumz = 9998 (= sempre LOD High):
    se crei LOD Medium/Low/VeryLow DEVI abbassarle, altrimenti non verranno mai usati.
    L'ultima (vlow) di solito = lodDist dell'archetipo (oltre, il prop sparisce)."""
    dp = drawable.drawable_properties
    dp.lod_dist_high, dp.lod_dist_med, dp.lod_dist_low, dp.lod_dist_vlow = high, med, low, vlow


# --------------------------------------------------------------------------------------------
# Materiali / shader
# --------------------------------------------------------------------------------------------
SAMPLER_ALIASES = {
    "diffuse": "DiffuseSampler", "albedo": "DiffuseSampler", "color": "DiffuseSampler",
    "normal": "BumpSampler", "bump": "BumpSampler",
    "spec": "SpecSampler", "specular": "SpecSampler",
    "tint": "TintPaletteSampler", "palette": "TintPaletteSampler",
    "detail": "DetailSampler", "env": "EnvironmentSampler", "height": "heightSampler",
}
NON_COLOR_SAMPLERS = {"BumpSampler", "SpecSampler", "heightSampler", "DetailSampler"}


def load_image(path: str | os.PathLike, non_color: bool = False) -> bpy.types.Image:
    """Carica (o riusa) un'immagine. Per l'export va bene SOLO .dds: il nome texture = nome file senza estensione."""
    path = str(Path(path).resolve())
    for img in bpy.data.images:
        if img.filepath and os.path.normcase(bpy.path.abspath(img.filepath)) == os.path.normcase(path):
            return img
    img = bpy.data.images.load(path, check_existing=True)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    return img


def new_shader_material(shader: str = "default.sps", name: Optional[str] = None) -> bpy.types.Material:
    """Crea un materiale Sollumz (es. 'normal_spec.sps'). Vedi references/shaders-catalog.md."""
    sm = szm("ydr.shader_materials")
    if not shader.endswith(".sps"):
        shader += ".sps"
    mat = sm.create_shader(shader)
    if name:
        mat.name = name
    return mat


def set_shader_textures(mat: bpy.types.Material, textures: dict, embedded: bool = True):
    """
    textures: {'DiffuseSampler'|'diffuse': path_or_Image, 'BumpSampler'|'normal': ..., 'SpecSampler'|'spec': ...}
    embedded=True -> texture dentro il .ydr; False -> vanno in un .ytd (vedi make_txd) e l'archetipo
    deve puntare a quel ytd (texture_dictionary).
    """
    nodes = mat.node_tree.nodes
    for key, value in textures.items():
        sampler = SAMPLER_ALIASES.get(key.lower(), key)
        node = nodes.get(sampler)
        if node is None or not isinstance(node, bpy.types.ShaderNodeTexImage):
            raise KeyError(f"Lo shader '{mat.shader_properties.filename}' non ha il sampler '{sampler}'. "
                           f"Disponibili: {[n.name for n in nodes if isinstance(n, bpy.types.ShaderNodeTexImage)]}")
        img = value if isinstance(value, bpy.types.Image) else load_image(value, sampler in NON_COLOR_SAMPLERS)
        if sampler in NON_COLOR_SAMPLERS:
            img.colorspace_settings.name = "Non-Color"
        node.image = img
        node.texture_properties.embedded = embedded


def set_shader_params(mat: bpy.types.Material, **params):
    """Imposta parametri numerici dello shader (es. emissiveMultiplier=5.0, bumpiness=1.0, specularIntensityMult=0.5).
    Valori vettoriali: passa una tupla/lista."""
    nodes = mat.node_tree.nodes
    for pname, value in params.items():
        node = nodes.get(pname)
        if node is None or not hasattr(node, "num_cols"):
            raise KeyError(f"Parametro '{pname}' non presente nello shader '{mat.shader_properties.filename}'")
        values = list(value) if isinstance(value, (list, tuple)) else [value]
        for i, v in enumerate(values):
            node.set(i, float(v))


def assign_material(obj: bpy.types.Object, mat: bpy.types.Material, replace: bool = True):
    """Assegna il materiale e crea UV/Color attribute mancanti richiesti dallo shader."""
    me = obj.data
    if replace:
        me.materials.clear()
    me.materials.append(mat)
    refresh_mesh_attributes(obj)


def refresh_mesh_attributes(obj: bpy.types.Object):
    """Rinomina/crea UV map e Color attribute richiesti dagli shader Sollumz assegnati."""
    me = obj.data
    mh = szm("tools.meshhelper")
    mh.mesh_rename_uv_maps_by_order(me)
    mh.mesh_rename_color_attrs_by_order(me)
    mh.mesh_add_missing_uv_maps(me)
    mh.mesh_add_missing_color_attrs(me)
    sm = szm("ydr.shader_materials")
    if sm.obj_has_tint_mats(obj):
        sm.create_tinted_shader_graph(obj)


def material(obj: bpy.types.Object, shader: str, textures: dict, embedded: bool = True,
             name: Optional[str] = None, replace: bool = True, **params) -> bpy.types.Material:
    """Scorciatoia: crea materiale Sollumz + texture + parametri e lo assegna all'oggetto."""
    mat = new_shader_material(shader, name)
    set_shader_textures(mat, textures, embedded)
    if params:
        set_shader_params(mat, **params)
    assign_material(obj, mat, replace=replace)
    return mat


def convert_existing_materials(obj: bpy.types.Object, shader: Optional[str] = None):
    """Converte materiali Principled BSDF esistenti in Sollumz (auto: default/normal/spec/normal_spec)."""
    mats_mod = szm("ydr.operators.materials")
    for mat in list(obj.data.materials):
        if mat is None or mat.sollum_type == _props().MaterialType.SHADER:
            continue
        conv = mats_mod.MaterialConverter(obj, mat)
        conv.convert(shader if shader.endswith(".sps") else shader + ".sps") if shader else conv.auto_convert()


# --------------------------------------------------------------------------------------------
# Texture dictionary (.ytd)
# --------------------------------------------------------------------------------------------
def make_txd(name: str, images: Iterable[bpy.types.Image | str] = (), source_objects: Iterable[bpy.types.Object] = ()):
    """Crea un Texture Dictionary di scena (esportato come <name>.ytd). Le immagini devono essere .dds."""
    txds = bpy.context.scene.sz_txds
    txd = txds.new_texture_dictionary(name)
    for img in images:
        txd.new_texture(img if isinstance(img, bpy.types.Image) else load_image(img))
    for obj in source_objects:
        src = txd.new_source()
        src.source_type = "OBJECT"
        src.object_name = obj.name
        src.object_include_children = True
    return txd


# --------------------------------------------------------------------------------------------
# Collisioni
# --------------------------------------------------------------------------------------------
def collision_material_index(name: str) -> int:
    cm = szm("ybn.collision_materials")
    names = [m.name for m in cm.collisionmats]
    name = name.upper()
    if name not in names:
        raise KeyError(f"Materiale collisione '{name}' sconosciuto. Esempi: CONCRETE, METAL_SOLID_MEDIUM, "
                       f"WOOD_SOLID_MEDIUM, PLASTIC, GLASS_SHOOT_THROUGH, CARDBOARD_BOX...")
    return names.index(name)


def _collision_material(name: str) -> bpy.types.Material:
    return szm("ybn.collision_materials").create_collision_material_from_index(collision_material_index(name))


def _apply_flags(obj, preset="General (Default)"):
    ok = szm("tools.boundhelper").apply_flag_preset(obj, preset)
    if not ok:
        raise RuntimeError(f"Flag preset '{preset}' non trovato")


def _new_bound_shape(kind: str):
    bh = szm("tools.boundhelper")
    t = ST()
    mapping = {"box": t.BOUND_BOX, "sphere": t.BOUND_SPHERE, "capsule": t.BOUND_CAPSULE,
               "cylinder": t.BOUND_CYLINDER, "disc": t.BOUND_DISC,
               "poly_box": t.BOUND_POLY_BOX, "poly_sphere": t.BOUND_POLY_SPHERE,
               "poly_capsule": t.BOUND_POLY_CAPSULE, "poly_cylinder": t.BOUND_POLY_CYLINDER}
    return bh.create_bound_shape(mapping[kind])


def _fit_bound_to(obj_bound, src_bbox_min: Vector, src_bbox_max: Vector, kind: str):
    """Dimensiona una bound primitiva sul bounding box dato (spazio del genitore)."""
    size = src_bbox_max - src_bbox_min
    center = (src_bbox_min + src_bbox_max) / 2
    obj_bound.location = center
    if kind in ("box", "poly_box"):
        # le primitive Sollumz sono cubi 1x1x1 (mesh) -> scala nei dati per non lasciare scale sull'oggetto
        obj_bound.data.transform(Matrix.Diagonal((size.x, size.y, size.z, 1.0)))
    elif kind in ("sphere", "poly_sphere"):
        obj_bound.bound_radius = max(size) / 2 if hasattr(obj_bound, "bound_radius") else None
    return obj_bound


def eval_matrix_world(o: bpy.types.Object) -> Matrix:
    """matrix_world valutata (include vincoli COPY_TRANSFORMS verso gli ossi)."""
    bpy.context.view_layer.update()
    return o.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world.copy()


def bbox_of(objs: Iterable[bpy.types.Object], space: Optional[Matrix] = None) -> tuple[Vector, Vector]:
    inv = space.inverted() if space is not None else Matrix()
    pts = []
    for o in objs:
        if o.type != "MESH":
            continue
        mw = inv @ eval_matrix_world(o)
        pts += [mw @ v.co for v in o.data.vertices]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def add_embedded_collision(drawable: bpy.types.Object, mode: str = "box", material: str = "DEFAULT",
                           mesh: Optional[bpy.types.Object] = None, flag_preset: str = "General (Default)",
                           boxes: Optional[Sequence[tuple[Sequence[float], Sequence[float]]]] = None):
    """
    Collisione EMBEDDED nel .ydr (prop spawnati/piazzati: e' quella che serve quasi sempre).
    mode:
      'box'   -> una Bound Box sul bounding box dei modelli (veloce, ottima per casse/mobili squadrati)
      'boxes' -> piu' Bound Poly Box da `boxes=[(min_xyz, max_xyz), ...]` (spazio del drawable)
      'mesh'  -> Bound Poly Mesh da `mesh` (una low-poly dedicata, <= ~500 tri, convessa a pezzi)
      'hull'  -> convex hull automatico dei modelli (buon default per forme organiche semplici)
    Gerarchia creata: Drawable > Bound Composite > (Bound Box | Bound GeometryBVH > poly...)
    """
    bh = szm("tools.boundhelper")
    bl = szm("tools.blenderhelper")
    t = ST()
    models = [c for c in drawable.children_recursive if c.sollum_type == t.DRAWABLE_MODEL]
    comp = bl.create_empty_object(t.BOUND_COMPOSITE, f"{drawable.name}.col")
    comp.parent = drawable
    comp.matrix_parent_inverse = Matrix()
    comp.location = (0, 0, 0)
    mat = _collision_material(material)

    if mode == "box":
        mn, mx = bbox_of(models, drawable.matrix_world)
        b = _new_bound_shape("box")
        b.parent = comp
        _fit_bound_to(b, mn, mx, "box")
        b.data.materials.append(mat)
        _apply_flags(b, flag_preset)
        return comp

    bvh = bl.create_empty_object(t.BOUND_GEOMETRYBVH, f"{drawable.name}.bvh")
    bvh.parent = comp
    _apply_flags(bvh, flag_preset)

    if mode == "boxes":
        assert boxes, "mode='boxes' richiede boxes=[(min,max), ...]"
        for mn, mx in boxes:
            b = _new_bound_shape("poly_box")
            b.parent = bvh
            _fit_bound_to(b, Vector(mn), Vector(mx), "poly_box")
            b.data.materials.append(mat)
    elif mode in ("mesh", "hull"):
        if mode == "hull":
            import bmesh
            bm = bmesh.new()
            for m in models:
                tmp = m.data.copy()
                tmp.transform(drawable.matrix_world.inverted() @ eval_matrix_world(m))
                bm.from_mesh(tmp)
                bpy.data.meshes.remove(tmp)
            res = bmesh.ops.convex_hull(bm, input=bm.verts)
            for g in res.get("geom_interior", []) + res.get("geom_unused", []):
                if isinstance(g, bmesh.types.BMVert) and g.is_valid:
                    pass
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
            bmesh.ops.triangulate(bm, faces=bm.faces)
            me = bpy.data.meshes.new(f"{drawable.name}.hull")
            bm.to_mesh(me)
            bm.free()
            col_obj = bpy.data.objects.new(f"{drawable.name}.hull", me)
            bpy.context.collection.objects.link(col_obj)
        else:
            assert mesh is not None, "mode='mesh' richiede mesh=<oggetto low-poly>"
            col_obj = mesh
            col_obj.data.transform(drawable.matrix_world.inverted() @ col_obj.matrix_world)
            col_obj.matrix_world = Matrix()
        col_obj.sollum_type = t.BOUND_POLY_TRIANGLE
        col_obj.data.materials.clear()
        col_obj.data.materials.append(mat)
        col_obj.parent = bvh
        col_obj.matrix_parent_inverse = Matrix()
        col_obj.location = (0, 0, 0)
    else:
        raise ValueError(mode)
    return comp


def make_static_collision(name: str, meshes: Sequence[bpy.types.Object], material: str = "CONCRETE",
                          flag_preset: str = "General (Default)") -> bpy.types.Object:
    """Collisione statica separata (.ybn) in COORDINATE MONDO (per mappe: affianca una ymap)."""
    bl = szm("tools.blenderhelper")
    t = ST()
    comp = bl.create_empty_object(t.BOUND_COMPOSITE, name)
    bvh = bl.create_empty_object(t.BOUND_GEOMETRYBVH, f"{name}.bvh")
    bvh.parent = comp
    _apply_flags(bvh, flag_preset)
    mat = _collision_material(material)
    for m in meshes:
        apply_transforms(m, location=True, rotation=True, scale=True)
        m.sollum_type = t.BOUND_POLY_TRIANGLE
        m.data.materials.clear()
        m.data.materials.append(mat)
        m.parent = bvh
    return comp


# --------------------------------------------------------------------------------------------
# Luci (embedded nel drawable)
# --------------------------------------------------------------------------------------------
FLASHINESS = ['CONSTANT', 'RANDOM', 'RANDOM_OVERRIDE_IF_WET', 'ONCE_PER_SECOND', 'TWICE_PER_SECOND',
              'FIVE_PER_SECOND', 'RANDOM_FLASHINESS', 'OFF', 'UNUSED', 'ALARM', 'ON_WHEN_RAINING', 'CYCLE_1',
              'CYCLE_2', 'CYCLE_3', 'DISCO', 'CANDLE', 'PLANE', 'FIRE', 'THRESHOLD', 'ELECTRIC', 'STROBE']


def add_light(drawable: bpy.types.Object, kind: str = "point", location=(0, 0, 1), color=(1.0, 0.85, 0.6),
              intensity: float = 5.0, falloff: float = 6.0, falloff_exponent: float = 8.0,
              cone_outer_deg: float = 60.0, cone_inner_deg: float = 30.0, direction=(0, 0, -1),
              flashiness: int | str = 0, time_flags_all_day: bool = True, cast_shadows: bool = False,
              corona_intensity: float = 1.0, corona_size: float = 0.5, bone: Optional[str] = None):
    """Luce embedded (point/spot/capsule). flashiness: 0 costante, 15 candela, 17 fuoco, 19 elettrico, 20 strobo."""
    props = _props()
    bl = szm("tools.blenderhelper")
    lt = {"point": props.LightType.POINT, "spot": props.LightType.SPOT, "capsule": props.LightType.CAPSULE}[kind]
    ldata = bpy.data.lights.new(name=f"{drawable.name}_light", type="SPOT" if kind in ("spot", "capsule") else "POINT")
    lobj = bl.create_blender_object(props.SollumType.LIGHT, ldata.name, ldata)
    ldata.sollum_type = lt
    if kind == "capsule":
        ldata.is_capsule = True
    lobj.parent = drawable
    lobj.location = location
    d = Vector(direction).normalized()
    lobj.rotation_mode = "QUATERNION"
    lobj.rotation_quaternion = Vector((0, 0, -1)).rotation_difference(d)
    ldata.color = color
    lp = ldata.light_properties
    lp.intensity = intensity
    lp.falloff = falloff
    lp.falloff_exponent = falloff_exponent
    lp.corona_intensity = corona_intensity
    lp.corona_size = corona_size
    if kind == "spot":
        lp.cone_outer_angle = math.radians(cone_outer_deg)
        lp.cone_inner_angle = math.radians(cone_inner_deg)
    lp.flashiness = FLASHINESS[flashiness] if isinstance(flashiness, int) else flashiness.upper()
    if time_flags_all_day:
        ldata.time_flags.total = str((1 << 24) - 1)
    if cast_shadows:
        ldata.light_flags.cast_shadows = True
    if bone is not None and drawable.type == "ARMATURE":
        bl.add_child_of_bone_constraint(lobj, drawable, bone)
    return lobj


# --------------------------------------------------------------------------------------------
# Scheletro / prop animati
# --------------------------------------------------------------------------------------------
def make_animated_drawable(name: str, parts: dict, root_location=(0, 0, 0)) -> bpy.types.Object:
    """
    Prop animato (rigid): un'armatura-Drawable con un osso root + un osso per parte mobile.
    parts = {
       "bone_name": {"mesh": obj, "pivot": (x,y,z) mondo, "parent": "root" | altro bone},
       ...
    }
    Il root bone ("<name>_root" -> tag 0) tiene le parti statiche (passa "root" come chiave per il corpo).
    Ogni mesh viene legata al suo osso con il vincolo COPY_TRANSFORMS di Sollumz (non vertex group).
    Gli ossi puntano lungo +Y senza roll => matrice osso = sola traslazione (keyframe intuitivi).
    """
    for p in check_asset_name(name):
        print("[sz_fivem][WARN]", p)
    t = ST()
    bl = szm("tools.blenderhelper")
    dh = szm("tools.drawablehelper")
    arm_data = bpy.data.armatures.new(name)
    arm = bpy.data.objects.new(name, arm_data)
    bpy.context.collection.objects.link(arm)
    arm.location = root_location
    arm.sollum_type = t.DRAWABLE
    _select_only([arm])
    bpy.ops.object.mode_set(mode="EDIT")
    root_name = "root" if "root" in parts else f"{name}_root"
    eb_root = arm_data.edit_bones.new(root_name)
    eb_root.head = (0, 0, 0)
    eb_root.tail = (0, 0.1, 0)
    eb_root.roll = 0
    inv_root = Matrix.Translation(-Vector(root_location))
    for bname, spec in parts.items():
        if bname == root_name:
            continue
        pivot = inv_root @ Vector(spec.get("pivot", (0, 0, 0)))
        eb = arm_data.edit_bones.new(bname)
        eb.head = pivot
        eb.tail = pivot + Vector((0, 0.1, 0))
        eb.roll = 0
        eb.parent = arm_data.edit_bones[spec.get("parent", root_name)] if spec.get("parent", "root") != "root" \
            else eb_root
    bpy.ops.object.mode_set(mode="OBJECT")

    for bname, spec in parts.items():
        mesh_obj = spec["mesh"]
        bone_key = root_name if bname in ("root", root_name) else bname
        bone = arm_data.bones[bone_key]
        # porta la geometria nello spazio dell'osso (origine = pivot)
        bone_world = arm.matrix_world @ bone.matrix_local
        mesh_obj.data.transform(bone_world.inverted() @ mesh_obj.matrix_world)
        mesh_obj.matrix_world = Matrix()
        dh.convert_obj_to_model(mesh_obj)
        if not mesh_obj.name.endswith(".model"):
            mesh_obj.name = f"{mesh_obj.name}.model"
        mesh_obj.parent = arm
        mesh_obj.matrix_parent_inverse = Matrix()
        bl.add_child_of_bone_constraint(mesh_obj, arm, bone_key)
        # flag DOF utili per ossi animati
        if bone_key != root_name:
            bone.bone_properties.flags_enum = {"RotX", "RotY", "RotZ", "TransX", "TransY", "TransZ"}
    return arm


DOOR_TYPES = {
    # tipo: (special attribute, dove va l'origine)
    "swing": ("IS_NORMAL_DOOR", "cardine: centro del lato del cardine, a terra"),
    "sliding": ("IS_SLIDING_DOOR", "angolo in basso"),
    "garage": ("IS_GARAGE_DOOR", "centro in basso"),
    "sliding_vertical": ("IS_SLIDING_DOOR_VERTICAL", "centro in basso"),
    "barrier": ("IS_BARRIER_DOOR", "perno della sbarra"),
}


def make_door(name: str, mesh: bpy.types.Object, hinge_world: Sequence[float], kind: str = "swing",
              collision_material: str = "WOOD_SOLID_MEDIUM") -> bpy.types.Object:
    """
    Porta pronta per il door system: Drawable-armatura con UN osso (tag 0) sul cardine, mesh legata all'osso,
    collisione box embedded. L'archetipo va creato con add_door_archetype(). Lo stesso schema delle porte
    vanilla (v_ilev_*_door*). Il pannello deve essere "chiuso" lungo +X o -X dal cardine.
    """
    if kind not in DOOR_TYPES:
        raise ValueError(f"kind in {list(DOOR_TYPES)}")
    hinge = Vector(hinge_world)
    mesh.data.transform(mesh.matrix_world)
    mesh.matrix_world = Matrix()
    mesh.data.transform(Matrix.Translation(-hinge))
    arm = make_animated_drawable(name, {"root": {"mesh": mesh}})
    add_embedded_collision(arm, "box", material=collision_material)
    arm["sz_door_kind"] = kind
    return arm


def add_door_archetype(ytyp, door: bpy.types.Object, kind: Optional[str] = None, lod_dist: float = 100.0):
    kind = kind or door.get("sz_door_kind", "swing")
    arch = add_archetype(ytyp, door, flags=("dynamic", "enable_door_physics"), lod_dist=lod_dist)
    arch.special_attribute = DOOR_TYPES[kind][0]
    return arch


def keyframe_bone(arm: bpy.types.Object, bone: str, frame: int, rot_euler_deg=None, loc=None, scale=None):
    """Keyframe su un osso. Usa SEMPRE quaternion (Sollumz esporta solo location/rotation_quaternion/scale)."""
    pb = arm.pose.bones[bone]
    pb.rotation_mode = "QUATERNION"
    if rot_euler_deg is not None:
        from mathutils import Euler
        pb.rotation_quaternion = Euler([math.radians(a) for a in rot_euler_deg], "XYZ").to_quaternion()
        pb.keyframe_insert("rotation_quaternion", frame=frame)
    if loc is not None:
        pb.location = loc
        pb.keyframe_insert("location", frame=frame)
    if scale is not None:
        pb.scale = scale
        pb.keyframe_insert("scale", frame=frame)


def record_action(target_id: bpy.types.ID, action_name: str, keyframes_fn) -> bpy.types.Action:
    """Crea una nuova Action eseguendo keyframes_fn() e la stacca dal target (pronta per un Clip)."""
    if target_id.animation_data is None:
        target_id.animation_data_create()
    target_id.animation_data.action = None
    keyframes_fn()
    action = target_id.animation_data.action
    action.name = action_name
    action.use_fake_user = True
    for fc in _fcurves(action):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    target_id.animation_data.action = None
    return action


def _fcurves(action):
    try:
        return list(szm("tools.animationhelper").action_fcurves(action))
    except Exception:
        return list(getattr(action, "fcurves", []))


def make_clip_dictionary(name: str) -> bpy.types.Object:
    """Crea il template Clip Dictionary (diventera' <name>.ycd). Convenzione nomi: minuscolo, es. 'myrp_door_anims'."""
    from importlib import import_module
    ycdimport = import_module(f"{sz_pkg()}.ycd.ycdimport")
    cd, clips, anims = ycdimport.create_clip_dictionary_template(name)
    return cd


def add_clip(clip_dict: bpy.types.Object, clip_name: str, action: bpy.types.Action, target: bpy.types.ID,
             start_frame: Optional[int] = None, end_frame: Optional[int] = None, uv: bool = False) -> bpy.types.Object:
    """
    Aggiunge Animation + Clip al dizionario.
    - clip_name = nome usato da PlayEntityAnim(entity, clip_name, ycd_name, ...).
      Per 'Auto Start Anim' usa clip_name = nome del modello (archetipo).
    - target = armatura DATA (arm.data) per animazioni d'ossa; materiale per UV anim (uv=True).
    - Durata = frame/30 s.
    """
    t = ST()
    ycdimport = szm("ycd.ycdimport")
    clips_obj = next(c for c in clip_dict.children if c.sollum_type == t.CLIPS)
    anims_obj = next(c for c in clip_dict.children if c.sollum_type == t.ANIMATIONS)
    anim = ycdimport.create_anim_obj(t.ANIMATION)
    anim.name = clip_name
    anim.parent = anims_obj
    ap = anim.animation_properties
    ap.hash = clip_name
    ap.target_id_type = "MATERIAL" if uv else ("ARMATURE" if isinstance(target, bpy.types.Armature) else "CAMERA")
    ap.target_id = target
    ap.action = action
    fr = action.frame_range
    s = int(fr[0]) if start_frame is None else start_frame
    e = int(fr[1]) if end_frame is None else end_frame

    clip = ycdimport.create_anim_obj(t.CLIP)
    clip.name = f"{clip_name}.clip"
    clip.parent = clips_obj
    cp = clip.clip_properties
    cp.hash = clip_name
    cp.name = f"{clip_name}.clip"
    cp.duration = max((e - s), 1) / bpy.context.scene.render.fps
    link = cp.animations.add()
    link.animation = anim
    link.start_frame = s
    link.end_frame = e
    if uv:
        # per le UV anim il gioco cerca il clip con hash = joaat(modello) + indice materiale + 1
        _select_only([clip])
        ok = szm("tools.animationhelper").update_uv_clip_hash(clip)
        if not ok:
            raise RuntimeError("Impossibile calcolare l'hash del clip UV: il materiale deve essere usato da un "
                               "Drawable Model dentro un Drawable gia' creato.")
    return clip


def uv_scroll_action(mat: bpy.types.Material, frames: int = 60, du: float = 1.0, dv: float = 0.0) -> bpy.types.Action:
    """Action che fa scorrere le UV (nastri, insegne, cascate, schermi finti). Lo shader deve supportare
    globalAnimUV0/1 (default, normal, spec, emissive, alpha, cutout, ... NON normal_spec)."""
    tr = mat.animation_tracks

    def keys():
        for f, k in ((0, 0.0), (frames, 1.0)):
            tr.uv0 = (1.0, 0.0, du * k)
            tr.uv1 = (0.0, 1.0, dv * k)
            mat.keyframe_insert("animation_tracks.uv0", frame=f)
            mat.keyframe_insert("animation_tracks.uv1", frame=f)
    return record_action(mat, f"{mat.name}_uvscroll", keys)


# --------------------------------------------------------------------------------------------
# Frammenti (.yft) - prop fisici/rompibili
# --------------------------------------------------------------------------------------------
def make_fragment(name: str, parts: dict) -> bpy.types.Object:
    """
    Fragment (.yft): prop con parti fisiche/separabili (lampioni, cartelli, casse con sportelli, barriere).
    parts = {
      "<bone>": {
        "mesh": obj,                       # geometria della parte (gia' con materiale Sollumz)
        "pivot": (x,y,z),                  # mondo; per il root ignorato (= origine fragment)
        "parent": "<bone>" | None,         # default: root
        "collision": "box" | "hull" | obj, # forma della collisione legata all'osso
        "material": "METAL_SOLID_MEDIUM",  # materiale collisione
        "mass": 10.0,                      # kg della parte
        "physics": True,                   # osso con fisica (ignorato per root: sempre True)
        "strength": 100.0,                 # forza per staccarla; -1 = non si stacca (cerniera/oscilla)
      }, ...
    }
    La chiave "root" e' il corpo principale (osso radice, tag 0). Archetipo: flag 'dynamic'.
    """
    for p in check_asset_name(name):
        print("[sz_fivem][WARN]", p)
    t = ST()
    bl = szm("tools.blenderhelper")
    dh = szm("tools.drawablehelper")
    arm_data = bpy.data.armatures.new(f"{name}_skel")
    frag = bpy.data.objects.new(name, arm_data)
    bpy.context.collection.objects.link(frag)
    frag.sollum_type = t.FRAGMENT
    _select_only([frag])
    bpy.ops.object.mode_set(mode="EDIT")
    root_name = name  # convenzione vanilla: osso radice col nome del prop
    eb_root = arm_data.edit_bones.new(root_name)
    eb_root.head, eb_root.tail, eb_root.roll = (0, 0, 0), (0, 0.05, 0), 0
    for bname, spec in parts.items():
        if bname == "root":
            continue
        pv = Vector(spec.get("pivot", (0, 0, 0)))
        eb = arm_data.edit_bones.new(bname)
        eb.head, eb.tail, eb.roll = pv, pv + Vector((0, 0.05, 0)), 0
        par = spec.get("parent")
        eb.parent = arm_data.edit_bones[par] if par and par != "root" else eb_root
    bpy.ops.object.mode_set(mode="OBJECT")

    drawable = bl.create_empty_object(t.DRAWABLE, f"{name}.mesh")
    drawable.parent = frag
    comp = bl.create_empty_object(t.BOUND_COMPOSITE, f"{name}.col")
    comp.parent = frag

    for bname, spec in parts.items():
        bone_key = root_name if bname == "root" else bname
        bone = arm_data.bones[bone_key]
        bone_world = frag.matrix_world @ bone.matrix_local
        mesh_obj = spec["mesh"]
        world_pts_obj = mesh_obj  # per collisione auto
        world_mesh = mesh_obj.data.copy()
        world_mesh.transform(mesh_obj.matrix_world)
        mesh_obj.data.transform(bone_world.inverted() @ mesh_obj.matrix_world)
        mesh_obj.matrix_world = Matrix()
        dh.convert_obj_to_model(mesh_obj)
        if not mesh_obj.name.endswith(".model"):
            mesh_obj.name = f"{mesh_obj.name}.model"
        mesh_obj.parent = drawable
        mesh_obj.matrix_parent_inverse = Matrix()
        bl.add_child_of_bone_constraint(mesh_obj, frag, bone_key)

        coll = spec.get("collision", "box")
        if coll:
            mat = _collision_material(spec.get("material", "DEFAULT"))
            if coll == "box":
                xs = [v.co for v in world_mesh.vertices]
                mn = Vector((min(p.x for p in xs), min(p.y for p in xs), min(p.z for p in xs)))
                mx = Vector((max(p.x for p in xs), max(p.y for p in xs), max(p.z for p in xs)))
                inv = bone_world.inverted()
                mn_l, mx_l = inv @ mn, inv @ mx
                b = _new_bound_shape("box")
                _fit_bound_to(b, Vector(map(min, mn_l, mx_l)), Vector(map(max, mn_l, mx_l)), "box")
                center_local = b.location.copy()
            else:
                import bmesh
                bm = bmesh.new()
                src = world_mesh if coll == "hull" else coll.data.copy()
                if coll != "hull":
                    src.transform(coll.matrix_world)
                bm.from_mesh(src)
                bmesh.ops.convex_hull(bm, input=bm.verts)
                bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
                bmesh.ops.triangulate(bm, faces=bm.faces)
                bm.transform(bone_world.inverted())
                me = bpy.data.meshes.new(f"{bname}.col")
                bm.to_mesh(me)
                bm.free()
                b = bl.create_blender_object(t.BOUND_GEOMETRY, f"{bname}.col", me)
                if coll != "hull":
                    bpy.data.objects.remove(coll, do_unlink=True)
                center_local = Vector()
            b.name = f"{bname}.col"
            b.parent = comp
            b.matrix_parent_inverse = Matrix()
            b.data.materials.append(mat)
            _apply_flags(b, spec.get("flags", "General (Default)"))
            bl.add_child_of_bone_constraint(b, frag, bone_key)
            b.location = center_local
            b.child_properties.mass = float(spec.get("mass", 10.0))
        bpy.data.meshes.remove(world_mesh)
        # il root DEVE avere fisica (gruppo radice), altrimenti la sua collisione non viene esportata
        bone.sollumz_use_physics = True if bname == "root" else bool(spec.get("physics", True))
        if "strength" in spec:
            bone.group_properties.strength = float(spec["strength"])
    return frag


def set_bone_physics(arm_data: bpy.types.Armature, bone: str, use_physics: bool = True, strength: float = -1.0):
    """strength=-1: la parte reagisce alla fisica ma non si stacca (porte, sportelli); >0 si stacca."""
    b = arm_data.bones[bone]
    b.sollumz_use_physics = use_physics
    b.group_properties.strength = strength


# --------------------------------------------------------------------------------------------
# YTYP / archetipi
# --------------------------------------------------------------------------------------------
ARCH_FLAGS = {
    "wet_road_reflection": 1 << 0, "dont_fade": 1 << 1, "draw_last": 1 << 2, "climbable_by_ai": 1 << 3,
    "suppress_hd_txds": 1 << 4, "static": 1 << 5, "disable_alpha_sorting": 1 << 6, "tough_for_bullets": 1 << 7,
    "is_generic": 1 << 8, "has_anim": 1 << 9, "has_uv_anim": 1 << 10, "shadow_only": 1 << 11,
    "damage_model": 1 << 12, "dont_cast_shadows": 1 << 13, "cast_texture_shadows": 1 << 14,
    "dont_collide_with_flyer": 1 << 15, "double_sided": 1 << 16, "dynamic": 1 << 17,
    "override_physics_bounds": 1 << 18, "auto_start_anim": 1 << 19, "has_pre_reflected_water_proxy": 1 << 20,
    "has_drawable_proxy_for_water_reflections": 1 << 21, "no_ai_cover": 1 << 22, "no_player_cover": 1 << 23,
    "is_ladder_deprecated": 1 << 24, "has_cloth": 1 << 25, "enable_door_physics": 1 << 26,
    "is_fixed_for_navigation": 1 << 27, "dont_avoid_by_peds": 1 << 28, "use_ambient_scale": 1 << 29,
    "is_debug": 1 << 30, "has_alpha_shadow": 1 << 31,
}

SPECIAL_ATTRIBUTES = {  # nome Sollumz enum
    "none": "NOTHING_SPECIAL", "door": "IS_NORMAL_DOOR", "garage_door": "IS_GARAGE_DOOR",
    "sliding_door": "IS_SLIDING_DOOR", "sliding_door_vertical": "IS_SLIDING_DOOR_VERTICAL",
    "barrier_door": "IS_BARRIER_DOOR", "rail_crossing_door": "IS_RAIL_CROSSING_DOOR",
    "traffic_light": "IS_TRAFFIC_LIGHT", "street_light": "IS_STREET_LIGHT", "bush": "NOISY_BUSH",
    "single_axis_rotation": "SINGLE_AXIS_ROTATION", "clock": "CLOCK",
}


def flags_value(*names: str) -> int:
    v = 0
    for n in names:
        v |= ARCH_FLAGS[n]
    return v


def get_or_make_ytyp(name: str):
    sc = bpy.context.scene
    for i, y in enumerate(sc.ytyps):
        if y.name == name:
            sc.ytyp_index = i
            return y
    y = sc.ytyps.add()
    y.name = name
    sc.ytyp_index = len(sc.ytyps) - 1
    return y


def add_archetype(ytyp, asset: bpy.types.Object, flags: Iterable[str] = (), lod_dist: float = 100.0,
                  texture_dictionary: Optional[str] = None, clip_dictionary: str = "",
                  special: str = "none", hd_texture_dist: float = 60.0):
    """
    Aggiunge un archetipo BASE per `asset` (Drawable/Fragment). Calcola bbox/sfera all'export.
    texture_dictionary: None -> nome asset se ha texture embedded, altrimenti '' ; passa il nome del .ytd
    se usi un ytd esterno (OBBLIGATORIO per texture non embedded, es. schermi DUI).
    Flag tipici: prop statico -> ('static',) ; prop fisico -> ('dynamic',) ; animato -> ('has_anim',
    'auto_start_anim'?) ; UV -> ('has_uv_anim','auto_start_anim') ; porta -> ('dynamic','enable_door_physics').
    """
    props = _props()
    arch = ytyp.new_archetype(props.ArchetypeType.BASE)
    arch.name = asset.name
    arch.asset = asset  # update_asset: asset_name, asset_type, physics_dictionary, txd
    arch.lod_dist = lod_dist
    arch.hd_texture_dist = hd_texture_dist
    arch.flags.total = str(flags_value(*flags))
    arch.special_attribute = SPECIAL_ATTRIBUTES.get(special, special)
    if texture_dictionary is not None:
        arch.texture_dictionary = texture_dictionary
    arch.clip_dictionary = clip_dictionary
    return arch


# --------------------------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------------------------
def export(out_dir: str | os.PathLike, objects: Sequence[bpy.types.Object] = (), formats=("NATIVE", "CWXML"),
           versions=("GEN8", "GEN9"), ytyps: bool = True, ytds: bool = True, ymaps: bool = False,
           apply_transforms: bool = False) -> list[str]:
    """
    Esporta con l'operatore ufficiale sollumz.export_assets.
    - objects: radici da esportare (Drawable, Fragment, Bound Composite, Clip Dictionary). Vuoto = tutto.
    - formats: 'NATIVE' (binario, richiede PyMateria = solo Windows) e/o 'CWXML' (.xml da convertire con CodeWalker).
      Se NATIVE non e' disponibile viene saltato automaticamente.
    - versions: GEN8 = FiveM Legacy (cartella stream/), GEN9 = FiveM Enhanced (stream_enhanced/).
      Con entrambe le versioni Sollumz crea out_dir/gen8 e out_dir/gen9.
    Ritorna la lista dei file scritti.
    NB: i .ycd escono SEMPRE come .ycd.xml (va convertito con CodeWalker o tools/CwXmlToBin).
    """
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    before = {p for p in out.rglob("*") if p.is_file()}
    from szio.gta5 import AssetFormat, AssetTarget, AssetVersion, is_provider_available
    fm = {f for f in formats if any(is_provider_available(AssetTarget(AssetFormat[f], AssetVersion[v])) for v in versions)}
    if not fm:
        raise RuntimeError("Nessun formato di export disponibile (NATIVE richiede PyMateria su Windows).")
    if objects:
        _select_only(objects)
    bpy.context.view_layer.update()  # in background le matrix_world non si aggiornano da sole
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    res = bpy.ops.sollumz.export_assets(
        "EXEC_DEFAULT",
        directory=str(out) + os.sep,
        direct_export=True,
        use_custom_settings=True,
        target_formats=fm,
        target_versions=set(versions),
        limit_to_selected=bool(objects),
        export_ytyps=ytyps, export_ytyps_include="ALL",
        export_ytds=ytds, export_ytds_include="ALL",
        export_ymaps=ymaps, export_ymaps_include="ALL",
        apply_transforms=apply_transforms,
    )
    after = {p for p in out.rglob("*") if p.is_file()}
    written = sorted(str(p.relative_to(out)) for p in after - before)
    print("[sz_fivem] export", res, "->", written)
    return written


# --------------------------------------------------------------------------------------------
# Audit / lint
# --------------------------------------------------------------------------------------------
def _is_pow2(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def audit(root: Optional[bpy.types.Object] = None) -> dict:
    """
    Controlli prima dell'export. Ritorna {"errors": [...], "warnings": [...]} e stampa un riepilogo.
    Errore = l'asset non funzionera' in gioco. Warning = funziona ma e' sbagliato/rischioso.
    """
    t = ST()
    props = _props()
    bpy.context.view_layer.update()
    errors, warnings = [], []
    roots = [root] if root else [o for o in bpy.context.scene.objects if o.parent is None and
                                 o.sollum_type in (t.DRAWABLE, t.FRAGMENT, t.DRAWABLE_DICTIONARY, t.BOUND_COMPOSITE)]
    if not roots:
        errors.append("Nessun Drawable/Fragment/Bound Composite in scena.")
    for r in roots:
        errors += [f"[{r.name}] {p}" for p in check_asset_name(r.name.split(".")[0]) if "troppo" in p or "solo" in p]
        warnings += [f"[{r.name}] {p}" for p in check_asset_name(r.name.split(".")[0]) if "prefisso" in p]
        if any(abs(s - 1.0) > 1e-4 for s in r.scale):
            warnings.append(f"[{r.name}] scala dell'oggetto radice {tuple(round(s, 3) for s in r.scale)}: "
                            "applica la scala (o export con apply_transforms)")
        models = [c for c in r.children_recursive if c.sollum_type == t.DRAWABLE_MODEL]
        if r.sollum_type in (t.DRAWABLE, t.FRAGMENT) and not models:
            errors.append(f"[{r.name}] nessun Drawable Model figlio")
        tri_total = 0
        for m in models:
            me = m.data
            if any(abs(s - 1.0) > 1e-4 for s in m.scale):
                warnings.append(f"[{m.name}] scala non applicata {tuple(round(s, 3) for s in m.scale)}")
            if not me.materials or any(mt is None or mt.sollum_type != props.MaterialType.SHADER for mt in me.materials):
                errors.append(f"[{m.name}] materiali non-Sollumz o slot vuoti (usa material()/convert_existing_materials)")
            uvn = [u.name for u in me.uv_layers]
            if not uvn or uvn[0] != "UVMap 0":
                errors.append(f"[{m.name}] UV map deve chiamarsi 'UVMap 0' (trovato {uvn})")
            if "Color 1" not in me.color_attributes:
                warnings.append(f"[{m.name}] manca 'Color 1' (vertex color): il prop sara' scuro/rosa di notte")
            me.calc_loop_triangles()
            tris = len(me.loop_triangles)
            tri_total += tris
            if tris > 65000:
                errors.append(f"[{m.name}] {tris} triangoli in un solo modello: dividi la mesh (<65k vertici per geometria)")
            for mt in me.materials:
                if mt is None or not mt.node_tree:
                    continue
                for n in mt.node_tree.nodes:
                    if isinstance(n, bpy.types.ShaderNodeTexImage):
                        img = n.image
                        if img is None:
                            errors.append(f"[{mt.name}] sampler '{n.name}' senza immagine")
                            continue
                        fp = bpy.path.abspath(img.filepath)
                        if img.packed_file is None and not fp.lower().endswith(".dds"):
                            (errors if n.texture_properties.embedded else warnings).append(
                                f"[{mt.name}/{n.name}] '{img.name}' non e' .dds (converti con dds_convert.py)")
                        w, h = img.size
                        if (w, h) != (0, 0) and (not _is_pow2(w) or not _is_pow2(h)):
                            errors.append(f"[{mt.name}/{n.name}] '{img.name}' {w}x{h} non potenza di 2")
                        if max(w, h) > 2048:
                            warnings.append(f"[{mt.name}/{n.name}] '{img.name}' {w}x{h} > 2048: pesante per lo streaming")
                        tname = os.path.splitext(os.path.basename(fp))[0].lower()
                        if tname and not _NAME_RE.match(tname):
                            warnings.append(f"[{mt.name}/{n.name}] nome texture '{tname}' con caratteri non sicuri")
        if tri_total > 30000 and r.sollum_type == t.DRAWABLE:
            warnings.append(f"[{r.name}] {tri_total} triangoli (LOD High): alto per un prop, servono LOD")
        if r.type == "ARMATURE":
            roots_b = [b for b in r.data.bones if b.parent is None]
            if len(roots_b) != 1:
                errors.append(f"[{r.name}] l'armatura deve avere UN solo osso radice (trovati {len(roots_b)})")
        comps = [c for c in r.children_recursive if c.sollum_type == t.BOUND_COMPOSITE]
        if r.sollum_type == t.DRAWABLE and not comps:
            warnings.append(f"[{r.name}] nessuna collisione embedded: il player ci passera' attraverso")
        for c in r.children_recursive:
            if c.sollum_type in (t.BOUND_GEOMETRYBVH, t.BOUND_BOX, t.BOUND_SPHERE, t.BOUND_CAPSULE,
                                 t.BOUND_CYLINDER, t.BOUND_GEOMETRY):
                f1 = getattr(c, "composite_flags1", None)
                f2 = getattr(c, "composite_flags2", None)
                has_flags = any(getattr(f, k) for f in (f1, f2) if f is not None
                                for k in f.bl_rna.properties.keys() if k not in ("rna_type", "name"))
                if f1 is not None and not has_flags:
                    errors.append(f"[{c.name}] bound senza flag (applica il preset 'General (Default)')")
            if c.sollum_type in (t.BOUND_POLY_TRIANGLE, t.BOUND_POLY_BOX, t.BOUND_BOX, t.BOUND_SPHERE,
                                 t.BOUND_CAPSULE, t.BOUND_CYLINDER, t.BOUND_POLY_SPHERE,
                                 t.BOUND_POLY_CAPSULE, t.BOUND_POLY_CYLINDER):
                if c.type == "MESH" and not any(m and m.sollum_type == props.MaterialType.COLLISION
                                                for m in c.data.materials):
                    errors.append(f"[{c.name}] collisione senza materiale di collisione")
    report = {"errors": errors, "warnings": warnings}
    print(f"[sz_fivem] AUDIT: {len(errors)} errori, {len(warnings)} warning")
    for e in errors:
        print("  ERROR  ", e)
    for w in warnings:
        print("  warning", w)
    return report
