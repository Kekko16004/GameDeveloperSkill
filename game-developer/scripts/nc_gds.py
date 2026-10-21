#!/usr/bin/env python3
"""nc_gds: the offline half of the GDS layer for Nucleon (no editor needed, standard library only).

Imported by ncli.py; also a CLI for the parts that never touch the editor:
  python nc_gds.py catalog <folder> [--out art/kit-catalog.json] [--project PROJECT]   kit measures from .glb/.gltf/.obj
  python nc_gds.py calls <spec.json> [--catalog art/kit-catalog.json]                  the entity_add list a spec makes
  python nc_gds.py hash <spec.json> [--catalog ...]                                    the cache key of a build

Coordinates: Nucleon display space, Z up, meters (x east, y north). A glTF model is Y up: its display box is
x = -gltf.x, y = gltf.z, z = gltf.y (docs/api/NATIVES.md "Coordinates"; verified against entity_get bounds).
"""
import hashlib
import json
import math
import os
import random
import re
import struct
import sys

# ------------------------------------------------------------------------------------------------ geometry helpers
def rot2(px, py, yaw):
    r = math.radians(yaw)
    return px * math.cos(r) - py * math.sin(r), px * math.sin(r) + py * math.cos(r)


def wall_segments(length, height, openings):
    """[(start, end, z0, z1)] along a wall of `length`, cutting door/window openings.
    An opening: at (0..1 centre along the wall) or offset (meters from the start), width, height, sill (0 for a door)."""
    cuts = []
    for o in openings:
        w = float(o.get("width", 1.0))
        c = float(o["offset"]) if "offset" in o else float(o.get("at", 0.5)) * length
        c = min(max(c, w / 2), length - w / 2)
        cuts.append((c - w / 2, c + w / 2, float(o.get("sill", 0.0)), min(height, float(o.get("height", 2.1)))))
    cuts.sort()
    segs, x = [], 0.0
    for s, e, sill, top in cuts:
        if s > x + 1e-3:
            segs.append((x, s, 0.0, height))
        if sill > 1e-3:
            segs.append((s, e, 0.0, sill))
        if top < height - 1e-3:
            segs.append((s, e, top, height))
        x = max(x, e)
    if x < length - 1e-3:
        segs.append((x, length, 0.0, height))
    return segs


def room_openings(room):
    openings = {"N": [], "S": [], "E": [], "W": []}
    for kind in ("doors", "windows"):
        for o in room.get(kind, []):
            o = dict(o)
            o["kind"] = "door" if kind == "doors" else "window"
            if kind == "windows":
                o.setdefault("sill", 0.9)
                o.setdefault("height", 2.0)
            openings[o.get("side", "S").upper()].append(o)
    return openings


def room_parts(room, defaults):
    """Boxes of one room (local meters, z up): floor, optional ceiling, four walls (S/N along x, W/E along y)."""
    name = room.get("name", "room")
    x0, y0 = float(room.get("x", 0)), float(room.get("y", 0))
    w, d, h = float(room["w"]), float(room["d"]), float(room.get("h", defaults.get("h", 3.0)))
    t = float(room.get("wall", defaults.get("wall", 0.2)))
    ft = float(room.get("floorThickness", defaults.get("floorThickness", 0.2)))
    z0 = float(room.get("z", 0))
    wall_color = room.get("wallColor", defaults.get("wallColor", [0.8, 0.78, 0.72]))
    floor_color = room.get("floorColor", defaults.get("floorColor", [0.45, 0.4, 0.35]))
    omit = set(room.get("omit", []))
    parts = []
    if room.get("floor", True):
        parts.append(dict(name="%s_floor" % name, size=(w, d, ft), center=(x0 + w / 2, y0 + d / 2, z0 - ft / 2),
                          color=floor_color, role="floor"))
    if room.get("ceiling", False):
        parts.append(dict(name="%s_ceiling" % name, size=(w, d, ft), center=(x0 + w / 2, y0 + d / 2, z0 + h + ft / 2),
                          color=wall_color, role="ceiling"))
    openings = room_openings(room)
    for side in ("S", "N", "W", "E"):
        if side in omit:
            continue
        along_x = side in ("S", "N")
        length = w if along_x else d - 2 * t
        for i, (s, e, za, zb) in enumerate(wall_segments(length, h, openings[side])):
            seg = e - s
            if along_x:
                cx = x0 + s + seg / 2
                cy = y0 + t / 2 if side == "S" else y0 + d - t / 2
                size = (seg, t, zb - za)
            else:
                cx = x0 + t / 2 if side == "W" else x0 + w - t / 2
                cy = y0 + t + s + seg / 2
                size = (t, seg, zb - za)
            parts.append(dict(name="%s_wall%s%d" % (name, side, i), size=size, center=(cx, cy, z0 + (za + zb) / 2),
                              color=wall_color, role="wall"))
    return parts


