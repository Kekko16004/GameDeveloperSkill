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
  build SPEC.json         GDS blueprint for Nucleon (box or kit rooms with door/window openings, pieces by asset or kit role,
                          seeded scatter, shapes, lights, player start) under folder BP_<name>; rebuild in place; skipped
                          when spec + catalog + builder are unchanged (--force); writes docs/lint/build-<name>.json
  cycle SPEC.json --owner lock -> build -> lint -> framed shot -> save -> unlock, one JSON line (the level-build task)
  lint [--play]           scene checks -> {"issues": N, ...}; --play measures the real ground in Play (Raycast)
  shot OUT.png            viewport_camera (optional) + capture_viewport, the PNG written to OUT.png
  play-test               Play, wait, capture, collect log errors, Stop
  capture PLAN.json       store / trailer shots and GIF frames in real Play (camera, keys, hidden HUD; rules untouched)
  log                     read_log (errors by default)
  save [PATH]             save_scene
  lock acquire|release    one editor driver at a time (PROJECT/Saved/gds-nucleon.lock, stale after 10 min)
  serve / session-stop    one editor kept open (stdio) and shared by every later ncli call of the project
  affected                the tests to run for what changed since the last checkpoint commit
  tools-check             the editor's MCP tools vs the verified snapshot (warns when the engine changed them)
  lua-check               game Lua vs the engine API: unknown calls (typos), native argument counts, syntax
  api-refresh             rebuild that API snapshot from an engine checkout, with the diff (new/removed/changed natives)
  exe ...                 headless editor: compile-blueprints, package, run-lua, new-project, migrate
  setup PROJECT           GDS test harness + example spec + folders + .gitignore into a Nucleon project
  mcp-config              the `claude mcp add` lines for this project
