# hero_kit: deterministic procedural modelling helpers for headless Blender hero props.
# Used by asset scripts `Tools/<asset>_build.py` run as:
#   blender -b -P Tools/<asset>_build.py -- <out.glb> <preview_prefix>
# Conventions: meters, Z up, the front of the prop faces -Y, pivot at the base. The glTF exporter turns it into
# Y up; Nucleon shows it Z up again with the front toward -Y (rotate the piece yaw 180 to face a PlayerStart at
# the origin looking +Y).
# Ornament frame ("local"): X right, Y up, Z out of the surface toward the viewer; `frame()` places it.
import bpy, bmesh, math, random, os, sys
from mathutils import Vector, Matrix

# ------------------------------------------------------------------ scene, args
def args():
    """Arguments after `--`: [out.glb, preview_prefix]."""
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return (a[0] if a else "asset.glb"), (a[1] if len(a) > 1 else None)

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene

def coll():
    return bpy.context.scene.collection

# ------------------------------------------------------------------ materials and images
def material(name, color, metallic=0.0, rough=0.5, coat=0.0, image=None, emission=None, strength=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    p.inputs["Base Color"].default_value = (*color, 1.0)
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Roughness"].default_value = rough
    for key in ("Coat Weight", "Clearcoat"):
        if key in p.inputs:
            p.inputs[key].default_value = coat
            break
    if image is not None:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = image
        nt.links.new(tex.outputs["Color"], p.inputs["Base Color"])
    if emission is not None:
        for key in ("Emission Color", "Emission"):
            if key in p.inputs:
                p.inputs[key].default_value = (*emission, 1.0)
                break
        if "Emission Strength" in p.inputs:
            p.inputs["Emission Strength"].default_value = strength
    return m

def image_from_rgb(name, rgb, path):
    """rgb: numpy float array (h, w, 3) in sRGB 0..1, row 0 = top. Saved as PNG (the GLB embeds it)."""
    import numpy as np
    h, w, _ = rgb.shape
    img = bpy.data.images.new(name, w, h, alpha=False)
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :3] = np.clip(rgb[::-1], 0, 1)
    img.pixels.foreach_set(rgba.ravel())
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    return img

# ------------------------------------------------------------------ matrices
FRONT = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))  # local X,Y,Z -> world X,Z,-Y

def frame(pos, yaw=0.0, roll=0.0, pitch=0.0, scale=1.0):
    """Ornament frame at `pos` on a front surface. yaw turns the plane around world Z (deg, + turns the face toward
    +X), roll spins inside the plane (deg, + counter-clockwise as seen), pitch tilts the top toward the viewer."""
    s = scale if isinstance(scale, (tuple, list)) else (scale, scale, scale)
    return (Matrix.Translation(Vector(pos)) @ Matrix.Rotation(math.radians(yaw), 4, "Z") @ FRONT
            @ Matrix.Rotation(math.radians(roll), 4, "Z") @ Matrix.Rotation(math.radians(-pitch), 4, "X")
            @ Matrix.Diagonal((*s, 1.0)))

def local(x=0.0, y=0.0, z=0.0, angle=0.0, scale=1.0, mirror=False):
    """Matrix inside an ornament frame: move, turn in the plane (deg, CCW), scale, optional mirror on X."""
    m = Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(angle), 4, "Z") @ Matrix.Diagonal((scale, scale, scale, 1.0))
    return (Matrix.Diagonal((-1, 1, 1, 1)) @ m) if mirror else m

MIRROR_X = Matrix.Diagonal((-1, 1, 1, 1))

# ------------------------------------------------------------------ objects
def mesh_object(name, me, mat=None, smooth=True, matrix=None):
    if matrix is not None:
        me.transform(matrix)
        if matrix.determinant() < 0:
            me.flip_normals()
    ob = bpy.data.objects.new(name, me)
    coll().objects.link(ob)
    if mat is not None:
        me.materials.append(mat)
    if smooth is not None:
        for p in me.polygons:
            p.use_smooth = smooth
    return ob

