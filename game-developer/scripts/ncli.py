#!/usr/bin/env python3
"""ncli: the GameDeveloperSkill bridge to the Nucleon editor (its built-in MCP server, docs/editor/MCP.md).

Standard library only. Every command prints ONE compact JSON line (screenshots go to files, never to stdout), so a worker
spends a few hundred tokens per step instead of carrying 24 tool schemas and base64 images in its context.

Transport:
  HTTP (default)   the editor is open with Editor Preferences > AI > Enable Server; port and token are read from
                   editor-settings.lua (NC_EDITOR_PREF_DIR, or the user folder Nucleon/Editor), or --port/--token.
  --stdio EXE      starts `EXE --mcp-stdio PROJECT` for this one command and closes it at the end (no window needed on
                   a machine with a display; Linux CI: run under xvfb-run). Save with --save, the editor quits unsaved.

Coordinates: everything here is the editor's display space, Z up, meters, rotation [pitch, roll, yaw] degrees
(docs/engine/COORDINATES.md). `ping` warns when the Up axis preference is Y (then the MCP fields are Y up).

Commands (python ncli.py <command> -h for the options):
  ping | state            editor_state, compact
  call TOOL [JSON|@file]  one MCP tool, prints its structuredContent
  batch FILE|-            [{"tool": name, "args": {...}}, ...] as ONE JSON-RPC batch (one round trip)
  build SPEC.json         GDS blueprint for Nucleon (rooms with door/window gaps, pieces, seeded scatter, lights,
                          player start) under a folder named after the spec; rebuild in place; writes docs/lint/build-<name>.json
  lint                    scene checks -> {"issues": N, ...}; --write docs/lint/scene-lint.json
  shot OUT.png            viewport_camera (optional) + capture_viewport, the PNG written to OUT.png
  play-test               Play, wait, capture, collect log errors, Stop
  log                     read_log (errors by default)
  save [PATH]             save_scene
  lock acquire|release    one editor driver at a time (PROJECT/Saved/gds-nucleon.lock, stale after 10 min)
  exe ...                 headless editor: compile-blueprints, package, run-lua, new-project, migrate
  setup PROJECT           GDS test harness + example spec + folders + .gitignore into a Nucleon project
  mcp-config              the `claude mcp add` lines for this project
"""
import argparse
import base64
import json
import math
import os
import queue
import random
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

PROTOCOL = "2025-06-18"


# ----------------------------------------------------------------------------------------------------------- settings
def pref_dir():
    env = os.environ.get("NC_EDITOR_PREF_DIR")
    if env:
        return env
    if sys.platform.startswith("win"):
        return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Nucleon", "Editor")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/Nucleon/Editor")
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, "Nucleon", "Editor")


def read_settings():
    """port, token, enabled and upAxis from editor-settings.lua (a Lua table: read with regular expressions)."""
    path = os.path.join(pref_dir(), "editor-settings.lua")
    out = {"file": path}
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return out
    ai = re.search(r"\bai\s*=\s*\{([^}]*)\}", text)
    if ai:
        body = ai.group(1)
        for key in ("port", "token", "enabled", "luaOverHttp"):
            m = re.search(r"\b%s\s*=\s*(\"[^\"]*\"|[\w.]+)" % key, body)
            if m:
                v = m.group(1).strip('"')
                out[key] = int(v) if v.isdigit() else (v == "true" if v in ("true", "false") else v)
    m = re.search(r"\bupAxis\s*=\s*(\d)", text)
    if m:
        out["upAxis"] = "y" if m.group(1) == "1" else "z"
    return out


# ----------------------------------------------------------------------------------------------------------- clients
class McpError(Exception):
    pass


class HttpClient:
    def __init__(self, port, token, timeout):
        self.url = "http://127.0.0.1:%d/mcp" % port
        self.token = token
        self.timeout = timeout

    def post(self, payload):
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode(), method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        if self.token:
            req.add_header("Authorization", "Bearer " + self.token)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = r.read()
        except urllib.error.HTTPError as e:
            hint = {401: "wrong or missing token (Editor Preferences > AI, or --token)",
                    403: "non-local Host/Origin rejected"}.get(e.code, "")
            raise McpError("HTTP %d %s" % (e.code, hint))
        except (urllib.error.URLError, OSError) as e:
            raise McpError("editor not reachable at %s (%s): open the editor and turn on Editor Preferences > AI > "
                           "Enable Server, or use --stdio <NucleonEditor>" % (self.url, e))
        return json.loads(body) if body else None

    def close(self):
        pass