"""
import argparse
import base64
import glob
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nc_gds  # noqa: E402  (offline half: specs, kit catalog, worlds)

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

    def rpc(self, method, params=None):
        self.next_id += 1
        reply = self.client.post({"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params or {}})
        if not reply or "error" in reply:
            raise McpError((reply or {}).get("error", {}).get("message", "empty reply"))
        return reply["result"]

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
    if not a.port:
        sess = read_session(a.project)
        if sess:   # a persistent `ncli serve` editor for this project wins over the owner's settings
            return Editor(HttpClient(sess["port"], sess["token"], a.timeout))
    s = read_settings()
    port = a.port or s.get("port") or 47420
    token = a.token or os.environ.get("NC_MCP_TOKEN") or s.get("token")
    return Editor(HttpClient(int(port), token, a.timeout))


def session_path(project):
    return os.path.join(os.path.abspath(project or os.getcwd()), "Saved", "ncli-session.json")


def read_session(project):
    try:
        sess = json.load(open(session_path(project), encoding="utf-8"))
    except (OSError, ValueError):
        return None
    try:
        urllib.request.urlopen("http://127.0.0.1:%d/alive" % sess["port"], timeout=2).read()
        return sess
    except (urllib.error.URLError, OSError, KeyError):
        return None


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
def build(ed, a, spec_path):
    """One spec -> entities; returns the report (also written to docs/lint/build-<name>.json)."""
    spec = json.load(open(spec_path, encoding="utf-8"))
    name = spec.get("name") or os.path.splitext(os.path.basename(spec_path))[0]
    folder_name = "BP_" + name
    proj = project_dir(a, ed)
    origin = spec.get("origin", [0, 0, 0])
    if len(origin) == 3 and origin[2] == "ground":   # the height of the flat spot of a generated world under the origin
        z = None
        for lay in glob.glob(os.path.join(proj, "art", "world", "*.layout.json")):
            for f in json.load(open(lay, encoding="utf-8")).get("flats", []):
                if math.hypot(origin[0] - f["x"], origin[1] - f["y"]) <= f["r"]:
                    z = f["z"]
        if z is None:
            raise McpError("origin z 'ground': no flat of art/world/*.layout.json contains (%g, %g)" % (origin[0], origin[1]))
        spec["origin"] = [origin[0], origin[1], z]
    catalog_path = a.catalog or os.path.join(proj, "art", "kit-catalog.json")
    calls, warnings = nc_gds.build_calls(spec, nc_gds.load_catalog(catalog_path))
    out = a.out or os.path.join(proj, "docs", "lint", "build-%s.json" % name)
    key = nc_gds.spec_hash(spec_path, catalog_path)
    old = ed.call("scene_list", {"type": "folder", "name_contains": folder_name}).get("entities", [])
    old_ids = [e["id"] for e in old if e["name"] == folder_name]
    if not a.force and old_ids and os.path.exists(out):
        try:
            prev = json.load(open(out, encoding="utf-8"))
        except ValueError:
            prev = {}
        inside = ed.call("scene_list", {"parent": old_ids[0]}).get("count", 0)
        if prev.get("specHash") == key and prev.get("status") == "PASS" and inside == prev.get("entities"):
            prev["cached"] = True
            return prev
    if old_ids:
        ed.call("entity_remove", {"ids": old_ids})
    fid = ed.call("entity_add", {"type": "folder", "name": folder_name})["id"]
    for c in calls:
        c["parent"] = fid
    results = ed.batch([("entity_add", c) for c in calls])
    failed = [{"name": calls[i]["name"], "error": v} for i, (ok, v) in enumerate(results) if not ok]
    by_type = {}
    for c in calls:
        by_type[c["type"]] = by_type.get(c["type"], 0) + 1
    b = nc_gds.calls_bounds(calls)
    report = {"status": "PASS" if not failed else "FAIL", "name": name, "folder": fid, "rebuilt": bool(old_ids),
              "entities": len(calls) - len(failed), "byType": by_type, "failed": failed[:20], "warnings": warnings,
              "specHash": key, "bounds": {"min": b[0], "max": b[1]} if b else None}
    if a.save:
        report["saved"] = ed.call("save_scene", {"path": a.save} if a.save != "current" else {}).get("saved")
    write_json(out, report)
    report["report"] = out
    return report


def cmd_build(a, ed):
    if a.dry_run:
        spec = json.load(open(a.spec, encoding="utf-8"))
        calls, warnings = nc_gds.build_calls(spec, nc_gds.load_catalog(a.catalog or os.path.join(project_dir(a), "art", "kit-catalog.json")))
        emit({"calls": len(calls), "warnings": warnings, "entity_add": calls[:a.show]})
        return
    report = build(ed, a, a.spec)
    emit(report)
    if report["status"] != "PASS":
        sys.exit(1)


def auto_camera(bounds):
    """A 3/4 view from the south-west that frames the bounds."""
    lo, hi = bounds["min"], bounds["max"]
    cx, cy, cz = [(lo[k] + hi[k]) / 2 for k in range(3)]
    r = max(hi[0] - lo[0], hi[1] - lo[1], 4.0)
    return [cx - 0.75 * r, cy - 1.05 * r, cz + 0.8 * r + 2], [cx, cy, cz]


def cmd_cycle(a, ed):
    """lock -> build (cached) -> lint -> shot -> save -> unlock: the whole loop of a level-build task in one call."""
    owner = a.owner
    lk = lock_acquire(project_dir(a, ed), owner, a.wait)
    if not lk.get("locked"):
        emit({"status": "FAIL", "error": "lock held", **lk})
        sys.exit(1)
    out = {"owner": owner}
    try:
        rep = build(ed, a, a.spec)
        out["build"] = {k: rep.get(k) for k in ("status", "name", "entities", "byType", "cached", "warnings", "failed", "report")}
        lint_args = argparse.Namespace(**{**vars(a), "write": os.path.join(project_dir(a, ed), "docs", "lint", "scene-lint.json")})
        out["lint"] = run_lint(ed, lint_args)
        if rep.get("bounds"):
            pos, tgt = auto_camera(rep["bounds"])
            ed.call("viewport_camera", {"position": pos, "target": tgt})
            shot = a.shot or os.path.join(project_dir(a, ed), "screenshots", "build-%s.png" % rep["name"])
            out["shot"] = capture(ed, shot, a.width)
        out["saved"] = bool(rep.get("saved"))
    finally:
        lock_release(project_dir(a, ed), owner)
    ok = out["build"]["status"] == "PASS" and out["lint"]["issues"] == 0
    out["status"] = "PASS" if ok else "FAIL"
    emit({"status": out.pop("status"), **out})
    if not ok:
        sys.exit(1)


# --- lint ---------------------------------------------------------------------------------------------------------------
SOLID = {"model", "actor", "shape", "landscape", "terrain", "water", "instances", "merged"}
TERRAIN = ("landscape", "terrain")   # the MCP names the type "landscape" (its scene_list filter says "terrain")


PROBE_FILE = os.path.join("Saved", "gds-probe.lua")


def probe_in_play(ed, a, solids):
    """Ground under and around every model/actor measured in Play with Raycast (the real colliders: terrain,
    models, shapes). Needs Content/Scripts/gds_probe.lua (ncli setup). Returns {floating, underground, noGround}."""
    proj = project_dir(a, ed)
    if not os.path.exists(os.path.join(proj, "Content", "Scripts", "gds_probe.lua")):
        raise McpError("lint --play needs Content/Scripts/gds_probe.lua: run ncli setup PROJECT")
    ground_re = re.compile(a.ground_names, re.I)
    ground_ids = [e["id"] for e in solids if e["type"] in TERRAIN or ground_re.search(e["name"])]
    rows = []
    for e in solids:
        if e["type"] not in ("model", "actor", "shape") or e["name"] in a.ignore or e["id"] in ground_ids:
            continue
        lo, hi = e["world_bounds"]["min"], e["world_bounds"]["max"]
        rows.append("{id=%d,name=%s,lo={%r,%r,%r},hi={%r,%r,%r}}" % (e["id"], json.dumps(e["name"]), *lo, *hi))
    path = os.path.join(proj, PROBE_FILE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("return {tol=%r, ground={%s}, items={\n%s\n}}\n" % (a.tol, ",".join(str(i) for i in ground_ids), ",\n".join(rows)))
    before = ed.call("read_log", {"limit": 1}).get("next_index")
    ed.call("play_control", {"action": "start"})
    t0, done = time.time(), None
    try:
        while time.time() - t0 < a.play_timeout:
            time.sleep(0.5)
            hit = ed.call("read_log", {"since_index": before, "contains": "GDS-PROBE DONE", "limit": 2}).get("lines", [])
            if hit:
                done = hit[0]["text"]
                break
    finally:
        ed.call("play_control", {"action": "stop"})
        try:
            os.remove(path)
        except OSError:
            pass
    if not done:
        raise McpError("the probe did not finish in %gs (is gds_probe.lua in Content/Scripts?)" % a.play_timeout)
    out = {"floating": [], "underground": [], "noGround": []}
    for l in ed.call("read_log", {"since_index": before, "contains": "GDS-PROBE ", "limit": 1000}).get("lines", []):
        m = re.match(r"GDS-PROBE (floating|underground|noGround) (\{.*\})$", l.get("text", ""))
        if m:
            out[m.group(1)].append(json.loads(m.group(2)))
    # a base exactly coplanar with the top of what it rests on (stacked props, a wall on a tile) is not floating: the
    # physics ray can not tell the two faces apart, the editor bounds can
    by_name = {e["name"]: e for e in solids}
    kept = []
    for f in out["floating"]:
        e = by_name.get(f["name"])
        if e:
            lo, hi = e["world_bounds"]["min"], e["world_bounds"]["max"]
            cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
            if any(s2 is not e and s2["world_bounds"]["min"][0] <= cx <= s2["world_bounds"]["max"][0]
                   and s2["world_bounds"]["min"][1] <= cy <= s2["world_bounds"]["max"][1]
                   and abs(s2["world_bounds"]["max"][2] - lo[2]) <= a.tol for s2 in solids):
                continue
        kept.append(f)
    out["floating"] = kept
    out["probed"] = len(rows)
    out["groundEntities"] = len(ground_ids)
    return out


def run_lint(ed, a):
    listing = ed.call("scene_list").get("entities", [])
    ids = [e["id"] for e in listing if e["type"] in SOLID or e["type"] in ("player start", "light")]
    full = {}
    for ok, v in ed.batch([("entity_get", {"id": i}) for i in ids]):
        if ok:
            full[v["id"]] = v
    ents = [full.get(e["id"], e) for e in listing]
    issues = {"belowKillZ": [], "duplicates": [], "floating": [], "underground": [], "noGround": [], "primitives": [],
              "missingAsset": [], "logErrors": []}
    warnings = {}
    has_terrain = any(e["type"] in TERRAIN for e in ents)
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
    mode = "play" if a.play else "bounds"
    if a.play:
        pr = probe_in_play(ed, a, solids)
        issues["floating"], issues["underground"] = pr["floating"], pr["underground"]
        if not a.allow_void:   # nothing at all below (off the edge of the ground / terrain): a prop over the void
            issues["noGround"] = pr["noGround"]
        warnings["probed"] = pr["probed"]
    elif a.ground is not None or not has_terrain:
        ground = a.ground if a.ground is not None else 0.0
        for e in [e for e in solids if e["type"] in ("model", "actor")]:
            lo, hi = e["world_bounds"]["min"], e["world_bounds"]["max"]
            if e["name"] in a.ignore:
                continue
            if hi[2] < ground - a.tol:
                issues["underground"].append(e["name"])
                continue
            cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
            support = ground if lo[2] >= ground - a.tol else None
            for s2 in solids:
                if s2 is e:
                    continue
                sl, sh = s2["world_bounds"]["min"], s2["world_bounds"]["max"]
                if sl[0] <= cx <= sh[0] and sl[1] <= cy <= sh[1] and sh[2] <= lo[2] + a.tol:
                    support = sh[2] if support is None else max(support, sh[2])
            if support is not None and lo[2] - support > a.tol:
                issues["floating"].append({"name": e["name"], "gap": round(lo[2] - support, 3)})
    else:
        warnings["floating"] = "terrain present: run lint --play (Raycast on the real colliders)"
    starts = [e for e in ents if e["type"] == "player start"]
    for s2 in starts:
        w = (s2.get("player_start") or {}).get("warning")
        if w:
            warnings.setdefault("playerStart", []).append({"name": s2["name"], "warning": w})
    if not starts and not a.no_player_start:
        warnings["noPlayerStart"] = True
    log = ed.call("read_log", {"level": "error", "limit": 50, **({"since_index": a.since} if a.since is not None else {})})
    issues["logErrors"] = [l.get("text", "")[:160] for l in log.get("lines", [])][:10]
    counts = {k: len(v) for k, v in issues.items()}
    report = {"issues": sum(counts.values()), **counts, "mode": mode, "entities": len(ents), "checked": len(solids),
              "details": {k: v for k, v in issues.items() if v}, "warnings": warnings,
              "logNextIndex": log.get("next_index")}
    if a.write:
        write_json(a.write, report)
    return report


def cmd_lint(a, ed):
    report = run_lint(ed, a)
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
    metrics = {"perf": [], "feel": []}
    for l in ed.call("read_log", {"since_index": before, "contains": "GDS-", "limit": 1000}).get("lines", []) if before is not None else []:
        m = re.match(r"GDS-(PERF|FEEL) (\{.*\})\s*$", l.get("text", ""))
        if m:
            try:
                metrics[m.group(1).lower()].append(json.loads(m.group(2)))
            except ValueError:
                pass
    over = []
    if a.fps and metrics["perf"]:
        budget = 1000.0 / a.fps
        over = [p for p in metrics["perf"] if p.get("p95_ms", 0) > budget]
    out = {"status": "PASS" if not errors and not over and (not a.expect or any(a.expect in l.get("text", "") for l in lines)) else "FAIL",
           "seconds": round(time.time() - t0, 1), "playState": state, "errors": errors[:15], "lines": len(lines), "shots": shots}
    if a.expect:
        out["expect"] = {a.expect: any(a.expect in l.get("text", "") for l in lines)}
    if metrics["perf"]:
        out["perf"] = {"runs": metrics["perf"], **({"budget_ms": round(1000.0 / a.fps, 2), "over": [p["name"] for p in over]} if a.fps else {})}
    if metrics["feel"]:
        out["feel"] = metrics["feel"]
    emit(out)
    if out["status"] != "PASS":
        sys.exit(1)


def to_lua(v):
    """JSON value -> Lua literal (the plans the Play harnesses read with load())."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "nil"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, list):
        return "{" + ", ".join(to_lua(x) for x in v) + "}"
    return "{" + ", ".join("[%s] = %s" % (json.dumps(k), to_lua(x)) for k, x in v.items()) + "}"


