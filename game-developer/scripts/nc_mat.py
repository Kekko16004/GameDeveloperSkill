#!/usr/bin/env python3
"""Materials for Nucleon (GameDeveloperSkill): the material system of 21 October 2026 used on purpose, not left at Default Lit.

  python nc_mat.py presets [--style lowpoly|toon|stylized|realistic]           every preset (role -> shading model and keys)
  python nc_mat.py make ROLE OUT.ncmat [--style S] [--texture T] [--set k=v ...]   one material from a preset
  python nc_mat.py auto --project P [--catalog C] [--folder F] [--style S] [--name N]
        reads the glTF/GLB of the kit: every material slot gets a role (material name, texture names, the asset's catalog role), shared
        .ncmat files are written to Content/Materials/Auto/<N>/ (one per role + texture set: the batches of the renderer merge per
        material, so fewer materials = fewer draws), separate PBR maps are packed into ORM, embedded GLB images are extracted, and
        art/materials/<N>.map.json says which asset slot takes which material and which plants get the vegetation wind
  python nc_mat.py assign --project P --map art/materials/N.map.json [--level L]
        writes `materials = {...}` and `wind = {...}` on the level's model entities of those assets (EDITOR CLOSED: it rewrites the file)
  python nc_mat.py check --project P --editor NucleonEditor M.ncmat [...] [--out DIR]
        renders each material in the editor's Material document twice (models on / NC_MATERIAL_MODELS=0) and reports black,
        unshaded or identical previews: the shading models are "written and built, never run" in the engine, so every new one is checked

Why (docs/rendering/MATERIAL_SYSTEM.md, MATERIALS.md, WIND.md of the engine):
- a .ncmat replaces the slot entirely, textures included: a material without baseColorTexture draws flat. `auto` always carries the
  glTF's textures over.
- the kit trees sway with the ENTITY wind (`wind = {type = "tree"}`: weights by height, the trunk base stays), not with the material
  wind block (`windStrength` moves the whole mesh unless a vertex color channel masks it): material wind only for grass/leaf cards.
- triplanar and parallax replace / displace the mesh UVs: never on atlas textures (a texture shared by many assets), only on
  tileable sets (rocks, ground, walls of realistic kits).
Standard library; Pillow optional (ORM packing).
"""
import argparse
import glob
import json
import os
import re
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# ------------------------------------------------------------------------------------------------ presets
# Keys are the .ncmat keys of the engine (materialasset.*, slab.cpp). Colors sRGB. Every preset is a real shading model of
# bsdf_table.cpp; `_style` overrides per art style. `_wind` = entity vegetation wind type for the models that use the role.
PRESETS = {
    "default":   {"shadingModel": "defaultLit", "roughness": 0.6, "specular": 0.5},
    "foliage":   {"shadingModel": "twoSidedFoliage", "twoSided": True, "roughness": 0.65, "specular": 0.35, "sssColor": [0.45, 0.62, 0.18],
                  "_wind": "tree", "_style": {"lowpoly": {"roughness": 0.8, "specular": 0.25}, "toon": {"roughness": 0.9, "specular": 0.2}}},
    "grass":     {"shadingModel": "twoSidedFoliage", "twoSided": True, "roughness": 0.75, "specular": 0.3, "sssColor": [0.5, 0.65, 0.2],
                  "windStrength": 0.06, "windFrequency": 1.4, "windBending": 0.9, "_wind": "grass"},
    "tree":      {"shadingModel": "defaultLit", "roughness": 0.75, "specular": 0.35, "_wind": "tree"},   # an atlas tree: leaves and trunk in one
    "bush":      {"shadingModel": "twoSidedFoliage", "twoSided": True, "roughness": 0.7, "specular": 0.3, "sssColor": [0.4, 0.55, 0.16], "_wind": "bush"},
    "bark":      {"shadingModel": "defaultLit", "roughness": 0.85, "specular": 0.3, "_wind": "tree"},
    "rock":      {"shadingModel": "defaultLit", "roughness": 0.88, "specular": 0.4,
                  "_style": {"realistic": {"detailNormalStrength": 0.6, "detailNormalTiling": 6, "_tileable": {"triplanarMode": 1, "triplanarScale": 0.5, "triplanarSharpness": 6}}}},
    "ground":    {"shadingModel": "defaultLit", "roughness": 0.92, "specular": 0.35,
                  "_style": {"realistic": {"_height": {"heightScale": 0.04, "parallaxSteps": 24, "parallaxShadow": 1}}}},
    "wood":      {"shadingModel": "defaultLit", "roughness": 0.7, "specular": 0.4},
    "plaster":   {"shadingModel": "defaultLit", "roughness": 0.9, "specular": 0.35},
    "brick":     {"shadingModel": "defaultLit", "roughness": 0.85, "specular": 0.4,
                  "_style": {"realistic": {"_height": {"heightScale": 0.02, "parallaxSteps": 16}}}},
    "roof":      {"shadingModel": "defaultLit", "roughness": 0.8, "specular": 0.4},
    "metal":     {"shadingModel": "defaultLit", "metallic": 1.0, "roughness": 0.35},
    "rust":      {"shadingModel": "defaultLit", "metallic": 0.6, "roughness": 0.8},
    "painted":   {"shadingModel": "clearCoat", "roughness": 0.45, "coatCoverage": 0.6, "coatRoughness": 0.12},
    "lacquer":   {"shadingModel": "clearCoat", "roughness": 0.3, "coatCoverage": 1.0, "coatRoughness": 0.04},
    "carPaint":  {"shadingModel": "carPaint", "metallic": 0.6, "roughness": 0.35, "coatCoverage": 1.0, "coatRoughness": 0.03,
                  "flakeColor": [0.9, 0.9, 0.95], "flakeRoughness": 0.3, "glintDensity": 0.5, "glintSize": 0.3},
    "plastic":   {"shadingModel": "defaultLit", "roughness": 0.45, "specular": 0.5},
    "rubber":    {"shadingModel": "defaultLit", "roughness": 0.9, "specular": 0.3},
    "leather":   {"shadingModel": "defaultLit", "roughness": 0.55, "specular": 0.4},
    "cloth":     {"shadingModel": "cloth", "roughness": 0.85, "fuzzColor": [0.8, 0.8, 0.8], "fuzzAmount": 0.6, "fuzzRoughness": 0.5, "twoSided": True},
    "velvet":    {"shadingModel": "cloth", "roughness": 0.9, "fuzzColor": [1.0, 0.9, 0.9], "fuzzAmount": 1.0, "fuzzRoughness": 0.35},
    "skin":      {"shadingModel": "preintegratedSkin", "roughness": 0.5, "specular": 0.35, "sssColor": [0.85, 0.3, 0.2], "thickness": 0.6},
    "wax":       {"shadingModel": "subsurface", "roughness": 0.35, "sssColor": [0.95, 0.8, 0.55], "thickness": 0.5},
    "jade":      {"shadingModel": "subsurface", "roughness": 0.2, "specular": 0.6, "sssColor": [0.3, 0.8, 0.45], "thickness": 0.4},
    "marble":    {"shadingModel": "subsurface", "roughness": 0.25, "specular": 0.55, "sssColor": [0.9, 0.88, 0.85], "thickness": 0.3},
    "hair":      {"shadingModel": "hair", "blendMode": "mask", "alphaCutoff": 0.33, "twoSided": True, "hairMelanin": 0.4, "hairRedness": 0.1, "hairScatter": 0.5},
    "eye":       {"shadingModel": "eye", "roughness": 0.05, "eyeIrisRadius": 0.15, "eyeIrisDepth": 0.3, "eyePupil": 0.4},
    "glass":     {"shadingModel": "glass", "roughness": 0.02, "ior": 1.5, "glassThickness": 0.6, "refractionMode": 1, "transmissionColor": [0.98, 1.0, 0.99]},
    "frosted":   {"shadingModel": "glass", "roughness": 0.35, "ior": 1.5, "glassThickness": 0.6, "refractionMode": 1},
    "ice":       {"shadingModel": "glass", "roughness": 0.12, "ior": 1.31, "glassThickness": 4, "absorptionDistance": 30, "transmissionColor": [0.85, 0.95, 1.0], "refractionMode": 1},
    "crystal":   {"shadingModel": "glass", "roughness": 0.0, "ior": 1.6, "dispersion": 30, "glassThickness": 2, "refractionMode": 2},
    "stained":   {"shadingModel": "thinTranslucent", "roughness": 0.1, "transmissionColor": [0.9, 0.4, 0.3]},
    "water":     {"shadingModel": "singleLayerWater", "ior": 1.33, "roughness": 0.05, "transmissionColor": [0.72, 0.92, 0.85], "waterAbsorption": 1.0,
                  "waterScatter": 0.2, "waterScatterColor": [0.45, 0.85, 0.7], "waterRefraction": 0.06, "waterShoreFade": 0.3},
    "ocean":     {"shadingModel": "singleLayerWater", "ior": 1.33, "roughness": 0.04, "transmissionColor": [0.80, 0.96, 0.99], "waterAbsorption": 1.0,
                  "waterScatter": 0.12, "waterScatterColor": [0.45, 0.80, 1.0], "waterRefraction": 0.06, "waterShoreFade": 0.4},
    "pool":      {"shadingModel": "singleLayerWater", "ior": 1.33, "roughness": 0.02, "transmissionColor": [0.90, 0.99, 1.0], "waterAbsorption": 1.0,
                  "waterScatter": 0.03, "waterScatterColor": [0.6, 0.9, 1.0], "waterRefraction": 0.08, "waterShoreFade": 0.15},
    "swamp":     {"shadingModel": "singleLayerWater", "ior": 1.33, "roughness": 0.1, "transmissionColor": [0.55, 0.70, 0.40], "waterAbsorption": 1.0,
                  "waterScatter": 0.6, "waterScatterColor": [0.45, 0.55, 0.25], "waterRefraction": 0.03, "waterShoreFade": 0.5},
    "neon":      {"shadingModel": "unlit", "emissive": [6.0, 6.0, 6.0], "_emissiveFromBase": True},
    "emissive":  {"shadingModel": "defaultLit", "roughness": 0.4, "emissive": [3.0, 3.0, 3.0], "_emissiveFromBase": True},
    "screen":    {"shadingModel": "defaultLit", "roughness": 0.15, "specular": 0.6, "emissive": [1.5, 1.5, 1.5], "_emissiveFromBase": True},
    "film":      {"shadingModel": "thinFilm", "roughness": 0.1, "thinFilmThickness": 450, "thinFilmIor": 1.4},
    "holo":      {"shadingModel": "thinTranslucent", "roughness": 0.1, "transmissionColor": [0.4, 0.9, 1.0], "emissive": [0.3, 1.6, 2.0]},
}