def scatter_points(sc, rng):
    x0, y0, x1, y1 = [float(v) for v in sc["area"]]
    count, min_d = int(sc.get("count", 10)), float(sc.get("minDist", 1.0))
    avoid = [tuple(map(float, r)) for r in sc.get("avoid", [])]   # [x0,y0,x1,y1] rectangles kept clear
    pts, tries = [], 0
    while len(pts) < count and tries < count * 60:
        tries += 1
        p = (rng.uniform(x0, x1), rng.uniform(y0, y1))
        if any(r[0] <= p[0] <= r[2] and r[1] <= p[1] <= r[3] for r in avoid):
            continue
        if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 >= min_d * min_d for q in pts):
            pts.append(p)
    return pts


# ------------------------------------------------------------------------------------------------ kit catalog
ROLE_WORDS = [  # first match wins: specific before generic
    ("wallDoor", r"door(way|frame)?|gate|entrance"), ("wallWindow", r"window"), ("corner", r"corner|pillar|column"),
    ("building", r"^building_|house|home|tavern|church|castle|barracks|blacksmith|mill|market|barn|cottage|shop|inn\b"),
    ("roof", r"roof"), ("stairs", r"stair|step"), ("floor", r"floor|tile|ground|plank"), ("fence", r"fence|railing|palisade"), ("wall", r"wall"),
    ("door", r"^door"), ("tree", r"tree|pine|oak|birch|palm"), ("rock", r"rock|stone|boulder"),
    ("plant", r"bush|grass|flower|plant|fern"), ("light", r"lamp|torch|lantern|candle|light"),
    ("container", r"crate|barrel|chest|box|sack"), ("furniture", r"table|chair|bench|bed|shelf|cabinet|stool"),
]


def guess_role(name):
    low = os.path.splitext(os.path.basename(name))[0].lower()
    for role, pat in ROLE_WORDS:
        if re.search(pat, low):
            if role == "door" and re.search(r"wall", low):
                return "wallDoor"
            return role
    return "prop"


def _mat_mul(a, b):
    return [sum(a[r * 4 + k] * b[k * 4 + c] for k in range(4)) for r in range(4) for c in range(4)]


def _node_matrix(node):
    if "matrix" in node:   # glTF column-major -> row-major
        m = node["matrix"]
        return [m[c * 4 + r] for r in range(4) for c in range(4)]
    t = node.get("translation", [0, 0, 0])
    q = node.get("rotation", [0, 0, 0, 1])
    s = node.get("scale", [1, 1, 1])
    x, y, z, w = q
    rm = [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w),
          2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w),
          2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]
    return [rm[0] * s[0], rm[1] * s[1], rm[2] * s[2], t[0],
            rm[3] * s[0], rm[4] * s[1], rm[5] * s[2], t[1],
            rm[6] * s[0], rm[7] * s[1], rm[8] * s[2], t[2],
            0, 0, 0, 1]


