#!/usr/bin/env python3
"""nc_world: seeded worlds for Nucleon from art/world/<name>.json (GameDeveloperSkill, references/nucleon-loop.md §4b).

Standard library only, deterministic (same JSON + seed = same world). Python does the generation; the engine only writes:
  python nc_world.py build art/world/<name>.json --project PROJECT [--catalog art/kit-catalog.json]
    terrain | island  -> Tools/gds_world_<name>.lua (+ Content/Textures/GDS/*.png layer colours)
                         run it headless: ncli exe run-lua Tools/gds_world_<name>.lua PROJECT  -> Content/Landscape/<name>.land
                         then: nc_world.py attach PROJECT --name <name>   (adds the terrain to the level; editor CLOSED)
                         and art/blueprints/_world_<name>.json (scatter of kit models at the real height, landmarks,
                         player start) for `ncli build`
    dungeon | cave    -> art/blueprints/_world_<name>.json (floors + walls on a grid: kit pieces when the catalog has
                         floor/wall roles, boxes otherwise; room props; torches; player start) for `ncli build`
    village           -> art/blueprints/_world_<name>.json (plaza, roads, lots, houses from the kit facing the road,
                         fences, lamps, trees outside lots and roads, player start) for `ncli build`
  look PROJECT art/look/<name>.json -> the level's lighting / sky / fog / sun (editor closed)
  every mode also writes art/world/<name>.layout.json (spawn, goal, rooms/lots/flats, landmark) for the systems workers.

`reference` (optional, filled by the worker from art/reference/BOARD.md: numbers measured on the reference images)
overrides the defaults of each mode, so the world looks like the references instead of like a generator:
  terrain: relief (0 flat .. 1 alpine), coast (0 smooth .. 1 jagged), treeline (0..1 of height), density (0..1)
  dungeon: roomMin/roomMax (cells), corridor (cells), rooms, loops (0..1 extra links), height (m)
  village: plazaRadius, streetWidth, lotWidth, lotDepth, setback, houseSpacing, roads (1..6), organic (0 grid .. 1 bent),
           fences (0..1 of lots), lampEvery (m), treeDensity (0..1)
Coordinates: display space, Z up, meters (x east, y north). The landscape is centred on the origin.
"""
import argparse
import json
import math
import os
import random
import re
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nc_gds  # noqa: E402


# ------------------------------------------------------------------------------------------------ noise
class Noise:
    """Seeded 2D gradient noise (Perlin style) + fBm, ridged and domain warp."""

    def __init__(self, seed):
        rng = random.Random(seed)
        p = list(range(256))
        rng.shuffle(p)
        self.p = p + p
        self.g = [(math.cos(a), math.sin(a)) for a in (rng.uniform(0, 2 * math.pi) for _ in range(256))]

    def noise(self, x, y):
        xi, yi = math.floor(x), math.floor(y)
        xf, yf = x - xi, y - yi
        xi &= 255
        yi &= 255
        p, g = self.p, self.g

        def dot(ix, iy, dx, dy):
            gx, gy = g[p[p[ix] + iy] & 255]
            return gx * dx + gy * dy
        u = xf * xf * xf * (xf * (xf * 6 - 15) + 10)
        v = yf * yf * yf * (yf * (yf * 6 - 15) + 10)
        n00 = dot(xi, yi, xf, yf)
        n10 = dot(xi + 1, yi, xf - 1, yf)
        n01 = dot(xi, yi + 1, xf, yf - 1)
        n11 = dot(xi + 1, yi + 1, xf - 1, yf - 1)
        a = n00 + u * (n10 - n00)
        b = n01 + u * (n11 - n01)
        return (a + v * (b - a)) * 1.4142

    def fbm(self, x, y, octaves=5, lac=2.0, gain=0.5):
        s, amp, freq, norm = 0.0, 1.0, 1.0, 0.0
        for _ in range(octaves):
            s += amp * self.noise(x * freq, y * freq)
            norm += amp
            amp *= gain
            freq *= lac
        return s / norm

    def ridged(self, x, y, octaves=4):
        s, amp, freq, norm = 0.0, 1.0, 1.0, 0.0
        for _ in range(octaves):
            n = 1 - abs(self.noise(x * freq + 13.7, y * freq - 7.3))
            s += amp * n * n
            norm += amp
            amp *= 0.5
            freq *= 2.0
        return s / norm


def smooth(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0) if b != a else (1.0 if x >= a else 0.0)
    return t * t * (3 - 2 * t)


def hex_rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def write_png(path, rgb, size=8):
    """A solid colour PNG (layer albedo for a stylized landscape)."""
    r, g, b = [max(0, min(255, int(round(c * 255)))) for c in rgb]
    raw = b"".join(b"\x00" + bytes([r, g, b]) * size for _ in range(size))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)) + \
        chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").write(data)