def cmd_capture(a, ed):
    """Store / trailer captures from a plan, in real Play (gds_capture.lua): camera moves, key presses, hidden HUD,
    GIF frame sequences; never the game rules. Writes <out>/manifest.json (every file labelled produced: real-play)
    and <name>.gif for frame sequences when Pillow is installed."""
    proj = project_dir(a, ed) if ed else os.path.abspath(a.project or os.getcwd())
    if not a.write_only and not os.path.exists(os.path.join(proj, "Content", "Scripts", "gds_capture.lua")):
        raise McpError("capture needs Content/Scripts/gds_capture.lua: run ncli setup PROJECT")
    plan = json.load(open(a.plan, encoding="utf-8"))
    out = plan.setdefault("out", "captures/%s" % time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(os.path.join(proj, out), exist_ok=True)
    path = os.path.join(proj, "Saved", "gds-capture.lua")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if a.write_only:   # for a packaged build: it reads <game folder>/Saved/gds-capture.lua and uses TakeScreenshot
        target = os.path.join(os.path.abspath(a.write_only), "Saved", "gds-capture.lua")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        open(target, "w", encoding="utf-8").write("return " + to_lua(plan) + "\n")
        emit({"written": target, "shots": len(plan["shots"]), "run": "start the game from its folder; frames go to %s/" % out})
        return
    plan["viaEditor"] = True   # in the editor the game view is captured by MCP, not by TakeScreenshot (whole window)
    open(path, "w", encoding="utf-8").write("return " + to_lua(plan) + "\n")
    before = ed.call("read_log", {"limit": 1}).get("next_index")
    ed.call("play_control", {"action": "start"})
    t0, done, served, cursor = time.time(), None, set(), before
    limit = a.seconds or (max([s.get("at", 0) for s in plan["shots"]] or [0]) + 60)
    try:
        while time.time() - t0 < limit:
            time.sleep(0.25)
            res = ed.call("read_log", {"since_index": cursor, "contains": "GDS-CAPTURE", "limit": 200})
            cursor = res.get("next_index", cursor)
            for l in res.get("lines", []):
                m = re.match(r"GDS-CAPTURE ready (\d+) (\S+)", l.get("text", ""))
                if m and m.group(1) not in served:
                    served.add(m.group(1))
                    try:
                        capture(ed, os.path.join(proj, m.group(2)), a.width)
                        status = "ok"
                    except McpError:
                        status = "failed"
                    open(os.path.join(proj, "Saved", "gds-capture-ack-%s" % m.group(1)), "w").write(status)
                if "GDS-CAPTURE DONE" in l.get("text", ""):
                    done = l["text"]
            if done:
                break
    finally:
        ed.call("play_control", {"action": "stop"})
        try:
            os.remove(path)
        except OSError:
            pass
    files = []
    for l in ed.call("read_log", {"since_index": before, "contains": "GDS-CAPTURE shot", "limit": 1000}).get("lines", []):
        m = re.match(r"GDS-CAPTURE shot (\S+) (\S+) (ok|failed)", l.get("text", ""))
        if m:
            files.append({"shot": m.group(1), "file": m.group(2), "ok": m.group(3) == "ok"})
    by_shot = {s["name"]: s for s in plan["shots"]}
    manifest = {"plan": os.path.relpath(os.path.abspath(a.plan), proj), "date": time.strftime("%Y-%m-%d %H:%M"),
                "files": [{**f, "produced": "real-play", "at": by_shot.get(f["shot"], {}).get("at"),
                           "camera": by_shot.get(f["shot"], {}).get("camera", "player"),
                           "hud": "hidden" if by_shot.get(f["shot"], {}).get("hide") else "visible"} for f in files]}
    gifs = []
    try:
        from PIL import Image   # optional
        for s in plan["shots"]:
            seq = [os.path.join(proj, f["file"]) for f in files if f["shot"] == s["name"] and f["ok"]]
            if len(seq) > 1:
                imgs = [Image.open(x).convert("P", palette=Image.ADAPTIVE) for x in seq]
                g = os.path.join(proj, out, s["name"] + ".gif")
                imgs[0].save(g, save_all=True, append_images=imgs[1:], duration=int(1000 * s.get("interval", 0.08)), loop=0)
                gifs.append(os.path.relpath(g, proj))
    except ImportError:
        if any(s.get("frames", 1) > 1 for s in plan["shots"]):
            manifest["gifNote"] = "Pillow not installed: frames kept; ffmpeg -framerate 12 -i <name>_%03d.png <name>.gif"
    manifest["gifs"] = gifs
    write_json(os.path.join(proj, out, "manifest.json"), manifest)
    ok = done is not None and all(f["ok"] for f in files) and files
    emit({"status": "PASS" if ok else "FAIL", "done": done, "files": len(files), "failed": sum(1 for f in files if not f["ok"]),
          "gifs": gifs, "manifest": os.path.join(out, "manifest.json")})
    if not ok:
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
def lock_path(proj):
    return os.path.join(os.path.abspath(proj), "Saved", "gds-nucleon.lock")


def lock_acquire(proj, owner, wait):
    path = lock_path(proj)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    deadline = time.time() + wait
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, json.dumps({"owner": owner, "since": time.time()}).encode())
            os.close(fd)
            return {"locked": True, "owner": owner}
        except FileExistsError:
            try:
                held = json.load(open(path))
            except (OSError, ValueError):
                held = {"since": 0}
            if held.get("owner") == owner:
                return {"locked": True, "owner": owner, "reentrant": True}
            if time.time() - held.get("since", 0) > 600:
                try:
                    os.remove(path)
                except OSError:
                    pass
                continue
            if time.time() > deadline:
                return {"locked": False, "heldBy": held.get("owner"), "age": round(time.time() - held.get("since", 0))}
            time.sleep(2)