def gltf_bounds(path):
    """Axis-aligned bounds of a .glb/.gltf in glTF space (Y up): accessor min/max of POSITION through the node tree."""
    data = open(path, "rb").read()
    if data[:4] == b"glTF":
        length = struct.unpack_from("<I", data, 12)[0]
        doc = json.loads(data[20:20 + length].decode("utf-8"))
    else:
        doc = json.loads(data.decode("utf-8"))
    nodes, meshes, acc = doc.get("nodes", []), doc.get("meshes", []), doc.get("accessors", [])
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    ident = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

    def visit(i, parent):
        node = nodes[i]
        m = _mat_mul(parent, _node_matrix(node))
        if "mesh" in node:
            for prim in meshes[node["mesh"]].get("primitives", []):
                a = acc[prim["attributes"]["POSITION"]]
                mn, mx = a.get("min"), a.get("max")
                if not mn or not mx:
                    continue
                for cx in (mn[0], mx[0]):
                    for cy in (mn[1], mx[1]):
                        for cz in (mn[2], mx[2]):
                            p = [m[r * 4] * cx + m[r * 4 + 1] * cy + m[r * 4 + 2] * cz + m[r * 4 + 3] for r in range(3)]
                            for k in range(3):
                                lo[k] = min(lo[k], p[k])
                                hi[k] = max(hi[k], p[k])
        for c in node.get("children", []):
            visit(c, m)

    scenes = doc.get("scenes") or [{"nodes": list(range(len(nodes)))}]
    roots = scenes[doc.get("scene", 0)].get("nodes", [])
    for r in roots:
        visit(r, ident)
    if lo[0] == math.inf:
        return None
    return lo, hi


def obj_bounds(path):
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("v "):
                p = [float(v) for v in line.split()[1:4]]
                for k in range(3):
                    lo[k], hi[k] = min(lo[k], p[k]), max(hi[k], p[k])
    return (lo, hi) if lo[0] != math.inf else None


def display_box(lo, hi):
    """glTF/OBJ Y-up bounds -> Nucleon display Z-up bounds."""
    return [-hi[0], lo[2], lo[1]], [-lo[0], hi[2], hi[1]]


def catalog_folder(folder, project=None):
    """Measure every model under folder -> catalog entries with display size, pivot offsets and a guessed role."""
    items, skipped = [], []
    for root, _, files in os.walk(folder):
        for f in sorted(files):
            ext = os.path.splitext(f)[1].lower()
            if ext not in (".glb", ".gltf", ".obj", ".fbx"):
                continue
            full = os.path.join(root, f)
            try:
                b = gltf_bounds(full) if ext in (".glb", ".gltf") else obj_bounds(full) if ext == ".obj" else None
            except Exception as e:   # broken file: listed, never fatal
                b = None
                skipped.append({"file": f, "why": str(e)[:80]})
                continue
            if not b:
                skipped.append({"file": f, "why": "fbx: measure after import (ncli catalog --live)" if ext == ".fbx" else "no geometry"})
                continue
            lo, hi = display_box(*b)
            size = [round(hi[k] - lo[k], 4) for k in range(3)]
            rel = os.path.relpath(full, project).replace("\\", "/") if project else full.replace("\\", "/")
            items.append({"asset": rel, "name": os.path.splitext(f)[0], "role": guess_role(f), "size": size,
                          "min": [round(v, 4) for v in lo], "max": [round(v, 4) for v in hi],
                          "pivot": "base-center" if abs(lo[2]) < 0.02 and abs(lo[0] + hi[0]) < 0.05 and abs(lo[1] + hi[1]) < 0.05
                          else "base" if abs(lo[2]) < 0.02 else "other"})
    roles = {}
    for it in items:
        roles.setdefault(it["role"], []).append(it["name"])
    module = None
    walls = [it for it in items if it["role"] == "wall"]
    if walls:   # the most common wall length is the grid module
        lengths = sorted(round(max(it["size"][0], it["size"][1]), 2) for it in walls)
        module = max(set(lengths), key=lengths.count)
    return {"version": 1, "engine": "nucleon", "folder": folder.replace("\\", "/"), "module": module,
            "count": len(items), "roles": {k: len(v) for k, v in sorted(roles.items())}, "items": items, "skipped": skipped}


def load_catalog(path):
    if not path or not os.path.exists(path):
        return None
    cat = json.load(open(path, encoding="utf-8"))
    cat["_by_name"] = {it["name"]: it for it in cat.get("items", [])}
    cat["_by_asset"] = {it["asset"]: it for it in cat.get("items", [])}
    return cat