# ------------------------------------------------------------------------------------------------ terrain / island
def terrain_field(w):
    """The height field of a terrain/island world: normalized H[iy][ix] (display axes) + samplers."""
    t = dict(w.get("terrain", {}))
    ref = w.get("reference", {})
    island = w["mode"] == "island"
    size = float(t.get("size", 256))
    res = int(t.get("resolution", 257))
    cell = size / (res - 1)
    height = float(t.get("height", 30))
    relief = float(ref.get("relief", t.get("mountains", 0.4)))
    coast = float(ref.get("coast", 0.5))
    scale = float(t.get("scale", 3.0 / size))
    warp = float(t.get("warp", 1.0 + coast))
    sea = float(t.get("seaLevel", 0.14 if island else 0.0))
    flats = t.get("flat", [])
    nz = Noise(w.get("seed", 1))
    half = (res - 1) / 2
    def raw(X, Y):
        wx = X * scale + warp * nz.fbm(X * scale * 0.5 + 31.1, Y * scale * 0.5 - 17.3, 3)
        wy = Y * scale + warp * nz.fbm(X * scale * 0.5 - 9.2, Y * scale * 0.5 + 44.4, 3)
        base = 0.5 + 0.5 * nz.fbm(wx, wy, int(t.get("octaves", 5)))
        mtn = nz.ridged(wx * 0.7, wy * 0.7)
        h = base * (1 - relief) + mtn * relief * (0.4 + 0.6 * base)
        if island:
            r = math.hypot(X, Y) / (size / 2)
            fall = float(t.get("islandFalloff", 0.55))
            h = h * (1 - smooth(fall, 1.0, r)) - 0.15 * smooth(fall, 1.0, r)
        return h
    targets = [raw(f["x"], f["y"]) for f in flats]   # a flat spot keeps the height of its centre
    H = [[0.0] * res for _ in range(res)]   # H[iy][ix], normalized 0..1, display coords
    for iy in range(res):
        for ix in range(res):
            X, Y = (ix - half) * cell, (iy - half) * cell
            h = raw(X, Y)
            for f, target in zip(flats, targets):   # villages, arenas, the spawn
                d = math.hypot(X - f["x"], Y - f["y"])
                k = 1 - smooth(f["r"] * 0.75, f["r"] * 1.25, d)
                if k > 0:
                    h = h + (target - h) * k
            H[iy][ix] = h
    lo = min(min(r) for r in H)
    hi = max(max(r) for r in H)
    for iy in range(res):
        for ix in range(res):
            H[iy][ix] = (H[iy][ix] - lo) / (hi - lo or 1)
    sea_n = sea

    def hgt(X, Y):   # metres, bilinear
        fx, fy = X / cell + half, Y / cell + half
        ix, iy = int(math.floor(fx)), int(math.floor(fy))
        if ix < 0 or iy < 0 or ix >= res - 1 or iy >= res - 1:
            return None
        ax, ay = fx - ix, fy - iy
        a = H[iy][ix] + (H[iy][ix + 1] - H[iy][ix]) * ax
        b = H[iy + 1][ix] + (H[iy + 1][ix + 1] - H[iy + 1][ix]) * ax
        return (a + (b - a) * ay) * height - sea_n * height

    def slope(ix, iy):
        x0, x1 = max(ix - 1, 0), min(ix + 1, res - 1)
        y0, y1 = max(iy - 1, 0), min(iy + 1, res - 1)
        dx = (H[iy][x1] - H[iy][x0]) * height / ((x1 - x0) * cell)
        dy = (H[y1][ix] - H[y0][ix]) * height / ((y1 - y0) * cell)
        return math.degrees(math.atan(math.hypot(dx, dy)))

    return dict(H=H, res=res, cell=cell, half=half, height=height, sea=sea_n, size=size, flats=flats, t=t, ref=ref,
                island=island, hgt=hgt, slope=slope)