def from_bmesh(name, bm, mat=None, smooth=True, matrix=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return mesh_object(name, me, mat, smooth, matrix)

def bake(ob, name, mat=None, matrix=None, smooth=True):
    """Any object (curve, text, modifiers) -> plain mesh object; the source is removed."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    me.materials.clear()
    return mesh_object(name, me, mat, smooth, matrix)

def join(objs, name):
    """Join meshes (one draw per material slot in the engine). Returns the joined object."""
    objs = [o for o in objs if o is not None and o.type == "MESH"]
    if not objs:
        return None
    if len(objs) == 1:
        objs[0].name = name
        return objs[0]
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    with bpy.context.temp_override(active_object=objs[0], object=objs[0], selected_objects=objs,
                                   selected_editable_objects=objs):
        bpy.ops.object.join()
    objs[0].name = name
    return objs[0]

def join_by_material(prefix="Part"):
    """Join every mesh of the scene into one object per first material."""
    groups = {}
    for o in list(coll().objects):
        if o.type == "MESH" and o.data.materials:
            groups.setdefault(o.data.materials[0].name, []).append(o)
    return [join(objs, "%s_%s" % (prefix, k)) for k, objs in groups.items()]

# ------------------------------------------------------------------ 2D outlines and prisms
def offset(poly, d):
    """Inset (d > 0) a convex counter-clockwise polygon along the vertex normals (keeps the vertex count)."""
    n = len(poly)
    res = []
    for i in range(n):
        a, b, c = poly[i - 1], poly[i], poly[(i + 1) % n]
        e1, e2 = (b - a).normalized(), (c - b).normalized()
        n1, n2 = Vector((-e1.y, e1.x)), Vector((-e2.y, e2.x))
        nm = n1 + n2
        if nm.length < 1e-6:
            nm = n1
        nm.normalize()
        res.append(b + nm * (d / max(0.35, nm.dot(n1))))
    return res

def rounded_rect(w, h, r, seg=6):
    """Counter-clockwise rounded rectangle centred on the origin."""
    pts = []
    for cx, cy, a0 in ((w/2 - r, h/2 - r, 0), (-w/2 + r, h/2 - r, 90), (-w/2 + r, -h/2 + r, 180), (w/2 - r, -h/2 + r, 270)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append(Vector((cx + r * math.cos(a), cy + r * math.sin(a))))
    return pts

def circle(r, n=64, cx=0.0, cy=0.0):
    return [Vector((cx + r * math.cos(2*math.pi*i/n), cy + r * math.sin(2*math.pi*i/n))) for i in range(n)]

def slab(name, rings, z0, z1, mat, bevel=0.0, matrix=None):
    """Prism from a convex outline (or outer + inner ring with the same vertex count) between z0 and z1 (local Z),
    top edges rounded with a bmesh bevel. Never use curve bevels for outlines: they spike at sharp tips."""
    bm = bmesh.new()
    outer = rings[0]
    inner = rings[1] if len(rings) > 1 else None
    ot = [bm.verts.new((p.x, p.y, z1)) for p in outer]
    ob_ = [bm.verts.new((p.x, p.y, z0)) for p in outer]
    n = len(outer)
    if inner:
        it = [bm.verts.new((p.x, p.y, z1)) for p in inner]
        ib = [bm.verts.new((p.x, p.y, z0)) for p in inner]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((ot[i], ot[j], it[j], it[i]))
            bm.faces.new((ob_[j], ob_[i], ib[i], ib[j]))
            bm.faces.new((ib[i], ib[j], it[j], it[i]))
    else:
        caps = [bm.faces.new(ot), bm.faces.new(list(reversed(ob_)))]
        bmesh.ops.poke(bm, faces=caps)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((ob_[i], ob_[j], ot[j], ot[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    rim = [e for e in bm.edges if all(abs(v.co.z - z1) < 1e-7 for v in e.verts)
           and len(e.link_faces) == 2 and abs(e.link_faces[0].normal.z - e.link_faces[1].normal.z) > 0.5]
    if bevel > 0 and rim:
        bmesh.ops.bevel(bm, geom=rim, offset=bevel, segments=3, profile=0.5, affect="EDGES", clamp_overlap=True)
    ob = from_bmesh(name, bm, mat, smooth=None, matrix=matrix)
    for p in ob.data.polygons:
        p.use_smooth = abs(p.normal.z) < 0.98 if matrix is None else True
    return ob

# ------------------------------------------------------------------ lofts, tubes, disks, text
def smooth_profile(points, z):
    """Catmull-Rom through (z, value...) keys sorted by z; returns the values at z."""
    zs = [p[0] for p in points]
    if z <= zs[0]:
        return points[0][1:]
    if z >= zs[-1]:
        return points[-1][1:]
    i = max(k for k in range(len(zs) - 1) if zs[k] <= z)
    t = (z - zs[i]) / (zs[i + 1] - zs[i])
    p0, p1, p2, p3 = points[max(i - 1, 0)], points[i], points[i + 1], points[min(i + 2, len(points) - 1)]
    out = []
    for k in range(1, len(p1)):
        a, b, c, d = p0[k], p1[k], p2[k], p3[k]
        out.append(0.5 * ((2*b) + (-a + c)*t + (2*a - 5*b + 4*c - d)*t*t + (-a + 3*b - 3*c + d)*t**3))
    return out

def superellipse(w, d, n=3.0, segs=64, cx=0.0, cy=0.0, z=0.0, start=math.pi/2):
    """Ring of segs + 1 points (first repeated last, for a UV seam), counter-clockwise from the back (+Y)."""
    pts = []
    for j in range(segs + 1):
        t = start + 2 * math.pi * j / segs
        c, s = math.cos(t), math.sin(t)
        pts.append(Vector((cx + w * math.copysign(abs(c) ** (2/n), c), cy + d * math.copysign(abs(s) ** (2/n), s), z)))
    return pts

def loft(name, rings, mat, cap_start=True, cap_end=True, uv_scale=1.0, matrix=None):
    """Skin over rings of equal length (each ring open with its first point repeated last = UV seam). UVs: u along
    the ring by arc length, v along the rings by distance, both / uv_scale (meters per texture tile)."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    us = []
    for r in rings:
        acc = [0.0]
        for a, b in zip(r, r[1:]):
            acc.append(acc[-1] + (b - a).length)
        us.append(acc)
    vv = [0.0]
    for a, b in zip(rings, rings[1:]):
        ca = sum(a, Vector()) / len(a); cb = sum(b, Vector()) / len(b)
        vv.append(vv[-1] + max((cb - ca).length, 1e-6))
    for i in range(len(rings) - 1):
        for j in range(len(rings[i]) - 1):
            f = bm.faces.new((vs[i][j], vs[i][j + 1], vs[i + 1][j + 1], vs[i + 1][j]))
            for loop, (ii, jj) in zip(f.loops, ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))):
                loop[uv].uv = (us[ii][jj] / uv_scale, vv[ii] / uv_scale)
    bmesh.ops.remove_doubles(bm, verts=[v for row in vs for v in (row[0], row[-1])], dist=1e-7)
    caps = []
    def ring_verts(row):
        seen, out = set(), []
        for v in row:
            if v.is_valid and v.index not in seen:
                seen.add(v.index); out.append(v)
        return out
    bm.verts.index_update()
    if cap_start:
        caps.append(bm.faces.new(list(reversed(ring_verts(vs[0])))))
    if cap_end:
        caps.append(bm.faces.new(ring_verts(vs[-1])))
    if caps:
        bmesh.ops.poke(bm, faces=caps)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return from_bmesh(name, bm, mat, True, matrix)