def pick(cat, role=None, name=None, rng=None, prefer=None):
    """A catalog item by exact name, or by role (prefer = substring to favour, rng = random choice among matches)."""
    if not cat:
        raise ValueError("this spec uses roles/kit pieces: pass --catalog art/kit-catalog.json (nc_gds.py catalog)")
    if name:
        it = cat["_by_name"].get(name) or cat["_by_asset"].get(name)
        if not it:
            raise ValueError("no kit piece named %s" % name)
        return it
    cands = [it for it in cat["items"] if it["role"] == role]
    if prefer:
        fav = [it for it in cands if prefer.lower() in it["name"].lower()]
        cands = fav or cands
    if not cands:
        raise ValueError("the kit has no piece with role %s (roles: %s)" % (role, ", ".join(cat["roles"])))
    return cands[rng.randrange(len(cands))] if rng else cands[0]


def place_piece(item, center_xy, base_z, yaw, scale=1.0):
    """Entity position so that the piece's footprint centre lands on center_xy and its bottom on base_z
    (bounds multiplied by the uniform `scale` the piece is placed with)."""
    lo, hi = [v * scale for v in item["min"]], [v * scale for v in item["max"]]
    ox, oy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    rx, ry = rot2(ox, oy, yaw)
    return [center_xy[0] - rx, center_xy[1] - ry, base_z - lo[2]]