def terrain_world(w, project, catalog):
    f_ = terrain_field(w)
    H, res, cell, half, height, sea_n, size, flats, t, ref, island = (f_[k] for k in
        ("H", "res", "cell", "half", "height", "sea", "size", "flats", "t", "ref", "island"))
    hgt, slope = f_["hgt"], f_["slope"]
    layers = w.get("layers") or ([{"name": "grass", "color": "#6B8E4E"},
                                  {"name": "sand", "color": "#D6C38E", "maxHeight": sea_n + 0.04},
                                  {"name": "rock", "color": "#7D7872", "minSlope": 30}] +
                                 # snow only on real mountains: a 15 m hill with a white top reads as a mistake
                                 ([{"name": "snow", "color": "#EEF1F4", "minHeight": 0.85}] if height >= 40 else []))
    name = w["name"]
    tex_dir = "Content/Textures/GDS"
    for L in layers:
        write_png(os.path.join(project, tex_dir, "%s_%s.png" % (name, L["name"])), hex_rgb(L.get("color", "#808080")))
    # weights of layers 1.. (layer 0 is the base)
    weights = [[] for _ in layers[1:]]
    for iy in range(res):
        for ix in range(res):
            h, s = H[iy][ix], slope(ix, iy)
            for k, L in enumerate(layers[1:]):
                wgt = 1.0
                if "maxHeight" in L:
                    wgt *= 1 - smooth(L["maxHeight"] - 0.02, L["maxHeight"] + 0.02, h)
                if "minHeight" in L:
                    wgt *= smooth(L["minHeight"] - 0.03, L["minHeight"] + 0.03, h)
                if "minSlope" in L:
                    wgt *= smooth(L["minSlope"] - 4, L["minSlope"] + 4, s)
                if "maxSlope" in L:
                    wgt *= 1 - smooth(L["maxSlope"] - 4, L["maxSlope"] + 4, s)
                weights[k].append(int(wgt * 255))
    # the Lua writer: engine vertex (ix, iz) is display X = -(ix - half) * cell, Y = (iz - half) * cell
    land_path = "Content/Landscape/%s.land" % name
    lua = ["-- generated by GameDeveloperSkill nc_world.py from art/world/%s.json (seed %s): do not edit, regenerate" % (name, w.get("seed", 1)),
           "-- run: NucleonEditor -run-lua Tools/gds_world_%s.lua <project>   (ncli exe run-lua)" % name,
           "hideConsole()", "local RES, CELL, HEIGHT, SEA = %d, %r, %r, %r" % (res, cell, height, sea_n),
           "local H = {"]
    for iz in range(res):   # engine iz <-> display iy; engine ix <-> display mirrored ix
        row = [H[iz][res - 1 - ix] for ix in range(res)]
        lua.append("{" + ",".join("%.4f" % v for v in row) + "},")
    lua.append("}")
    for k, wl in enumerate(weights):
        lua.append("local W%d = {" % (k + 1))
        for iz in range(res):
            row = [wl[iz * res + (res - 1 - ix)] for ix in range(res)]
            lua.append("{" + ",".join(str(v) for v in row) + "},")
        lua.append("}")
    lua += ["local land = LandscapeNew(RES, CELL)",
            "for iz = 0, RES - 1 do local r = H[iz + 1] for ix = 0, RES - 1 do land:setHeightAt(ix, iz, (r[ix + 1] - SEA) * HEIGHT) end end",
            'land:setLayer(0, "%s/%s_%s.png", %r)' % (tex_dir, name, layers[0]["name"], float(layers[0].get("tiling", 8)))]
    for k, L in enumerate(layers[1:]):
        lua.append('land:addLayer("%s/%s_%s.png", %r)' % (tex_dir, name, L["name"], float(L.get("tiling", 8))))
        lua.append("for iz = 0, RES - 1 do local r = W%d[iz + 1] for ix = 0, RES - 1 do land:setWeightAt(%d, ix, iz, r[ix + 1]) end end" % (k + 1, k + 1))
    fol = w.get("foliage", [{"name": "Grass", "kind": "cross", "width": 0.8, "height": 0.6, "density": 2.5 * float(ref.get("density", 0.6)),
                             "color": [0.5, 0.75, 0.38], "heightMin": (sea_n + 0.03) * height - sea_n * height, "slopeMax": 30,
                             "cullDistance": 60, "windStrength": 0.25}])
    if fol:
        lua.append("local types = {}")
        for k, F in enumerate(fol):
            fields = ", ".join("%s = %s" % (key, json.dumps(v).replace("[", "{").replace("]", "}")) for key, v in F.items())
            lua.append("types[%d] = land:addFoliageType{%s}" % (k + 1, fields))
        step = max(8, int(size / 16))
        lua.append("for gz = %d, %d, %d do for gx = %d, %d, %d do for k = 1, #types do land:paintFoliage(types[k], gx, gz, %d, 1, 0.3, %d + gx * 3 + gz * 17 + k) end end end"
                   % (-int(size / 2), int(size / 2), step, -int(size / 2), int(size / 2), step, step, int(w.get("seed", 1)) * 1000))
        for f in flats:   # clearings: no grass on villages / arenas
            lua.append("for k = 1, #types do land:eraseFoliage(%r, %r, %r, types[k]) end" % (-f["x"], f["y"], f["r"]))
    lua += ['local ok, err = land:save("%s")' % land_path, "assert(ok, tostring(err))",
            'print("GDS-WORLD land %s res " .. RES .. " size %g")' % (land_path, size), "exit()"]
    os.makedirs(os.path.join(project, "Content", "Landscape"), exist_ok=True)   # land:save does not create folders
    script = os.path.join(project, "Tools", "gds_world_%s.lua" % name)
    os.makedirs(os.path.dirname(script), exist_ok=True)
    open(script, "w", encoding="utf-8").write("\n".join(lua) + "\n")
    # kit scatter at the real height (models are entities; procedural grass is foliage above)
    rng = random.Random(int(w.get("seed", 1)) * 7 + 1)
    pieces, placed = [], []
    for si, sc in enumerate(w.get("scatter", [])):
        assets = sc.get("assets") or ([sc["asset"]] if "asset" in sc else
                                      [it["asset"] for it in (catalog or {}).get("items", []) if it["role"] == sc.get("role")])
        if not assets:
            continue
        count = int(sc.get("count", 50) * float(ref.get("density", 1.0) if "density" in ref else 1.0))
        min_d = float(sc.get("minDist", 4))
        tries = 0
        cl_centres = [(rng.uniform(-size / 2, size / 2), rng.uniform(-size / 2, size / 2)) for _ in range(max(1, count // 12))]
        while count > 0 and tries < count * 80:
            tries += 1
            if rng.random() < float(sc.get("clusters", 0.3)):
                cx, cy = cl_centres[rng.randrange(len(cl_centres))]
                X, Y = cx + rng.gauss(0, min_d * 3), cy + rng.gauss(0, min_d * 3)
            else:
                X, Y = rng.uniform(-size / 2 * 0.96, size / 2 * 0.96), rng.uniform(-size / 2 * 0.96, size / 2 * 0.96)
            z = hgt(X, Y)
            if z is None:
                continue
            hn = (z + sea_n * height) / height
            ix, iy = int(X / cell + half), int(Y / cell + half)
            if not (sc.get("minHeight", sea_n + 0.03) <= hn <= sc.get("maxHeight", float(ref.get("treeline", 0.8)))):
                continue
            if slope(ix, iy) > sc.get("maxSlope", 28):
                continue
            if any(math.hypot(X - f["x"], Y - f["y"]) < f["r"] for f in flats):
                continue
            if any((X - px) ** 2 + (Y - py) ** 2 < min_d * min_d for px, py in placed):
                continue
            placed.append((X, Y))
            a = assets[rng.randrange(len(assets))]
            k = rng.uniform(*sc.get("scale", [0.85, 1.25])) * float(w.get("kitScale", 1.0))
            item = (catalog or {}).get("_by_asset", {}).get(a)
            base = item["min"][2] * k if item else 0.0   # the bottom of the model on the ground, whatever its pivot
            pieces.append({"asset": a, "name": "%s_%d" % (sc.get("name", "scatter%d" % si), len(placed)),
                           "position": [round(X, 3), round(Y, 3), round(z - base - float(sc.get("sink", 0.08)), 3)],
                           "rotation": [0, 0, round(rng.uniform(0, 360), 1)], "scale": [round(k, 3)] * 3})
            count -= 1
    spawn_f = next((f for f in flats if f.get("spawn")), flats[0] if flats else None)
    sx, sy = (spawn_f["x"], spawn_f["y"]) if spawn_f else (0.0, 0.0)
    if spawn_f and isinstance(spawn_f.get("spawn"), list):   # "spawn": [dx, dy]: off the centre (a well, a statue there)
        sx, sy = sx + spawn_f["spawn"][0], sy + spawn_f["spawn"][1]
    spec = {"name": "_world_%s" % name, "seed": w.get("seed", 1), "pieces": pieces,
            "playerStart": {"position": [sx, sy, round((hgt(sx, sy) or 0) + 0.3, 3)], "yaw": 0}}   # clear of the landscape triangles
    layout = {"name": name, "mode": w["mode"], "size": size, "height": height, "water": sea_n > 0,
              "seaLevelZ": 0.0, "spawn": spec["playerStart"]["position"],
              "flats": [{"x": f["x"], "y": f["y"], "r": f["r"], "z": round(hgt(f["x"], f["y"]) or 0, 3), **{k: v for k, v in f.items() if k not in ("x", "y", "r", "_h")}} for f in flats],
              "land": land_path, "script": "Tools/gds_world_%s.lua" % name, "scattered": len(pieces)}
    return spec, layout, ["ncli exe run-lua Tools/gds_world_%s.lua PROJECT" % name, "nc_world.py attach PROJECT --name %s" % name,
                          "ncli build art/blueprints/_world_%s.json --save current" % name]


# ------------------------------------------------------------------------------------------------ dungeon / cave
def grid_rooms(w, rng):
    g = dict(w.get("grid", {}))
    ref = w.get("reference", {})
    W, D = int(g.get("width", 24)), int(g.get("depth", 24))
    n = int(ref.get("rooms", g.get("rooms", 8)))
    rmin, rmax = int(ref.get("roomMin", g.get("minRoom", 3))), int(ref.get("roomMax", g.get("maxRoom", 6)))
    cw = int(ref.get("corridor", g.get("corridorWidth", 1)))
    occ = [[0] * W for _ in range(D)]
    rooms = []
    for _ in range(n * 30):
        if len(rooms) >= n:
            break
        rw, rd = rng.randint(rmin, rmax), rng.randint(rmin, rmax)
        x, y = rng.randint(1, W - rw - 1), rng.randint(1, D - rd - 1)
        if any(x - 1 < r[0] + r[2] and r[0] - 1 < x + rw and y - 1 < r[1] + r[3] and r[1] - 1 < y + rd for r in rooms):
            continue
        rooms.append((x, y, rw, rd))
    for x, y, rw, rd in rooms:
        for j in range(y, y + rd):
            for i in range(x, x + rw):
                occ[j][i] = 1
    centres = [(x + rw // 2, y + rd // 2) for x, y, rw, rd in rooms]
    # minimum spanning tree (always connected) + `loops` extra links
    links, inside = [], {0} if centres else set()
    while len(inside) < len(centres):
        best = min(((math.dist(centres[a], centres[b]), a, b) for a in inside for b in range(len(centres)) if b not in inside))
        links.append((best[1], best[2]))
        inside.add(best[2])
    extra = int(round(float(ref.get("loops", 0.15)) * len(centres)))
    for _ in range(extra):
        a, b = rng.randrange(len(centres)), rng.randrange(len(centres))
        if a != b:
            links.append((a, b))

    def carve(i, j):
        for dj in range(cw):
            for di in range(cw):
                if 0 <= j + dj < D and 0 <= i + di < W:
                    occ[j + dj][i + di] = occ[j + dj][i + di] or 2
    for a, b in links:
        (x0, y0), (x1, y1) = centres[a], centres[b]
        if rng.random() < 0.5:
            for i in range(min(x0, x1), max(x0, x1) + 1):
                carve(i, y0)
            for j in range(min(y0, y1), max(y0, y1) + 1):
                carve(x1, j)
        else:
            for j in range(min(y0, y1), max(y0, y1) + 1):
                carve(x0, j)
            for i in range(min(x0, x1), max(x0, x1) + 1):
                carve(i, y1)
    return occ, rooms, centres


def cave_grid(w, rng):
    g = dict(w.get("grid", {}))
    W, D = int(g.get("width", 40)), int(g.get("depth", 40))
    fill = float(g.get("fill", 0.46))
    occ = [[1 if rng.random() > fill else 0 for _ in range(W)] for _ in range(D)]
    for _ in range(int(g.get("smooth", 5))):
        nxt = [[0] * W for _ in range(D)]
        for j in range(D):
            for i in range(W):
                walls = sum(1 for dj in (-1, 0, 1) for di in (-1, 0, 1) if (di or dj) and
                            not (0 <= j + dj < D and 0 <= i + di < W and occ[j + dj][i + di]))
                nxt[j][i] = 0 if walls > 4 else 1 if walls < 4 else occ[j][i]
        occ = nxt
    for j in range(D):   # closed border
        for i in range(W):
            if i in (0, W - 1) or j in (0, D - 1):
                occ[j][i] = 0
    # keep the largest open region
    seen, best = set(), []
    for j in range(D):
        for i in range(W):
            if occ[j][i] and (i, j) not in seen:
                stack, region = [(i, j)], []
                seen.add((i, j))
                while stack:
                    ci, cj = stack.pop()
                    region.append((ci, cj))
                    for ni, nj in ((ci + 1, cj), (ci - 1, cj), (ci, cj + 1), (ci, cj - 1)):
                        if 0 <= ni < W and 0 <= nj < D and occ[nj][ni] and (ni, nj) not in seen:
                            seen.add((ni, nj))
                            stack.append((ni, nj))
                if len(region) > len(best):
                    best = region
    keep = set(best)
    occ = [[1 if (i, j) in keep else 0 for i in range(W)] for j in range(D)]
    return occ, best


def grid_world(w, project, catalog):
    rng = random.Random(w.get("seed", 1))
    g = dict(w.get("grid", {}))
    ref = w.get("reference", {})
    cell = float(g.get("cell", 4))
    hgt = float(ref.get("height", g.get("wallHeight", 4)))
    if w["mode"] == "cave":
        occ, region = cave_grid(w, rng)
        rooms = []
        centres = [region[0], region[len(region) // 2], region[-1]] if region else []
    else:
        occ, rooms, centres = grid_rooms(w, rng)
    D, W = len(occ), len(occ[0])
    has_kit = bool(catalog and any(it["role"] == "floor" for it in catalog["items"]) and any(it["role"] == "wall" for it in catalog["items"]))
    floor_c = hex_rgb(g.get("floorColor", "#4E4945"))
    wall_c = hex_rgb(g.get("wallColor", "#6A635C"))
    shapes, pieces, lights = [], [], []
    fl = nc_gds.pick(catalog, role="floor") if has_kit else None
    wl = nc_gds.pick(catalog, role="wall") if has_kit else None
    if has_kit:
        Lw = max(wl["size"][0], wl["size"][1])
        if abs(Lw - cell) > 0.05:
            cell = Lw   # the kit module decides the cell
        base_yaw = 0 if wl["size"][0] >= wl["size"][1] else -90
    walls = 0
    torch_every = int(g.get("torchEvery", 5))
    for j in range(D):
        for i in range(W):
            if not occ[j][i]:
                continue
            cx, cy = (i + 0.5) * cell, (j + 0.5) * cell
            if has_kit:
                pieces.append({"asset": fl["asset"], "name": "f%d_%d" % (i, j),
                               "position": nc_gds.place_piece(fl, (cx, cy), -fl["size"][2], 0), "rotation": [0, 0, 0]})
            else:
                shapes.append({"name": "f%d_%d" % (i, j), "position": [cx, cy, -0.1],
                               "shape": {"kind": "box", "width": cell, "depth": cell, "height": 0.2, "color": floor_c}})
            for di, dj, ex, ey, face in ((0, -1, cx, cy - cell / 2, 0), (0, 1, cx, cy + cell / 2, 180),
                                         (-1, 0, cx - cell / 2, cy, 90), (1, 0, cx + cell / 2, cy, -90)):
                ni, nj = i + di, j + dj
                if 0 <= ni < W and 0 <= nj < D and occ[nj][ni]:
                    continue
                walls += 1
                if has_kit:
                    yaw = (base_yaw + face) % 360
                    pieces.append({"asset": wl["asset"], "name": "w%d_%d_%d%d" % (i, j, di + 1, dj + 1),
                                   "position": nc_gds.place_piece(wl, (ex, ey), 0, yaw), "rotation": [0, 0, yaw]})
                else:
                    along_x = dj != 0
                    shapes.append({"name": "w%d_%d_%d%d" % (i, j, di + 1, dj + 1), "position": [ex, ey, hgt / 2],
                                   "shape": {"kind": "box", "width": cell if along_x else 0.3, "depth": 0.3 if along_x else cell,
                                             "height": hgt, "color": wall_c}})
                if torch_every and walls % torch_every == 0:
                    nx, ny = (ex - cx), (ey - cy)
                    lights.append({"type": "point", "name": "torch%d" % walls, "position": [ex - nx * 0.15, ey - ny * 0.15, hgt * 0.62],
                                   "color": [1, 0.62, 0.3], "intensity": float(g.get("torchIntensity", 250)), "range": cell * 2.2})
    # props per room (by role or asset), against the room centre
    for pr in g.get("roomProps", []):
        for k, (x, y, rw, rd) in enumerate(rooms):
            for m in range(int(pr.get("perRoom", 1))):
                px, py = (x + rng.uniform(0.6, rw - 0.6)) * cell, (y + rng.uniform(0.6, rd - 0.6)) * cell
                entry = {"position": [round(px, 3), round(py, 3), 0], "rotation": [0, 0, rng.choice([0, 90, 180, 270])],
                         "name": "room%d_%s%d" % (k, pr.get("role", "prop"), m)}
                if "asset" in pr or "file" in pr:
                    entry["asset"] = pr.get("asset", pr.get("file"))
                else:
                    entry["role"] = pr.get("role", "container")
                pieces.append(entry)
    spawn = centres[0] if centres else (W // 2, D // 2)
    goal = max(centres, key=lambda c: math.dist(c, spawn)) if centres else spawn
    sp = [(spawn[0] + 0.5) * cell, (spawn[1] + 0.5) * cell, 0.05]
    spec = {"name": "_world_%s" % w["name"], "seed": w.get("seed", 1), "origin": w.get("origin", [0, 0, 0]),
            "shapes": shapes, "pieces": pieces, "lights": lights, "playerStart": {"position": sp, "yaw": 0}}
    layout = {"name": w["name"], "mode": w["mode"], "cell": cell, "grid": [W, D], "kit": has_kit,
              "spawn": sp, "goal": [(goal[0] + 0.5) * cell, (goal[1] + 0.5) * cell, 0],
              "rooms": [{"x": x * cell, "y": y * cell, "w": rw * cell, "d": rd * cell,
                         "centre": [(x + rw / 2) * cell, (y + rd / 2) * cell]} for x, y, rw, rd in rooms],
              "openCells": sum(map(sum, [[1 if v else 0 for v in r] for r in occ])), "walls": walls}
    return spec, layout, ["ncli build art/blueprints/_world_%s.json --save current" % w["name"]]


# ------------------------------------------------------------------------------------------------ village
def village_world(w, project, catalog):
    v = dict(w.get("village", {}))
    ref = w.get("reference", {})
    rng = random.Random(w.get("seed", 1))
    P = lambda k, d: float(ref.get(k, v.get(k, d)))   # noqa: E731
    plaza, street = P("plazaRadius", 10), P("streetWidth", 4)
    lot_w, lot_d, setback = P("lotWidth", 12), P("lotDepth", 12), P("setback", 2)
    roads = int(P("roads", 4))
    reach = P("radius", 60)
    organic = P("organic", 0.35)
    fence_p, lamp_every, tree_d = P("fences", 0.4), P("lampEvery", 14), P("treeDensity", 0.6)
    road_c = hex_rgb(v.get("roadColor", "#8C7B62"))
    shapes, pieces, lights, lots = [], [], [], []
    shapes.append({"name": "plaza", "position": [0, 0, -0.04],
                   "shape": {"kind": "cylinder", "radius": plaza, "height": 0.1, "segments": 32, "color": road_c}})
    has_kit = bool(catalog and any(it["role"] == "wall" for it in catalog["items"]))
    blds = [it for it in (catalog or {}).get("items", []) if it["role"] in ("building", "house")]
    blds += [{"asset": a} for a in v.get("buildings", [])]
    house_specs = v.get("houseSpecs", [])   # optional room specs (kit rooms) reused for houses
    def seg_dist(px, py, ax, ay, bx, by):
        vx, vy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy or 1)))
        return math.hypot(px - (ax + vx * t), py - (ay + vy * t))

    polylines = []
    for r in range(roads):   # every road first, so no lot of road 1 lands on road 3
        ang = 2 * math.pi * r / roads + rng.uniform(-0.25, 0.25) * organic
        length = reach - plaza
        steps = max(2, int(length / 8))
        pts, a = [], ang
        for k in range(steps + 1):
            d = plaza * 0.9 + (length + plaza * 0.1) * k / steps
            a += rng.uniform(-0.12, 0.12) * organic
            pts.append((d * math.cos(a), d * math.sin(a)))
        polylines.append(pts)
        for k in range(steps):   # road segments: thin boxes along the polyline
            (x0, y0), (x1, y1) = pts[k], pts[k + 1]
            seg = math.hypot(x1 - x0, y1 - y0)
            shapes.append({"name": "road%d_%d" % (r, k), "position": [round((x0 + x1) / 2, 3), round((y0 + y1) / 2, 3), -0.04],
                           "rotation": [0, 0, round(math.degrees(math.atan2(y1 - y0, x1 - x0)), 2)],
                           "shape": {"kind": "box", "width": round(seg + street * 0.5, 3), "depth": street, "height": 0.1, "color": road_c}})
    segments = [(pts[k], pts[k + 1]) for pts in polylines for k in range(len(pts) - 1)]
    rad = max(lot_w, lot_d) / 2 * 0.92

    def free(cx, cy):
        if math.hypot(cx, cy) < plaza + rad:
            return False
        if any(seg_dist(cx, cy, a[0], a[1], b[0], b[1]) < street / 2 + rad * 0.8 for a, b in segments):
            return False
        return all(math.hypot(cx - l["centre"][0], cy - l["centre"][1]) >= 2 * rad for l in lots)

    for r, pts in enumerate(polylines):
        travelled = 0.0   # lamps along the road, on its left
        for k in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[k], pts[k + 1]
            seg = math.hypot(x1 - x0, y1 - y0)
            nx, ny = -(y1 - y0) / seg, (x1 - x0) / seg
            while travelled < seg:
                t = travelled / seg
                lx, ly = x0 + (x1 - x0) * t + nx * (street / 2 + 0.6), y0 + (y1 - y0) * t + ny * (street / 2 + 0.6)
                if catalog and any(it["role"] == "light" for it in catalog["items"]):
                    pieces.append({"role": "light", "name": "lamp%d_%d" % (r, len(lights)), "position": [round(lx, 3), round(ly, 3), 0]})
                lights.append({"type": "point", "name": "lampLight%d_%d" % (r, len(lights)), "position": [round(lx, 3), round(ly, 3), 3.2],
                               "color": [1, 0.8, 0.55], "intensity": 300, "range": 10})
                travelled += lamp_every
            travelled -= seg
        # lots on both sides, facing the road
        along_total = sum(math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]) for k in range(len(pts) - 1))
        d = rad + 2
        while d < along_total - rad:
            acc, k = 0.0, 0
            while k < len(pts) - 2 and acc + math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]) < d:
                acc += math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1])
                k += 1
            (x0, y0), (x1, y1) = pts[k], pts[k + 1]
            seg = math.hypot(x1 - x0, y1 - y0)
            t = min(1.0, (d - acc) / seg)
            px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            dx, dy = (x1 - x0) / seg, (y1 - y0) / seg
            for side in (1, -1):
                nx, ny = -dy * side, dx * side   # from the road towards the lot
                off = street / 2 + setback + lot_d / 2
                cx, cy = px + nx * off, py + ny * off
                if not free(cx, cy):
                    continue
                # the house front (local south, -y) looks at the road: local -y -> (sin yaw, -cos yaw) = (-nx, -ny)
                yaw = math.degrees(math.atan2(-nx, ny))
                lots.append({"centre": [round(cx, 3), round(cy, 3)], "yaw": round(yaw % 360, 2), "road": r,
                             "box": (cx - rad, cy - rad, cx + rad, cy + rad)})
            d += lot_w + P("houseSpacing", 2)
    occupied = [(-plaza, -plaza, plaza, plaza)]
    # houses on the lots
    for k, lot in enumerate(lots):
        cx, cy = lot["centre"]
        yaw = lot["yaw"]
        if house_specs or (has_kit and not blds):
            hs = dict(house_specs[k % len(house_specs)]) if house_specs else {"rooms": [{"name": "h", "w": 8, "d": 8, "kit": {}, "doors": [{"side": "S", "at": 0.5}],
                                                                                       "windows": [{"side": "E", "at": 0.5}, {"side": "W", "at": 0.5}]}]}
            room = hs["rooms"][0]
            rx, ry = nc_gds.rot2(float(room.get("x", 0)) + float(room["w"]) / 2, float(room.get("y", 0)) + float(room["d"]) / 2, yaw)
            hs["origin"] = [cx - rx, cy - ry, 0]
            hs["yaw"] = yaw
            hs["seed"] = int(w.get("seed", 1)) * 100 + k
            calls, _ = nc_gds.build_calls(hs, catalog)
            for c in calls:
                if c["type"] in ("model", "actor"):
                    pieces.append({"asset": c["asset"], "name": "lot%d_%s" % (k, c["name"]), "position": c["position"], "rotation": c["rotation"]})
                elif c["type"] == "shape":
                    shapes.append({"name": "lot%d_%s" % (k, c["name"]), "position": c["position"], "rotation": c["rotation"], "shape": c["shape"]})
        elif blds:
            b = blds[rng.randrange(len(blds))]
            pieces.append({"asset": b["asset"], "name": "house%d" % k, "position": [cx, cy, 0], "rotation": [0, 0, yaw]})
        else:   # greybox house: a box with a door gap, facing the road
            hs = {"origin": [cx, cy, 0], "yaw": yaw,
                  "rooms": [{"name": "h", "x": -4, "y": -4, "w": 8, "d": 8, "h": 3, "doors": [{"side": "S", "at": 0.5}]}]}
            for c in nc_gds.build_calls(hs, None)[0]:
                shapes.append({"name": "lot%d_%s" % (k, c["name"]), "position": c["position"], "rotation": c["rotation"], "shape": c["shape"]})
        if rng.random() < fence_p and catalog and any(it["role"] == "fence" for it in catalog["items"]):
            fence = next(it for it in catalog["items"] if it["role"] == "fence")
            L = max(fence["size"][0], fence["size"][1])
            n = max(1, int(lot_w / L))
            for s in range(n):   # the back fence of the lot
                lx, ly = -lot_w / 2 + (s + 0.5) * L, lot_d / 2
                rx, ry = nc_gds.rot2(lx, ly, yaw)
                pieces.append({"asset": fence["asset"], "name": "lot%d_fence%d" % (k, s),
                               "position": nc_gds.place_piece(fence, (cx + rx, cy + ry), 0, yaw), "rotation": [0, 0, yaw]})
    # trees outside the village core
    trees = [it["asset"] for it in (catalog or {}).get("items", []) if it["role"] == "tree"]
    placed = []
    if trees:
        boxes = [l["box"] for l in lots] + occupied
        for _ in range(int(tree_d * 120)):
            a = rng.uniform(0, 2 * math.pi)
            d = rng.uniform(reach * 0.55, reach * 1.25)
            X, Y = d * math.cos(a), d * math.sin(a)
            if any(b[0] - 2 < X < b[2] + 2 and b[1] - 2 < Y < b[3] + 2 for b in boxes):
                continue
            if any(seg_dist(X, Y, a2[0], a2[1], b2[0], b2[1]) < street / 2 + 2.5 for a2, b2 in segments):
                continue
            if any((X - px) ** 2 + (Y - py) ** 2 < 16 for px, py in placed):
                continue
            placed.append((X, Y))
            pieces.append({"asset": trees[rng.randrange(len(trees))], "name": "tree%d" % len(placed),
                           "position": [round(X, 3), round(Y, 3), -0.05], "rotation": [0, 0, round(rng.uniform(0, 360), 1)],
                           "scale": [round(rng.uniform(0.85, 1.3), 3)] * 3})
    spec = {"name": "_world_%s" % w["name"], "seed": w.get("seed", 1), "origin": w.get("origin", [0, 0, 0]),
            "shapes": shapes, "pieces": pieces, "lights": lights,
            "playerStart": {"position": [0, -plaza * 0.5, 0.05], "yaw": 0}}
    layout = {"name": w["name"], "mode": "village", "plaza": plaza, "spawn": spec["playerStart"]["position"],
              "lots": [{k: v for k, v in l.items() if k != "box"} for l in lots], "roads": roads, "trees": len(placed),
              "landmark": [0, 0, 0]}
    return spec, layout, ["ncli build art/blueprints/_world_%s.json --save current" % w["name"]]


