"""
build_from_spec.py - costruisce ed esporta asset FiveM da una spec JSON, 100% Python (zero UI).

Esecuzione:
  blender -b -P build_from_spec.py -- spec.json            (headless, Blender con Sollumz installato)
  python build_from_spec.py spec.json                       (se `import bpy` e' disponibile come modulo)
  da MCP/console Blender:
      import sys; sys.path.append(r"<skill>/scripts"); import build_from_spec as b; b.build("spec.json")

Formato spec: vedi ../templates/spec_examples/*.json e references/python-pipeline.md.
Percorsi relativi nella spec = relativi alla cartella del file spec.
Le texture .png/.tga/.jpg vengono convertite in .dds (stesso nome, minuscolo) in <output>/_textures.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import bpy  # noqa: E402
import sz_fivem as sz  # noqa: E402
import dds_convert  # noqa: E402

IMG_EXT = (".png", ".tga", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")


class Ctx:
    def __init__(self, spec_path: Path, spec: dict):
        self.base = spec_path.parent
        self.spec = spec
        self.out = self.path(spec.get("output", "build"))
        self.tex_dir = self.out / "_textures"
        self.roots: list[bpy.types.Object] = []
        self.clip_dicts: dict[str, bpy.types.Object] = {}
        self.report: dict = {"assets": [], "audit": {}, "written": []}

    def path(self, p) -> Path:
        p = Path(p)
        return p if p.is_absolute() else (self.base / p).resolve()

    def texture(self, p, kind="auto", fmt=None, mips=True, flip_green=False) -> str:
        src = self.path(p)
        if src.suffix.lower() == ".dds":
            return str(src)
        if src.suffix.lower() not in IMG_EXT:
            raise ValueError(f"Formato texture non supportato: {src}")
        self.tex_dir.mkdir(parents=True, exist_ok=True)
        dst = self.tex_dir / (src.stem.lower().replace(" ", "_").replace("-", "_") + ".dds")
        if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
            dds_convert.convert(src, dst, fmt=fmt, kind=kind, mips=mips, flip_green=flip_green)
        return str(dst)


# ------------------------------------------------------------------------------------------
def import_source(ctx: Ctx, source) -> list[bpy.types.Object]:
    """source: {"file": "x.glb|fbx|obj|blend", "objects": [nomi opzionali], "scale": 1.0}
               | {"objects": ["Nome", ...]}  (gia' in scena)
               | {"primitive": "cube|cylinder|plane", "size": [x,y,z], "location": [..]}"""
    if isinstance(source, str):
        source = {"file": source}
    before = set(bpy.data.objects)
    if "file" in source:
        f = ctx.path(source["file"])
        ext = f.suffix.lower()
        if ext in (".glb", ".gltf"):
            bpy.ops.import_scene.gltf(filepath=str(f))
        elif ext == ".fbx":
            bpy.ops.import_scene.fbx(filepath=str(f))
        elif ext == ".obj":
            bpy.ops.wm.obj_import(filepath=str(f))
        elif ext == ".blend":
            with bpy.data.libraries.load(str(f), link=False) as (src, dst):
                dst.objects = [n for n in src.objects if not source.get("objects") or n in source["objects"]]
            for o in dst.objects:
                if o is not None:
                    bpy.context.collection.objects.link(o)
        else:
            raise ValueError(f"Formato modello non supportato: {f}")
        new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
        if source.get("objects") and ext != ".blend":
            new = [o for o in new if o.name in source["objects"]]
    elif "primitive" in source:
        kind = source["primitive"]
        loc = source.get("location", (0, 0, 0))
        if kind == "cube":
            bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        elif kind == "cylinder":
            bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=1, location=loc)
        elif kind == "plane":
            bpy.ops.mesh.primitive_plane_add(size=1, location=loc)
        else:
            raise ValueError(kind)
        o = bpy.context.object
        o.scale = source.get("size", (1, 1, 1))
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.uv.smart_project()
        bpy.ops.object.mode_set(mode="OBJECT")
        new = [o]
    else:
        new = [bpy.data.objects[n] for n in source["objects"]]
    if not new:
        raise RuntimeError(f"Nessuna mesh trovata per source={source}")
    # rimuovi parent/empty d'importazione mantenendo la trasformazione mondo
    for o in new:
        if o.parent is not None and o.parent.type != "ARMATURE":
            mw = o.matrix_world.copy()
            o.parent = None
            o.matrix_world = mw
    for o in [o for o in bpy.data.objects if o not in before and o.type == "EMPTY" and not o.children]:
        bpy.data.objects.remove(o, do_unlink=True)
    sc = source.get("scale")
    for o in new:
        if sc:
            o.scale = [s * sc for s in o.scale]
        sz.apply_modifiers(o)
    return new


def join(objs: list[bpy.types.Object], name: str) -> bpy.types.Object:
    if len(objs) == 1:
        objs[0].name = name
        return objs[0]
    sz._select_only(objs, objs[0])
    bpy.ops.object.join()
    o = bpy.context.object
    o.name = name
    return o


def apply_materials(ctx: Ctx, obj: bpy.types.Object, mat_spec):
    """mat_spec:
         {"shader": "normal_spec", "textures": {"diffuse": "a.png", ...}, "embedded": true, "params": {...}}
       | {"convert_existing": true, "shader": null}   (converte i Principled BSDF importati; texture -> dds)
       | {"slots": {"<nome materiale importato>": {shader...}, ...}}  (multi-materiale)"""
    if mat_spec is None:
        mat_spec = {"convert_existing": True}
    if mat_spec.get("convert_existing"):
        # converte le immagini usate dai materiali in DDS prima della conversione
        for m in obj.data.materials:
            if m and m.node_tree:
                for n in m.node_tree.nodes:
                    if isinstance(n, bpy.types.ShaderNodeTexImage) and n.image:
                        fp = n.image.filepath_raw or n.image.filepath
                        if n.image.packed_file and not fp.lower().endswith(".dds"):
                            ctx.tex_dir.mkdir(parents=True, exist_ok=True)
                            tmp = ctx.tex_dir / (n.image.name.split(".")[0].lower() + ".png")
                            n.image.filepath_raw = str(tmp)
                            n.image.file_format = "PNG"
                            n.image.save()
                            fp = str(tmp)
                        if fp and not fp.lower().endswith(".dds"):
                            n.image = sz.load_image(ctx.texture(bpy.path.abspath(fp)))
        sz.convert_existing_materials(obj, mat_spec.get("shader"))
        emb = mat_spec.get("embedded", True)
        for m in obj.data.materials:
            for n in m.node_tree.nodes:
                if isinstance(n, bpy.types.ShaderNodeTexImage):
                    n.texture_properties.embedded = emb
        return
    if "slots" in mat_spec:
        for i, m in enumerate(list(obj.data.materials)):
            sub = mat_spec["slots"].get(m.name) if m else None
            if sub:
                new = _make_mat(ctx, sub)
                obj.data.materials[i] = new
        sz.refresh_mesh_attributes(obj)
        return
    sz.assign_material(obj, _make_mat(ctx, mat_spec))
    if mat_spec.get("tint_palette"):
        sz.set_tint_column(obj, int(mat_spec.get("tint_column", 0)))


def _make_mat(ctx: Ctx, ms: dict):
    tex = {}
    for k, v in ms.get("textures", {}).items():
        sampler = sz.SAMPLER_ALIASES.get(k.lower(), k)
        kind = "normal" if sampler == "BumpSampler" else "spec" if sampler == "SpecSampler" else "auto"
        fmt = "RGBA" if sampler == "TintPaletteSampler" or ms.get("dui") else None
        # GTA usa normal map DirectX; sorgenti OpenGL (Blender/glTF/default) vanno invertite sul verde
        flip = sampler == "BumpSampler" and ms.get("normal_format", ctx.spec.get("normal_format", "opengl")) == "opengl"
        tex[sampler] = ctx.texture(v, kind=kind, fmt=fmt, mips=not ms.get("dui", False), flip_green=flip)
    if ms.get("tint_palette"):
        # varianti colore: genera la palette e la mette nel TintPaletteSampler (shader *_tnt)
        ctx.tex_dir.mkdir(parents=True, exist_ok=True)
        pal_name = ms.get("tint_palette_name", f"{ms.get('name') or 'sz'}_tint_pal").lower()
        tex["TintPaletteSampler"] = str(dds_convert.make_tint_palette(ms["tint_palette"], ctx.tex_dir / f"{pal_name}.dds"))
    mat = sz.new_shader_material(ms.get("shader", "default"), ms.get("name"))
    sz.set_shader_textures(mat, tex, ms.get("embedded", True))
    if ms.get("params"):
        sz.set_shader_params(mat, **ms["params"])
    return mat


def mesh_from(ctx: Ctx, part: dict, name: str) -> bpy.types.Object:
    objs = import_source(ctx, part["source"])
    o = join(objs, name)
    sz.prepare_mesh(o, vertex_rgba=part.get("vertex_color", ctx.spec.get("vertex_color", (1, 0, 0, 1))))
    if part.get("origin"):
        sz.set_origin(o, part["origin"] if isinstance(part["origin"], str) else "POINT",
                      None if isinstance(part["origin"], str) else part["origin"])
    apply_materials(ctx, o, part.get("material"))
    return o


# ------------------------------------------------------------------------------------------
def build_static(ctx, a):
    o = mesh_from(ctx, a, a["name"] + "_hi")
    if "origin" not in a:
        sz.set_origin(o, "BOTTOM_CENTER")
    d = sz.make_drawable(a["name"], [o])
    if a.get("lods") == "auto":
        sz.auto_lods(o)
        if not a.get("lod_distances"):
            ld = float(a.get("lod_dist", 100))
            sz.set_lod_distances(d, ld * 0.25, ld * 0.5, ld * 0.75, ld)
    if a.get("lod_distances"):
        sz.set_lod_distances(d, *a["lod_distances"])
    _collision(ctx, d, a.get("collision", {"mode": "box"}))
    for L in a.get("lights", []):
        sz.add_light(d, **L)
    return d


def _collision(ctx, root, c):
    if not c:
        return
    mode = c.get("mode", "box")
    mesh = None
    if mode == "mesh":
        mesh = join(import_source(ctx, c["source"]), f"{root.name}_colmesh")
    sz.add_embedded_collision(root, mode, material=c.get("material", "DEFAULT"), mesh=mesh, boxes=c.get("boxes"))


def build_animated(ctx, a):
    parts = {}
    for bname, p in a["parts"].items():
        o = mesh_from(ctx, p, f"{a['name']}_{bname}")
        parts[bname] = {"mesh": o, "pivot": p.get("pivot", (0, 0, 0)), "parent": p.get("parent", "root")}
    arm = sz.make_animated_drawable(a["name"], parts)
    _collision(ctx, arm, a.get("collision", {"mode": "hull"}))
    for L in a.get("lights", []):
        sz.add_light(arm, **L)
    for clip in a.get("clips", []):
        dict_name = clip.get("dict", a.get("clip_dictionary", f"{a['name']}_anims"))
        cd = ctx.clip_dicts.get(dict_name) or sz.make_clip_dictionary(dict_name)
        ctx.clip_dicts[dict_name] = cd

        def keys(clip=clip):
            for bone, frames in clip["keys"].items():
                for frame, k in frames:
                    sz.keyframe_bone(arm, bone, int(frame), rot_euler_deg=k.get("rot"), loc=k.get("loc"),
                                     scale=k.get("scale"))
        act = sz.record_action(arm, f"{a['name']}_{clip['name']}", keys)
        sz.add_clip(cd, clip["name"], act, arm.data)
    return arm


def build_uv(ctx, a):
    d = build_static(ctx, a)
    mats = [m for c in d.children_recursive if c.type == "MESH" and c.sollum_type == sz.ST().DRAWABLE_MODEL
            for m in c.data.materials]
    mat = mats[a.get("uv", {}).get("material_index", 0)]
    uv = a.get("uv", {})
    dict_name = a.get("clip_dictionary", f"{a['name']}_uv")
    cd = ctx.clip_dicts.get(dict_name) or sz.make_clip_dictionary(dict_name)
    ctx.clip_dicts[dict_name] = cd
    act = sz.uv_scroll_action(mat, uv.get("frames", 60), uv.get("du", 1.0), uv.get("dv", 0.0))
    sz.add_clip(cd, a["name"], act, mat, uv=True)
    return d


def build_door(ctx, a):
    o = mesh_from(ctx, a, a["name"] + "_panel")
    return sz.make_door(a["name"], o, a["hinge"], a.get("kind", "swing"),
                        a.get("collision", {}).get("material", "WOOD_SOLID_MEDIUM"))


def build_fragment(ctx, a):
    parts = {}
    for bname, p in a["parts"].items():
        o = mesh_from(ctx, p, f"{a['name']}_{bname}")
        q = {k: v for k, v in p.items() if k in ("pivot", "parent", "material_col", "mass", "physics", "strength")}
        q["mesh"] = o
        q["collision"] = p.get("collision", "box")
        q["material"] = p.get("collision_material", "DEFAULT")
        parts[bname] = q
    return sz.make_fragment(a["name"], parts)


BUILDERS = {"static": build_static, "dynamic": build_static, "dui": build_static, "light": build_static,
            "animated": build_animated, "uv_scroll": build_uv, "door": build_door, "fragment": build_fragment}

DEFAULT_FLAGS = {"static": ["static"], "dynamic": ["dynamic"], "dui": ["static"], "light": ["static"],
                 "animated": ["has_anim"], "uv_scroll": ["static", "has_uv_anim", "auto_start_anim"],
                 "fragment": ["dynamic"]}


def build(spec_path) -> dict:
    spec_path = Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    ctx = Ctx(spec_path, spec)
    if spec.get("reset_scene", True):
        sz.reset_scene()
    sz.env_report()
    ytyp = sz.get_or_make_ytyp(spec.get("ytyp", spec.get("resource", {}).get("name", "my_props")))
    txds: dict[str, list[str]] = {}
    for a in spec["assets"]:
        t = a.get("type", "static")
        root = BUILDERS[t](ctx, a)
        ctx.roots.append(root)
        txd = a.get("texture_dictionary")
        if txd:  # texture non embedded -> ytd
            imgs = {n.image for c in root.children_recursive if c.type == "MESH"
                    for m in c.data.materials if m and m.node_tree
                    for n in m.node_tree.nodes if isinstance(n, bpy.types.ShaderNodeTexImage)
                    and n.image and not n.texture_properties.embedded}
            txds.setdefault(txd, []).extend(i for i in imgs if i not in txds.get(txd, []))
        if t == "door":
            sz.add_door_archetype(ytyp, root, a.get("kind"), a.get("lod_dist", 100))
        else:
            flags = a.get("flags", DEFAULT_FLAGS.get(t, ["static"]))
            if t == "animated" and a.get("auto_start"):
                flags = list(flags) + ["auto_start_anim"]
            clip_dict = a.get("clip_dictionary") or (f"{a['name']}_uv" if t == "uv_scroll" else
                                                     (a["clips"][0].get("dict", f"{a['name']}_anims")
                                                      if t == "animated" and a.get("clips") else ""))
            sz.add_archetype(ytyp, root, flags=flags, lod_dist=a.get("lod_dist", 100), texture_dictionary=txd,
                             clip_dictionary=clip_dict, special=a.get("special", "none"))
        ctx.report["assets"].append({"name": a["name"], "type": t, "texture_dictionary": txd})
    for name, imgs in txds.items():
        sz.make_txd(name, imgs)
    ok = True
    for r in ctx.roots:
        res = sz.audit(r)
        ctx.report["audit"][r.name] = res
        ok = ok and not res["errors"]
    if not ok and not spec.get("export_even_with_errors", False):
        print("[build] ERRORI di audit: export annullato. Correggi la spec o metti export_even_with_errors=true")
        (ctx.out / "build_report.json").parent.mkdir(parents=True, exist_ok=True)
        (ctx.out / "build_report.json").write_text(json.dumps(ctx.report, indent=2))
        return ctx.report
    exp = ctx.out / "export"
    ctx.report["written"] = sz.export(exp, ctx.roots + list(ctx.clip_dicts.values()),
                                      formats=spec.get("formats", ["NATIVE", "CWXML"]),
                                      versions=spec.get("versions", ["GEN8", "GEN9"]))
    if spec.get("save_blend", True):
        bpy.ops.wm.save_as_mainfile(filepath=str(ctx.out / f"{ytyp.name}.blend"))
    res = spec.get("resource")
    if res:
        import make_resource
        ctx.report["resource"] = make_resource.make_resource(
            export_dir=exp, resource_dir=ctx.path(res.get("path", ctx.out / res["name"])),
            name=res["name"], assets=spec["assets"], ytyp=ytyp.name,
            versions=spec.get("versions", ["GEN8", "GEN9"]), cwconv=res.get("cwconv"))
    (ctx.out / "build_report.json").write_text(json.dumps(ctx.report, indent=2, default=str))
    print("[build] OK ->", ctx.out)
    return ctx.report


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if not argv:
        print(__doc__)
        sys.exit(1)
    build(argv[0])
