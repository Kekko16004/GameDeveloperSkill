# GDS Building — procedural low-poly buildings for Blender 4.x / 5.x (pure bpy + bmesh, no addons).
# Deterministic: a JSON spec in → a finished, textured, game-ready building out (GLB + FBX, pivot at base, 1 unit = 1 m).
# A weak LLM only has to write the spec (footprint volumes + style); proportions, trims, frames, roofs, beams, chimneys,
# balconies, shutters, interior floors/partitions/stairs all come from here with good defaults.
#
# Use from Blender MCP:  execute_blender_code:
#     exec(open(r"<skill>/templates/blender/gds_building.py", encoding="utf-8").read()); print(gds_build(r"<project>/art/specs/inn.json"))
# Or headless:           blender -b --python gds_building.py -- spec.json
#
# Plan coordinates: x = right, z = depth (like Unity). Heights along up. Blender internally uses (x, y=z_plan, z=up); the
# glTF/FBX exporters convert to Y-up, so Unity gets x/z back as written.

import bpy, bmesh, json, math, os, sys, warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from mathutils import Vector

STYLES = {
    # base colors (hex), flags. Low-poly stylized palettes tuned to read well under GDS.LookDev presets.
    "medieval": {"wall": "#D9C9A8", "wall_ground": "#8F8A80", "trim": "#5A3E28", "wood": "#7A5230", "roof": "#8C3B2E", "stone": "#7D7A74", "glass": "#8FC6D9", "door": "#4A2E1B", "beams": True, "shutters": True, "plinth": 0.5, "stone_ground": True},
    "fantasy":  {"wall": "#E8D8B8", "wall_ground": "#A79C8C", "trim": "#4E3A5A", "wood": "#6E4A7A", "roof": "#3E6E8E", "stone": "#8A8A92", "glass": "#B8E8F0", "door": "#3A2A4A", "beams": True, "shutters": True, "plinth": 0.5, "stone_ground": True},
    "village":  {"wall": "#F2E6D0", "wall_ground": "#F2E6D0", "trim": "#8A6A4A", "wood": "#9A6A3A", "roof": "#B5583C", "stone": "#9A948C", "glass": "#A8D8E8", "door": "#6A4A2A", "beams": False, "shutters": True, "plinth": 0.4, "stone_ground": False},
    "modern":   {"wall": "#E6E6E2", "wall_ground": "#CFCFCA", "trim": "#3A3A3A", "wood": "#5A4A3A", "roof": "#4A4A4A", "stone": "#6A6A6A", "glass": "#9FCFE8", "door": "#2A2A2A", "beams": False, "shutters": False, "plinth": 0.3, "stone_ground": False},
    "scifi":    {"wall": "#C8CDD3", "wall_ground": "#8A9098", "trim": "#2E3A48", "wood": "#4A5A6A", "roof": "#3A4450", "stone": "#5A6068", "glass": "#7FD8FF", "door": "#1E2830", "beams": False, "shutters": False, "plinth": 0.4, "stone_ground": True},
    "dungeon":  {"wall": "#6F6B66", "wall_ground": "#5A5652", "trim": "#3E3A36", "wood": "#4A3A2A", "roof": "#4A4642", "stone": "#5C5854", "glass": "#6A8A9A", "door": "#2E2620", "beams": False, "shutters": False, "plinth": 0.6, "stone_ground": True},
}

DEFAULTS = {
    "style": "medieval", "wallThickness": 0.3, "floorHeight": 3.0, "slab": 0.2,
    "window": {"w": 1.1, "h": 1.4, "sill": 1.0, "frame": 0.1, "spacing": 2.4, "margin": 1.0},
    "door": {"w": 1.2, "h": 2.3, "frame": 0.12},
    "roof": {"pitch": 0.55, "overhang": 0.5, "thickness": 0.16},
    "cornice": {"h": 0.18, "out": 0.12}, "bevel": 0.012,
}

# ----------------------------------------------------------------------------- helpers
def _hex(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)) + (1.0,)

def _srgb_to_linear(c):
    def f(v): return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (f(c[0]), f(c[1]), f(c[2]), 1.0)

class Ctx:
    def __init__(self, spec):
        self.spec = spec
        self.style = dict(STYLES.get(spec.get("style", "medieval"), STYLES["medieval"]))
        self.style.update(spec.get("styleOverride", {}))
        self.mats = {}
        self.parts = []          # (object, material_key)
        self.name = spec.get("name", "building")
        self.col = bpy.data.collections.new("GDS_" + self.name)
        bpy.context.scene.collection.children.link(self.col)

    def mat(self, key):
        if key in self.mats: return self.mats[key]
        # 1) an existing scene material named in spec.materials (e.g. downloaded by Blender MCP Poly Haven)
        named = self.spec.get("materials", {}).get(key)
        if named and named in bpy.data.materials:
            self.mats[key] = bpy.data.materials[named]; return self.mats[key]
        m = bpy.data.materials.new(f"GDS_{self.name}_{key}")
        m.use_nodes = True
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        color = _srgb_to_linear(_hex(self.style.get(key, "#CCCCCC")))
        if bsdf:
            bsdf.inputs["Base Color"].default_value = color
            bsdf.inputs["Roughness"].default_value = 0.35 if key == "glass" else 0.85
            bsdf.inputs["Metallic"].default_value = 0.0
            if key == "glass":
                bsdf.inputs["Roughness"].default_value = 0.15
            tex = self.spec.get("textures", {}).get(key)
            if tex and os.path.exists(tex):
                img = bpy.data.images.load(tex)
                n = m.node_tree.nodes.new("ShaderNodeTexImage"); n.image = img
                m.node_tree.links.new(n.outputs["Color"], bsdf.inputs["Base Color"])
        m.diffuse_color = color
        self.mats[key] = m
        return m

    def add(self, obj, key):
        obj.data.materials.clear(); obj.data.materials.append(self.mat(key))
        for c in list(obj.users_collection): c.objects.unlink(obj)
        self.col.objects.link(obj)
        self.parts.append(obj)
        return obj