# ------------------------------------------------------------------------------------------------ attach the terrain
WATER = ('    {id = %d, name = "%s_Sea", type = "water", position = {0, 0, 0}, rotation = {0, 0, 0}, scale = {1, 1, 1}, visible = true,\n'
         '     fx = {waveHeight = 0.45, wavelength = 22, choppiness = 0.5, windDirection = 40, waveSpeed = 1, roughness = 0.06, refraction = 0.05,'
         ' reflection = 1, foam = 0.6, foamWidth = 1.2, absorption = 0.25, color = {0.3, 0.62, 0.7}, deepColor = {0.02, 0.12, 0.2},'
         ' planarReflection = false, tileSize = 64, rings = 5}},\n')


def remove_entity(text, name):
    """Removes the level entity `{id = N, name = "<name>", ...}` (brace matched, strings respected)."""
    m = re.search(r'\n[ \t]*\{id = \d+, name = "%s",' % re.escape(name), text)
    if not m:
        return text, False
    i = text.index("{", m.start())
    depth, k, in_str = 0, i, False
    while k < len(text):
        ch = text[k]
        if in_str:
            if ch == "\\":
                k += 1
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        k += 1
    end = k + 1
    if text[end:end + 1] == ",":
        end += 1
    return text[:m.start()] + text[end:], True