class StdioClient:
    def __init__(self, exe, project, timeout, no_lua=False):
        args = [exe, "--mcp-stdio"] + (["--mcp-no-lua"] if no_lua else []) + [project]
        self.timeout = timeout
        self.log = open(os.devnull, "wb") if not os.environ.get("NCLI_EDITOR_LOG") else open(os.environ["NCLI_EDITOR_LOG"], "wb")
        self.proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log)
        self.lines = queue.Queue()
        threading.Thread(target=self._reader, daemon=True).start()
        reply = self.post({"jsonrpc": "2.0", "id": 0, "method": "initialize",
                           "params": {"protocolVersion": PROTOCOL, "capabilities": {},
                                      "clientInfo": {"name": "ncli", "version": "1"}}}, startup=True)
        if not reply or "result" not in reply:
            raise McpError("the editor did not initialize")
        self.proc.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        self.proc.stdin.flush()

    def _reader(self):
        for raw in self.proc.stdout:
            text = raw.decode("utf-8", "replace").strip()
            if text:
                try:
                    self.lines.put(json.loads(text))
                except ValueError:
                    pass
        self.lines.put(None)

    def post(self, payload, startup=False):
        ids = {m["id"] for m in payload if "id" in m} if isinstance(payload, list) else {payload.get("id")}
        self.proc.stdin.write((json.dumps(payload) + "\n").encode())
        self.proc.stdin.flush()
        deadline = time.time() + (max(self.timeout, 180) if startup else self.timeout)
        while True:
            try:
                reply = self.lines.get(timeout=max(0.1, deadline - time.time()))
            except queue.Empty:
                raise McpError("timeout waiting for the editor")
            if reply is None:
                raise McpError("the editor closed its output (exit code %s)" % self.proc.poll())
            if isinstance(reply, list) or reply.get("id") in ids:
                return reply

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=30)
        except Exception:
            self.proc.kill()


class Editor:
    """tools/call helpers over either client."""

    def __init__(self, client):
        self.client = client
        self.next_id = 1

    def _msg(self, tool, args):
        self.next_id += 1
        return {"jsonrpc": "2.0", "id": self.next_id, "method": "tools/call",
                "params": {"name": tool, "arguments": args or {}}}

    @staticmethod
    def _unwrap(reply, raw=False):
        if reply is None:
            raise McpError("empty reply")
        if "error" in reply:
            raise McpError(reply["error"].get("message", "error"))
        result = reply["result"]
        if result.get("isError"):
            raise McpError(" ".join(c.get("text", "") for c in result.get("content", [])))
        if raw:
            return result
        sc = result.get("structuredContent")
        if sc is not None:
            return sc.get("result", sc) if list(sc.keys()) == ["result"] else sc
        return result

    def call(self, tool, args=None, raw=False):
        return self._unwrap(self.client.post(self._msg(tool, args)), raw)

    def batch(self, calls, chunk=200):
        """calls = [(tool, args)]; one JSON-RPC batch per chunk; returns [(ok, value_or_error)] in order."""
        out = []
        for start in range(0, len(calls), chunk):
            msgs = [self._msg(t, a) for t, a in calls[start:start + chunk]]
            replies = self.client.post(msgs) or []
            by_id = {r.get("id"): r for r in replies}
            for m in msgs:
                try:
                    out.append((True, self._unwrap(by_id.get(m["id"]))))
                except McpError as e:
                    out.append((False, str(e)))
        return out


def connect(a):
    if a.stdio:
        if not a.project:
            raise McpError("--stdio needs --project")
        return Editor(StdioClient(a.stdio, a.project, a.timeout, a.no_lua))
    s = read_settings()
    port = a.port or s.get("port") or 47420
    token = a.token or os.environ.get("NC_MCP_TOKEN") or s.get("token")
    return Editor(HttpClient(int(port), token, a.timeout))