def lock_release(proj, owner, force=False):
    path = lock_path(proj)
    try:
        held = json.load(open(path))
        if held.get("owner") != owner and not force:
            return {"released": False, "heldBy": held.get("owner")}
        os.remove(path)
    except (OSError, ValueError):
        pass
    return {"released": True}


def cmd_lock(a):
    proj = a.project or os.getcwd()
    res = lock_release(proj, a.owner, a.force) if a.action == "release" else lock_acquire(proj, a.owner, a.wait)
    emit(res)
    if not (res.get("locked") or res.get("released")):
        sys.exit(1)


# --- persistent session (one editor kept open for many commands) -----------------------------------------------------
def cmd_serve(a):
    """--stdio EXE --project P serve: starts the editor once and serves its MCP on 127.0.0.1 for every later ncli call
    of this project (they find Saved/ncli-session.json). Saves 5-10 s of editor start per command. Stop: ncli session-stop."""
    import secrets
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    if not a.stdio or not a.project:
        raise McpError("serve needs --stdio <NucleonEditor> and --project")
    if read_session(a.project):
        raise McpError("a session is already running for this project (ncli session-stop)")
    client = StdioClient(a.stdio, a.project, a.timeout, a.no_lua)
    token = secrets.token_hex(16)
    gate = threading.Lock()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code, body=b""):
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self._send(200 if self.path == "/alive" else 404, b"{}")

        def do_POST(self):
            if self.headers.get("Authorization") != "Bearer " + token:
                return self._send(401)
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if self.path == "/shutdown":
                self._send(200, b"{}")
                threading.Thread(target=server.shutdown, daemon=True).start()
                return
            with gate:   # one request at a time on the editor's stdin
                try:
                    reply = client.post(json.loads(body))
                    self._send(200, json.dumps(reply).encode())
                except McpError as e:
                    self._send(502, json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": str(e)}}).encode())

    server = ThreadingHTTPServer(("127.0.0.1", a.serve_port), H)
    port = server.server_address[1]
    write_json(session_path(a.project), {"port": port, "token": token, "pid": os.getpid(), "since": time.time()})
    emit({"serving": True, "port": port, "project": os.path.abspath(a.project)})
    sys.stdout.flush()
    try:
        server.serve_forever()
    finally:
        try:
            os.remove(session_path(a.project))
        except OSError:
            pass
        client.close()


def cmd_session_stop(a):
    sess = read_session(a.project)
    if not sess:
        emit({"stopped": False, "why": "no session"})
        return
    if a.save:
        Editor(HttpClient(sess["port"], sess["token"], a.timeout)).call("save_scene", {})
    req = urllib.request.Request("http://127.0.0.1:%d/shutdown" % sess["port"], data=b"{}", method="POST")
    req.add_header("Authorization", "Bearer " + sess["token"])
    urllib.request.urlopen(req, timeout=10).read()
    emit({"stopped": True, "saved": bool(a.save)})


# --- what changed -> which tests (incremental checkpoints) -------------------------------------------------------------
CORE_GLOBS = ["project.ncproject", "Config/*.lua", "Content/Scripts/gds_test.lua", "Content/Actors/Player*",
              "Content/Levels/*", "Content/Scripts/game.lua"]


def _glob_match(path, pattern):
    import fnmatch
    return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern)