def kit_room_calls(room, cat, rng, defaults, ks=1.0):
    """A room of modular kit pieces: floor tiles, wall modules along each side, door/window modules at the openings,
    optional corners and roof. Lengths snap to the kit module; returns (local calls, warnings)."""
    kit = room.get("kit") if isinstance(room.get("kit"), dict) else {}
    prefer = kit.get("prefer")
    wall = pick(cat, name=kit.get("wall"), role=None if kit.get("wall") else "wall", prefer=prefer)
    L = max(wall["size"][0], wall["size"][1]) * ks
    wall_along_x = wall["size"][0] >= wall["size"][1]
    base_yaw = 0 if wall_along_x else -90   # the yaw that lays the module along +x
    x0, y0 = float(room.get("x", 0)), float(room.get("y", 0))
    nx = max(1, round(float(room["w"]) / L))
    ny = max(1, round(float(room["d"]) / L))
    warnings = []
    if abs(nx * L - float(room["w"])) > 0.01 or abs(ny * L - float(room["d"])) > 0.01:
        warnings.append("%s: %gx%g snapped to the kit module %g -> %gx%g" % (room.get("name", "room"), room["w"], room["d"], L, nx * L, ny * L))
    w, d = nx * L, ny * L
    z0 = float(room.get("z", 0))
    name = room.get("name", "room")
    calls = []

    def add(item, center, yaw, tag, top=False):
        base = z0 - item["size"][2] * ks if top else z0   # floor tiles: their top is the room level
        calls.append({"type": "actor" if item["asset"].endswith(".ncactor") else "model", "asset": item["asset"],
                      "name": "%s_%s" % (name, tag), "local": place_piece(item, center, base, yaw, ks), "yaw": yaw, "ks": ks})

    if room.get("floor", True):
        fl = pick(cat, name=kit.get("floor"), role=None if kit.get("floor") else "floor", prefer=prefer)
        fx, fy = max(fl["size"][0], 0.1) * ks, max(fl["size"][1], 0.1) * ks
        for i in range(max(1, round(w / fx))):
            for j in range(max(1, round(d / fy))):
                add(fl, (x0 + (i + 0.5) * fx, y0 + (j + 0.5) * fy), 0, "floor%d_%d" % (i, j), top=True)
    openings = room_openings(room)
    omit = set(room.get("omit", []))
    sides = {"S": (nx, lambda k: (x0 + (k + 0.5) * L, y0), 0), "N": (nx, lambda k: (x0 + (k + 0.5) * L, y0 + d), 180),
             "W": (ny, lambda k: (x0, y0 + (k + 0.5) * L), 90), "E": (ny, lambda k: (x0 + w, y0 + (k + 0.5) * L), -90)}
    for side, (n, at, face) in sides.items():
        if side in omit:
            continue
        slots = {}
        for o in openings[side]:
            pos = float(o["offset"]) if "offset" in o else float(o.get("at", 0.5)) * n * L
            slots[min(n - 1, max(0, int(pos // L)))] = o["kind"]
        for k in range(n):
            kind = slots.get(k)
            role = "wallDoor" if kind == "door" else "wallWindow" if kind == "window" else "wall"
            try:
                item = wall if role == "wall" else pick(cat, name=kit.get(role), role=None if kit.get(role) else role, prefer=prefer)
            except ValueError as e:
                warnings.append(str(e) + " (box gap left instead)")
                continue
            add(item, at(k), (base_yaw + face) % 360, "wall%s%d" % (side, k))
    if room.get("corners", kit.get("corners", False)):
        try:
            c = pick(cat, name=kit.get("corner"), role=None if kit.get("corner") else "corner", prefer=prefer)
            for k, (cx, cy) in enumerate(((x0, y0), (x0 + w, y0), (x0 + w, y0 + d), (x0, y0 + d))):
                add(c, (cx, cy), 90 * k, "corner%d" % k)
        except ValueError as e:
            warnings.append(str(e))
    return calls, warnings


# ------------------------------------------------------------------------------------------------ spec -> calls
def build_calls(spec, catalog=None):
    """MCP entity_add arguments (without parent) for a blueprint spec, in world display coordinates; and warnings."""
    ox, oy, oz = [float(v) for v in spec.get("origin", [0, 0, 0])]
    yaw = float(spec.get("yaw", 0))
    rng = random.Random(spec.get("seed", 1))
    defaults = spec.get("defaults", {})
    ks = float(spec.get("kitScale", 1.0))   # a miniature kit (KayKit hex: a 0.9 m house) scaled to metres once, here
    calls, warnings = [], []

    def scaled(v):
        if v is None:
            return [round(ks, 4)] * 3 if ks != 1 else None
        v = [v] * 3 if isinstance(v, (int, float)) else v
        return [round(x * ks, 4) for x in v]

    def place(lx, ly, lz):
        rx, ry = rot2(lx, ly, yaw)
        return [round(ox + rx, 4), round(oy + ry, 4), round(oz + lz, 4)]

    for room in spec.get("rooms", []):
        if room.get("kit"):
            kc, kw = kit_room_calls(room, catalog, rng, defaults, ks)
            warnings += kw
            for c in kc:
                e = {"type": c["type"], "asset": c["asset"], "name": c["name"], "position": place(*c["local"]),
                     "rotation": [0, 0, round((c["yaw"] + yaw) % 360, 3)]}
                if ks != 1:
                    e["scale"] = [round(ks, 4)] * 3
                calls.append(e)
            continue
        for p in room_parts(room, defaults):
            sx, sy, sz = p["size"]
            # box parameters are the entity's own axes: width = x (east), depth = y (north), height = z (up)
            calls.append({"type": "shape", "name": p["name"], "position": place(*p["center"]), "rotation": [0, 0, yaw],
                          "shape": {"kind": "box", "width": round(sx, 4), "depth": round(sy, 4), "height": round(sz, 4),
                                    "color": p["color"]}})
    for i, s in enumerate(spec.get("shapes", [])):
        r = s.get("rotation", [0, 0, 0])
        args = {"type": "shape", "name": s.get("name", "shape%d" % i), "position": place(*s["position"]),
                "rotation": [r[0], r[1], r[2] + yaw], "shape": s["shape"]}
        if "scale" in s:
            args["scale"] = s["scale"]
        calls.append(args)
    for i, pc in enumerate(spec.get("pieces", [])):
        r = pc.get("rotation", [0, 0, 0])
        own = pc.get("scale", 1.0)
        own_u = own if isinstance(own, (int, float)) else own[0]
        if "asset" not in pc:   # by kit role or name: the bottom of the piece on the given z
            item = pick(catalog, role=pc.get("role"), name=pc.get("piece"), rng=rng, prefer=pc.get("prefer"))
            lx, ly, lz = pc.get("position", [0, 0, 0])
            pos = place_piece(item, (lx, ly), lz, r[2], ks * own_u)
            asset = item["asset"]
        else:
            pos, asset = pc.get("position", [0, 0, 0]), pc["asset"]
        args = {"type": pc.get("type", "actor" if asset.endswith(".ncactor") else "model"), "asset": asset,
                "name": pc.get("name", "%s_%d" % (os.path.splitext(os.path.basename(asset))[0], i)),
                "position": place(*pos), "rotation": [r[0], r[1], r[2] + yaw]}
        sc_ = scaled(pc.get("scale"))
        if sc_:
            args["scale"] = sc_
        if "properties" in pc:
            args["properties"] = pc["properties"]
        calls.append(args)
    for si, sc in enumerate(spec.get("scatter", [])):
        if "assets" in sc:
            assets = sc["assets"]
        elif "asset" in sc:
            assets = [sc["asset"]]
        else:   # by role from the catalog: every piece of that role
            assets = [it["asset"] for it in catalog["items"] if it["role"] == sc["role"]] if catalog else []
            if not assets:
                raise ValueError("scatter %d: no catalog pieces with role %s" % (si, sc.get("role")))
        smin, smax = sc.get("scale", [1, 1])
        for j, (px, py) in enumerate(scatter_points(sc, rng)):
            asset = assets[rng.randrange(len(assets))]
            k = rng.uniform(float(smin), float(smax)) * ks
            calls.append({"type": "actor" if asset.endswith(".ncactor") else "model", "asset": asset,
                          "name": "%s_s%d_%d" % (sc.get("name", "scatter"), si, j),
                          "position": place(px, py, float(sc.get("z", 0))),
                          "rotation": [0, 0, round(rng.uniform(0, 360) if sc.get("yawRandom", True) else yaw, 2)],
                          "scale": [round(k, 3)] * 3})
    for i, li in enumerate(spec.get("lights", [])):
        light = {k: v for k, v in li.items() if k not in ("position", "name", "rotation")}
        args = {"type": "light", "name": li.get("name", "light%d" % i), "position": place(*li.get("position", [0, 0, 3])),
                "light": light}
        if "rotation" in li:
            args["rotation"] = li["rotation"]
        calls.append(args)
    ps = spec.get("playerStart")
    if ps:
        calls.append({"type": "playerstart", "name": ps.get("name", "PlayerStart"), "position": place(*ps["position"]),
                      "rotation": [0, 0, float(ps.get("yaw", 0)) + yaw],
                      **({"player_start": {"tag": ps["tag"]}} if "tag" in ps else {})})
    return calls, warnings


def to_lua(v, indent=0):
    """JSON value -> Lua literal (level tables, plans read with load())."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "nil"
    if isinstance(v, (int, float)):
        return repr(round(v, 6)) if isinstance(v, float) else repr(v)
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, list):
        return "{" + ", ".join(to_lua(x) for x in v) + "}"
    return "{" + ", ".join(("%s = %s" % (k, to_lua(x))) if re.match(r"^[A-Za-z_]\w*$", k) else
                           "[%s] = %s" % (json.dumps(k), to_lua(x)) for k, x in v.items()) + "}"


def calls_bounds(calls):
    pts = [c["position"] for c in calls if "position" in c]
    if not pts:
        return None
    return [min(p[k] for p in pts) for k in range(3)], [max(p[k] for p in pts) for k in range(3)]


def spec_hash(spec_path, catalog_path=None):
    h = hashlib.sha1(open(spec_path, "rb").read())
    if catalog_path and os.path.exists(catalog_path):
        h.update(open(catalog_path, "rb").read())
    h.update(open(os.path.abspath(__file__), "rb").read())   # a builder change invalidates the cache too
    return h.hexdigest()[:16]


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("catalog")
    c.add_argument("folder")
    c.add_argument("--out")
    c.add_argument("--project", help="paths in the catalog relative to this project folder")
    c = sub.add_parser("calls")
    c.add_argument("spec")
    c.add_argument("--catalog")
    c = sub.add_parser("hash")
    c.add_argument("spec")
    c.add_argument("--catalog")
    a = p.parse_args()
    if a.cmd == "catalog":
        cat = catalog_folder(a.folder, a.project)
        if a.out:
            os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
            json.dump(cat, open(a.out, "w", encoding="utf-8"), indent=1)
        print(json.dumps({"count": cat["count"], "module": cat["module"], "roles": cat["roles"],
                          "skipped": len(cat["skipped"]), "out": a.out}))
    elif a.cmd == "calls":
        calls, warnings = build_calls(json.load(open(a.spec, encoding="utf-8")), load_catalog(a.catalog))
        print(json.dumps({"calls": calls, "warnings": warnings}, indent=1))
    else:
        print(spec_hash(a.spec, a.catalog))


if __name__ == "__main__":
    sys.exit(main())