def _mesh_obj(name, bm):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob

def box(ctx, key, cx, cz, cy_bottom, w, d, h, name="box"):
    """Axis-aligned box. Plan center (cx,cz), bottom at height cy_bottom, size w (x) × d (plan depth) × h (up)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(w, d, h), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(cx, cz, cy_bottom + h / 2.0), verts=bm.verts)
    return ctx.add(_mesh_obj(name, bm), key)

def box_rot(ctx, key, cx, cz, cy_bottom, w, d, h, rot_deg, name="box"):
    ob = box(ctx, key, 0, 0, 0, w, d, h, name)
    ob.rotation_euler = (0, 0, math.radians(rot_deg))
    ob.location = (cx, cz, cy_bottom)
    return ob

def prism(ctx, key, pts_xz, z0, z1, name="prism"):
    """Vertical extrusion of a plan polygon (list of (x,z)) between heights z0..z1."""
    bm = bmesh.new()
    bottom = [bm.verts.new((x, z, z0)) for x, z in pts_xz]
    top = [bm.verts.new((x, z, z1)) for x, z in pts_xz]
    bm.faces.new(bottom[::-1]); bm.faces.new(top)
    n = len(pts_xz)
    for i in range(n):
        bm.faces.new((bottom[i], bottom[(i + 1) % n], top[(i + 1) % n], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return ctx.add(_mesh_obj(name, bm), key)

def poly_solid(ctx, key, faces_pts, name="solid"):
    """Closed solid from explicit faces (lists of (x,z,y_up) tuples)."""
    bm = bmesh.new(); cache = {}
    def v(p):
        k = (round(p[0], 5), round(p[1], 5), round(p[2], 5))
        if k not in cache: cache[k] = bm.verts.new(k)
        return cache[k]
    for f in faces_pts:
        vs = []
        for p in f:
            vv = v(p)
            if not vs or vs[-1] is not vv: vs.append(vv)
        if len(vs) > 1 and vs[0] is vs[-1]: vs.pop()
        if len(vs) < 3: continue
        try: bm.faces.new(vs)
        except ValueError: pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return ctx.add(_mesh_obj(name, bm), key)

def _select_only(ob):
    for o in bpy.data.objects:
        try: o.select_set(False)
        except Exception: pass
    ob.select_set(True); bpy.context.view_layer.objects.active = ob

def boolean(target, cutter, op="DIFFERENCE"):
    _select_only(target)
    mod = target.modifiers.new("gds_bool", "BOOLEAN"); mod.operation = op; mod.object = cutter
    try: mod.solver = "EXACT"
    except Exception: pass
    bpy.ops.object.modifier_apply(modifier=mod.name)

def join(objs, name):
    objs = [o for o in objs if o is not None]
    if not objs: return None
    _select_only(objs[0])
    for o in objs: o.select_set(True)
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active; ob.name = name
    return ob

def delete(objs):
    for o in objs:
        if o and o.name in bpy.data.objects: bpy.data.objects.remove(o, do_unlink=True)

def box_uv(ob, scale=2.0):
    """Deterministic box projection UVs (no operator): dominant normal axis → planar coords / scale."""
    me = ob.data
    if not me.uv_layers: me.uv_layers.new(name="UVMap")
    uv = me.uv_layers.active.data
    for poly in me.polygons:
        n = poly.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            u, v = (co.y, co.z) if ax == 0 else (co.x, co.z) if ax == 1 else (co.x, co.y)
            uv[li].uv = (u / scale, v / scale)

# ----------------------------------------------------------------------------- building parts
def volume_rect(vol):
    return vol["x"], vol["z"], vol["w"], vol["d"]

def side_geom(vol, side):
    """Returns (center_x, center_z, length, outward normal (nx,nz), along axis unit (ax,az)) for a volume side."""
    x, z, w, d = volume_rect(vol)
    if side == "S": return x + w / 2, z, w, (0, -1), (1, 0)
    if side == "N": return x + w / 2, z + d, w, (0, 1), (1, 0)
    if side == "W": return x, z + d / 2, d, (-1, 0), (0, 1)
    return x + w, z + d / 2, d, (1, 0), (0, 1)

def inside_other_volume(px, pz, vols, skip):
    for i, v in enumerate(vols):
        if i == skip: continue
        x, z, w, d = volume_rect(v)
        if x + 0.01 < px < x + w - 0.01 and z + 0.01 < pz < z + d - 0.01: return True
    return False

def openings_for_side(spec, vi, vol, side, floor, ctx):
    """List of openings on this wall: dicts with t (0..1 along side), w, h, y (bottom), kind."""
    ops = []
    win = dict(DEFAULTS["window"]); win.update(spec.get("window", {}))
    dr = dict(DEFAULTS["door"]); dr.update(spec.get("door", {}))
    cx, cz, length, nrm, ax = side_geom(vol, side)
    for dspec in spec.get("doors", []):
        if dspec.get("volume", 0) == vi and dspec.get("side") == side and dspec.get("floor", 0) == floor:
            ops.append({"t": dspec.get("t", 0.5), "w": dspec.get("w", dr["w"]), "h": dspec.get("h", dr["h"]), "y": 0.0, "kind": "door", "awning": dspec.get("awning", True)})
    for b in spec.get("balconies", []):
        if b.get("volume", 0) == vi and b.get("side") == side and b.get("floor", 1) == floor:
            ops.append({"t": b.get("t", 0.5), "w": dr["w"], "h": dr["h"], "y": 0.0, "kind": "balconydoor"})
    ovr = [o for o in spec.get("windowsOverride", []) if o.get("volume", 0) == vi and o.get("side") == side and o.get("floor", "*") in (floor, "*")]
    if ovr and ovr[0].get("count", None) is not None:
        count = ovr[0]["count"]
    elif not spec.get("window", {}).get("auto", True) and not ovr:
        count = 0
    else:
        usable = length - 2 * win["margin"]
        count = max(0, int(usable // win["spacing"]) + 1) if usable > win["w"] else 0
        if side in ("S",) and floor == 0 and count > 0: count = max(count, 1)
    if count > 0:
        for k in range(count):
            t = (k + 1) / (count + 1)
            # skip windows that collide with a door on the same wall
            if any(abs(o["t"] - t) * length < (o["w"] + win["w"]) / 2 + 0.3 for o in ops): continue
            ops.append({"t": t, "w": win["w"], "h": win["h"], "y": win["sill"], "kind": "window"})
    return ops

def build_wall_side(ctx, spec, vi, vol, side, floor, vols):
    """One wall slab with openings cut, plus frames/sills/shutters/door/awning parts. Returns list of objects."""
    st = ctx.style
    T = spec.get("wallThickness", DEFAULTS["wallThickness"]); H = vol.get("floorHeight", spec.get("floorHeight", DEFAULTS["floorHeight"]))
    y0 = floor * H
    cx, cz, length, (nx, nz), (ax, az) = side_geom(vol, side)
    # wall centered on the side line, half thickness in, half out
    wall_key = "wall_ground" if (floor == 0 and st.get("stone_ground")) else "wall"
    along_x = ax == 1
    wall = box(ctx, wall_key, cx, cz, y0, (length + T) if along_x else T, T if along_x else (length + T), H, f"wall_{side}_f{floor}")
    # trim inner faces where another volume overlaps (L/T shapes): cut the wall with other volumes' inner voids
    cutters = []
    for oi, ov in enumerate(vols):
        if oi == vi: continue
        ox, oz, ow, od = volume_rect(ov)
        oH = ov.get("floorHeight", H) * ov.get("floors", 1)
        c = box(ctx, "wall", ox + ow / 2, oz + od / 2, -0.05, ow - 2 * T, od - 2 * T, oH + 0.1, "cut_void")
        cutters.append(c)
    ops = openings_for_side(spec, vi, vol, side, floor, ctx)
    parts = []
    for o in ops:
        # position along the wall
        px = cx + ax * (o["t"] - 0.5) * length; pz = cz + az * (o["t"] - 0.5) * length
        ow, oh, oy = o["w"], o["h"], y0 + o["y"]
        depth = T + 0.4
        cut = box(ctx, "wall", px, pz, oy, ow if along_x else depth, depth if along_x else ow, oh, "cut_open")
        cutters.append(cut)
        f = DEFAULTS["window"]["frame"] if o["kind"] == "window" else DEFAULTS["door"]["frame"]
        fd = T + 0.08  # frame depth (slightly proud of the wall both sides)
        def fbox(key, along_off, up_off, bw, bh, bd=fd, name="frame"):
            bx = px + ax * along_off; bz = pz + az * along_off
            return box(ctx, key, bx, bz, up_off, bw if along_x else bd, bd if along_x else bw, bh, name)
        # frame: left, right, top (+ bottom for windows)
        parts.append(fbox("trim", -(ow / 2 + f / 2), oy, f, oh + f, name="frame_l"))
        parts.append(fbox("trim", (ow / 2 + f / 2), oy, f, oh + f, name="frame_r"))
        parts.append(fbox("trim", 0, oy + oh, ow + 2 * f, f, name="frame_t"))
        if o["kind"] == "window":
            parts.append(fbox("trim", 0, oy - f, ow + 2 * f, f, name="frame_b"))
            parts.append(fbox("glass", 0, oy, ow, oh, bd=0.04, name="glass"))
            # sill, proud outward
            sx = px + nx * (T / 2 + 0.06); sz = pz + nz * (T / 2 + 0.06)
            parts.append(box(ctx, "stone", sx, sz, oy - f - 0.06, (ow + 2 * f + 0.2) if along_x else 0.22, 0.22 if along_x else (ow + 2 * f + 0.2), 0.08, "sill"))
            # mullion cross
            parts.append(fbox("trim", 0, oy, 0.05, oh, bd=0.05, name="mullion_v"))
            parts.append(fbox("trim", 0, oy + oh / 2 - 0.025, ow, 0.05, bd=0.05, name="mullion_h"))
            if st.get("shutters"):
                for sgn in (-1, 1):
                    shx = px + ax * sgn * (ow / 2 + f + 0.3) + nx * (T / 2 + 0.03); shz = pz + az * sgn * (ow / 2 + f + 0.3) + nz * (T / 2 + 0.03)
                    parts.append(box(ctx, "wood", shx, shz, oy, 0.5 if along_x else 0.05, 0.05 if along_x else 0.5, oh, "shutter"))
        else:
            # door leaf recessed, planks + handle-ish knob, step
            lx = px + nx * (-0.06); lz = pz + nz * (-0.06)
            parts.append(box(ctx, "door", lx, lz, oy, ow if along_x else 0.08, 0.08 if along_x else ow, oh, "door_leaf"))
            for k in range(1, 4):
                parts.append(fbox("wood", -ow / 2 + k * ow / 4, oy + 0.05, 0.03, oh - 0.1, bd=0.11, name="plank"))
            if o["kind"] == "door":
                stx = px + nx * (T / 2 + 0.25); stz = pz + nz * (T / 2 + 0.25)
                parts.append(box(ctx, "stone", stx, stz, -0.02, (ow + 0.6) if along_x else 0.5, 0.5 if along_x else (ow + 0.6), 0.12 + y0, "step"))
                if o.get("awning", True):
                    parts += awning(ctx, px, pz, oy + oh + f + 0.15, ow + 0.8, 0.9, nx, nz, along_x)
    for c in cutters: boolean(wall, c)
    delete(cutters)
    parts.append(wall)
    return parts

def awning(ctx, px, pz, y, w, depth, nx, nz, along_x):
    """Small sloped roof over a door with two wooden brackets."""
    parts = []
    cxo = px + nx * depth / 2; czo = pz + nz * depth / 2
    tilt = 22
    slab = box(ctx, "roof", 0, 0, 0, w if along_x else depth, depth if along_x else w, 0.08, "awning")
    slab.location = (cxo, czo, y + 0.25)
    slab.rotation_euler = (math.radians(-tilt) * nz if along_x else 0, math.radians(tilt) * nx if not along_x else 0, 0)
    parts.append(slab)
    for sgn in (-1, 1):
        bx = px + (sgn * (w / 2 - 0.15) if along_x else nx * 0.3); bz = pz + (nz * 0.3 if along_x else sgn * (w / 2 - 0.15))
        parts.append(box(ctx, "wood", bx, bz, y - 0.5, 0.1 if along_x else 0.6, 0.6 if along_x else 0.1, 0.1, "bracket_h"))
        parts.append(box(ctx, "wood", px + (sgn * (w / 2 - 0.15) if along_x else nx * 0.08), pz + (nz * 0.08 if along_x else sgn * (w / 2 - 0.15)), y - 0.55, 0.1, 0.1, 0.6, "bracket_v"))
    return parts

def build_roof(ctx, spec, vol, top_y, vols):
    st = ctx.style; r = dict(DEFAULTS["roof"]); r.update(spec.get("roof", {})); r.update(vol.get("roofParams", {}))
    kind = vol.get("roof", "gable"); x, z, w, d = volume_rect(vol); ov = r["overhang"]; th = r["thickness"]
    parts = []
    if kind == "flat":
        parts.append(box(ctx, "roof", x + w / 2, z + d / 2, top_y, w + 0.2, d + 0.2, th, "roof_flat"))
        # parapet
        for (cx, cz, ww, dd) in ((x + w / 2, z - 0.1, w + 0.4, 0.2), (x + w / 2, z + d + 0.1, w + 0.4, 0.2), (x - 0.1, z + d / 2, 0.2, d + 0.4), (x + w + 0.1, z + d / 2, 0.2, d + 0.4)):
            parts.append(box(ctx, "trim", cx, cz, top_y + th, ww, dd, 0.5, "parapet"))
        return parts
    ridge_x = vol.get("ridgeAxis", "x" if w >= d else "z") == "x"
    span = d if ridge_x else w
    rise = span / 2 * r["pitch"]
    if kind == "hip":
        # pyramid frustum: 4 sloped faces meeting at a ridge segment (or point)
        rl = max(0.0, (w - d)) if ridge_x else max(0.0, (d - w))
        cx, cz = x + w / 2, z + d / 2
        rise_h = min(w, d) / 2 * r["pitch"]; lift = th * 0.75  # keep the roof skin clear of the wall top (no coplanar z-fight)
        if ridge_x: ridge = [(cx - rl / 2, cz, top_y + lift + rise_h), (cx + rl / 2, cz, top_y + lift + rise_h)]
        else: ridge = [(cx, cz - rl / 2, top_y + lift + rise_h), (cx, cz + rl / 2, top_y + lift + rise_h)]
        ex0, ex1, ez0, ez1 = x - ov, x + w + ov, z - ov, z + d + ov
        e = top_y + lift - ov * r["pitch"]
        base = [(ex0, ez0, e), (ex1, ez0, e), (ex1, ez1, e), (ex0, ez1, e)]
        rA, rB = ridge
        if ridge_x: faces = [[base[0], base[1], rB, rA], [base[1], base[2], rB], [base[2], base[3], rA, rB], [base[3], base[0], rA]]
        else: faces = [[base[0], base[1], rA], [base[1], base[2], rB, rA], [base[2], base[3], rB], [base[3], base[0], rA, rB]]
        # thickness: add a lowered copy for the underside
        under = [[(p[0], p[1], p[2] - th) for p in f][::-1] for f in faces]
        rim = []
        for i in range(4):
            a, b = base[i], base[(i + 1) % 4]
            rim.append([a, (a[0], a[1], a[2] - th), (b[0], b[1], b[2] - th), b])
        parts.append(poly_solid(ctx, "roof", faces + under + rim, "roof_hip"))
        return parts
    # gable: two slabs + gable-end triangles (wall material) + ridge beam + fascia
    if ridge_x:
        half = d / 2 + ov; L = w + 2 * ov; slope_len = math.hypot(half, rise + ov * r["pitch"] * 0)  # eave drop handled by angle
        ang = math.atan2(rise, d / 2)
        for sgn in (-1, 1):
            s = box(ctx, "roof", 0, 0, 0, L, math.hypot(half, half * math.tan(ang)), th, "roof_slab")
            s.rotation_euler = (sgn * -ang, 0, 0)
            s.location = (x + w / 2, z + d / 2 + sgn * half / 2, top_y + rise - (half / 2) * math.tan(ang) + th * 0.2)
            parts.append(s)
        for gx in (x, x + w):
            parts.append(poly_solid(ctx, "wall", [[(gx - 0.15, z, top_y), (gx - 0.15, z + d, top_y), (gx - 0.15, z + d / 2, top_y + rise)],
                                                  [(gx + 0.15, z, top_y), (gx + 0.15, z + d / 2, top_y + rise), (gx + 0.15, z + d, top_y)],
                                                  [(gx - 0.15, z, top_y), (gx + 0.15, z, top_y), (gx + 0.15, z + d, top_y), (gx - 0.15, z + d, top_y)],
                                                  [(gx - 0.15, z, top_y), (gx - 0.15, z + d / 2, top_y + rise), (gx + 0.15, z + d / 2, top_y + rise), (gx + 0.15, z, top_y)],
                                                  [(gx - 0.15, z + d, top_y), (gx + 0.15, z + d, top_y), (gx + 0.15, z + d / 2, top_y + rise), (gx - 0.15, z + d / 2, top_y + rise)]], "gable_end"))
        parts.append(box(ctx, "wood", x + w / 2, z + d / 2, top_y + rise - 0.05, w + 2 * ov + 0.1, 0.18, 0.18, "ridge_beam"))
        for sgn in (-1, 1):
            parts.append(box(ctx, "trim", x + w / 2, z + d / 2 + sgn * (d / 2 + ov), top_y - ov * math.tan(ang) - 0.2, w + 2 * ov + 0.1, 0.06, 0.22, "fascia"))
    else:
        half = w / 2 + ov; L = d + 2 * ov; ang = math.atan2(rise, w / 2)
        for sgn in (-1, 1):
            s = box(ctx, "roof", 0, 0, 0, math.hypot(half, half * math.tan(ang)), L, th, "roof_slab")
            s.rotation_euler = (0, sgn * ang, 0)
            s.location = (x + w / 2 + sgn * half / 2, z + d / 2, top_y + rise - (half / 2) * math.tan(ang) + th * 0.2)
            parts.append(s)
        for gz in (z, z + d):
            parts.append(poly_solid(ctx, "wall", [[(x, gz - 0.15, top_y), (x + w / 2, gz - 0.15, top_y + rise), (x + w, gz - 0.15, top_y)],
                                                  [(x, gz + 0.15, top_y), (x + w, gz + 0.15, top_y), (x + w / 2, gz + 0.15, top_y + rise)],
                                                  [(x, gz - 0.15, top_y), (x + w, gz - 0.15, top_y), (x + w, gz + 0.15, top_y), (x, gz + 0.15, top_y)],
                                                  [(x, gz - 0.15, top_y), (x, gz + 0.15, top_y), (x + w / 2, gz + 0.15, top_y + rise), (x + w / 2, gz - 0.15, top_y + rise)],
                                                  [(x + w, gz - 0.15, top_y), (x + w / 2, gz - 0.15, top_y + rise), (x + w / 2, gz + 0.15, top_y + rise), (x + w, gz + 0.15, top_y)]], "gable_end"))
        parts.append(box(ctx, "wood", x + w / 2, z + d / 2, top_y + rise - 0.05, 0.18, d + 2 * ov + 0.1, 0.18, "ridge_beam"))
        for sgn in (-1, 1):
            parts.append(box(ctx, "trim", x + w / 2 + sgn * (w / 2 + ov), z + d / 2, top_y - ov * math.tan(ang) - 0.2, 0.06, d + 2 * ov + 0.1, 0.22, "fascia"))
    # chimney
    for ch in spec.get("chimneys", []):
        if ch.get("volume", 0) != vols.index(vol): continue
        chx, chz = x + ch.get("x", w * 0.25), z + ch.get("z", d * 0.5)
        parts.append(box(ctx, "stone", chx, chz, top_y - 0.5, 0.7, 0.7, rise + 1.4, "chimney"))
        parts.append(box(ctx, "trim", chx, chz, top_y + rise + 0.9, 0.9, 0.9, 0.15, "chimney_cap"))
    return parts

def build_volume(ctx, spec, vi, vol, vols):
    st = ctx.style; parts = []
    T = spec.get("wallThickness", DEFAULTS["wallThickness"]); H = vol.get("floorHeight", spec.get("floorHeight", DEFAULTS["floorHeight"]))
    floors = vol.get("floors", 1); x, z, w, d = volume_rect(vol); slab = DEFAULTS["slab"]
    co = dict(DEFAULTS["cornice"]); co.update(spec.get("cornice", {}))
    for f in range(floors):
        for side in ("S", "N", "W", "E"):
            # skip a whole side if its midpoint lies inside another volume (fully interior wall)
            cx, cz, length, (nx, nz), _ = side_geom(vol, side)
            if inside_other_volume(cx - nx * 0.05, cz - nz * 0.05, vols, vi) and inside_other_volume(cx + nx * 0.05, cz + nz * 0.05, vols, vi): continue
            parts += build_wall_side(ctx, spec, vi, vol, side, f, vols)
        # floor slab (inside the walls), top at f*H; cut by lower-index overlapping volumes so shared areas are not double-faced
        sl = box(ctx, "stone" if f == 0 else "wood", x + w / 2, z + d / 2, f * H - slab, w - T, d - T, slab, f"slab_f{f}")
        for oi, ov in enumerate(vols[:vi]):
            ox, oz, ow, od = volume_rect(ov)
            c = box(ctx, "wall", ox + ow / 2, oz + od / 2, -1, ow - 2 * T + 0.02, od - 2 * T + 0.02, 200, "cut_slab"); boolean(sl, c); delete([c])
        parts.append(sl)
        # cornice band + timber beams at floor lines
        if f < floors - 1 or floors == 1:
            pass
        if f > 0 and spec.get("corniceEnabled", True):
            parts.append(box(ctx, "trim", x + w / 2, z + d / 2, f * H - co["h"] / 2, w + T + 2 * co["out"], d + T + 2 * co["out"], co["h"], "cornice"))
        if st.get("beams"):
            bw = 0.18
            for (bx, bz) in ((x, z), (x + w, z), (x, z + d), (x + w, z + d)):
                if inside_other_volume(bx, bz, vols, vi): continue
                parts.append(box(ctx, "wood", bx, bz, f * H, bw + T * 0.2, bw + T * 0.2, H, "corner_beam"))
            if f > 0:
                parts.append(box(ctx, "wood", x + w / 2, z, f * H, w + T, bw, bw, "beam_h"))
                parts.append(box(ctx, "wood", x + w / 2, z + d, f * H, w + T, bw, bw, "beam_h"))
                parts.append(box(ctx, "wood", x, z + d / 2, f * H, bw, d + T, bw, "beam_h"))
                parts.append(box(ctx, "wood", x + w, z + d / 2, f * H, bw, d + T, bw, "beam_h"))
    # plinth
    pl = st.get("plinth", 0.4)
    if pl > 0:
        parts.append(box(ctx, "stone", x + w / 2, z + d / 2, -0.05, w + T + 0.24, d + T + 0.24, pl, "plinth"))
    # roof
    parts += build_roof(ctx, spec, vol, floors * H, vols)
    # top slab (ceiling of last floor) so interiors read as rooms
    ce = box(ctx, "wood", x + w / 2, z + d / 2, floors * H - slab, w - T, d - T, slab, "ceiling")
    for oi, ov in enumerate(vols[:vi]):
        ox, oz, ow, od = volume_rect(ov)
        if ov.get("floors", 1) * ov.get("floorHeight", H) >= floors * H - 0.01:
            c = box(ctx, "wall", ox + ow / 2, oz + od / 2, -1, ow - 2 * T + 0.02, od - 2 * T + 0.02, 200, "cut_ceil"); boolean(ce, c); delete([c])
    parts.append(ce)
    return parts

def build_balconies(ctx, spec, vols):
    parts = []
    for b in spec.get("balconies", []):
        vol = vols[b.get("volume", 0)]; side = b["side"]; f = b.get("floor", 1)
        H = vol.get("floorHeight", spec.get("floorHeight", DEFAULTS["floorHeight"])); T = spec.get("wallThickness", DEFAULTS["wallThickness"])
        cx, cz, length, (nx, nz), (ax, az) = side_geom(vol, side)
        t = b.get("t", 0.5); w = b.get("w", 3.0); dep = b.get("depth", 1.2); y = f * H
        px = cx + ax * (t - 0.5) * length + nx * (T / 2 + dep / 2); pz = cz + az * (t - 0.5) * length + nz * (T / 2 + dep / 2)
        along_x = ax == 1
        parts.append(box(ctx, "wood", px, pz, y - 0.15, w if along_x else dep, dep if along_x else w, 0.15, "balcony_slab"))
        # brackets
        for sgn in (-1, 1):
            bx = px + ax * sgn * (w / 2 - 0.2) - nx * dep * 0.25; bz = pz + az * sgn * (w / 2 - 0.2) - nz * dep * 0.25
            parts.append(box(ctx, "wood", bx, bz, y - 0.6, 0.12 if along_x else dep * 0.5, dep * 0.5 if along_x else 0.12, 0.12, "balcony_bracket"))
        # railing: posts + top rail + balusters on the 3 open sides
        rail_h = 1.0
        def rail_line(x0, z0, x1, z1):
            n = max(1, int(math.hypot(x1 - x0, z1 - z0) / 0.25)); out = []
            for k in range(n + 1):
                fx = x0 + (x1 - x0) * k / n; fz = z0 + (z1 - z0) * k / n
                out.append(box(ctx, "wood", fx, fz, y, 0.05, 0.05, rail_h - 0.06, "baluster"))
            mx, mz = (x0 + x1) / 2, (z0 + z1) / 2
            out.append(box(ctx, "wood", mx, mz, y + rail_h - 0.06, abs(x1 - x0) + 0.08 if abs(x1 - x0) > abs(z1 - z0) else 0.08, 0.08 if abs(x1 - x0) > abs(z1 - z0) else abs(z1 - z0) + 0.08, 0.08, "rail"))
            out.append(box(ctx, "wood", x0, z0, y, 0.1, 0.1, rail_h, "post")); out.append(box(ctx, "wood", x1, z1, y, 0.1, 0.1, rail_h, "post"))
            return out
        ox = px + nx * dep / 2; oz = pz + nz * dep / 2  # outer edge center
        ix = px - nx * dep / 2; iz = pz - nz * dep / 2  # wall edge center
        c1 = (ox + ax * w / 2, oz + az * w / 2); c2 = (ox - ax * w / 2, oz - az * w / 2)
        i1 = (ix + ax * w / 2, iz + az * w / 2); i2 = (ix - ax * w / 2, iz - az * w / 2)
        parts += rail_line(c2[0], c2[1], c1[0], c1[1]) + rail_line(i1[0], i1[1], c1[0], c1[1]) + rail_line(i2[0], i2[1], c2[0], c2[1])
    return parts

def build_interior(ctx, spec, vols):
    parts = []
    it = spec.get("interior", {})
    T = 0.15
    for p in it.get("partitions", []):
        vol = vols[p.get("volume", 0)]; H = vol.get("floorHeight", spec.get("floorHeight", DEFAULTS["floorHeight"])); f = p.get("floor", 0)
        (x0, z0), (x1, z1) = p["from"], p["to"]; x0 += vol["x"]; x1 += vol["x"]; z0 += vol["z"]; z1 += vol["z"]
        L = math.hypot(x1 - x0, z1 - z0); along_x = abs(x1 - x0) >= abs(z1 - z0)
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        door_t = p.get("door", None); dw = 1.0; dh = 2.1
        if door_t is None:
            parts.append(box(ctx, "wall", cx, cz, f * H, L if along_x else T, T if along_x else L, H, "partition"))
        else:
            dcx = x0 + (x1 - x0) * door_t; dcz = z0 + (z1 - z0) * door_t
            legA = door_t * L - dw / 2; legB = L - door_t * L - dw / 2
            if along_x:
                parts.append(box(ctx, "wall", x0 + legA / 2, cz, f * H, legA, T, H, "partition")); parts.append(box(ctx, "wall", x1 - legB / 2, cz, f * H, legB, T, H, "partition"))
                parts.append(box(ctx, "wall", dcx, cz, f * H + dh, dw, T, H - dh, "lintel")); parts.append(box(ctx, "trim", dcx, cz, f * H, dw + 0.16, T + 0.04, dh + 0.08, "door_frame_in_tmp"))
            else:
                parts.append(box(ctx, "wall", cx, z0 + legA / 2, f * H, T, legA, H, "partition")); parts.append(box(ctx, "wall", cx, z1 - legB / 2, f * H, T, legB, H, "partition"))
                parts.append(box(ctx, "wall", cx, dcz, f * H + dh, T, dw, H - dh, "lintel")); parts.append(box(ctx, "trim", cx, dcz, f * H, T + 0.04, dw + 0.16, dh + 0.08, "door_frame_in_tmp"))
            # hollow the interior door frame with a cutter
            fr = parts[-1]
            cut = box(ctx, "wall", dcx if along_x else cx, cz if along_x else dcz, f * H - 0.01, dw if along_x else T + 0.2, T + 0.2 if along_x else dw, dh, "cut_in")
            boolean(fr, cut); delete([cut])
    st_spec = it.get("stairs")
    if st_spec:
        vol = vols[st_spec.get("volume", 0)]; H = vol.get("floorHeight", spec.get("floorHeight", DEFAULTS["floorHeight"]))
        if vol.get("floors", 1) > 1:
            sx = vol["x"] + st_spec.get("x", 1.0); sz = vol["z"] + st_spec.get("z", 1.0); rot = st_spec.get("rotY", 0); width = st_spec.get("w", 1.1)
            steps = 12; run = 3.2; rise = H / steps
            objs = []
            for k in range(steps):
                objs.append(box(ctx, "wood", run / steps * (k + 0.5), 0, k * rise, run / steps, width, (k + 1) * rise, "step"))
            objs.append(box(ctx, "wood", run / 2, width / 2 + 0.05, 0, run, 0.06, H * 0.55, "stair_string"))
            objs.append(box(ctx, "wood", run / 2, -width / 2 - 0.05, 0, run, 0.06, H * 0.55, "stair_string"))
            stair = join(objs, "stairs"); stair.rotation_euler = (0, 0, math.radians(rot)); stair.location = (sx, sz, 0)
            parts.append(stair)
    return parts

# ----------------------------------------------------------------------------- main
def gds_build(spec_or_path):
    spec = json.load(open(spec_or_path, encoding="utf-8")) if isinstance(spec_or_path, str) else spec_or_path
    # relative export/preview paths resolve against GDS_PROJECT (set by scripts/gds-building.ps1) or the spec's folder
    base = os.environ.get("GDS_PROJECT") or (os.path.dirname(os.path.abspath(spec_or_path)) if isinstance(spec_or_path, str) else os.getcwd())
    for k in ("export", "preview"):
        v = spec.get(k)
        if v and not os.path.isabs(v): spec[k] = os.path.join(base, v).replace("\\", "/")
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    if spec.get("wipe", True):
        # remove everything that is not needed for the export (default cube/light/camera, previous builds)
        for o in list(bpy.data.objects):
            if o.type in ("MESH", "LIGHT", "CAMERA", "EMPTY", "CURVE"): bpy.data.objects.remove(o, do_unlink=True)
        for me in list(bpy.data.meshes):
            if me.users == 0: bpy.data.meshes.remove(me)
        bpy.context.view_layer.update()
    ctx = Ctx(spec)
    vols = spec.get("volumes") or [{"x": 0, "z": 0, "w": spec.get("w", 8), "d": spec.get("d", 6), "floors": spec.get("floors", 1), "roof": spec.get("roofKind", "gable")}]
    parts = []
    for vi, vol in enumerate(vols): parts += build_volume(ctx, spec, vi, vol, vols)
    parts += build_balconies(ctx, spec, vols)
    parts += build_interior(ctx, spec, vols)
    for ob in parts: box_uv(ob, spec.get("uvScale", 2.0))
    building = join(parts, spec.get("name", "building"))
    # bevel for soft low-poly edges, flat shading
    _select_only(building)
    bev = building.modifiers.new("gds_bevel", "BEVEL"); bev.width = spec.get("bevel", DEFAULTS["bevel"]); bev.segments = 1; bev.limit_method = "ANGLE"; bev.angle_limit = math.radians(40)
    try: bpy.ops.object.modifier_apply(modifier=bev.name)
    except Exception: building.modifiers.remove(bev)
    bpy.ops.object.shade_flat()
    # pivot: footprint min corner at ground (x_min, z_min, 0) → translate mesh so that corner is the origin
    mx = min(v["x"] for v in vols); mz = min(v["z"] for v in vols)
    building.data.transform(__import__("mathutils").Matrix.Translation((-mx, -mz, 0)))
    building.location = (0, 0, 0)
    stats = {"name": building.name, "tris": sum(len(p.vertices) - 2 for p in building.data.polygons), "materials": [m.name for m in building.data.materials],
             "dims": [round(v, 3) for v in building.dimensions]}
    out = spec.get("export")
    if out:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        _select_only(building)
        base, ext = os.path.splitext(out)
        if ext.lower() in (".glb", ".gltf", ""):
            bpy.ops.export_scene.gltf(filepath=base + ".glb", export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
            stats["glb"] = base + ".glb"
        if spec.get("exportFbx", True):
            bpy.ops.export_scene.fbx(filepath=base + ".fbx", use_selection=True, apply_unit_scale=True, apply_scale_options="FBX_SCALE_ALL", bake_space_transform=True, axis_forward="-Z", axis_up="Y", path_mode="COPY", embed_textures=True)
            stats["fbx"] = base + ".fbx"
        stats["bytes"] = os.path.getsize(stats.get("glb", stats.get("fbx")))
    if spec.get("preview"):
        stats["preview"] = render_preview(building, spec["preview"])
    return json.dumps(stats)

def render_preview(ob, path):
    """Workbench render (fast, headless) from a 3/4 view for the gate screenshot."""
    sc = bpy.context.scene
    cam_data = bpy.data.cameras.new("gds_cam"); cam = bpy.data.objects.new("gds_cam", cam_data); sc.collection.objects.link(cam)
    dims = ob.dimensions; center = Vector((dims.x / 2, dims.y / 2, dims.z / 2))
    dist = max(dims) * 1.9
    cam.location = center + Vector((dist * 0.75, -dist * 0.85, dist * 0.55))
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    try: sc.render.engine = "BLENDER_WORKBENCH"
    except TypeError: pass
    sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "MATERIAL"; sc.display.shading.show_shadows = True; sc.display.shading.show_cavity = True
    sc.render.resolution_x = 1280; sc.render.resolution_y = 800; sc.render.filepath = path
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True); bpy.data.cameras.remove(cam_data)
    return path

if __name__ == "__main__" and "--" in sys.argv:
    print("GDS_RESULT " + gds_build(sys.argv[sys.argv.index("--") + 1]))