def cmd_affected(a):
    proj = os.path.abspath(a.project or os.getcwd())
    git = lambda *args: subprocess.run(["git", "-C", proj] + list(args), capture_output=True, text=True).stdout
    since = a.since
    if not since:   # the last checkpoint commit, else everything
        since = git("log", "--grep=^checkpoint", "-n", "1", "--format=%H").strip()
    changed = set()
    if since:
        changed |= set(git("diff", "--name-only", since, "--").split())
    changed |= set(git("diff", "--name-only").split()) | set(git("ls-files", "--others", "--exclude-standard").split())
    changed = sorted(c for c in changed if c)
    tests, all_tests = {}, []
    for root, _, files in os.walk(os.path.join(proj, "Content")):
        for f in files:
            if not (f.startswith("test_") and f.endswith(".lua")):
                continue
            path = os.path.relpath(os.path.join(root, f), proj).replace("\\", "/")
            text = open(os.path.join(root, f), encoding="utf-8", errors="replace").read()
            names = re.findall(r"Register\(\s*[\"']([^\"']+)", text)
            covers = [g.strip() for line in re.findall(r"--\s*covers:\s*(.+)", text) for g in line.split(",") if g.strip()]
            if not covers:   # test_door.lua covers Content/**/door*.lua by default
                covers = ["*%s*" % f[5:-4]]
            tests[path] = (names, covers)
            all_tests += names
    run_all = not since or any(_glob_match(c, g) for c in changed for g in CORE_GLOBS)
    pick = set(all_tests) if run_all else set()
    if not run_all:
        for path, (names, covers) in tests.items():
            if path in changed or any(_glob_match(c, g) for c in changed for g in covers):
                pick |= set(names)
    emit({"since": since or None, "changed": changed[:50], "all": run_all, "tests": sorted(pick),
          "env": "NC_GDS_TEST=" + (",".join(sorted(pick)) if pick and not run_all else "1") if pick else None,
          "expect": "GDS-TEST DONE pass=%d fail=0" % len(pick) if pick else None})


