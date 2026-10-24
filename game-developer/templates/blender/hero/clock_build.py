# Louis XV bracket clock (cartel on its console): red lacquer case painted with flowers, gilt bronze rococo mounts,
# white enamel dial with roman hours and arabic minutes, pierced gilt hands, pendulum window, gilt finial.
# blender -b -P Tools/clock_build.py -- <out.glb> <preview_prefix>      (hero_kit from the game-developer skill)
import os, sys, math, random
KIT = os.environ.get("HERO_KIT_DIR") or os.path.expanduser("~/.claude/skills/game-developer/scripts/blender")
sys.path.insert(0, KIT)
import numpy as np
import hero_kit as hk
from mathutils import Vector, Matrix

OUT, PREVIEW = hk.args()
TEX_DIR = os.path.join(os.path.dirname(os.path.abspath(OUT)), "textures")
FONT = "C:/Windows/Fonts/timesbd.ttf"
hk.reset()
rnd = random.Random(11)

# ------------------------------------------------------------------ painted lacquer texture (vernis Martin style)
def lacquer_texture(size=1024, seed=3):
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) / size
    base = np.array([0.70, 0.16, 0.08], np.float32)
    var = (np.sin(xx * 9.1 + yy * 3.7) * 0.5 + np.sin(xx * 23.0 - yy * 17.0) * 0.25) * 0.035
    img = np.empty((size, size, 3), np.float32)
    img[:] = base
    img += var[..., None] * np.array([1.0, 0.4, 0.3])
    def stamp(cx, cy, rad, col, alpha=1.0):
        x0, x1 = int(max(cx - rad - 2, 0)), int(min(cx + rad + 3, size))
        y0, y1 = int(max(cy - rad - 2, 0)), int(min(cy + rad + 3, size))
        if x0 >= x1 or y0 >= y1:
            return
        gy, gx = np.mgrid[y0:y1, x0:x1]
        d = np.sqrt((gx - cx) ** 2 + (gy - cy) ** 2)
        a = np.clip(rad + 0.5 - d, 0, 1)[..., None] * alpha
        img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - a) + np.array(col, np.float32) * a
    def ellipse(cx, cy, a_len, b_len, ang, col):
        steps = int(a_len * 1.5) + 2
        for k in range(steps):
            t = -1 + 2 * k / (steps - 1)
            w = b_len * math.sqrt(max(0.0, 1 - t * t))
            stamp(cx + math.cos(ang) * a_len * t, cy + math.sin(ang) * a_len * t, w, col)
    def blossom(x, y, rad, ang):
        petal = (0.93, 0.82, 0.76) if r.random() < 0.55 else (0.86, 0.50, 0.50)
        for p in range(5):
            pa = ang + p * 2 * math.pi / 5
            stamp((x + math.cos(pa) * rad) % size, (y + math.sin(pa) * rad) % size, rad * 0.85, petal)
        stamp(x % size, y % size, rad * 0.45, (0.92, 0.74, 0.28))
    for sprig in range(16):
        x, y = r.uniform(0, size), r.uniform(0, size)
        ang = r.uniform(0, 2 * math.pi)
        for step in range(int(r.uniform(40, 80))):
            ang += r.normal(0, 0.12)
            x += math.cos(ang) * 4.0; y += math.sin(ang) * 4.0
            stamp(x % size, y % size, 2.4, (0.20, 0.12, 0.06), 0.95)
            if step % 6 == 3:
                side = 1 if (step // 6) % 2 else -1
                la = ang + side * 0.8
                ellipse((x + math.cos(la) * 14) % size, (y + math.sin(la) * 14) % size, 13, 5, la, (0.18, 0.27, 0.13))
            if step % 19 == 18:
                blossom(x, y, 7, ang)
        blossom(x, y, 11, ang)
    return img

lac_img = hk.image_from_rgb("LacquerPaint", lacquer_texture(), os.path.join(TEX_DIR, "lacquer_paint.png"))

M_LAC    = hk.material("RedLacquer", (0.92, 0.9, 0.9), 0.0, 0.4, coat=0.1, image=lac_img)
M_GOLD   = hk.material("Ormolu", (0.80, 0.56, 0.24), 1.0, 0.28)
M_GOLD2  = hk.material("OrmoluHands", (0.86, 0.62, 0.28), 1.0, 0.22)
M_ENAMEL = hk.material("Enamel", (0.86, 0.85, 0.81), 0.0, 0.12, coat=1.0)
M_INK    = hk.material("Numerals", (0.012, 0.012, 0.014), 0.0, 0.35)
M_EBONY  = hk.material("BlackLacquer", (0.012, 0.010, 0.010), 0.0, 0.18, coat=0.8)
M_INNER  = hk.material("Interior", (0.16, 0.025, 0.015), 0.0, 0.4)

# ------------------------------------------------------------------ case (violin / bombé silhouette)
Y0 = -0.01                        # centre line of the case in depth; the back sits against the wall at y ~ +0.08
CASE = [  # z, half width, half depth
    (0.285, 0.232, 0.100), (0.300, 0.238, 0.100), (0.335, 0.218, 0.097), (0.39, 0.182, 0.093),
    (0.46, 0.160, 0.088), (0.535, 0.170, 0.087), (0.615, 0.198, 0.087), (0.70, 0.212, 0.088),
    (0.78, 0.201, 0.085), (0.835, 0.180, 0.080), (0.88, 0.152, 0.075), (0.92, 0.120, 0.070), (0.952, 0.096, 0.064)]
N_CASE = 3.2
def case_wd(z):
    return hk.smooth_profile(CASE, z)
def front_y(z, xfrac=0.0):
    w, d = case_wd(z)
    return Y0 - d * max(0.0, 1 - abs(xfrac) ** N_CASE) ** (1 / N_CASE)

rings = []
NZ = 120
for i in range(NZ + 1):
    z = CASE[0][0] + (CASE[-1][0] - CASE[0][0]) * i / NZ
    w, d = case_wd(z)
    rings.append(hk.superellipse(w, d, N_CASE, segs=72, cy=Y0, z=z))
case = hk.loft("Case", rings, M_LAC, uv_scale=0.8)

# top cap and plinth
hk.slab("CapPlate", [hk.rounded_rect(0.215, 0.14, 0.03)], 0.95, 0.968, M_GOLD, bevel=0.005,
        matrix=Matrix.Translation((0, Y0, 0)))
hk.slab("Plinth", [hk.rounded_rect(0.50, 0.215, 0.05)], 0.285, 0.30, M_GOLD, bevel=0.006,
        matrix=Matrix.Translation((0, Y0, 0)))

# gilt rocaille ribbons along both front edges: a double moulding, leaves climbing it, C-scrolls, ears standing out
def edge_frame(side, z, out=0.0, yaw=35):
    w, d = case_wd(z)
    return hk.frame((side * (0.93 * w + out), front_y(z, 0.93) - 0.004, z), yaw=side * yaw)
for side in (-1, 1):
    for xf, rad in ((0.95, 0.010), (0.875, 0.005)):
        pts = []
        for i in range(90):
            z = 0.30 + (0.948 - 0.30) * i / 89
            w, d = case_wd(z)
            pts.append(Vector((side * xf * w, front_y(z, xf) - 0.003, z)))
        hk.tube("EdgeMould", pts, rad, M_GOLD)
    z, k = 0.32, 0
    while z < 0.93:
        k += 1
        tilt = rnd.uniform(-12, 18) * (1 if k % 2 else -1)
        hk.leaf("EdgeLeaf", rnd.uniform(0.04, 0.055), 0.013, M_GOLD, curl=rnd.uniform(0.8, 1.6), lobes=3, cup=0.3,
                matrix=edge_frame(side, z, 0.0, yaw=20) @ hk.local(angle=90 + tilt))
        if k % 3 == 0:
            hk.scroll("EdgeScroll", 0.09, 0.0055, M_GOLD, "C", matrix=edge_frame(side, z, 0.006) @ hk.local(angle=90, mirror=side < 0))
        z += rnd.uniform(0.045, 0.06)
    for zz, size, ang in ((0.80, 0.11, 70), (0.62, 0.08, 95), (0.335, 0.13, 20)):
        F = edge_frame(side, zz, 0.012, yaw=60)
        hk.scroll("Ear", size, 0.009, M_GOLD, "S", matrix=F @ hk.local(angle=ang if side > 0 else 180 - ang))
        hk.cluster("EarLeaves%d" % int(zz * 100), F, size * 0.9, M_GOLD, "corner", int(zz * 100) + side, 0.8,
                   spread=(-40, 80) if side > 0 else (100, 220))

# ------------------------------------------------------------------ dial
DZ, DR = 0.705, 0.146
DY = front_y(DZ) - 0.010
dome = lambda rn, a: 0.006 * (1 - rn * rn)
F_DIAL = hk.frame((0, DY, DZ))
hk.polar_disk("Dial", DR, M_ENAMEL, height=dome, rings=18, segs=128, matrix=F_DIAL)
# drum behind the dial and the bezels
hk.slab("Drum", [hk.circle(DR + 0.008, 96)], -0.03, 0.0, M_GOLD, bevel=0.0, matrix=F_DIAL)
hk.ring_tube("Bezel", DR + 0.006, 0.0085, M_GOLD, matrix=F_DIAL @ Matrix.Translation((0, 0, 0.002)))
hk.ring_tube("BezelRope", DR + 0.017, 0.004, M_GOLD, matrix=F_DIAL @ Matrix.Translation((0, 0, -0.002)))

def on_dial(r, theta_deg, lift=0.0007):
    """Frame on the dial surface at radius r, clockwise angle theta from XII, text up = outward."""
    t = math.radians(theta_deg)
    x, y = math.sin(t) * r, math.cos(t) * r
    return F_DIAL @ Matrix.Translation((x, y, dome(r / DR, 0) + lift)) @ Matrix.Rotation(-t, 4, "Z")

ROMAN = ["XII", "I", "II", "III", "IIII", "V", "VI", "VII", "VIII", "IX", "X", "XI"]
for h, s in enumerate(ROMAN):
    hk.text("Hour_" + s, s, 0.044, M_INK, font=FONT, matrix=on_dial(0.093, h * 30))
for m in range(5, 61, 5):
    hk.text("Min_%d" % m, str(m), 0.019, M_INK, font=FONT, matrix=on_dial(0.1345, m * 6))
# minute track: two circles and the 60 ticks
for rr in (0.1185, 0.1245):
    hk.ring_tube("Track", rr, 0.0006, M_INK, n=160, matrix=F_DIAL @ Matrix.Translation((0, 0, dome(rr / DR, 0) + 0.0003)))
for k in range(60):
    hk.slab("Tick", [hk.rounded_rect(0.0012, 0.006, 0.0004, 1)], 0.0, 0.0006, M_INK, matrix=on_dial(0.1215, k * 6, 0.0002))
# winding holes and centre boss
for ang in (128, 232):
    t = math.radians(ang)
    hk.ring_tube("Winding", 0.0075, 0.0018, M_GOLD, n=32,
                 matrix=F_DIAL @ Matrix.Translation((math.sin(t) * 0.055, math.cos(t) * 0.055, dome(0.055 / DR, 0) + 0.001)))
    hk.slab("WindingHole", [hk.circle(0.0062, 32, math.sin(t) * 0.055, math.cos(t) * 0.055)], 0.0, 0.0008, M_INK,
            matrix=F_DIAL @ Matrix.Translation((0, 0, dome(0.055 / DR, 0))))

# pierced gilt hands
def hand(name, length, width, loop_at, theta, z):
    F = F_DIAL @ Matrix.Translation((0, 0, 0.006 + z)) @ Matrix.Rotation(-math.radians(theta), 4, "Z")
    blade = [hk.Vector((0, length)), hk.Vector((-width * 0.35, length * 0.75)), hk.Vector((-width * 0.25, loop_at + width)),
             hk.Vector((-width * 0.6, 0.0)), hk.Vector((-width * 0.35, -length * 0.18)), hk.Vector((width * 0.35, -length * 0.18)),
             hk.Vector((width * 0.6, 0.0)), hk.Vector((width * 0.25, loop_at + width)), hk.Vector((width * 0.35, length * 0.75))]
    blade = blade[:1] + blade[1:][::-1]   # counter-clockwise
    hk.slab(name, [blade], 0.0, 0.0022, M_GOLD2, bevel=0.0006, matrix=F)
    hk.ring_tube(name + "Loop", width * 0.9, 0.0016, M_GOLD2, n=32, matrix=F @ Matrix.Translation((0, loop_at, 0.0012)))
    for side in (-1, 1):
        hk.scroll(name + "Curl", width * 2.4, 0.0012, M_GOLD2, "C",
                  matrix=F @ Matrix.Translation((side * width * 1.1, loop_at - width * 1.8, 0.0012)) @ Matrix.Rotation(math.radians(90 * side), 4, "Z"))
hand("HourHand", 0.075, 0.016, 0.04, 213, 0.000)
hand("MinuteHand", 0.122, 0.011, 0.075, 336, 0.003)
hk.polar_disk("Boss", 0.008, M_GOLD2, height=lambda rn, a: 0.004 * (1 - rn * rn) + 0.009, rings=4, segs=24, matrix=F_DIAL)

# ------------------------------------------------------------------ pendulum window
WZ0, WZ1, WW = 0.415, 0.565, 0.085
win = []
for i in range(25):
    a = math.pi * i / 24
    win.append(hk.Vector((WW * math.cos(a), (WZ1 - WW * 0.6) + WW * 0.6 * math.sin(a))))
win += [hk.Vector((-WW, WZ0 + 0.02)), hk.Vector((-WW * 0.6, WZ0)), hk.Vector((WW * 0.6, WZ0)), hk.Vector((WW, WZ0 + 0.02))]
F_WIN = hk.frame((0, front_y(0.49) - 0.003, 0))
hk.slab("Window", [win], 0.0, 0.002, M_INNER, matrix=F_WIN)
hk.tube("WindowFrame", [F_WIN @ hk.Vector((p.x, p.y, 0.002)) for p in win + win[:1]], 0.005, M_GOLD)
hk.polar_disk("Bob", 0.034, M_GOLD, height=lambda rn, a: 0.012 * (1 - rn * rn) ** 0.5, rings=8, segs=48,
              matrix=hk.frame((0.0, front_y(0.49) - 0.006, 0.47)))
hk.tube("Rod", [hk.Vector((0, front_y(0.53) - 0.005, 0.56)), hk.Vector((0, front_y(0.49) - 0.005, 0.47))], 0.003, M_GOLD)

# ------------------------------------------------------------------ ormolu mounts on the case
def place(name, x, z, size, style, seed, yaw=0, roll=0, density=1.0, spread=(-30, 210), xfrac=None):
    w, d = case_wd(z)
    xf = (x / w) if xfrac is None else xfrac
    F = hk.frame((x, front_y(z, min(abs(xf), 0.97)) - 0.004, z), yaw=yaw, roll=roll)
    hk.cluster(name, F, size, M_GOLD, style, seed, density, spread)

place("Crest", 0.0, 0.872, 0.15, "cartouche", 5)
for s in (-1, 1):
    place("DialSide", s * 0.165, 0.64, 0.10, "corner", 41 + s, yaw=s * 30, roll=s * 15, density=0.8,
          spread=(-70, 40) if s > 0 else (140, 250))
    place("Foot", s * 0.20, 0.33, 0.13, "corner", 51 + s, yaw=s * 40, roll=s * 25, density=1.3,
          spread=(-60, 60) if s > 0 else (120, 240))
# the big asymmetric rocaille over the pendulum window
F_P = hk.frame((0.0, front_y(0.44) - 0.012, 0.44))
hk.cluster("Pendulum", F_P, 0.19, M_GOLD, "spray", 61, density=1.6, spread=(-25, 205))
hk.cluster("PendShell", hk.frame((0.0, front_y(0.42) - 0.022, 0.42)), 0.16, M_GOLD, "cartouche", 62, 0.8)
place("Apron", 0.0, 0.325, 0.13, "cartouche", 71)
# finial on the cap
hk.cluster("Finial", hk.frame((0.0, Y0, 0.968)), 0.26, M_GOLD, "flame", 81, density=2.0)
hk.cluster("FinialBack", hk.frame((0.0, Y0 + 0.02, 0.968), yaw=180), 0.2, M_GOLD, "flame", 82, density=1.2)

# ------------------------------------------------------------------ console (bracket)
SHELF_Z0, SHELF_Z1 = 0.248, 0.285
hk.slab("Shelf", [hk.rounded_rect(0.58, 0.25, 0.03)], SHELF_Z0, SHELF_Z1, M_GOLD, bevel=0.008,
        matrix=Matrix.Translation((0, -0.045, 0)))
hk.tube("ShelfRim", [Vector((p.x, p.y - 0.045, SHELF_Z1)) for p in hk.offset(hk.rounded_rect(0.58, 0.25, 0.03), 0.008)][:] +
        [Vector((hk.offset(hk.rounded_rect(0.58, 0.25, 0.03), 0.008)[0].x, hk.offset(hk.rounded_rect(0.58, 0.25, 0.03), 0.008)[0].y - 0.045, SHELF_Z1))],
        0.007, M_GOLD)
hk.slab("ShelfTop", [hk.offset(hk.rounded_rect(0.58, 0.25, 0.03), 0.018)], SHELF_Z1 - 0.004, SHELF_Z1 + 0.0015, M_EBONY,
        matrix=Matrix.Translation((0, -0.045, 0)))
BRACKET = [  # z, half width, half depth
    (0.055, 0.045, 0.040), (0.08, 0.06, 0.05), (0.11, 0.085, 0.065), (0.15, 0.13, 0.085),
    (0.19, 0.19, 0.10), (0.225, 0.235, 0.11), (0.248, 0.255, 0.115)]
WALL_Y = 0.075
brings = []
for i in range(41):
    z = BRACKET[0][0] + (BRACKET[-1][0] - BRACKET[0][0]) * i / 40
    w, d = hk.smooth_profile(BRACKET, z)
    brings.append(hk.superellipse(w, d, 2.8, segs=64, cy=WALL_Y - d, z=z))
hk.loft("Bracket", brings, M_LAC, uv_scale=0.8)
def bfront(z):
    w, d = hk.smooth_profile(BRACKET, z)
    return WALL_Y - 2 * d
hk.tube("BracketMould", [hk.Vector((math.sin(a) * 0.29, -0.045 - math.cos(a) * 0.125 - 0.004, SHELF_Z0 + 0.012))
                         for a in [math.radians(-90 + 180 * i / 40) for i in range(41)]], 0.009, M_GOLD)
hk.cluster("BracketCartouche", hk.frame((0.0, bfront(0.175) - 0.004, 0.175)), 0.16, M_GOLD, "cartouche", 91)
for side in (-1, 1):
    pts = []
    for i in range(40):
        z = 0.06 + (0.228 - 0.06) * i / 39
        w, d = hk.smooth_profile(BRACKET, z)
        pts.append(Vector((side * 0.9 * w, WALL_Y - d - d * (1 - 0.9 ** 2.8) ** (1 / 2.8) - 0.003, z)))
    hk.tube("BracketEdge", pts, 0.009, M_GOLD)
for s in (-1, 1):
    hk.cluster("BracketCorner", hk.frame((s * 0.2, WALL_Y - 2 * hk.smooth_profile(BRACKET, 0.215)[1] * 0.75, 0.215),
               yaw=s * 50, roll=s * 30), 0.10, M_GOLD, "corner", 95 + s, 1.0)
hk.cluster("Pendant", hk.frame((0.0, bfront(0.06) + 0.01, 0.07), roll=180), 0.11, M_GOLD, "flame", 99, density=1.0)
hk.cluster("PendantLeaves", hk.frame((0.0, bfront(0.10) - 0.004, 0.10)), 0.08, M_GOLD, "spray", 98, 0.7, spread=(200, 340))

# ------------------------------------------------------------------ finish
hk.join_by_material("Clock")
hk.stats()
hk.export_glb(OUT)
if PREVIEW:
    hk.preview(PREVIEW, (0, 0, 0.6), 2.4, views=(("front", 0, 4), ("three_quarter", 38, 12), ("detail", 12, 4)), lens=60)