def emit(obj):
    sys.stdout.write(json.dumps(obj, separators=(",", ":"), ensure_ascii=False) + "\n")


def load_json_arg(text):
    if text is None:
        return {}
    if text == "-":
        return json.load(sys.stdin)
    if text.startswith("@"):
        return json.load(open(text[1:], encoding="utf-8"))
    return json.loads(text)


def project_dir(a, ed=None):
    if a.project:
        return os.path.abspath(a.project)
    if ed is not None:
        try:
            return ed.call("editor_state").get("project") or os.getcwd()
        except McpError:
            pass
    return os.getcwd()


def write_json(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ----------------------------------------------------------------------------------------------------------- commands
def cmd_ping(a, ed):
    st = ed.call("editor_state")
    s = read_settings()
    out = {"ok": True, "project": st.get("project"), "level": st.get("scene_file"), "entities": st.get("entity_count"),
           "unsaved": st.get("unsaved_changes"), "play": st.get("play_state"), "upAxis": s.get("upAxis", "z")}
    if out["upAxis"] == "y":
        out["warning"] = "Up axis preference is Y: ncli and the GDS specs assume Z up (Editor Preferences > Appearance)"
    emit(out)


def cmd_state(a, ed):
    emit(ed.call("editor_state"))


def cmd_call(a, ed):
    res = ed.call(a.tool, load_json_arg(a.args), raw=a.raw)
    if a.raw:
        for c in res.get("content", []):
            if c.get("type") == "image":
                c["data"] = "<%d bytes base64, use ncli shot>" % len(c["data"])
    emit(res)


def cmd_batch(a, ed):
    calls = load_json_arg(a.file if a.file in ("-",) or a.file.startswith("@") else "@" + a.file)
    results = ed.batch([(c["tool"], c.get("args", {})) for c in calls])
    failed = [{"i": i, "tool": calls[i]["tool"], "error": v} for i, (ok, v) in enumerate(results) if not ok]
    summary = {"calls": len(calls), "ok": len(calls) - len(failed), "failed": failed}
    if a.full:
        summary["results"] = [v for _, v in results]
    else:
        summary["ids"] = [v.get("id") if ok and isinstance(v, dict) else None for ok, v in results]
    emit(summary)
    if failed:
        sys.exit(1)


# --- build: GDS blueprints for Nucleon ---------------------------------------------------------------------------------
def _rot(px, py, yaw):
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


def room_parts(room, defaults):
    """Boxes of one room (local meters, z up): floor, optional ceiling, four walls (N/S along x, E/W along y)."""
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
    openings = {"N": [], "S": [], "E": [], "W": []}
    for kind in ("doors", "windows"):
        for o in room.get(kind, []):
            o = dict(o)
            if kind == "windows":
                o.setdefault("sill", 0.9)
                o.setdefault("height", 2.0)
            openings[o.get("side", "S").upper()].append(o)
    # S: y = y0, N: y = y0 + d (walls along x, full length incl. corners); W/E: along y between them
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


def build_calls(spec):
    """MCP entity_add arguments (without parent) for a blueprint spec, in world display coordinates."""
    ox, oy, oz = [float(v) for v in spec.get("origin", [0, 0, 0])]
    yaw = float(spec.get("yaw", 0))
    rng = random.Random(spec.get("seed", 1))
    defaults = spec.get("defaults", {})
    calls = []

    def place(lx, ly, lz):
        rx, ry = _rot(lx, ly, yaw)
        return [round(ox + rx, 4), round(oy + ry, 4), round(oz + lz, 4)]

    for room in spec.get("rooms", []):
        for p in room_parts(room, defaults):
            sx, sy, sz = p["size"]
            # box parameters are the entity's own axes: width = x (east), depth = y (north), height = z (up)
            calls.append({"type": "shape", "name": p["name"], "position": place(*p["center"]), "rotation": [0, 0, yaw],
                          "shape": {"kind": "box", "width": round(sx, 4), "depth": round(sy, 4), "height": round(sz, 4),
                                    "color": p["color"]}})
    for i, s in enumerate(spec.get("shapes", [])):
        args = {"type": "shape", "name": s.get("name", "shape%d" % i), "position": place(*s["position"]),
                "rotation": [s.get("rotation", [0, 0, 0])[0], s.get("rotation", [0, 0, 0])[1],
                             s.get("rotation", [0, 0, 0])[2] + yaw], "shape": s["shape"]}
        if "scale" in s:
            args["scale"] = s["scale"]
        calls.append(args)
    for i, pc in enumerate(spec.get("pieces", [])):
        rot = pc.get("rotation", [0, 0, 0])
        args = {"type": pc.get("type", "actor" if pc["asset"].endswith(".ncactor") else "model"), "asset": pc["asset"],
                "name": pc.get("name", "%s_%d" % (os.path.splitext(os.path.basename(pc["asset"]))[0], i)),
                "position": place(*pc.get("position", [0, 0, 0])), "rotation": [rot[0], rot[1], rot[2] + yaw]}
        for k in ("scale", "properties"):
            if k in pc:
                args[k] = pc[k]
        calls.append(args)
    for si, sc in enumerate(spec.get("scatter", [])):
        assets = sc["assets"] if "assets" in sc else [sc["asset"]]
        smin, smax = sc.get("scale", [1, 1])
        for j, (px, py) in enumerate(scatter_points(sc, rng)):
            asset = assets[rng.randrange(len(assets))]
            k = rng.uniform(float(smin), float(smax))
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
    return calls


def cmd_build(a, ed):
    spec = json.load(open(a.spec, encoding="utf-8"))
    name = spec.get("name") or os.path.splitext(os.path.basename(a.spec))[0]
    folder_name = "BP_" + name
    calls = build_calls(spec)
    if a.dry_run:
        emit({"name": name, "calls": len(calls), "entity_add": calls[:a.show]})
        return
    removed = 0
    old = ed.call("scene_list", {"type": "folder", "name_contains": folder_name}).get("entities", [])
    old_ids = [e["id"] for e in old if e["name"] == folder_name]
    if old_ids:
        ed.call("entity_remove", {"ids": old_ids})
        removed = len(old_ids)
    folder = ed.call("entity_add", {"type": "folder", "name": folder_name})
    fid = folder["id"]
    for c in calls:
        c["parent"] = fid
    results = ed.batch([("entity_add", c) for c in calls])
    failed = [{"name": calls[i]["name"], "error": v} for i, (ok, v) in enumerate(results) if not ok]
    roles = {}
    for c in calls:
        roles[c["type"]] = roles.get(c["type"], 0) + 1
    report = {"status": "PASS" if not failed else "FAIL", "name": name, "folder": fid, "rebuilt": bool(removed),
              "entities": len(calls) - len(failed), "byType": roles, "failed": failed[:20]}
    if a.save:
        report["saved"] = ed.call("save_scene", {"path": a.save} if a.save != "current" else {}).get("saved")
    out = a.out or os.path.join(project_dir(a, ed), "docs", "lint", "build-%s.json" % name)
    write_json(out, report)
    report["report"] = out
    emit(report)
    if failed:
        sys.exit(1)


# --- lint ---------------------------------------------------------------------------------------------------------------
SOLID = {"model", "actor", "shape", "terrain", "water", "instances", "merged"}


def cmd_lint(a, ed):
    listing = ed.call("scene_list").get("entities", [])
    ids = [e["id"] for e in listing if e["type"] in SOLID or e["type"] in ("player start", "light")]
    full = {}
    for ok, v in ed.batch([("entity_get", {"id": i}) for i in ids]):
        if ok:
            full[v["id"]] = v
    ents = [full.get(e["id"], e) for e in listing]
    issues = {"belowKillZ": [], "duplicates": [], "floating": [], "underground": [], "primitives": [],
              "missingAsset": [], "logErrors": []}
    warnings = {}
    has_terrain = any(e["type"] == "terrain" for e in ents)
    solids = [e for e in ents if e["type"] in SOLID and e.get("world_bounds") and e.get("effectively_visible", True)]
    seen = {}
    for e in solids:
        b = e["world_bounds"]
        if b["min"][2] < a.kill_z:
            issues["belowKillZ"].append(e["name"])
        key = (e["type"], e.get("source", ""), tuple(round(v, 2) for v in e["position"]),
               json.dumps(e.get("shape", {}).get("params")) if e["type"] == "shape" else "")
        if key in seen:
            issues["duplicates"].append(e["name"])
        seen[key] = e["name"]
        if e["type"] == "shape" and a.no_primitives:
            issues["primitives"].append(e["name"])
        warn = (e.get("audio_emitter") or {}).get("warning") or ""
        if "not found" in warn.lower():
            issues["missingAsset"].append(e["name"])
    if a.ground is not None or not has_terrain:
        ground = a.ground if a.ground is not None else 0.0
        movable = [e for e in solids if e["type"] in ("model", "actor")]
        for e in movable:
            lo, hi = e["world_bounds"]["min"], e["world_bounds"]["max"]
            if e["name"] in a.ignore:
                continue
            if hi[2] < ground - a.tol:
                issues["underground"].append(e["name"])
                continue
            cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
            support = ground if lo[2] >= ground - a.tol else None
            for s in solids:
                if s is e:
                    continue
                sl, sh = s["world_bounds"]["min"], s["world_bounds"]["max"]
                if sl[0] <= cx <= sh[0] and sl[1] <= cy <= sh[1] and sh[2] <= lo[2] + a.tol:
                    support = sh[2] if support is None else max(support, sh[2])
            if support is not None and lo[2] - support > a.tol:
                issues["floating"].append({"name": e["name"], "gap": round(lo[2] - support, 3)})
    else:
        warnings["floating"] = "terrain present: floating/underground need --ground or a Play raycast check"
    starts = [e for e in ents if e["type"] == "player start"]
    for s in starts:
        w = (s.get("player_start") or {}).get("warning")
        if w:
            warnings.setdefault("playerStart", []).append({"name": s["name"], "warning": w})
    if not starts and not a.no_player_start:
        warnings["noPlayerStart"] = True
    log = ed.call("read_log", {"level": "error", "limit": 50, **({"since_index": a.since} if a.since is not None else {})})
    issues["logErrors"] = [l.get("text", "")[:160] for l in log.get("lines", log.get("entries", []))][:10]
    counts = {k: len(v) for k, v in issues.items()}
    report = {"issues": sum(counts.values()), **counts, "entities": len(ents), "checked": len(solids),
              "details": {k: v for k, v in issues.items() if v}, "warnings": warnings,
              "logNextIndex": log.get("next_index")}
    if a.write:
        write_json(a.write, report)
    emit(report)
    if report["issues"] and a.strict:
        sys.exit(1)


# --- screenshots, play, log, save ---------------------------------------------------------------------------------------
def capture(ed, out, width, target="viewport", wait=20.0):
    deadline = time.time() + wait
    while True:
        try:
            res = ed.call("capture_viewport", {"target": target, "max_width": width}, raw=True)
            break
        except McpError as e:
            # right after start (or a document switch) the viewport has not been drawn yet
            if "not visible" not in str(e) or time.time() > deadline:
                raise
            time.sleep(0.5)
    for c in res.get("content", []):
        if c.get("type") == "image":
            data = base64.b64decode(c["data"])
            os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
            open(out, "wb").write(data)
            w, h = (int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")) if data[:8] == b"\x89PNG\r\n\x1a\n" else (0, 0)
            return {"png": out, "w": w, "h": h, "bytes": len(data)}
    raise McpError("no image in the reply")


def vec(text):
    return [float(v) for v in text.split(",")]


def cmd_shot(a, ed):
    if a.pos or a.mode:
        args = {}
        if a.pos:
            args["position"] = vec(a.pos)
            args["target"] = vec(a.target) if a.target else [0, 0, 0]
        if a.mode:
            args["view_mode"] = a.mode
        ed.call("viewport_camera", args)
    emit(capture(ed, a.out, a.width, a.target_kind))


def cmd_play_test(a, ed):
    before = ed.call("read_log", {"limit": 1}).get("next_index")
    ed.call("play_control", {"action": "start"})
    t0 = time.time()
    shots = []
    stop_on = a.until or ("GDS-TEST DONE" if a.expect and a.expect.startswith("GDS-TEST") else a.expect)
    try:
        while time.time() - t0 < a.seconds:
            time.sleep(min(0.5, a.seconds))
            if stop_on and before is not None and time.time() - t0 > a.min_seconds:
                seen = ed.call("read_log", {"since_index": before, "contains": stop_on, "limit": 5}).get("lines", [])
                if seen:
                    break
        if a.shot:
            shots.append(capture(ed, a.shot, a.width))
        state = ed.call("editor_state").get("play_state")
    finally:
        ed.call("play_control", {"action": "stop"})
    log = ed.call("read_log", {"since_index": before, "limit": 1000, **({"contains": a.grep} if a.grep else {})}) \
        if before is not None else {"lines": []}
    if a.verbose:
        print(json.dumps(log)[:4000], file=sys.stderr)
    lines = log.get("lines", log.get("entries", []))
    errors = [l.get("text", "")[:200] for l in lines if l.get("level") == "error"]
    out = {"status": "PASS" if not errors and (not a.expect or any(a.expect in l.get("text", "") for l in lines)) else "FAIL",
           "seconds": round(time.time() - t0, 1), "playState": state, "errors": errors[:15], "lines": len(lines), "shots": shots}
    if a.expect:
        out["expect"] = {a.expect: any(a.expect in l.get("text", "") for l in lines)}
    emit(out)
    if out["status"] != "PASS":
        sys.exit(1)


def cmd_log(a, ed):
    args = {"level": a.level, "limit": a.limit}
    if a.since is not None:
        args["since_index"] = a.since
    if a.contains:
        args["contains"] = a.contains
    res = ed.call("read_log", args)
    lines = res.get("lines", res.get("entries", []))
    emit({"next_index": res.get("next_index"), "lines": [{"i": l.get("index"), "l": l.get("level", "")[:1],
                                                          "t": l.get("text", "")[:300]} for l in lines]})


def cmd_save(a, ed):
    emit(ed.call("save_scene", {"path": a.path} if a.path else {}))


# --- lock (no editor needed) --------------------------------------------------------------------------------------------
def cmd_lock(a):
    proj = os.path.abspath(a.project or os.getcwd())
    path = os.path.join(proj, "Saved", "gds-nucleon.lock")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if a.action == "release":
        try:
            held = json.load(open(path))
            if held.get("owner") != a.owner and not a.force:
                emit({"released": False, "heldBy": held.get("owner")})
                sys.exit(1)
            os.remove(path)
        except (OSError, ValueError):
            pass
        emit({"released": True})
        return
    deadline = time.time() + a.wait
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, json.dumps({"owner": a.owner, "since": time.time()}).encode())
            os.close(fd)
            emit({"locked": True, "owner": a.owner})
            return
        except FileExistsError:
            try:
                held = json.load(open(path))
            except (OSError, ValueError):
                held = {"since": 0}
            if held.get("owner") == a.owner:
                emit({"locked": True, "owner": a.owner, "reentrant": True})
                return
            if time.time() - held.get("since", 0) > 600:
                try:
                    os.remove(path)
                except OSError:
                    pass
                continue
            if time.time() > deadline:
                emit({"locked": False, "heldBy": held.get("owner"), "age": round(time.time() - held.get("since", 0))})
                sys.exit(1)
            time.sleep(2)


# --- headless editor commands (no MCP) ------------------------------------------------------------------------------------
def find_exe(a):
    exe = a.exe or os.environ.get("NUCLEON_EDITOR")
    if not exe:
        cfg = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
        try:
            exe = json.load(open(cfg, encoding="utf-8")).get("paths", {}).get("nucleon", "")
        except (OSError, ValueError):
            exe = ""
    if exe and os.path.isdir(exe):
        for cand in ("NucleonEditor.exe", "NucleonEditor", os.path.join("bin", "NucleonEditor")):
            if os.path.isfile(os.path.join(exe, cand)):
                exe = os.path.join(exe, cand)
                break
    if not exe or not os.path.isfile(exe):
        raise McpError("NucleonEditor not found: --exe, NUCLEON_EDITOR or config.json paths.nucleon")
    return exe


def cmd_exe(a):
    exe = find_exe(a)
    env = dict(os.environ)
    if a.what == "compile-blueprints":
        argv = [exe, "-compile-blueprints", a.target]
    elif a.what == "package":
        argv = [exe, "-package", a.target, "-out", a.out or os.path.join(a.target, "Packaged")] + \
               (["-config", a.config] if a.config else []) + (["-platform", a.platform] if a.platform else [])
    elif a.what == "run-lua":
        argv = [exe, "-run-lua", a.script, a.target]
    elif a.what == "migrate":
        argv = [exe, "-migrate", a.target] + (["--dry-run"] if a.dry_run else [])
    elif a.what == "new-project":
        env["NC_EDITOR_NEW_PROJECT"] = "%s:%s" % (a.template, os.path.abspath(a.target))
        argv = [exe]
    else:
        raise McpError("unknown exe command")
    t0 = time.time()
    p = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=a.timeout)
    tail = (p.stdout + p.stderr).strip().splitlines()
    errors = [l for l in tail if l.lower().startswith(("error", "[error]")) or " error" in l.lower()[:20]]
    emit({"ok": p.returncode == 0, "code": p.returncode, "seconds": round(time.time() - t0, 1), "errors": errors[:15], "tail": tail[-a.tail:]})
    if p.returncode:
        sys.exit(p.returncode)