def attach(project, name, level=None, land=None, water=None, remove=None):
    """Adds `{type = "terrain", source = <land>}` to the level file. The editor must NOT have the level open."""
    proj = os.path.abspath(project)
    if not level:
        pf = open(os.path.join(proj, "project.ncproject"), encoding="utf-8").read()
        m = re.search(r'startupLevel\s*=\s*"([^"]+)"', pf)
        level = m.group(1) if m else "Content/Levels/Main.nclevel"
    land = land or "Content/Landscape/%s.land" % name
    path = os.path.join(proj, level)
    text = open(path, encoding="utf-8").read()
    # the template's flat Ground box (and any --remove names, e.g. the template's starter shapes) would stay colliders
    # inside the landscape (hidden shapes still collide): remove them; the world replaces them
    removed = []
    for nm in ["Ground"] + list(remove or []):
        text, ok = remove_entity(text, nm)
        if ok:
            removed.append(nm)
    if re.search(r'source\s*=\s*"%s"' % re.escape(land), text):
        if removed:
            open(path, "w", encoding="utf-8").write(text)   # the removals still apply
        return {"attached": False, "why": "already in the level", "level": level, "removed": removed}
    ids = [int(x) for x in re.findall(r"\{\s*id\s*=\s*(\d+)", text)]
    nid = (max(ids) + 1) if ids else 1
    entry = ('    {id = %d, name = "%s", type = "terrain", source = "%s",\n'
             '     position = {0, 0, 0}, rotation = {0, 0, 0}, scale = {1, 1, 1}, visible = true},\n') % (nid, name, land)
    m = re.search(r"entities\s*=\s*\{\n", text)
    if not m:
        raise SystemExit("no entities table in %s" % level)
    if water is None:
        lay = os.path.join(proj, "art", "world", "%s.layout.json" % name)
        water = os.path.exists(lay) and json.load(open(lay, encoding="utf-8")).get("water", False)
    if water and not re.search(r'name = "%s_Sea"' % re.escape(name), text):
        entry += WATER % (nid + 1, name)   # the sea at z 0 (the sample's ocean settings)
    text = text[:m.end()] + entry + text[m.end():]
    open(path, "w", encoding="utf-8").write(text)
    return {"attached": True, "level": level, "id": nid, "land": land, "water": bool(water), "removed": removed}