# --- the editor's MCP and Lua API against the snapshot this skill was verified with ------------------------------------
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def tool_shapes(tools):
    return {t["name"]: sorted((t.get("inputSchema") or {}).get("properties", {}).keys()) for t in tools}


def cmd_tools_check(a, ed):
    live = tool_shapes(ed.rpc("tools/list").get("tools", []))
    snap_path = os.path.join(DATA, "nucleon-mcp-tools.json")
    if a.update:
        write_json(snap_path, {"version": 1, "serverInfo": "nucleon-editor", "tools": live})
        emit({"updated": snap_path, "tools": len(live)})
        return
    snap = json.load(open(snap_path, encoding="utf-8"))["tools"]
    added = sorted(set(live) - set(snap))
    removed = sorted(set(snap) - set(live))
    changed = {n: {"added": sorted(set(live[n]) - set(snap[n])), "removed": sorted(set(snap[n]) - set(live[n]))}
               for n in set(live) & set(snap) if live[n] != snap[n]}
    same = not (added or removed or changed)
    out = {"same": same, "added": added, "removed": removed, "changed": changed, "tools": len(live)}
    if not same:
        out["action"] = ("ncli still works on the tools it uses (entity_*, scene_list, capture_viewport, play_control, "
                         "read_log, save_scene, viewport_camera); new tools: read their schema with `ncli call` and "
                         "update references/nucleon-loop.md, then `ncli tools-check --update`")
    emit(out)


def cmd_api_refresh(a):
    """Rebuild data/nucleon-api.json from an engine checkout (docs/api/lua/natives.json + nucleon.lua) and say what
    changed: new natives, removed natives, changed argument counts. Registry slips are corrected the same way as in
    the shipped snapshot (a parameter documented as "leave it out" is optional; a trailing ... is optional)."""
    repo = os.path.abspath(a.engine_repo)
    src = json.load(open(os.path.join(repo, "docs", "api", "lua", "natives.json"), encoding="utf-8"))
    nat, fixes = {}, {"optionalByDoc": [], "varargsOptional": []}
    for n in src["natives"]:
        ps = n.get("params", [])
        doc_opt = [bool(p.get("optional") or re.search(r"leave it out|optional|if omitted|can be omitted", p.get("doc", ""), re.I)) for p in ps]
        vararg = bool(ps) and ps[-1].get("name", "").startswith("...")
        req = 0
        for k, p in enumerate(ps):
            if doc_opt[k] or (vararg and k == len(ps) - 1):
                break
            req += 1
        if any(doc_opt[k] and not ps[k].get("optional") for k in range(len(ps))):
            fixes["optionalByDoc"].append(n["name"])
        if vararg and not ps[-1].get("optional"):
            fixes["varargsOptional"].append(n["name"])
        nat[n["name"]] = {"c": n.get("category", ""), "min": req, "max": 99 if vararg else len(ps)}
    lsrc = open(os.path.join(repo, "docs", "api", "lua", "nucleon.lua"), encoding="utf-8").read()
    legacy = sorted(set(re.findall(r"^function ([A-Za-z_]\w*)\b", lsrc, re.M)) | set(re.findall(r"^([A-Z]\w*) = ", lsrc, re.M)))
    rev = subprocess.run(["git", "-C", repo, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    path = os.path.join(DATA, "nucleon-api.json")
    old = json.load(open(path, encoding="utf-8"))["natives"] if os.path.exists(path) else {}
    diff = {"added": sorted(set(nat) - set(old)), "removed": sorted(set(old) - set(nat)),
            "arity": sorted(k for k in set(nat) & set(old) if (nat[k]["min"], nat[k]["max"]) != (old[k]["min"], old[k]["max"]))}
    if not a.dry_run:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "source": "NucleonEngine main@%s docs/api/lua/natives.json + nucleon.lua" % rev,
                       "natives": nat, "legacy": legacy, "registryFixes": fixes}, f, separators=(",", ":"))
    emit({"natives": len(nat), "legacy": len(legacy), "engine": rev, **diff, "registryFixes": fixes, "written": not a.dry_run})


def lua_files(proj):
    for sub in ("Content/Scripts", "Content/Actors"):
        for root, _, files in os.walk(os.path.join(proj, sub)):
            if "Generated" in root.replace("\\", "/").split("/"):
                continue
            for f in files:
                if f.endswith(".lua"):
                    yield os.path.join(root, f)