# words -> role, first match wins (material name, then texture file names, then the asset's catalog role)
ROLE_WORDS = [
    ("water", r"water|liquid"), ("ocean", r"ocean|sea\b"), ("glass", r"glass|window|pane|lens"), ("ice", r"\bice\b|frozen"),
    ("neon", r"neon|sign_?light|glow"), ("screen", r"screen|monitor|display|tv\b"), ("emissive", r"emiss|lamp_?bulb|bulb|light_?on"),
    ("skin", r"skin|face|body|head"), ("eye", r"\beye|cornea|iris"), ("hair", r"hair|fur\b|beard|brow"),
    ("carPaint", r"car_?paint|carpaint|car_?body"), ("painted", r"paint|enamel"), ("lacquer", r"lacquer|varnish|piano"),
    ("grass", r"grass|lawn|weed|reed"), ("foliage", r"leaf|leaves|foliage|needle|frond|canopy|ivy|moss"), ("bark", r"bark|trunk|branch|twig"),
    ("bush", r"bush|shrub|hedge"),
    ("cloth", r"cloth|fabric|cotton|linen|wool|canvas|curtain|carpet|rug|banner|flag|sail|tent"), ("velvet", r"velvet|silk|satin"),
    ("leather", r"leather"), ("rubber", r"rubber|tyre|tire"), ("plastic", r"plastic|vinyl"),
    ("rust", r"rust"), ("metal", r"metal|steel|iron|chrome|alum|brass|copper|gold|silver|bronze"),
    ("marble", r"marble"), ("jade", r"jade"), ("wax", r"wax|candle|soap"),
    ("brick", r"brick"), ("plaster", r"plaster|stucco|concrete|cement"), ("rock", r"rock|stone|boulder|cliff|pebble|gravel|cobble"),
    ("ground", r"ground|dirt|soil|mud|sand|terrain|path|road"), ("roof", r"roof|shingle|thatch"), ("wood", r"wood|plank|log|timber|oak|pine|crate|barrel"),
]
CATALOG_ROLE = {"tree": "tree", "plant": "bush", "rock": "rock", "floor": "ground", "roof": "roof", "fence": "wood", "container": "wood",
                "furniture": "wood", "light": "default"}