def tube(name, pts, radius, mat, radii=None, caps=True, res=3, matrix=None):
    """Tube along points; radii = per-point multipliers of radius (tapering)."""
    if matrix is not None:
        pts = [matrix @ Vector(p) for p in pts]
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = res
    cu.use_fill_caps = caps
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (p[0], p[1], p[2], 1.0)
        if radii:
            sp.points[i].radius = radii[i]
    ob = bpy.data.objects.new(name + "_c", cu)
    coll().objects.link(ob)
    return bake(ob, name, mat)

def ring_tube(name, r, minor, mat, n=96, matrix=None):
    pts = [Vector((r * math.cos(2*math.pi*i/n), r * math.sin(2*math.pi*i/n), 0)) for i in range(n + 1)]
    return tube(name, pts, minor, mat, caps=False, matrix=matrix)

def polar_disk(name, R, mat, height=lambda r, a: 0.0, rings=16, segs=96, a0=0.0, a1=2*math.pi, thickness=0.0, matrix=None):
    """Disk (or fan a0..a1) in local XY, height(r_norm, angle) along local Z; optional solidify thickness."""
    bm = bmesh.new()
    full = abs(a1 - a0 - 2*math.pi) < 1e-6
    na = segs if full else segs + 1
    c = bm.verts.new((0, 0, height(0.0, 0.0)))
    grid = []
    for i in range(1, rings + 1):
        rn = i / rings
        row = []
        for j in range(na):
            a = a0 + (a1 - a0) * j / segs
            row.append(bm.verts.new((R * rn * math.cos(a), R * rn * math.sin(a), height(rn, a))))
        grid.append(row)
    wrap = segs if full else segs
    for j in range(wrap):
        j2 = (j + 1) % na if full else j + 1
        bm.faces.new((c, grid[0][j], grid[0][j2]))
        for i in range(rings - 1):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j2], grid[i][j2]))
    if thickness > 0:
        bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=thickness)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return from_bmesh(name, bm, mat, True, matrix)