def cmd_lua_check(a):
    """Static check of the game's Lua against the engine's API, before any Play: unknown PascalCase calls (typos of
    natives), wrong argument counts of natives, and syntax errors if `luac` is on PATH."""
    import shutil
    proj = os.path.abspath(a.project or os.getcwd())
    api = json.load(open(os.path.join(DATA, "nucleon-api.json"), encoding="utf-8"))
    natives, legacy = api["natives"], set(api["legacy"])
    luac = shutil.which("luac5.4") or shutil.which("luac")
    problems, files = [], 0
    for path in lua_files(proj):
        files += 1
        rel = os.path.relpath(path, proj).replace("\\", "/")
        text = open(path, encoding="utf-8", errors="replace").read()
        code = re.sub(r"--\[(=*)\[.*?\]\1\]|--[^\n]*", "", text, flags=re.S)
        code = re.sub(r"\[(=*)\[.*?\]\1\]|\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'", '""', code, flags=re.S)
        defined = set(re.findall(r"(?:local\s+function|function|local)\s+([A-Za-z_][\w]*)", code)) | \
            set(re.findall(r"^\s*([A-Z][\w]*)\s*=", code, re.M)) | set(re.findall(r"function\s+[\w.:]*[.:]([A-Z]\w*)", code))
        for m in re.finditer(r"(?<![\w.:])([A-Z][A-Za-z0-9_]*)\s*\(", code):
            name = m.group(1)
            line = code.count("\n", 0, m.start()) + 1
            if name in natives:
                depth, i, args, cur = 0, m.end(), 0, ""
                while i < len(code):   # count top-level arguments of this call
                    ch = code[i]
                    if ch in "([{":
                        depth += 1
                    elif ch in ")]}":
                        if depth == 0:
                            break
                        depth -= 1
                    elif ch == "," and depth == 0:
                        args += 1
                        cur = ""
                        i += 1
                        continue
                    cur += ch
                    i += 1
                n = args + (1 if (cur.strip() or args) else 0)
                spec = natives[name]
                body = code[m.end():i]
                if re.search(r"\bfunction\b", body):   # an inline function: its own commas are not arguments
                    continue
                if not (spec["min"] <= n <= spec["max"]):
                    problems.append({"file": rel, "line": line, "native": name, "args": n,
                                     "expected": "%d..%d" % (spec["min"], spec["max"]) if spec["max"] < 99 else ">=%d" % spec["min"]})
            elif name not in legacy and name not in defined:
                import difflib
                near = difflib.get_close_matches(name, list(natives), n=1, cutoff=0.75)
                problems.append({"file": rel, "line": line, "unknown": name, **({"did_you_mean": near[0]} if near else {})})
        if luac:
            r = subprocess.run([luac, "-p", path], capture_output=True, text=True)
            if r.returncode:
                problems.append({"file": rel, "syntax": (r.stderr or r.stdout).strip()[:200]})
    out = {"issues": len(problems), "files": files, "luac": bool(luac), "problems": problems[:40], "api": api["source"]}
    if a.write:
        write_json(a.write, out)
    emit(out)
    if problems and a.strict:
        sys.exit(1)


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
    elif a.what == "run-lua":   # exe run-lua SCRIPT PROJECT  (or: exe run-lua PROJECT --script SCRIPT)
        script, proj = (a.target, a.extra) if a.extra else (a.script, a.target)
        argv = [exe, "-run-lua", script, proj]
    elif a.what == "migrate":
        argv = [exe, "-migrate", a.target] + (["--dry-run"] if a.dry_run else [])
    elif a.what == "new-project":
        env["NC_EDITOR_NEW_PROJECT"] = "%s:%s" % (a.template, os.path.abspath(a.target))
        if not a.starter:   # the template's starter shapes are noise in a GDS project (the world replaces them)
            env["NC_EDITOR_NEW_PROJECT_STARTER"] = "0"
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
                             ("Content/Scripts/gds_probe.lua", "Content/Scripts/gds_probe.lua"),
                             ("Content/Scripts/gds_capture.lua", "Content/Scripts/gds_capture.lua"),
                             ("Content/Scripts/gds_telemetry.lua", "Content/Scripts/gds_telemetry.lua"),
                             ("Content/Scripts/test_bug_template.lua", "Tools/gds/test_bug_template.lua"),
                             ("specs/house_example.json", "art/blueprints/_example.json")):
        dst = os.path.join(proj, dst_rel)
        if os.path.exists(dst) and not a.force:
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.exists(os.path.join(tpl, src_rel)):
            continue
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
def lint_args(c):
    c.add_argument("--ground", type=float, help="ground height (z) when there is no terrain or to force the check")
    c.add_argument("--play", action="store_true", help="measure the ground in Play with Raycast (terrain, slopes, stacked props)")
    c.add_argument("--play-timeout", type=float, default=60)
    c.add_argument("--allow-void", action="store_true", help="--play: objects with nothing below are not issues (space, sky islands)")
    c.add_argument("--ground-names", default=r"ground|floor|terrain|landscape|road|path",
                   help="regex: entities that ARE the ground (with every terrain) for --play")
    c.add_argument("--tol", type=float, default=0.05)
    c.add_argument("--kill-z", type=float, default=-100)
    c.add_argument("--no-primitives", action="store_true", help="visible shapes count as issues (after greybox)")
    c.add_argument("--no-player-start", action="store_true", help="no Player Start is fine (pawn placed by hand)")
    c.add_argument("--ignore", nargs="*", default=[])
    c.add_argument("--since", type=int, help="log errors only from this index")
    c.add_argument("--strict", action="store_true", help="exit 1 when issues > 0")