WIND_TYPE = {"tree": "tree", "bush": "bush", "plant": "bush", "grass": "grass"}
MAP_SUFFIX = {   # separate PBR maps of realistic kits (Megascans, Poly Haven, ambientCG, Substance exports)
    "normal": r"(_|-|\b)(normal|nrm|nor(_gl)?|n)(\.|_|$)",
    "rough": r"(_|-|\b)(rough(ness)?|rgh)(\.|_|$)",
    "metal": r"(_|-|\b)(metal(lic|ness)?|mtl)(\.|_|$)",
    "ao": r"(_|-|\b)(ao|ambient_?occlusion|occlusion)(\.|_|$)",
    "height": r"(_|-|\b)(height|disp(lacement)?|bump)(\.|_|$)",
    "orm": r"(_|-|\b)(orm|arm|occlusion_?roughness_?metal)(\.|_|$)",
    "opacity": r"(_|-|\b)(opacity|alpha|mask)(\.|_|$)",
    "emissive": r"(_|-|\b)(emiss(ive)?|emit|glow)(\.|_|$)",
}


def preset(role, style="lowpoly", tileable=False, has_height=False):
    p = dict(PRESETS.get(role) or PRESETS["default"])
    st = p.pop("_style", {}).get(style, {})
    extra = {}
    for k, v in st.items():
        if k == "_tileable":
            if tileable:
                extra.update(v)
        elif k == "_height":
            if has_height:
                extra.update(v)
        else:
            p[k] = v
    p.update(extra)
    return p


# ------------------------------------------------------------------------------------------------ Lua writer
def lua(v, ind=""):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return ("%g" % v) if isinstance(v, float) else str(v)
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, list):
        return "{" + ", ".join(lua(x, ind) for x in v) + "}"
    return "{" + ", ".join("%s = %s" % (k, lua(x, ind)) for k, x in v.items()) + "}"