def cmd_setup(a):
    """GDS files into a Nucleon project: test harness, example spec, skill folders, .gitignore lines."""
    import shutil
    proj = os.path.abspath(a.target)
    if not any(f.endswith(".ncproject") for f in os.listdir(proj)):
        raise McpError("%s has no .ncproject" % proj)
    skill = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tpl = os.path.join(skill, "templates", "nucleon")
    copied = []
    for src_rel, dst_rel in (("Content/Scripts/gds_test.lua", "Content/Scripts/gds_test.lua"),
                             ("Content/Scripts/test_move.lua", "Content/Scripts/test_move.lua"),
                             ("specs/house_example.json", "art/blueprints/_example.json")):
        dst = os.path.join(proj, dst_rel)
        if os.path.exists(dst) and not a.force:
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(tpl, src_rel), dst)
        copied.append(dst_rel)
    for d in ("art/blueprints", "art/world", "art/exports", "art/cc0", "ui", "screenshots", "captures", "docs/gates",
              "docs/lint", "docs/progress", "docs/tests", "docs/screens"):
        os.makedirs(os.path.join(proj, d), exist_ok=True)
    gi = os.path.join(proj, ".gitignore")
    lines = open(gi, encoding="utf-8").read().splitlines() if os.path.exists(gi) else []
    added = [l for l in ("Saved/", "Intermediate/", "Packaged/", "Binaries/", "art/cc0/**/*.zip") if l not in lines]
    if added:
        with open(gi, "a", encoding="utf-8") as f:
            f.write(("\n" if lines and lines[-1] else "") + "\n".join(added) + "\n")
    emit({"ok": True, "project": proj, "copied": copied, "gitignore": added})