_fonts = {}
def text(name, body, size, mat, font=None, extrude=0.0006, matrix=None):
    """Centred text in local XY (reading along +X, up +Y), facing +Z. font = a .ttf path (e.g. C:/Windows/Fonts/times.ttf)."""
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    if font and os.path.exists(font):
        if font not in _fonts:
            _fonts[font] = bpy.data.fonts.load(font)
        cu.font = _fonts[font]
    ob = bpy.data.objects.new(name + "_t", cu)
    coll().objects.link(ob)
    return bake(ob, name, mat, matrix=matrix, smooth=False)

# ------------------------------------------------------------------ ornament (rococo / acanthus / scrolls)
def curl_path(L, k_mid, k_end, p=3.0, kind="C", n=90):
    """Centreline of a scroll: curvature k_mid in the middle growing to k_end at both ends (Euler spiral curls).
    kind C: both ends curl the same way; S: opposite ways. Returns [(Vector2, s in -1..1)], centred."""
    ds = L / n
    def integrate(sign):
        pts, ang, pos = [(Vector((0, 0)), 0.0)], 0.0, Vector((0, 0))
        for i in range(1, n // 2 + 1):
            s = i / (n // 2)
            k = k_mid + (k_end - k_mid) * s ** p
            if kind == "S":
                k = k * sign
            ang += k * ds * sign
            pos = pos + Vector((math.cos(ang), math.sin(ang))) * ds * sign
            pts.append((pos.copy(), s * sign))
        return pts
    right = integrate(1)
    left = integrate(-1)
    return [ (p_, s) for p_, s in reversed(left[1:]) ] + right

def scroll(name, L, radius, mat, kind="C", k_mid=None, k_end=None, lift=0.25, matrix=None):
    """C or S scroll as a tapered tube in local XY (ends curl), slightly raised toward +Z in the middle."""
    k_mid = (2.0 / L) if k_mid is None else k_mid
    k_end = (16.0 / L) if k_end is None else k_end
    path = curl_path(L, k_mid, k_end, kind=kind)
    pts = [Vector((p.x, p.y, lift * radius * (1 - abs(s)))) for p, s in path]
    radii = [max(0.25, 1.0 - 0.7 * abs(s) ** 1.6) for _, s in path]
    return tube(name, pts, radius, mat, radii=radii, matrix=matrix)

def leaf(name, L, W, mat, curl=1.6, cup=0.45, lobes=3, serr=0.3, thick=0.0025, wave=0.12, nu=28, nv=9, matrix=None):
    """Acanthus leaf along local +X, width on Y, curling toward +Z (the viewer) at the tip, lobed edge, cupped."""
    bm = bmesh.new()
    cs, ang, pos = [], 0.0, Vector((0, 0))
    for i in range(nu + 1):
        s = i / nu
        cs.append((pos.copy(), ang))
        ang = curl * (s + 1/nu) ** 2
        pos = pos + Vector((math.cos(ang), math.sin(ang))) * (L / nu)
    grid = []
    for i, (c, a) in enumerate(cs):
        s = i / nu
        w = W * (4 * s * (1 - s) + 0.08) ** 0.6 * (1 - serr * abs(math.sin(lobes * math.pi * s)) ** 0.7)
        if i == nu:
            w *= 0.15
        nrm = Vector((-math.sin(a), math.cos(a)))       # in the (x, z) plane
        row = []
        for j in range(nv + 1):
            v = -1 + 2 * j / nv
            z_off = cup * w * v * v - 0.25 * w * (1 - abs(v)) * 0.3 + wave * w * math.sin(7 * math.pi * s + 2 * v)
            x = c.x + nrm.x * z_off
            z = c.y + nrm.y * z_off
            row.append(bm.verts.new((x, v * w, z)))
        grid.append(row)
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
    bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=thick)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return from_bmesh(name, bm, mat, True, matrix)

def shell(name, R, mat, ribs=9, depth=0.35, matrix=None):
    """Rococo shell (coquille): ribbed half fan opening upward (+Y), bulging toward +Z."""
    def h(rn, a):
        return R * (depth * (1 - rn ** 2) ** 0.5 + 0.06 * abs(math.cos(ribs * (a - math.pi/2) / 2)) ** 3 * rn)
    return polar_disk(name, R, mat, height=h, rings=10, segs=ribs * 8, a0=math.radians(-15), a1=math.radians(195),
                      thickness=R * 0.04, matrix=matrix)

def cluster(prefix, F, size, mat, style="spray", seed=1, density=1.0, spread=(-30, 210)):
    """A rococo ormolu group in ornament frame F. styles: spray (asymmetric leaves + scrolls), cartouche (symmetric:
    shell + C-scroll frame + leaf fans), flame (finial: leaves rising and curling), corner (S-scroll + leaves)."""
    rnd = random.Random(seed)
    objs = []
    def L(m):
        return F @ m
    if style == "cartouche":
        for mir in (False, True):
            objs.append(scroll(prefix + "cs", size * 0.9, size * 0.05, mat, "C", matrix=L(local(size * 0.32, 0, 0, 100, 1, mir))))
            for k in range(int(4 * density)):
                a = rnd.uniform(10, 80)
                objs.append(leaf(prefix + "lf", size * rnd.uniform(0.35, 0.6), size * rnd.uniform(0.12, 0.18), mat,
                                 curl=rnd.uniform(1.2, 2.4), matrix=L(local(size * 0.15, size * 0.05, 0, a, 1, mir))))
            objs.append(scroll(prefix + "cs2", size * 0.45, size * 0.035, mat, "S",
                               matrix=L(local(size * 0.25, -size * 0.3, 0, -30, 1, mir))))
        objs.append(shell(prefix + "sh", size * 0.32, mat, matrix=L(local(0, -size * 0.12, size * 0.01))))
    elif style == "flame":
        for k in range(int(9 * density)):
            a = 90 + rnd.uniform(-45, 45)
            y = size * rnd.uniform(0.0, 0.45)
            objs.append(leaf(prefix + "fl", size * rnd.uniform(0.35, 0.7), size * rnd.uniform(0.08, 0.13), mat,
                             curl=rnd.uniform(1.0, 2.4), lobes=rnd.choice((2, 3, 4)),
                             matrix=L(local(rnd.uniform(-0.08, 0.08) * size, y, rnd.uniform(-0.05, 0.08) * size, a))))
        for mir in (False, True):
            objs.append(scroll(prefix + "fs", size * 0.4, size * 0.04, mat, "C", matrix=L(local(size * 0.12, size * 0.05, 0, 60, 1, mir))))
    elif style == "corner":
        objs.append(scroll(prefix + "ss", size * 0.9, size * 0.05, mat, "S", matrix=L(local(0, 0, 0, 70))))
        for k in range(int(5 * density)):
            objs.append(leaf(prefix + "cl", size * rnd.uniform(0.3, 0.55), size * rnd.uniform(0.1, 0.16), mat,
                             curl=rnd.uniform(1.2, 2.6), matrix=L(local(rnd.uniform(-0.15, 0.15) * size,
                             rnd.uniform(-0.3, 0.3) * size, 0, rnd.uniform(*spread)))))
    else:  # spray
        for k in range(int(10 * density)):
            a = rnd.uniform(*spread)
            objs.append(leaf(prefix + "sp", size * rnd.uniform(0.3, 0.65), size * rnd.uniform(0.08, 0.13), mat,
                             curl=rnd.uniform(0.9, 2.2), lobes=rnd.choice((2, 3, 4)),
                             matrix=L(local(rnd.uniform(-0.12, 0.12) * size, rnd.uniform(-0.12, 0.12) * size,
                                            rnd.uniform(0, 0.06) * size, a))))
        for k in range(int(3 * density)):
            objs.append(scroll(prefix + "sc", size * rnd.uniform(0.35, 0.7), size * 0.035, mat, rnd.choice("CS"),
                               matrix=L(local(rnd.uniform(-0.25, 0.25) * size, rnd.uniform(-0.25, 0.25) * size, 0,
                                              rnd.uniform(0, 360)))))
    return objs

# ------------------------------------------------------------------ export and preview
def export_glb(path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_apply=True, export_yup=True)
    print("GLB", path)

def stats():
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in coll().objects if o.type == "MESH")
    mats = {m.name for o in coll().objects if o.type == "MESH" for m in o.data.materials if m}
    print("STATS objects=%d tris=%d materials=%d" % (len([o for o in coll().objects if o.type == "MESH"]), tris, len(mats)))