def write_ncmat(path, values, note=""):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    keys = [k for k in values if not k.startswith("_")]
    order = ["version", "shadingModel", "baseColor", "baseColorTexture", "normalTexture", "ormTexture", "aoTexture", "emissive",
             "emissiveTexture", "heightTexture", "roughness", "metallic", "specular", "blendMode", "alphaCutoff", "twoSided", "tiling"]
    keys.sort(key=lambda k: (order.index(k) if k in order else 99, k))
    body = ["return {", "  version = 1,"] + ["  %s = %s," % (k, lua(values[k])) for k in keys if k != "version"] + ["}"]
    head = "-- %s\n" % note if note else ""
    open(path, "w", encoding="utf-8").write(head + "\n".join(body) + "\n")


def parse_sets(sets):
    out = {}
    for s in sets or []:
        k, _, v = s.partition("=")
        try:
            out[k] = json.loads(v)
        except ValueError:
            out[k] = v
    return out


# ------------------------------------------------------------------------------------------------ glTF reading
def read_gltf(path):
    """(json, bin chunk or None) of a .gltf or .glb."""
    if path.lower().endswith(".glb"):
        data = open(path, "rb").read()
        if data[:4] != b"glTF":
            raise ValueError("not a GLB")
        off, js, binc = 12, None, None
        while off < len(data):
            ln, typ = struct.unpack_from("<II", data, off)
            chunk = data[off + 8: off + 8 + ln]
            if typ == 0x4E4F534A:
                js = json.loads(chunk.decode("utf-8"))
            elif typ == 0x004E4942:
                binc = chunk
            off += 8 + ln
        return js, binc
    return json.load(open(path, encoding="utf-8")), None


def slot_info(path, project):
    """[{slot, name, alphaMode, doubleSided, textures: {base, normal, orm, emissive}, vertexColor}] for each glTF material (slot order)."""
    g, binc = read_gltf(path)
    images = g.get("images", [])
    textures = g.get("textures", [])
    base_dir = os.path.dirname(path)
    vcol = any("COLOR_0" in p.get("attributes", {}) for m in g.get("meshes", []) for p in m.get("primitives", []))

    def image_file(tex_ref, tag, slot):
        if not tex_ref or tex_ref.get("index") is None or tex_ref["index"] >= len(textures):
            return None
        src = textures[tex_ref["index"]].get("source")
        if src is None or src >= len(images):
            return None
        im = images[src]
        if im.get("uri") and not im["uri"].startswith("data:"):
            f = os.path.normpath(os.path.join(base_dir, im["uri"].replace("%20", " ")))
            return os.path.relpath(f, project).replace("\\", "/") if os.path.exists(f) else None
        if im.get("bufferView") is not None and binc is not None:   # embedded GLB image: extract next to the model once
            bv = g["bufferViews"][im["bufferView"]]
            blob = binc[bv.get("byteOffset", 0): bv.get("byteOffset", 0) + bv["byteLength"]]
            ext = ".png" if im.get("mimeType", "image/png").endswith("png") else ".jpg"
            out = os.path.join(base_dir, "%s_%s%d%s" % (os.path.splitext(os.path.basename(path))[0], tag, slot, ext))
            if not os.path.exists(out):
                open(out, "wb").write(blob)
            return os.path.relpath(out, project).replace("\\", "/")
        return None
    out = []
    for i, m in enumerate(g.get("materials", []) or [{"name": "default"}]):
        pbr = m.get("pbrMetallicRoughness", {})
        out.append({"slot": i, "name": m.get("name", "material%d" % i), "alphaMode": m.get("alphaMode", "OPAQUE"),
                    "doubleSided": bool(m.get("doubleSided")), "vertexColor": vcol,
                    "baseColorFactor": pbr.get("baseColorFactor"), "roughnessFactor": pbr.get("roughnessFactor"),
                    "metallicFactor": pbr.get("metallicFactor"), "emissiveFactor": m.get("emissiveFactor"),
                    "textures": {"base": image_file(pbr.get("baseColorTexture"), "base", i),
                                 "orm": image_file(pbr.get("metallicRoughnessTexture"), "orm", i),
                                 "normal": image_file(m.get("normalTexture"), "normal", i),
                                 "emissive": image_file(m.get("emissiveTexture"), "emissive", i)}})
    return out


# a model whose name says it is a piece of landscape, a building or a stump: never vegetation wind, never a "plant" material
NOT_A_PLANT = r"hill|mountain|terrain|tile|hex|ground|cliff|island|building|house|mill|cut|stump|log|trunk_?cut|base"
# roles that change how light goes through or out of a surface: only from the material's own name, never guessed for a whole atlas model
SURFACE_ONLY = {"water", "ocean", "pool", "swamp", "glass", "frosted", "ice", "crystal", "stained", "neon", "emissive", "screen", "holo",
                "skin", "eye", "hair", "film", "cloth", "velvet", "carPaint"}


def tex_id(project, rel):
    """The same image copied into several folders is one atlas: identity = file name + size."""
    f = os.path.join(project, rel)
    return (os.path.basename(rel).lower(), os.path.getsize(f) if os.path.exists(f) else 0)