def build_args(c):
    c.add_argument("spec")
    c.add_argument("--catalog", help="kit catalog (default PROJECT/art/kit-catalog.json)")
    c.add_argument("--force", action="store_true", help="rebuild even when the spec, catalog and builder did not change")
    c.add_argument("--save", help="save after the build: a level path, or 'current'")
    c.add_argument("--out")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--project", help="project folder (lock, reports, --stdio, session)")
    p.add_argument("--port", type=int)
    p.add_argument("--token")
    p.add_argument("--stdio", metavar="EXE", help="start EXE --mcp-stdio PROJECT for this command (or for `serve`)")
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
    build_args(c)
    c.add_argument("--dry-run", action="store_true")
    c.add_argument("--show", type=int, default=5)
    c = sub.add_parser("cycle", help="lock, build (cached), lint, framed shot, save, unlock: one call per level task")
    build_args(c)
    lint_args(c)
    c.add_argument("--owner", required=True)
    c.add_argument("--wait", type=float, default=600)
    c.add_argument("--shot")
    c.add_argument("--width", type=int, default=1280)
    c = sub.add_parser("lint")
    c.add_argument("--write")
    lint_args(c)
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
    c.add_argument("--expect", help="a log line text that must appear (e.g. 'GDS-TEST DONE pass=3 fail=0')")
    c.add_argument("--grep", help="only log lines containing this")
    c.add_argument("--verbose", action="store_true")
    c.add_argument("--until", help="stop as soon as a log line contains this (default: GDS-TEST DONE when --expect is a GDS-TEST line)")
    c.add_argument("--min-seconds", type=float, default=0)
    c.add_argument("--fps", type=float, help="frame budget: every GDS-PERF p95 must be under 1000/fps ms (GDD targetFps)")
    c = sub.add_parser("capture", help="store/trailer screenshots and GIF frames from a plan, in real Play")
    c.add_argument("plan")
    c.add_argument("--seconds", type=float, help="maximum Play time (default: last shot + 60 s)")
    c.add_argument("--width", type=int, default=1920, help="viewport capture width (store screenshots: 1920)")
    c.add_argument("--write-only", metavar="GAME_FOLDER", help="only write the plan for a packaged build (store-size shots)")
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
    c = sub.add_parser("serve", help="keep one editor open (--stdio EXE --project P) for every later ncli call")
    c.add_argument("--serve-port", type=int, default=0)
    c = sub.add_parser("session-stop")
    c.add_argument("--save", action="store_true")
    c = sub.add_parser("affected", help="tests to run for what changed since the last checkpoint commit")
    c.add_argument("--since", help="git ref (default: last commit whose message starts with 'checkpoint')")
    c = sub.add_parser("tools-check", help="the editor's MCP tools vs the snapshot this skill was verified with")
    c.add_argument("--update", action="store_true")
    c = sub.add_parser("api-refresh", help="rebuild the Lua API snapshot from an engine checkout")
    c.add_argument("--engine-repo", required=True)
    c.add_argument("--dry-run", action="store_true")
    c = sub.add_parser("lua-check", help="game Lua vs the engine API: unknown calls, native arity, syntax (luac)")
    c.add_argument("--write")
    c.add_argument("--strict", action="store_true")
    c = sub.add_parser("exe")
    c.add_argument("what", choices=["compile-blueprints", "package", "run-lua", "migrate", "new-project"])
    c.add_argument("target", help="project folder (new-project: the new folder; run-lua: the script, then the project)")
    c.add_argument("extra", nargs="?", help="run-lua: the project folder")
    c.add_argument("--script")
    c.add_argument("--out")
    c.add_argument("--config")
    c.add_argument("--platform")
    c.add_argument("--template", default="third-person")
    c.add_argument("--starter", action="store_true", help="new-project: keep the template's starter shapes")
    c.add_argument("--dry-run", action="store_true")
    c.add_argument("--tail", type=int, default=8)
    c = sub.add_parser("setup", help="copy the GDS harnesses, example spec and folders into a Nucleon project")
    c.add_argument("target")
    c.add_argument("--force", action="store_true")
    sub.add_parser("mcp-config")
    a = p.parse_args()
    offline = {"lock": cmd_lock, "setup": cmd_setup, "mcp-config": cmd_mcp_config, "serve": cmd_serve,
               "session-stop": cmd_session_stop, "affected": cmd_affected, "lua-check": cmd_lua_check,
               "api-refresh": cmd_api_refresh}
    try:
        if a.cmd == "exe":
            a.timeout = max(a.timeout, 1800)
            return cmd_exe(a)
        if a.cmd in offline:
            return offline[a.cmd](a)
        if a.cmd == "capture" and a.write_only:
            return cmd_capture(a, None)
        if a.cmd == "build" and a.dry_run:
            return cmd_build(a, None)
        ed = connect(a)
        try:
            globals()["cmd_" + a.cmd.replace("-", "_")](a, ed)
        finally:
            ed.client.close()
    except (McpError, ValueError) as e:
        emit({"ok": False, "error": str(e)})
        sys.exit(2)


if __name__ == "__main__":
    main()