def preview(prefix, target, dist, views=(("front", 0, 0), ("three_quarter", 35, 12)), res=1024, lens=70,
            background=(0.05, 0.04, 0.035)):
    """Renders PNG previews: views = (tag, azimuth deg from the front toward +X, elevation deg)."""
    scene = bpy.context.scene
    world = bpy.data.worlds.new("W"); scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (*background, 1); bg.inputs["Strength"].default_value = 0.8
    target = Vector(target)
    def light(name, d, energy, size, color):
        ld = bpy.data.lights.new(name, "AREA"); ld.energy = energy; ld.size = size; ld.color = color
        lo = bpy.data.objects.new(name, ld); coll().objects.link(lo)
        lo.location = target + Vector(d)
        lo.rotation_euler = (target - lo.location).to_track_quat("-Z", "Y").to_euler()
    k = dist / 2.0
    light("Key", (-1.0 * k, -1.6 * k, 1.3 * k), 140 * k * k, 1.2 * k, (1.0, 0.93, 0.84))
    light("Fill", (1.4 * k, -1.2 * k, 0.3 * k), 45 * k * k, 2.0 * k, (0.85, 0.9, 1.0))
    light("Rim", (0.4 * k, 1.5 * k, 1.4 * k), 80 * k * k, 1.0 * k, (1.0, 1.0, 1.0))
    cam_d = bpy.data.cameras.new("Cam"); cam_d.lens = lens; cam_d.clip_start = 0.01
    cam = bpy.data.objects.new("Cam", cam_d); coll().objects.link(cam); scene.camera = cam
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "CYCLES"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            pass
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    out = []
    for tag, az, el in views:
        a, e = math.radians(az), math.radians(el)
        cam.location = target + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * dist
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = "%s_%s.png" % (prefix, tag)
        bpy.ops.render.render(write_still=True)
        print("PNG", scene.render.filepath)
        out.append(scene.render.filepath)
    return out