def classify(slot, asset, catalog_role, atlas):
    """(role, why). On an atlas (one texture shared by many models: the material covers the whole model) only the asset's catalog role
    counts, and only roles that are safe for a whole model; the material and texture names of an atlas say nothing about the surface."""
    low = os.path.splitext(os.path.basename(asset))[0].lower()
    if not atlas:
        words = " ".join([slot["name"] or ""] + [os.path.basename(t or "") for t in slot["textures"].values()]).lower()
        for role, pat in ROLE_WORDS:
            if re.search(pat, words):
                return role, "material/texture name"
    if catalog_role in CATALOG_ROLE:
        role = CATALOG_ROLE[catalog_role]
        if role in ("tree", "bush") and re.search(NOT_A_PLANT, low):
            return "default", "catalog role %s, but the name says landscape/building/stump" % catalog_role
        return role, "catalog role %s" % catalog_role
    for role, pat in ROLE_WORDS:
        if re.search(pat, low):
            if atlas and role in SURFACE_ONLY:
                return "default", "asset name says %s, ignored on an atlas" % role
            if role in ("tree", "bush", "grass", "foliage") and re.search(NOT_A_PLANT, low):
                return "default", "asset name says %s, but also landscape/building/stump" % role
            return role, "asset name"
    return "default", "no match"


def sibling_maps(base_tex, project):
    """Separate maps next to a base color texture with the same stem (Megascans *_Albedo + *_Normal, Poly Haven *_diff + *_nor_gl ...)."""
    if not base_tex:
        return {}
    f = os.path.join(project, base_tex)
    d, name = os.path.dirname(f), os.path.basename(f)
    stem = re.split(r"(_|-)(albedo|base_?colou?r|diff(use)?|col(or)?|basecolor|a|d)(\.|_|$)", name, flags=re.I)[0]
    if not stem or stem == name:
        return {}
    found = {}
    for g in glob.glob(os.path.join(d, stem + "*")):
        rest = os.path.basename(g)[len(stem):].lower()
        if g == f or not re.search(r"\.(png|jpe?g|tga|dds|exr)$", rest):
            continue
        for kind, pat in MAP_SUFFIX.items():
            if kind not in found and re.search(pat, rest):
                found[kind] = os.path.relpath(g, project).replace("\\", "/")
    return found