def look(project, look_path, level=None):
    """Lighting, sky, fog and sun of a level from art/look/<name>.json (editor CLOSED: it rewrites the level file).
    {"lighting": {Lighting.set keys: exposure, autoExposure, bloom, atmosphere, clouds, volumetricClouds, heightFog,
                  heightFogDensity, volumetricFog, fogDensity, lightShafts, gi, ...},
     "sun": {"azimuth": deg from north towards east, "elevation": deg, "color": [r,g,b], "intensity": lux-ish},
     "ambient": [r,g,b], "clear": [r,g,b]}
    The values come from the reference board (time of day, haze, colour of the light), not from a fixed preset."""
    proj = os.path.abspath(project)
    L = json.load(open(look_path, encoding="utf-8"))
    if not level:
        pf = open(os.path.join(proj, "project.ncproject"), encoding="utf-8").read()
        m = re.search(r'startupLevel\s*=\s*"([^"]+)"', pf)
        level = m.group(1) if m else "Content/Levels/Main.nclevel"
    path = os.path.join(proj, level)
    text = open(path, encoding="utf-8").read()
    changed = []
    sun = L.get("sun")
    if sun:
        az, el = math.radians(float(sun.get("azimuth", 135))), math.radians(float(sun.get("elevation", 35)))
        d = (math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el))   # display, towards the sun
        e = (-d[0], d[2], d[1])                                                       # engine (Y up)
        col = sun.get("color", [1, 0.95, 0.85])
        env_sun = "sun = {enabled = true, direction = {%.6f, %.6f, %.6f}, color = %s}" % (e[0], e[1], e[2], nc_gds.to_lua(col))
        text, n = re.subn(r"sun = \{enabled = [^}]*\{[^}]*\}[^}]*\{[^}]*\}\}", env_sun, text, count=1)
        changed.append("environment.sun" if n else "environment.sun (not found)")
        pitch, yaw = math.degrees(el), math.degrees(math.atan2(e[0], e[2])) - 180   # the light points away from the sun
        m = re.search(r'\{id = \d+, name = "Sun", type = "light",.*?atmosphereSun = true\}', text, flags=re.S)
        if m:
            block = m.group(0)
            nb = re.sub(r"rotation = \{[^}]*\}", "rotation = {%.4f, %.4f, 0}" % (pitch, yaw), block, count=1)
            nb = re.sub(r"color = \{[^}]*\}", "color = %s" % nc_gds.to_lua(col), nb, count=1)
            if "intensity" in sun:
                nb = re.sub(r"intensity = [\d.]+", "intensity = %g" % float(sun["intensity"]), nb, count=1)
            text = text.replace(block, nb)
            changed.append("Sun entity")
    for key in ("ambient", "clear"):
        if key in L:
            text, n = re.subn(r"%s = \{[^}]*\}" % key, "%s = %s" % (key, nc_gds.to_lua(L[key])), text, count=1)
            if n:
                changed.append(key)
    if "lighting" in L:
        block = "  lighting = %s,\n" % nc_gds.to_lua(L["lighting"])
        if re.search(r"^  lighting = \{.*?\},\n", text, flags=re.M | re.S):
            text = re.sub(r"^  lighting = \{.*?\},\n", lambda _: block, text, count=1, flags=re.M | re.S)
        else:
            text = re.sub(r"(^  version = \d+,\n)", lambda m: m.group(1) + block, text, count=1, flags=re.M)
        changed.append("lighting")
    open(path, "w", encoding="utf-8").write(text)
    return {"level": level, "changed": changed}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("build")
    c.add_argument("world")
    c.add_argument("--project", required=True)
    c.add_argument("--catalog")
    c = sub.add_parser("attach")
    c.add_argument("project")
    c.add_argument("--name", required=True)
    c.add_argument("--level")
    c.add_argument("--land")
    c.add_argument("--remove", default="", help="comma separated entity names to drop (the template's starter shapes)")
    c = sub.add_parser("look", help="lighting, sky, fog and sun of a level from art/look/<name>.json (editor closed)")
    c.add_argument("project")
    c.add_argument("look")
    c.add_argument("--level")
    a = p.parse_args()
    if a.cmd == "look":
        print(json.dumps(look(a.project, a.look, a.level)))
        return
    if a.cmd == "attach":
        print(json.dumps(attach(a.project, a.name, a.level, a.land, remove=[n for n in a.remove.split(",") if n])))
        return
    w = json.load(open(a.world, encoding="utf-8"))
    proj = os.path.abspath(a.project)
    catalog = nc_gds.load_catalog(a.catalog or os.path.join(proj, "art", "kit-catalog.json"))
    mode = w.get("mode", "terrain")
    fn = {"terrain": terrain_world, "island": terrain_world, "dungeon": grid_world, "cave": grid_world,
          "village": village_world}.get(mode)
    if not fn:
        raise SystemExit("mode %s: terrain | island | dungeon | cave | village" % mode)
    spec, layout, nxt = fn(w, proj, catalog)
    spec_path = os.path.join(proj, "art", "blueprints", "_world_%s.json" % w["name"])
    os.makedirs(os.path.dirname(spec_path), exist_ok=True)
    json.dump(spec, open(spec_path, "w", encoding="utf-8"), indent=1)
    lay_path = os.path.join(proj, "art", "world", "%s.layout.json" % w["name"])
    os.makedirs(os.path.dirname(lay_path), exist_ok=True)
    json.dump(layout, open(lay_path, "w", encoding="utf-8"), indent=1)
    calls, warnings = nc_gds.build_calls(spec, catalog)
    print(json.dumps({"mode": mode, "spec": os.path.relpath(spec_path, proj), "layout": os.path.relpath(lay_path, proj),
                      "entities": len(calls), "warnings": warnings[:10], "next": nxt,
                      **{k: layout[k] for k in ("rooms", "lots", "scattered", "walls", "trees") if k in layout and not isinstance(layout[k], list)},
                      "counts": {k: len(layout[k]) for k in ("rooms", "lots", "flats") if isinstance(layout.get(k), list)}}))


if __name__ == "__main__":
    main()
