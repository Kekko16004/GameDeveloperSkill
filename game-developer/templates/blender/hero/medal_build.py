# Airborne supply medal: shield badge with a parachute and a brick crate.
# Deterministic Blender build (headless):
#   blender -b -P Tools/medal_build.py -- <out.glb> <preview_prefix>
# Modelled in XY with the relief toward +Z, then stood up (front = -Y, Z up) for export.
import bpy, bmesh, math, sys, random
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT_GLB = argv[0] if argv else "medal.glb"
PREVIEW = argv[1] if len(argv) > 1 else None
HEIGHT_M = 0.5          # final height of the medal in meters (showcase size)
random.seed(7)

# ---------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection

def material(name, color, metallic=0.0, rough=0.5, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    p.inputs["Base Color"].default_value = (*color, 1.0)
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Roughness"].default_value = rough
    for key in ("Coat Weight", "Clearcoat"):
        if key in p.inputs:
            p.inputs[key].default_value = coat
            break
    return m

M_GOLD   = material("Gold",        (0.70, 0.47, 0.20), 1.0, 0.30)
M_BAND   = material("DarkMetal",   (0.06, 0.06, 0.055), 0.85, 0.55)
M_FIELD  = material("Enamel",      (0.022, 0.040, 0.041), 0.0, 0.55, coat=0.15)
M_CANOPY = material("Canopy",      (0.34, 0.235, 0.11), 0.15, 0.5)
M_SEAM   = material("CanopySeam",  (0.16, 0.09, 0.035), 0.3, 0.55)
M_LINE   = material("Lines",       (0.36, 0.24, 0.11), 0.3, 0.5)
M_BRICK  = [material("Brick%d" % i, c, 0.15, 0.6) for i, c in enumerate(
            [(0.24, 0.072, 0.02), (0.19, 0.055, 0.016), (0.28, 0.095, 0.03)])]

# ---------------------------------------------------------------- shield outline
TOP, HALF_W, SIDE_Y, TIP_Y, CORNER = 1.15, 1.0, 0.30, -1.32, 0.10

def shield_outline(n=160):
    """Convex heater shield, counter-clockwise, starting at the top-right corner."""
    arc = lambda cx, cy, a0: [Vector((cx + CORNER*math.cos(a0 + k*math.pi/16),
                                      cy + CORNER*math.sin(a0 + k*math.pi/16))) for k in range(9)]
    pts = arc(HALF_W - CORNER, TOP - CORNER, 0.0) + arc(-HALF_W + CORNER, TOP - CORNER, math.pi/2)
    pts += [Vector((-HALF_W, TOP - CORNER - (TOP - CORNER - SIDE_Y) * i / 12)) for i in range(1, 13)]
    p0, c, p1 = Vector((-HALF_W, SIDE_Y)), Vector((-HALF_W, -0.75)), Vector((0.0, TIP_Y))
    left = [((1-t)**2)*p0 + 2*(1-t)*t*c + (t**2)*p1 for t in [i/n for i in range(1, n+1)]]
    pts += left
    pts += [Vector((-p.x, p.y)) for p in reversed(left[:-1])]
    pts += [Vector((HALF_W, SIDE_Y + (TOP - CORNER - SIDE_Y) * i / 12)) for i in range(0, 12)]
    out = []
    for p in pts:
        if not out or (p - out[-1]).length > 1e-5:
            out.append(p)
    return out

def offset(poly, d):
    """Inset (d > 0) a convex counter-clockwise polygon along the vertex normals."""
    n = len(poly)
    res = []
    for i in range(n):
        a, b, c = poly[i-1], poly[i], poly[(i+1) % n]
        e1, e2 = (b - a).normalized(), (c - b).normalized()
        n1, n2 = Vector((-e1.y, e1.x)), Vector((-e2.y, e2.x))  # inward normals for CCW
        nm = (n1 + n2)
        if nm.length < 1e-6:
            nm = n1
        nm.normalize()
        cosh = max(0.35, nm.dot(n1))
        res.append(b + nm * (d / cosh))
    return res

OUTLINE = shield_outline()

def slab(name, rings, extrude, bevel, z, mat):
    """Prism between z - extrude and z + extrude from an outline (or an outer/inner ring with matching
    vertex counts), top edges rounded with a bmesh bevel. No curve bevel: it spikes at the shield tip."""
    z0, z1 = z - extrude, z + extrude
    bm = bmesh.new()
    outer = rings[0]
    inner = rings[1] if len(rings) > 1 else None
    ot = [bm.verts.new((p.x, p.y, z1)) for p in outer]
    ob_ = [bm.verts.new((p.x, p.y, z0)) for p in outer]
    n = len(outer)
    top_edges = []
    if inner:
        it = [bm.verts.new((p.x, p.y, z1)) for p in inner]
        ib = [bm.verts.new((p.x, p.y, z0)) for p in inner]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((ot[i], ot[j], it[j], it[i]))      # top
            bm.faces.new((ob_[j], ob_[i], ib[i], ib[j]))    # bottom
            bm.faces.new((ib[i], ib[j], it[j], it[i]))      # inner wall
    else:
        caps = [bm.faces.new(ot), bm.faces.new(list(reversed(ob_)))]
        bmesh.ops.poke(bm, faces=caps)          # fan from the centre: no long slivers across the face
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((ob_[i], ob_[j], ot[j], ot[i]))        # outer wall
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.edges.ensure_lookup_table()
    rim = [e for e in bm.edges if all(abs(v.co.z - z1) < 1e-6 for v in e.verts)
           and len(e.link_faces) == 2 and abs(e.link_faces[0].normal.z - e.link_faces[1].normal.z) > 0.5]
    if bevel > 0 and rim:
        bmesh.ops.bevel(bm, geom=rim, offset=bevel, segments=3, profile=0.5, affect="EDGES", clamp_overlap=True)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    mo = bpy.data.objects.new(name, me)
    col.objects.link(mo)
    me.materials.append(mat)
    for poly in me.polygons:
        poly.use_smooth = abs(poly.normal.z) < 0.98
    return mo

# layers (top surfaces): base 0.06, field 0.072, band 0.10, gold edge 0.115
base  = slab("Base",  [offset(OUTLINE, 0.006)],                                       0.03,  0.012, 0.03,  M_BAND)
field = slab("Field", [offset(OUTLINE, 0.14)],                         0.006, 0.0,   0.066, M_FIELD)
band  = slab("Band",  [offset(OUTLINE, 0.075), offset(OUTLINE, 0.14)], 0.02,  0.008, 0.08,  M_BAND)
edge  = slab("Edge",  [OUTLINE, offset(OUTLINE, 0.075)],               0.0275, 0.014, 0.0875, M_GOLD)
FIELD_TOP = 0.072

# ---------------------------------------------------------------- parachute canopy
CX, CY0, RX, RY, RZ = 0.0, 0.05, 0.62, 0.72, 0.20
PANELS, SCALLOP, PUFF = 7, 0.13, 0.07
SEAMS = [-math.pi/2 + k*math.pi/PANELS for k in range(PANELS + 1)]

def canopy_point(theta, lam):
    frac = ((theta + math.pi/2) / (math.pi/PANELS)) % 1.0
    bulge = math.sin(math.pi * frac)
    r = 1.0 + PUFF * bulge * math.cos(lam) ** 0.6
    x = RX * r * math.cos(lam) * math.sin(theta)
    y = CY0 + RY * math.sin(lam)
    z = RZ * r * math.cos(lam) * math.cos(theta)
    return Vector((CX + x, y, FIELD_TOP + z))

def lam_min(theta):
    frac = ((theta + math.pi/2) / (math.pi/PANELS)) % 1.0
    return -SCALLOP * math.sin(math.pi * frac)

NU, NV = PANELS * 16, 48
bm = bmesh.new()
grid = []
for i in range(NU + 1):
    th = -math.pi/2 + math.pi * i / NU
    lo = lam_min(th)
    row = []
    for j in range(NV + 1):
        v = j / NV
        lam = lo + (math.pi/2 - 1e-3 - lo) * (v ** 0.85)
        row.append(bm.verts.new(canopy_point(th, lam)))
    grid.append(row)
for i in range(NU):
    for j in range(NV):
        bm.faces.new((grid[i][j], grid[i+1][j], grid[i+1][j+1], grid[i][j+1]))
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
me = bpy.data.meshes.new("Canopy")
bm.to_mesh(me); bm.free()
for p in me.polygons:
    p.use_smooth = True
canopy = bpy.data.objects.new("Canopy", me)
col.objects.link(canopy)
me.materials.append(M_CANOPY)
sol = canopy.modifiers.new("solid", "SOLIDIFY")
sol.thickness = 0.018
sol.offset = -1.0

def tube(name, pts, radius, mat):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 2
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (p.x, p.y, p.z, 1.0)
    ob = bpy.data.objects.new(name + "_c", cu)
    col.objects.link(ob)
    m = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(ob)
    mo = bpy.data.objects.new(name, m)
    col.objects.link(mo)
    m.materials.append(mat)
    for p in m.polygons:
        p.use_smooth = True
    return mo

seam_objs = []
for k, th in enumerate(SEAMS[1:-1], 1):
    pts = [canopy_point(th, (math.pi/2 - 0.02) * t / 30) + Vector((0, 0, 0.004)) for t in range(31)]
    seam_objs.append(tube("Seam%d" % k, pts, 0.011, M_SEAM))
# hem along the scalloped lower edge
hem = [canopy_point(-math.pi/2 + math.pi*i/(NU), lam_min(-math.pi/2 + math.pi*i/NU)) for i in range(NU + 1)]
seam_objs.append(tube("Hem", hem, 0.012, M_SEAM))
# apex vent ring
seam_objs.append(tube("Apex", [canopy_point(t, math.pi/2 - 0.12) for t in
                               [-math.pi/2 + math.pi*i/24 for i in range(25)]], 0.01, M_SEAM))

# ---------------------------------------------------------------- brick crate
S, LAYERS, GAP = 0.44, 5, 0.007
h = S / LAYERS
bm = bmesh.new()
brick_mat_index = []
def brick(cx, cy, cz, sx, sy, sz):
    r = bmesh.ops.create_cube(bm, size=1.0)
    vs = r["verts"]
    bmesh.ops.scale(bm, vec=(sx - GAP, sy - GAP, sz - GAP), verts=vs)
    bmesh.ops.translate(bm, vec=(cx, cy, cz), verts=vs)
    idx = random.randrange(3)
    for f in {f for v in vs for f in v.link_faces}:
        f.material_index = idx
for layer in range(LAYERS):
    y = -S/2 + h*(layer + 0.5)
    if layer % 2 == 0:   # two long bricks along X, split in Z
        brick(0, y, -S/4, S, h, S/2); brick(0, y, S/4, S, h, S/2)
    else:                # two long bricks along Z, split in X
        brick(-S/4, y, 0, S/2, h, S); brick(S/4, y, 0, S/2, h, S)
bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.012, segments=2, affect="EDGES", profile=0.5)
me = bpy.data.meshes.new("Crate")
bm.to_mesh(me); bm.free()
crate = bpy.data.objects.new("Crate", me)
col.objects.link(crate)
for m in M_BRICK:
    me.materials.append(m)