def cmd_mcp_config(a):
    proj = os.path.abspath(a.project or os.getcwd())
    try:
        exe = find_exe(a)
    except McpError:
        exe = "<path to NucleonEditor>"
    s = read_settings()
    emit({"stdio": 'claude mcp add nucleon -- "%s" --mcp-stdio "%s"' % (exe, proj),
          "http": 'claude mcp add --transport http nucleon http://127.0.0.1:%s/mcp --header "Authorization: Bearer %s"'
                  % (s.get("port", 47420), s.get("token", "<token from Editor Preferences > AI>")),
          "note": "workers use ncli (no schemas in context); register the MCP only for interactive sessions"})


# ----------------------------------------------------------------------------------------------------------- main
def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--project", help="project folder (lock, reports, --stdio)")
    p.add_argument("--port", type=int)
    p.add_argument("--token")
    p.add_argument("--stdio", metavar="EXE", help="start EXE --mcp-stdio PROJECT for this command")
    p.add_argument("--no-lua", action="store_true", help="with --stdio: --mcp-no-lua")
    p.add_argument("--exe", help="NucleonEditor for exe/mcp-config")
    p.add_argument("--timeout", type=float, default=120)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping")
    sub.add_parser("state")
    c = sub.add_parser("call")
    c.add_argument("tool")
    c.add_argument("args", nargs="?")
    c.add_argument("--raw", action="store_true")
    c = sub.add_parser("batch")
    c.add_argument("file")
    c.add_argument("--full", action="store_true")
    c = sub.add_parser("build")
    c.add_argument("spec")
    c.add_argument("--dry-run", action="store_true")
    c.add_argument("--show", type=int, default=5)
    c.add_argument("--save", help="save after the build: a level path, or 'current'")
    c.add_argument("--out")
    c = sub.add_parser("lint")
    c.add_argument("--write")
    c.add_argument("--ground", type=float, help="ground height (z) when there is no terrain or to force the check")
    c.add_argument("--tol", type=float, default=0.05)
    c.add_argument("--kill-z", type=float, default=-100)
    c.add_argument("--no-primitives", action="store_true", help="visible shapes count as issues (after greybox)")
    c.add_argument("--no-player-start", action="store_true", help="no Player Start is fine (pawn placed by hand)")
    c.add_argument("--ignore", nargs="*", default=[])
    c.add_argument("--since", type=int, help="log errors only from this index")
    c.add_argument("--strict", action="store_true", help="exit 1 when issues > 0")
    c = sub.add_parser("shot")
    c.add_argument("out")
    c.add_argument("--pos", help="camera x,y,z")
    c.add_argument("--target", help="look at x,y,z")
    c.add_argument("--mode", help="view mode (lit, unlit, wireframe, ...)")
    c.add_argument("--width", type=int, default=1280)
    c.add_argument("--window", dest="target_kind", action="store_const", const="window", default="viewport")
    c = sub.add_parser("play-test")
    c.add_argument("--seconds", type=float, default=5, help="maximum seconds of Play")
    c.add_argument("--shot")
    c.add_argument("--width", type=int, default=1280)
    c.add_argument("--expect", help="a log line text that must appear (e.g. 'GDS-TEST PASS')")
    c.add_argument("--grep", help="only log lines containing this")
    c.add_argument("--verbose", action="store_true")
    c.add_argument("--until", help="stop as soon as a log line contains this (default: GDS-TEST DONE when --expect is a GDS-TEST line)")
    c.add_argument("--min-seconds", type=float, default=0)
    c = sub.add_parser("log")
    c.add_argument("--level", default="error")
    c.add_argument("--since", type=int)
    c.add_argument("--limit", type=int, default=50)
    c.add_argument("--contains")
    c = sub.add_parser("save")
    c.add_argument("path", nargs="?")
    c = sub.add_parser("lock")
    c.add_argument("action", choices=["acquire", "release"])
    c.add_argument("--owner", required=True)
    c.add_argument("--wait", type=float, default=600)
    c.add_argument("--force", action="store_true")
    c = sub.add_parser("exe")
    c.add_argument("what", choices=["compile-blueprints", "package", "run-lua", "migrate", "new-project"])
    c.add_argument("target", help="project folder (new-project: the new folder)")
    c.add_argument("--script")
    c.add_argument("--out")
    c.add_argument("--config")
    c.add_argument("--platform")
    c.add_argument("--template", default="third-person")
    c.add_argument("--dry-run", action="store_true")
    c.add_argument("--tail", type=int, default=8)
    c = sub.add_parser("setup", help="copy the GDS test harness, example spec and folders into a Nucleon project")
    c.add_argument("target")
    c.add_argument("--force", action="store_true")
    sub.add_parser("mcp-config")
    a = p.parse_args()
    try:
        if a.cmd == "lock":
            return cmd_lock(a)
        if a.cmd == "exe":
            a.timeout = max(a.timeout, 1800)
            return cmd_exe(a)
        if a.cmd == "setup":
            return cmd_setup(a)
        if a.cmd == "mcp-config":
            return cmd_mcp_config(a)
        if a.cmd == "build" and a.dry_run:
            return cmd_build(a, None)
        ed = connect(a)
        try:
            globals()["cmd_" + a.cmd.replace("-", "_")](a, ed)
        finally:
            ed.client.close()
    except McpError as e:
        emit({"ok": False, "error": str(e)})
        sys.exit(2)


if __name__ == "__main__":
    main()