def pack_orm(project, maps, out_rel):
    """R occlusion, G roughness, B metal from separate maps (Pillow). Returns the project relative path or None."""
    try:
        from PIL import Image
    except ImportError:
        return None
    src = {k: maps.get(k) for k in ("ao", "rough", "metal")}
    if not src["rough"]:
        return None
    imgs = {k: Image.open(os.path.join(project, v)).convert("L") for k, v in src.items() if v}
    size = imgs["rough"].size
    chan = []
    for k, default in (("ao", 255), ("rough", 255), ("metal", 0)):
        chan.append(imgs[k].resize(size) if k in imgs else Image.new("L", size, default))
    out = os.path.join(project, out_rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if not os.path.exists(out):
        Image.merge("RGB", chan).save(out)
    return out_rel


# ------------------------------------------------------------------------------------------------ commands
def cmd_presets(a):
    rows = {}
    for role in PRESETS:
        p = preset(role, a.style, tileable=True, has_height=True)
        rows[role] = {"model": p.get("shadingModel"), "wind": PRESETS[role].get("_wind"),
                      "keys": {k: v for k, v in p.items() if not k.startswith("_") and k != "shadingModel"}}
    print(json.dumps({"style": a.style, "presets": rows}, indent=1))


def cmd_make(a):
    p = preset(a.role, a.style, tileable=a.tileable, has_height=False)
    if a.texture:
        p["baseColorTexture"] = a.texture
    if p.pop("_emissiveFromBase", False) and a.texture:
        p["emissiveTexture"] = a.texture
    p.update(parse_sets(a.set))
    write_ncmat(a.out, p, "GameDeveloperSkill nc_mat.py preset %s (%s)" % (a.role, a.style))
    print(json.dumps({"written": a.out, "shadingModel": p.get("shadingModel")}))


def load_catalog_roles(path):
    if not path or not os.path.exists(path):
        return {}
    cat = json.load(open(path, encoding="utf-8"))
    return {it["asset"]: it.get("role") for it in cat.get("items", [])}


def cmd_auto(a):
    proj = os.path.abspath(a.project)
    roles = load_catalog_roles(a.catalog)
    folder = os.path.join(proj, a.folder)
    assets = sorted(set(glob.glob(os.path.join(folder, "**", "*.gltf"), recursive=True) + glob.glob(os.path.join(folder, "**", "*.glb"), recursive=True)))
    if not assets:
        raise SystemExit("no .gltf/.glb under %s" % folder)
    # texture -> how many assets use it: an atlas never gets triplanar or parallax (they replace / displace the UVs)
    infos, tex_users = {}, {}
    for f in assets:
        rel = os.path.relpath(f, proj).replace("\\", "/")
        try:
            infos[rel] = slot_info(f, proj)
        except Exception as e:   # a broken file is reported, the rest goes on
            infos[rel] = {"error": str(e)}
            continue
        for s in infos[rel]:
            if s["textures"]["base"]:
                tex_users.setdefault(tex_id(proj, s["textures"]["base"]), set()).add(rel)
    out_dir_rel = "Content/Materials/Auto/%s" % a.name
    mats, mapping, wind, stats, notes = {}, {}, {}, {}, []
    for rel, slots in infos.items():
        if isinstance(slots, dict):
            notes.append("%s: %s" % (rel, slots["error"]))
            continue
        cat_role = roles.get(rel)
        entries = []
        for s in slots:
            base = s["textures"]["base"]
            atlas = base is not None and len(tex_users.get(tex_id(proj, base), ())) > 2
            role, why = classify(s, rel, cat_role, atlas)
            if role == "default" and not a.all:
                continue   # nothing better than the file's own material: keep it (fewer materials, same look)
            maps = sibling_maps(base, proj) if a.style == "realistic" else {}
            p = preset(role, a.style, tileable=not atlas and base is not None, has_height=bool(maps.get("height")) and not atlas)
            if s["baseColorFactor"] and not base:
                p["baseColor"] = [round(c ** (1 / 2.2), 4) for c in s["baseColorFactor"][:3]]   # glTF factors are linear, .ncmat sRGB
            if base:
                p["baseColorTexture"] = base
            normal = s["textures"]["normal"] or maps.get("normal")
            if normal:
                p["normalTexture"] = normal
            orm = s["textures"]["orm"] or maps.get("orm") or (pack_orm(proj, maps, "%s/%s_ORM.png" % (out_dir_rel, os.path.splitext(os.path.basename(base))[0]))
                                                          if maps.get("rough") else None)
            if orm:
                p["ormTexture"] = orm
                p["metallic"] = 1.0 if (maps.get("metal") or s["textures"]["orm"]) else 0   # the map's blue channel decides
                p["roughness"] = 1.0   # the map carries it (the factor multiplies the green channel)
            if maps.get("height") and "heightScale" in p:
                p["heightTexture"] = maps["height"]
            if maps.get("ao") and orm is None:
                p["aoTexture"] = maps["ao"]
            emissive_tex = s["textures"]["emissive"] or maps.get("emissive")
            if p.pop("_emissiveFromBase", False):
                p["emissiveTexture"] = emissive_tex or base
            elif emissive_tex:
                p["emissiveTexture"] = emissive_tex
                p.setdefault("emissive", [1, 1, 1])
            alpha = s["alphaMode"]
            if alpha == "MASK" or maps.get("opacity"):
                p["blendMode"], p["alphaCutoff"] = "mask", 0.5
            elif alpha == "BLEND" and p.get("shadingModel") not in ("glass", "thinTranslucent", "singleLayerWater"):
                p["blendMode"] = "blend"
            if s["doubleSided"]:
                p["twoSided"] = True
            if p.get("windStrength") and s["vertexColor"]:
                p["windMask"] = 1   # paint the roots black in the red channel: the base stays
            elif p.get("windStrength"):
                p["windStrength"] = round(p["windStrength"] * 0.5, 3)   # no mask: the whole card moves, keep it small
            p.pop("_wind", None)
            key = json.dumps({k: v for k, v in sorted(p.items())}, sort_keys=True)
            if key not in mats:
                stem = re.sub(r"[^A-Za-z0-9]+", "_", os.path.splitext(os.path.basename(base or s["name"] or role))[0]).strip("_")[:40]
                fname = "M_%s_%s.ncmat" % (role, stem or "flat")
                n = 2
                while fname in {m["file"] for m in mats.values()}:
                    fname = "M_%s_%s_%d.ncmat" % (role, stem or "flat", n)
                    n += 1
                mats[key] = {"file": fname, "values": p, "role": role, "uses": 0}
            mats[key]["uses"] += 1
            stats[role] = stats.get(role, 0) + 1
            entries.append({"slot": s["slot"], "source": "%s/%s" % (out_dir_rel, mats[key]["file"]), "role": role, "why": why})
        if entries:
            mapping[rel] = entries
        wt = next((PRESETS[e["role"]].get("_wind") for e in entries if PRESETS[e["role"]].get("_wind")), None)
        if wt and not a.no_wind and not re.search(NOT_A_PLANT, os.path.basename(rel).lower()):
            wind[rel] = {"type": wt}
    for m in mats.values():
        write_ncmat(os.path.join(proj, out_dir_rel, m["file"]), m["values"],
                    "GameDeveloperSkill nc_mat.py auto: role %s, %d slot(s); edit freely, `auto` rewrites only files it made" % (m["role"], m["uses"]))
    map_path = os.path.join(proj, "art", "materials", "%s.map.json" % a.name)
    os.makedirs(os.path.dirname(map_path), exist_ok=True)
    json.dump({"version": 1, "style": a.style, "folder": a.folder, "materials": out_dir_rel, "assets": mapping, "wind": wind,
               "date": time.strftime("%Y-%m-%d %H:%M")}, open(map_path, "w", encoding="utf-8"), indent=1)
    print(json.dumps({"map": os.path.relpath(map_path, proj), "materials": len(mats), "assets": len(mapping), "wind": len(wind),
                      "roles": stats, "notes": notes[:10],
                      "next": "close the editor, then: nc_mat.py assign --project %s --map %s ; then nc_mat.py check on the new models"
                              % (a.project, os.path.relpath(map_path, proj))}))


def entity_spans(text):
    """(start, end) of every `{id = ...}` entity table of a level (brace matched, strings skipped)."""
    spans = []
    for m in re.finditer(r"\{id = \d+,", text):
        i, depth, ins = m.start(), 0, None
        while i < len(text):
            c = text[i]
            if ins:
                if c == "\\":
                    i += 1
                elif c == ins:
                    ins = None
            elif c in "\"'":
                ins = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    spans.append((m.start(), i + 1))
                    break
            i += 1
    return spans


def drop_key(entity, key):
    m = re.search(r",?\s*\b%s = \{" % key, entity)
    if not m:
        return entity
    i, depth = m.end() - 1, 0
    while i < len(entity):
        if entity[i] == "{":
            depth += 1
        elif entity[i] == "}":
            depth -= 1
            if depth == 0:
                return entity[:m.start()] + entity[i + 1:]
        i += 1
    return entity


def cmd_assign(a):
    proj = os.path.abspath(a.project)
    mp = json.load(open(os.path.join(proj, a.map) if not os.path.isabs(a.map) else a.map, encoding="utf-8"))
    level = a.level
    if not level:
        pj = open(os.path.join(proj, "project.ncproject"), encoding="utf-8").read()
        m = re.search(r'startupLevel\s*=\s*"([^"]+)"', pj)
        level = m.group(1) if m else "Content/Levels/Main.nclevel"
    path = os.path.join(proj, level)
    text = open(path, encoding="utf-8").read()
    lock = os.path.join(proj, "Saved", "ncli-session.json")
    if os.path.exists(lock) and not a.force:
        raise SystemExit("an ncli session is open on this project (Saved/ncli-session.json): stop it first (ncli session-stop), the editor would overwrite the level")
    out, last, changed, winded = [], 0, 0, 0
    for s, e in entity_spans(text):
        ent = text[s:e]
        if 'type = "model"' not in ent:
            continue
        m = re.search(r'source = "([^"]+)"', ent)
        if not m:
            continue
        src = m.group(1)
        mats, wnd = mp["assets"].get(src), mp.get("wind", {}).get(src)
        if not mats and not wnd:
            continue
        new = ent
        ins = ""
        if mats:
            new = drop_key(new, "materials")
            ins += ", materials = {%s}" % ", ".join('{slot = %d, source = "%s"}' % (x["slot"], x["source"]) for x in mats)
            changed += 1
        if wnd and not a.no_wind:
            new = drop_key(new, "wind")
            ins += ", wind = %s" % lua(wnd)
            winded += 1
        g = re.search(r'(source = "[^"]+")(, guid = "[^"]+")?', new)
        new = new[:g.end()] + ins + new[g.end():]
        out.append(text[last:s] + new)
        last = e
    out.append(text[last:])
    if changed or winded:
        backup = path + ".bak-ncmat"
        if not os.path.exists(backup):
            open(backup, "w", encoding="utf-8").write(text)
        open(path, "w", encoding="utf-8").write("".join(out))
    print(json.dumps({"level": level, "entitiesWithMaterials": changed, "entitiesWithWind": winded,
                      "backup": os.path.relpath(path + ".bak-ncmat", proj) if (changed or winded) else None}))


def image_stats(png):
    """Mean / std of the preview side of the Material document. When the big preview is empty (the D3D12 editor draws it blank in
    a window shot: engine notes, D2) the strip of model spheres under it is measured instead: it is rendered by the same
    thumbnails, once per shading model, with the models on or off."""
    try:
        from PIL import Image, ImageStat
    except ImportError:
        return None
    im = Image.open(png).convert("RGB")
    w, h = im.size

    def stat(box):
        st = ImageStat.Stat(im.crop(tuple(int(v) for v in box)))
        return {"mean": [round(x, 1) for x in st.mean], "std": [round(x, 1) for x in st.stddev]}
    main = stat((w * 0.03, h * 0.2, w * 0.44, h * 0.82))
    if max(main["std"]) >= 3:
        return main
    strip = stat((w * 0.0, h * 0.84, w * 0.45, h * 0.96))
    strip["region"] = "model strip (the big preview is blank)"
    return strip


def cmd_check(a):
    proj = os.path.abspath(a.project)
    out_dir = os.path.abspath(a.out or os.path.join(proj, "Saved", "gds-matcheck"))
    os.makedirs(out_dir, exist_ok=True)
    pref = os.path.join(out_dir, "_prefs")
    results = []
    for mat in a.materials:
        rel = os.path.relpath(os.path.abspath(mat), proj).replace("\\", "/") if os.path.isabs(mat) or os.path.exists(mat) else mat
        stem = re.sub(r"[^A-Za-z0-9]+", "_", rel)
        shots = {}
        for label, extra in (("on", {}), ("off", {"NC_MATERIAL_MODELS": "0"})):
            png = os.path.join(out_dir, "%s-%s.png" % (stem, label))
            env = dict(os.environ, NC_EDITOR_MATERIAL="%s:%s" % (rel, a.shape), NC_EDITOR_SCREENSHOT=png, NC_EDITOR_PREF_DIR=pref,
                       NC_EDITOR_MATERIAL_CUTAWAY="0", **extra)
            cmd = [a.editor, proj]
            runner = os.path.join(os.path.dirname(os.path.abspath(a.editor)), "nc_desktop_run.exe")
            if sys.platform == "win32" and os.path.isfile(runner) and not os.environ.get("NCLI_VISIBLE"):
                # never a window on the desktop the owner works on: the editor runs on a hidden Win32 desktop (like ncli)
                cmd = [runner, "--desktop", "gds-mat-%d" % os.getpid(), "--"] + cmd
                env["NC_UNATTENDED"] = "1"
            elif sys.platform != "win32" and not os.environ.get("DISPLAY") and shutil_which("xvfb-run"):
                cmd = ["xvfb-run", "-a", "-s", "-screen 0 1600x900x24"] + cmd
            try:
                p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=a.timeout)
                log = (p.stdout or "") + (p.stderr or "")
            except subprocess.TimeoutExpired:
                log = "timeout"
            shots[label] = {"png": png if os.path.exists(png) else None, "stats": image_stats(png) if os.path.exists(png) else None,
                            "log": [l for l in log.splitlines() if re.search(r"(?i)error|fail|shader|not shaded", l) and not re.search(r"ALSA|XDG_RUNTIME|OpenAL|sound disabled", l)][:6]}
        on, off = shots["on"]["stats"], shots["off"]["stats"]
        issues = []
        if not shots["on"]["png"]:
            issues.append("no screenshot (the editor did not open the material: see the log lines)")
        elif on:
            if sum(on["mean"]) < 15:
                issues.append("black preview")
            if max(on["std"]) < 2:
                issues.append("flat preview (nothing shaded?)")
            if off and all(abs(x - y) < 0.5 for x, y in zip(on["mean"], off["mean"])) and not re.search(r"shadingModel = \"(defaultLit|unlit)\"", open(os.path.join(proj, rel), encoding="utf-8").read()):   # these two are the same picture by design
                issues.append("identical to NC_MATERIAL_MODELS=0: the shading model did not change the picture (stub / fallback?)")
        if on and off and max(on["std"]) < 0.4 * max(off["std"]):
            issues.append("the object almost vanished (contrast %.0f vs %.0f of the fallback): a glass/translucent model with no reflection or "
                          "Fresnel highlight is broken; look at the PNG" % (max(on["std"]), max(off["std"])))
        results.append({"material": rel, "ok": not issues, "issues": issues, "shots": shots})
    print(json.dumps({"out": out_dir, "checked": len(results), "failed": [r["material"] for r in results if not r["ok"]], "results": results}, indent=1))