# corner toward the viewer, top tilted toward the viewer, depth flattened into a relief
rot = Matrix.Rotation(math.radians(24), 4, "X") @ Matrix.Rotation(math.radians(45), 4, "Y")
me.transform(rot)
me.transform(Matrix.Diagonal((1.12, 1.0, 0.62, 1.0)))
zmin = min(v.co.z for v in me.vertices)
crate.location = (0.0, -0.52, FIELD_TOP - 0.02 - zmin)
for p in me.polygons:
    p.use_smooth = False

# attach points on the crate top: left, front and right corners of the top face
def crate_world(local):
    v = rot @ Vector(local)
    v = Vector((v.x*1.12, v.y, v.z*0.62))
    return v + crate.location
top_y = S/2
corners = sorted([crate_world((sx*S/2, top_y, sz*S/2)) for sx in (-1, 1) for sz in (-1, 1)], key=lambda v: v.x)
attach_l, attach_r = corners[0], corners[-1]
attach_f = max(corners[1:3], key=lambda v: v.z)
lines = []
for k, th in enumerate(SEAMS):
    start = canopy_point(th, 0.0) + Vector((0, 0, -0.004))
    if th < -0.3: end = attach_l
    elif th > 0.3: end = attach_r
    else: end = attach_f
    end = end + Vector((0, 0.0, 0.005))
    lines.append(tube("Line%d" % k, [start.lerp(end, t/12) for t in range(13)], 0.0075, M_LINE))