def shutil_which(name):
    import shutil
    return shutil.which(name)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    styles = ["lowpoly", "toon", "stylized", "realistic"]
    c = sub.add_parser("presets")
    c.add_argument("--style", default="realistic", choices=styles)
    c = sub.add_parser("make")
    c.add_argument("role", choices=sorted(PRESETS))
    c.add_argument("out")
    c.add_argument("--style", default="lowpoly", choices=styles)
    c.add_argument("--texture")
    c.add_argument("--tileable", action="store_true", help="the texture tiles (allows triplanar / parallax of the preset)")
    c.add_argument("--set", action="append", help="key=json value, e.g. baseColor=[0.5,0.4,0.3]")
    c = sub.add_parser("auto")
    c.add_argument("--project", required=True)
    c.add_argument("--folder", default="Content/Models")
    c.add_argument("--catalog", help="art/kits/<kit>.catalog.json of nc_gds.py (asset roles)")
    c.add_argument("--style", default="lowpoly", choices=styles)
    c.add_argument("--name", default="kit")
    c.add_argument("--all", action="store_true", help="also slots with no better role (default: they keep the file's material)")
    c.add_argument("--no-wind", action="store_true")
    c = sub.add_parser("assign")
    c.add_argument("--project", required=True)
    c.add_argument("--map", required=True)
    c.add_argument("--level")
    c.add_argument("--no-wind", action="store_true")
    c.add_argument("--force", action="store_true")
    c = sub.add_parser("check")
    c.add_argument("--project", required=True)
    c.add_argument("--editor", required=True)
    c.add_argument("materials", nargs="+")
    c.add_argument("--shape", default="sphere", choices=["sphere", "cube", "world"])
    c.add_argument("--out")
    c.add_argument("--timeout", type=float, default=240)
    a = p.parse_args()
    {"presets": cmd_presets, "make": cmd_make, "auto": cmd_auto, "assign": cmd_assign, "check": cmd_check}[a.cmd](a)


if __name__ == "__main__":
    main()