# ---------------------------------------------------------------- assemble, stand up, scale
parts = [base, field, band, edge, canopy, crate] + seam_objs + lines
root = bpy.data.objects.new("AirborneSupplyMedal", None)
col.objects.link(root)
for o in parts:
    o.parent = root
height_units = TOP - TIP_Y
s = HEIGHT_M / height_units
root.scale = (s, s, s)
root.rotation_euler = (math.radians(90), 0, 0)   # XY plane -> XZ, relief toward -Y
root.location = (0, 0, -TIP_Y * s)               # tip sits on the ground
bpy.context.view_layer.update()

bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format="GLB", export_apply=True, export_yup=True)
print("GLB", OUT_GLB)

# ---------------------------------------------------------------- previews
if PREVIEW:
    world = bpy.data.worlds.new("W"); scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.05, 0.035, 0.03, 1); bg.inputs["Strength"].default_value = 0.6
    def light(name, loc, energy, size, color=(1, 1, 1)):
        ld = bpy.data.lights.new(name, "AREA"); ld.energy = energy; ld.size = size; ld.color = color
        lo = bpy.data.objects.new(name, ld); col.objects.link(lo); lo.location = loc
        d = Vector((0, 0, HEIGHT_M/2)) - Vector(loc)
        lo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    light("Key",  (-0.6, -1.0, 0.9), 38, 0.6, (1.0, 0.92, 0.82))
    light("Fill", (0.8, -0.8, 0.3), 18, 1.0, (0.8, 0.88, 1.0))
    light("Rim",  (0.3, 0.8, 0.9), 30, 0.5)
    cam_d = bpy.data.cameras.new("Cam"); cam_d.lens = 85
    cam = bpy.data.objects.new("Cam", cam_d); col.objects.link(cam); scene.camera = cam
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "CYCLES"):
        try:
            scene.render.engine = eng; break
        except TypeError:
            pass
    scene.render.resolution_x = scene.render.resolution_y = 1024
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    target = Vector((0, 0, HEIGHT_M/2))
    for tag, pos in (("front", (0, -2.1, HEIGHT_M/2)), ("three_quarter", (1.25, -1.6, 0.75))):
        cam.location = pos
        cam.rotation_euler = (target - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = "%s_%s.png" % (PREVIEW, tag)
        bpy.ops.render.render(write_still=True)
        print("PNG", scene.render.filepath)
