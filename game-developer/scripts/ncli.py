#!/usr/bin/env python3
"""ncli: the GameDeveloperSkill bridge to the Nucleon editor (its built-in MCP server, docs/editor/MCP.md).

Standard library only. Every command prints ONE compact JSON line (screenshots go to files, never to stdout), so a worker
spends a few hundred tokens per step instead of carrying 52 tool schemas and base64 images in its context.

Transport:
  HTTP (default)   the editor is open with Editor Preferences > AI > Enable Server; port and token are read from
                   editor-settings.lua (NC_EDITOR_PREF_DIR / --pref-dir, or the user folder Nucleon/Editor), or --port/--token.
  --stdio EXE      starts `EXE --mcp-stdio PROJECT` for this one command and closes it at the end. On Windows it runs on a
                   hidden desktop (nc_desktop_run.exe next to the editor; --visible / NCLI_VISIBLE=1 opts out) with
                   NC_UNATTENDED=1, so no window ever appears on the owner's screen. --pref-dir keeps the owner's preferences
                   untouched, --env K=V adds editor environment (NC_GDS_TEST=1, NC_EDITOR_GAME_VIEW=1 ...). Linux CI: xvfb-run.
                   Save with --save, the editor quits unsaved. `serve` keeps one such editor for every later command.

Coordinates: everything here is the editor's display space, Z up, meters, rotation [pitch, roll, yaw] degrees
(docs/engine/COORDINATES.md). `ping` warns when the Up axis preference is Y (then the MCP fields are Y up).

Commands (python ncli.py <command> -h for the options):
  ping | state            editor_state, compact
  call TOOL [JSON|@file]  one MCP tool, prints its structuredContent
                          (entity_modify renames with new_name; name / id only select the entity)
  batch FILE|-            [{"tool": name, "args": {...}}, ...] as ONE JSON-RPC batch (one round trip)
  build SPEC.json         GDS blueprint for Nucleon (box or kit rooms with door/window openings, pieces by asset or kit role,
                          seeded scatter, `instances` groups, shapes, lights, cameras, post volumes, render flags, player start) under folder BP_<name>; rebuild in
                          place; skipped when spec + catalog + builder are unchanged (--force); writes docs/lint/build-<name>.json
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
  tools [NAME]            tools/list of the running editor: fields per tool, or the whole schema of one
  lua-check               game Lua vs the engine API: unknown calls (typos), native argument counts, syntax
  api-refresh             rebuild that API snapshot from an engine checkout (--from-editor: the built editor's own registry), with the diff
  The rest of the editor's MCP tools, one compact line each:
  entities                scene_list (--type --name --parent --count)
  entity get|set|add|rm|select   entity_get / entity_modify / entity_add / entity_remove / scene_select (id or name)
  camera list|add|pilot|stop|shot   Camera entities (a shot looks through the camera, then gives the viewport back)
  post list|add|set       Post Process Volumes (settings, blendable materials)    material domain PATH   material_domain
  assets / import         asset_search / asset_import (--place puts the models in the level)
  commands / command ID   list_commands / run_command (edit.undo, edit.redo, file.save, tools.build_reflection_captures ...)
  input get|set           get_input_mapping / set_input_mapping (Config/Input.lua)
  docs list|switch|open|close   the editor's document tabs (actor, mesh, preferences, project settings)
  play start|stop|pause|resume|step   play_control
  lua CODE|@file          run_lua (ENGINE coordinates, Y up; not undoable)
  profile start|stop|save profile_capture (.ncprof + CPU/GPU means), only when the owner authorizes profiling
  weather get|set|clear|strike   the weather tool: presets, time of day, wind, lightning; scope level (World Settings) | project | live
  destruction ACTION      fracture / info / make-actor / make-cloth-actor; in Play: state, damage, break, set-health, ray, explode, cloth-wind
  memory [memory|load|text]   memory_stats: CPU/GPU memory by tag, video memory budget, load timeline
  resources list|read     MCP resources (editor guide, the Lua modules games load, project text files)
  exe ...                 headless editor: compile-blueprints, package, run-lua, migrate, new-project, hlod, build-gi,
                          optimize-level, upgrade-ddc, raw
  run-game GAME_DIR       run a packaged game (hidden desktop): log, exit code, GDS tests, screenshots
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
import nc_proc  # noqa: E402  (bounded child processes, locks, watchdog)

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


# ------------------------------------------------------------------------------------------------- hidden desktop launcher
LAUNCH = {"visible": False, "launcher": None, "pref_dir": None, "env": []}   # set from the global options in main()


def launch_env():
    """The environment of an editor started by ncli. NC_EDITOR_PREF_DIR keeps the owner's preferences, layouts and recent
    list untouched (--pref-dir); on a hidden desktop NC_UNATTENDED stops the engine from raising or activating its window."""
    env = dict(os.environ)
    if LAUNCH["pref_dir"]:
        env["NC_EDITOR_PREF_DIR"] = os.path.abspath(LAUNCH["pref_dir"])
    for kv in LAUNCH["env"]:
        k, _, v = kv.partition("=")
        env[k] = v
    return env


def launch_argv(exe, args, env=None):
    """argv to start the editor / the runtime. On Windows the engine never opens a window on the desktop the owner works
    on: `nc_desktop_run.exe -- <cmd>` (shipped next to NucleonEditor.exe) runs it on a hidden Win32 desktop and keeps
    stdin / stdout inherited, so --mcp-stdio still works. --launcher "<prefix>" replaces it ("" = none), --visible or
    NCLI_VISIBLE=1 opts out (a visible window, for debugging)."""
    prefix = []
    if LAUNCH["launcher"] is not None:
        prefix = LAUNCH["launcher"].split() if LAUNCH["launcher"] else []
    elif sys.platform.startswith("win") and not LAUNCH["visible"] and not os.environ.get("NCLI_VISIBLE"):
        runner = os.path.join(os.path.dirname(os.path.abspath(exe)), "nc_desktop_run.exe")
        if os.path.isfile(runner):
            prefix = [runner, "--desktop", "ncli-%d" % os.getpid(), "--"]
    if prefix and env is not None:
        env.setdefault("NC_UNATTENDED", "1")
    return prefix + [exe] + list(args)


class StdioClient:
    def __init__(self, exe, project, timeout, no_lua=False):
        env = launch_env()
        args = launch_argv(exe, ["--mcp-stdio"] + (["--mcp-no-lua"] if no_lua else []) + [project], env)
        self.timeout = timeout
        self.log = open(os.devnull, "wb") if not os.environ.get("NCLI_EDITOR_LOG") else open(os.environ["NCLI_EDITOR_LOG"], "wb")
        self.proc = nc_proc.popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log, env=env)
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
            nc_proc.kill_tree(self.proc.pid)   # the launcher AND the editor under it
        nc_proc.CHILDREN.discard(self.proc)


class Editor:
    """tools/call helpers over either client."""

    def __init__(self, client, transport="http"):
        self.client = client
        self.transport = transport   # http (the owner's editor) | session (ncli serve) | stdio (one command)
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


def worker_name(a):
    """Who is running this command: --as, the `--owner` of cycle / lock / locked, or NCLI_WORKER."""
    return getattr(a, "worker", None) or getattr(a, "owner", None) or os.environ.get("NCLI_WORKER") or None


READ_ONLY_CMDS = {"ping", "state", "entities", "log", "tools", "resources", "tools-check", "assets", "commands", "memory"}
READ_ONLY_ACTIONS = {"get", "list", "status"}


def is_read_only(a):
    return a.cmd in READ_ONLY_CMDS or (a.cmd in ("entity", "docs", "camera", "post", "input", "weather") and
                                       getattr(a, "action", None) in READ_ONLY_ACTIONS)


def check_session_access(a, sess):
    """A `serve` session belongs to the worker that started it. Anything that is not a plain read, from another worker (or from
    one with no name), is refused: a play-test on someone else's session once ended with its session-stop closing that session."""
    owner = sess.get("owner")
    if not owner or is_read_only(a):
        return
    if worker_name(a) != owner:
        raise McpError("refused: the serve session of this project belongs to '%s' (you are %s). Do not use it: start your own "
                       "(`ncli --as <you> --project <your copy> --stdio <editor> serve`), wait for its owner to `session-stop`, or ask "
                       "the parent. Name yourself with --as NAME or NCLI_WORKER" % (owner, "'%s'" % worker_name(a) if worker_name(a) else "unnamed"))


def connect(a):
    if a.stdio:
        if not a.project:
            raise McpError("--stdio needs --project")
        return Editor(StdioClient(a.stdio, a.project, a.timeout, a.no_lua), "stdio")
    if not a.port:
        sess = read_session(a.project)
        if sess:   # a persistent `ncli serve` editor for this project wins over the owner's settings
            check_session_access(a, sess)
            return Editor(HttpClient(sess["port"], sess["token"], a.timeout), "session")
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
def flat_under(flats, x, y):
    """The flat spot of a generated world under (x, y): (flat, how) or (None, None).
    A flat with a `lot` rectangle [x, y, w, d] (a blueprint plot) contains exactly its rectangle, corners included (its `r`
    is only the rounded half diagonal); a plain flat is its circle (+1 cm). Among the flats that contain the point the
    lots win (they are the plot the blueprint was made for), then the flat whose centre is nearest relative to its radius:
    never "the last one in the file" (overlapping circles). Nothing contains it: None (the build stops, no guess)."""
    eps = 0.01
    best, best_key = None, None
    for f in flats:
        d = math.hypot(x - f["x"], y - f["y"])
        lot = f.get("lot")
        if lot and len(lot) == 4:
            lx, ly, lw, ld = [float(v) for v in lot]
            inside = lx - eps <= x <= lx + lw + eps and ly - eps <= y <= ly + ld + eps
            key = (0, d / max(f["r"], 1e-6))
        else:
            inside = d <= f["r"] + eps
            key = (1, d / max(f["r"], 1e-6))
        if inside and (best_key is None or key < best_key):
            best, best_key = f, key
    if best is not None:
        return best, "lot" if best_key[0] == 0 else "circle"
    return None, None


def ground_origin(proj, x, y):
    """origin z "ground": the z of the flat spot of art/world/*.layout.json under (x, y), and that flat's id."""
    flats = []
    for lay in sorted(glob.glob(os.path.join(proj, "art", "world", "*.layout.json"))):
        with open(lay, encoding="utf-8") as f:
            flats += json.load(f).get("flats", [])
    f, how = flat_under(flats, x, y)
    if f is None:
        raise McpError("origin z 'ground': no flat of art/world/*.layout.json contains (%g, %g)" % (x, y))
    return f["z"], {"id": f.get("id"), "z": f["z"], "how": how}


def refuse_main_level_save(ed, a):
    """`--save current` from a session / stdio editor writes whatever level that editor opened: the project's main level, with a
    worker's test content in it. Name the level, or say it is meant (--save-main-level)."""
    if getattr(a, "save", None) == "current" and ed.transport in ("stdio", "session") and not getattr(a, "save_main_level", False):
        raise McpError("refused: `--save current` through --stdio / serve writes the project's main level. Give the level path "
                       "(--save Content/Levels/<name>.nclevel) or add --save-main-level if the main level is the target")


def build(ed, a, spec_path):
    """One spec -> entities; returns the report (also written to docs/lint/build-<name>.json)."""
    refuse_main_level_save(ed, a)
    spec = json.load(open(spec_path, encoding="utf-8"))
    name = spec.get("name") or os.path.splitext(os.path.basename(spec_path))[0]
    folder_name = "BP_" + name
    proj = project_dir(a, ed)
    origin = spec.get("origin", [0, 0, 0])
    ground_flat = None
    if len(origin) == 3 and origin[2] == "ground":   # the height of the flat spot of a generated world under the origin
        z, ground_flat = ground_origin(proj, origin[0], origin[1])
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
            prev["report"] = out
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
    if ground_flat:
        report["groundFlat"] = ground_flat
    if a.save:
        report["saved"] = ed.call("save_scene", {"path": a.save} if a.save != "current" else {}).get("saved")
    if old_ids and glob.glob(os.path.join(proj, "art", "materials", "*.map.json")):
        report["warnings"].append("rebuilt in place: the materials / wind that `nc_mat.py assign` put on this folder's models are gone; "
                                  "run `nc_mat.py assign` again (editor closed), or put them in the spec")
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
    reentrant = bool(lk.get("reentrant"))   # a `locked` wrapper (same owner) holds it: it releases, not this call
    out = {"owner": owner}
    if getattr(a, "since", None) is None:   # the lint counts the log errors of THIS cycle, not of earlier work in the session
        a.since = ed.call("read_log", {"limit": 1}).get("next_index")
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
        if not reentrant:
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


def _box(e):
    b = e["world_bounds"]
    return b["min"], b["max"]


def _xy_overlap(alo, ahi, blo, bhi, eps=1e-3):
    return min(ahi[0], bhi[0]) - max(alo[0], blo[0]) > eps and min(ahi[1], bhi[1]) - max(alo[1], blo[1]) > eps


def _rests_on(elo, ehi, slo, shi, tol):
    """e stands on s: the bottom of e is at the top of s (or inside s), their footprints overlap."""
    return slo[2] - tol <= elo[2] <= shi[2] + tol and shi[2] < ehi[2] and _xy_overlap(elo, ehi, slo, shi)


def _hangs_from(elo, ehi, slo, shi, tol):
    """e hangs from s: the top of e is at the bottom of s (or inside s), their footprints overlap (a trolley under its
    beam, washing under the line)."""
    return slo[2] - tol <= ehi[2] <= shi[2] + tol and slo[2] > elo[2] and _xy_overlap(elo, ehi, slo, shi)


def _touches(elo, ehi, slo, shi, tol):
    """e and s touch or interpenetrate on a side: closer than tol on every axis, overlapping in height."""
    gaps = [max(slo[k] - ehi[k], elo[k] - shi[k]) for k in range(3)]
    return max(gaps) <= tol and min(ehi[2], shi[2]) - max(elo[2], slo[2]) > 0.01


class BoxGrid:
    """The boxes of the solids (terrain left out) hashed on a 4 m XY grid: neighbours without an n^2 scan."""
    CELL = 4.0

    def __init__(self, ents):
        self.boxes, self.cells = {}, {}
        for e in ents:
            lo, hi = _box(e)
            self.boxes[e["id"]] = (lo, hi)
            for c in self._cells(lo, hi, 0.0):
                self.cells.setdefault(c, []).append(e["id"])

    def _cells(self, lo, hi, pad):
        k = self.CELL
        x0, x1 = int(math.floor((lo[0] - pad) / k)), int(math.floor((hi[0] + pad) / k))
        y0, y1 = int(math.floor((lo[1] - pad) / k)), int(math.floor((hi[1] + pad) / k))
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                yield (x, y)

    def near(self, i, pad):
        lo, hi = self.boxes[i]
        seen = set()
        for c in self._cells(lo, hi, pad):
            for j in self.cells.get(c, ()):
                if j != i and j not in seen:
                    seen.add(j)
                    yield j


ROOM_NAME = re.compile(r"^(?P<room>.+)_(?P<part>floor(\d+_\d+)?|ceiling|wall[NSEW]\d+|corner\d+)$")


def room_parts_index(proj, ents):
    """{entity id: (room key, role)} for the parts of the GDS rooms: role floor | wall | lintel | ceiling | corner.
    From the blueprint of each BP_<name> folder (art/blueprints/<name>.json, nc_gds.room_parts: a lintel is a wall
    segment that starts above the room floor, i.e. the piece over a door or a window), else by the builder's names
    (<room>_floor, <room>_ceiling, <room>_wall<side><i>, kit <room>_floor<i>_<j> / _corner<k>)."""
    folders = {e["id"]: e["name"][3:] for e in ents if e.get("type") == "folder" and str(e.get("name", "")).startswith("BP_")}
    roles = {}   # (blueprint, entity name) -> (room, role)
    for bp in set(folders.values()):
        try:
            with open(os.path.join(proj, "art", "blueprints", bp + ".json"), encoding="utf-8") as f:
                spec = json.load(f)
        except (OSError, ValueError):
            continue
        defaults = spec.get("defaults", {})
        for room in spec.get("rooms", []):
            if room.get("kit"):
                continue   # kit rooms: by name below
            z0 = float(room.get("z", 0))
            for p in nc_gds.room_parts(room, defaults):
                role = p["role"]
                if role == "wall" and p["center"][2] - p["size"][2] / 2 > z0 + 1e-3:
                    role = "lintel"
                roles[(bp, p["name"])] = (room.get("name", "room"), role)
    out = {}
    for e in ents:
        if e.get("type") not in ("shape", "model", "actor"):
            continue
        bp = folders.get(e.get("parent"))
        hit = roles.get((bp, e["name"])) if bp else None
        if hit is None:
            m = ROOM_NAME.match(str(e["name"]))
            if not m:
                continue
            part = m.group("part")
            role = "floor" if part.startswith("floor") else "ceiling" if part == "ceiling" else \
                "corner" if part.startswith("corner") else "wall"
            hit = (m.group("room"), role)
        out[e["id"]] = ("%s/%s" % (bp or "", hit[0]), hit[1])
    return out


def ground_named(name, ground_re):
    """The name matches the ground regex as a word: at the start, after a separator / digit, or as a CamelCase part
    (`floor_1`, `R1_road_051`, `flatA1_floor`, `MainFloor`, `GroundPlane`), not inside a word (`playground_sandbox`,
    `underground_box`, `footpath` are props)."""
    for m in ground_re.finditer(name):
        k = m.start()
        if k == 0 or not name[k - 1].islower() or name[k].isupper():
            return True
    return False


def ground_level_ids(solids, ground_re, tol, grid=None):
    """(ids, upper): the entities that ARE the ground (every terrain, and the ground-named ones that are at ground
    level) and the names of the ground-named ones that are not. A ground-named slab with another solid standing under
    it (the walls of the storey below, the legs of a deck) is an upper floor, not the ground: the props under it would
    read as "underground". Only non-ground solids count as "standing under": two ground slabs (road strips pitched down
    a slope, a floor on its plinth) overlap in their bounds without being storeys."""
    grid = grid or BoxGrid([e for e in solids if e["type"] not in TERRAIN])
    ids, upper = [e["id"] for e in solids if e["type"] in TERRAIN], []
    named = set(e["id"] for e in solids if e["type"] not in TERRAIN and ground_named(e["name"], ground_re))
    for g in solids:
        if g["id"] not in named:
            continue
        glo, ghi = grid.boxes[g["id"]]
        if any(j not in named and grid.boxes[j][1][2] <= glo[2] + tol and grid.boxes[j][0][2] < glo[2] - 0.3
               and _xy_overlap(glo, ghi, *grid.boxes[j]) for j in grid.near(g["id"], 0.0)):
            upper.append(g["name"])
        else:
            ids.append(g["id"])
    return ids, upper


def settle_floating(solids, floating, flagged, ground_ids, rooms, tol, grid=None):
    """The floating objects the probe found that are held by something, removed. Returns (kept, held).
    Held = connected to the ground through the bounds of the level:
      restsOn   its bottom is at the top of (or inside) a grounded solid whose footprint overlaps its own
                (a roof on posts, a deck on legs, stacked props: the probe's centre ray misses the posts)
      hangsFrom its top is at the bottom of (or inside) a grounded solid above it (a trolley under its beam)
      room      a lintel / ceiling / wall of a GDS room touching a grounded part of the SAME room (the piece over a
                door has nothing under its centre by construction); touching another room or a prop does not hold it
      attached  a room FLOOR touching a grounded solid that is not of its own room (a mezzanine office against the
                hall wall and the walkway), or any non-room piece touching a grounded solid on a side (a sign on a
                post, a flag on a pole)
    Grounded = terrain and ground entities, the probed objects without a problem that stand on nothing (the terrain)
    and, step by step, whatever stands on something grounded: the walls on the floor of a room that floats, and its
    ceiling on those walls, are not grounded, so they hold nothing (the floor is the one reported). `flagged` = every
    id the probe reported (floating, underground, noGround); the underground ones still count as standing."""
    grid = grid or BoxGrid([e for e in solids if e["type"] not in TERRAIN])
    by_id = {e["id"]: e for e in solids}
    cand = {int(f["id"]): f for f in floating if f.get("id") is not None and int(f["id"]) in grid.boxes}
    void = set(int(i) for i in flagged) - set(cand)
    grounded = set(i for i in ground_ids if i in by_id)
    pending = {}   # id -> what it stands on (by the bounds), not grounded yet
    for i, (lo, hi) in grid.boxes.items():
        if i in grounded or i in cand:
            continue
        sup = set(j for j in grid.near(i, tol) if _rests_on(lo, hi, *grid.boxes[j], tol))
        if sup:
            pending[i] = sup
        elif i not in void:
            grounded.add(i)   # on the terrain

    def hold(i):
        lo, hi = grid.boxes[i]
        room = rooms.get(i)
        near = [j for j in grid.near(i, tol) if j in grounded and j not in void]
        for j in near:   # first what it stands on, and its own room
            slo, shi = grid.boxes[j]
            if _rests_on(lo, hi, slo, shi, tol):
                return "restsOn", j
            if room is not None and room[1] != "floor" and rooms.get(j, (None,))[0] == room[0] \
                    and _touches(lo, hi, slo, shi, tol):
                return "room", j
        for j in near:   # then what it hangs from or is fixed to
            slo, shi = grid.boxes[j]
            if _hangs_from(lo, hi, slo, shi, tol):
                return "hangsFrom", j
            if (room is None or (room[1] == "floor" and rooms.get(j, (None,))[0] != room[0])) \
                    and _touches(lo, hi, slo, shi, tol):
                return "attached", j
        return None, None

    held = []
    changed = True
    while changed:
        changed = False
        # the objects the probe found fine: grounded once what they stand on is, or once they hang from / are
        # attached to something grounded (a washing line through its poles, the walls of a room against a building)
        for i in list(pending):
            if pending[i] & grounded or hold(i)[0]:
                del pending[i]
                grounded.add(i)
                changed = True
        for i in list(cand):
            how, by = hold(i)
            if how:
                held.append({"name": by_id[i]["name"], "how": how, "by": by_id[by]["name"]})
                del cand[i]
                grounded.add(i)
                changed = True
    kept = [f for f in floating if f.get("id") is None or int(f["id"]) in cand]
    return kept, held


def probe_in_play(ed, a, solids, ents=None):
    """Ground under and around every model/actor/shape measured in Play with Raycast (the real colliders: terrain,
    models, shapes). Needs Content/Scripts/gds_probe.lua (ncli setup). Returns {floating, underground, noGround}."""
    proj = project_dir(a, ed)
    if not os.path.exists(os.path.join(proj, "Content", "Scripts", "gds_probe.lua")):
        raise McpError("lint --play needs Content/Scripts/gds_probe.lua: run ncli setup PROJECT")
    ground_re = re.compile(a.ground_names, re.I)
    grid = BoxGrid([e for e in solids if e["type"] not in TERRAIN])
    ground_ids, upper = ground_level_ids(solids, ground_re, a.tol, grid)
    gset = set(ground_ids)
    rows, zlo = [], []
    for e in solids:
        lo, hi = _box(e)
        if e["type"] not in TERRAIN:
            zlo.append("[%d]=%r" % (e["id"], lo[2]))
        if e["type"] not in ("model", "actor", "shape") or e["name"] in a.ignore or e["id"] in gset:
            continue
        rows.append("{id=%d,name=%s,lo={%r,%r,%r},hi={%r,%r,%r}}" % (e["id"], json.dumps(e["name"]), *lo, *hi))
    path = os.path.join(proj, PROBE_FILE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("return {tol=%r, ground={%s},\nterrain={%s},\nzlo={%s},\nitems={\n%s\n}}\n"
                % (a.tol, ",".join(str(i) for i in ground_ids),
                   ",".join(str(e["id"]) for e in solids if e["type"] in TERRAIN), ",".join(zlo), ",\n".join(rows)))
    # Engine: the Raycast native fails ("attempt to index a boolean value", natives/world.lua entityOfBody) in a level with an
    # `instances` entity that has a collider (scene.lua sets entity.body = true): the instances stand without colliders for the
    # probe and get their collision back after it (docs/NUCLEON-ENGINE-NOTES.md D1).
    swapped = []
    for e in (ents or solids):
        if e.get("type") == "instances" and e.get("collision") not in (None, "", "none"):
            ed.call("entity_modify", {"id": e["id"], "collision": "none"})
            swapped.append((e["id"], e["collision"]))
    before = ed.call("read_log", {"limit": 1}).get("next_index")
    ed.call("play_control", {"action": "start"})
    t0, done, failed = time.time(), None, None
    try:
        while time.time() - t0 < a.play_timeout:
            time.sleep(0.5)
            hit = ed.call("read_log", {"since_index": before, "contains": "GDS-PROBE DONE", "limit": 2}).get("lines", [])
            if hit:
                done = hit[0]["text"]
                break
            bad = ed.call("read_log", {"since_index": before, "contains": "gds_probe", "level": "error", "limit": 3}).get("lines", [])
            bad = bad or [l for l in ed.call("read_log", {"since_index": before, "contains": "error in a thread", "limit": 3}).get("lines", [])]
            if bad:
                failed = bad[0]["text"][:300]
                break
    finally:
        ed.call("play_control", {"action": "stop"})
        for i, mode in swapped:
            ed.call("entity_modify", {"id": i, "collision": mode})
        try:
            os.remove(path)
        except OSError:
            pass
    if failed:
        raise McpError("the probe script failed in Play: %s" % failed)
    if not done:
        raise McpError("the probe did not finish in %gs (is gds_probe.lua in Content/Scripts?)" % a.play_timeout)
    out = {"floating": [], "underground": [], "noGround": []}
    since = before
    while True:   # paged: a level with many problems prints more lines than one read_log page
        page = ed.call("read_log", {"since_index": since, "contains": "GDS-PROBE ", "limit": 1000})
        lines = page.get("lines", [])
        for l in lines:
            m = re.match(r"GDS-PROBE (floating|underground|noGround) (\{.*\})$", l.get("text", ""))
            if m:
                out[m.group(1)].append(json.loads(m.group(2)))
        nxt = page.get("next_index")
        if len(lines) < 1000 or nxt is None or nxt == since:
            break
        since = nxt
    flagged = [f["id"] for k in out for f in out[k] if f.get("id") is not None]
    rooms = room_parts_index(proj, ents or solids)
    out["floating"], held = settle_floating(solids, out["floating"], flagged, gset, rooms, a.tol, grid)
    names = {e["id"]: e["name"] for e in solids}
    for k in out:
        for f in out[k]:
            f.pop("id", None)
            if isinstance(f.get("on"), (int, float)):   # what the centre ray hit under it, by name
                f["on"] = names.get(int(f["on"]), "terrain" if int(f["on"]) not in names else f["on"])
    out["probed"] = len(rows)
    out["groundEntities"] = len(ground_ids)
    out["upperFloors"] = len(upper)
    out["roomParts"] = len(rooms)
    out["held"] = held
    return out


def run_lint(ed, a):
    listing = ed.call("scene_list").get("entities", [])
    ids = [e["id"] for e in listing if e["type"] in SOLID or e["type"] in ("player start", "light")]
    full = {}
    for ok, v in ed.batch([("entity_get", {"id": i}) for i in ids]):
        if ok:
            full[v["id"]] = v
    ents = [{**e, **full[e["id"]]} if e["id"] in full else e for e in listing]   # keep the listing's parent
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
        pr = probe_in_play(ed, a, solids, ents)
        issues["floating"], issues["underground"] = pr["floating"], pr["underground"]
        if not a.allow_void:   # nothing at all below (off the edge of the ground / terrain): a prop over the void
            issues["noGround"] = pr["noGround"]
        elif pr["noGround"]:
            warnings["noGroundAllowed"] = len(pr["noGround"])
        warnings["probed"] = pr["probed"]
        warnings["groundEntities"] = pr["groundEntities"]
        if pr["upperFloors"]:
            warnings["upperFloors"] = pr["upperFloors"]   # ground-named slabs above other solids: not the ground
        if pr["held"]:   # floating to the centre ray, held by what they rest on / their room / a side contact
            by_how = {}
            for h in pr["held"]:
                by_how[h["how"]] = by_how.get(h["how"], 0) + 1
            warnings["held"] = by_how
            warnings["heldSample"] = pr["held"][:8]
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


def restart_session(a):
    """--fresh: a second Play in one `serve` session can start with input state left by the first (a key held when a test timed
    out). A new editor costs 5-10 s, so it is for the run that is gate evidence. Skipped (with a warning) when the level has
    unsaved changes: they would be lost."""
    sess = read_session(a.project)
    if not sess or not sess.get("stdio"):
        return None
    check_session_access(a, sess)
    try:
        st = Editor(HttpClient(sess["port"], sess["token"], a.timeout)).call("editor_state")
    except McpError:
        return None
    if st.get("unsaved_changes"):
        return "fresh skipped: the level has unsaved changes (save first)"
    cmd_session_stop(argparse.Namespace(project=a.project, save=False, timeout=a.timeout))
    for _ in range(40):
        if not read_session(a.project):
            break
        time.sleep(0.5)
    serve_detached(argparse.Namespace(project=a.project, stdio=sess["stdio"], timeout=a.timeout, no_lua=a.no_lua), sess.get("owner") or worker_name(a))
    return None


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
    lines = log.get("lines", log.get("entries", []))
    proj = project_dir(a, ed)
    log_path = os.path.join(proj, "Saved", "ncli-logs", "play-test-%d.log" % time.time())   # the FULL log, whatever is printed
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join("%s %s" % ((l.get("level") or "?")[:1].upper(), l.get("text", "")) for l in lines) + "\n")
    if a.verbose:
        print("\n".join(l.get("text", "") for l in lines), file=sys.stderr)
    errors = [l.get("text", "")[:400] for l in lines if l.get("level") == "error"]
    metrics = {"perf": [], "feel": []}
    gaps = []
    for l in ed.call("read_log", {"since_index": before, "contains": "GDS-", "limit": 1000}).get("lines", []) if before is not None else []:
        m = re.match(r"GDS-(PERF|FEEL) (\{.*\})\s*$", l.get("text", ""))
        if m:
            try:
                metrics[m.group(1).lower()].append(json.loads(m.group(2)))
            except ValueError:
                pass
        if l.get("text", "").startswith("GDS-GAP"):
            gaps.append(l["text"][8:].strip())
    over = []
    if a.fps and metrics["perf"]:
        budget = 1000.0 / a.fps
        over = [p for p in metrics["perf"] if p.get("p95_ms", 0) > budget]
    out = {"status": "PASS" if not errors and not over and (not a.expect or any(a.expect in l.get("text", "") for l in lines)) else "FAIL",
           "seconds": round(time.time() - t0, 1), "playState": state, "errors": errors[:15], "lines": len(lines), "log": log_path, "shots": shots}
    if gaps:
        out["engine_gap"] = list(dict.fromkeys(gaps))   # data the engine did not give: copy into the gate as `engine_gap:` with the repro
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
    t0, done, served, cursor, errors = time.time(), None, set(), before, []
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
                    except McpError as e:
                        status = "failed"
                        errors.append({"file": m.group(2), "error": str(e)[:200]})
                    ack = os.path.join(proj, "Saved", "gds-capture-ack-%s" % m.group(1))
                    with open(ack + ".tmp", "w") as f:   # atomic: the game polls for the file and must never read it empty
                        f.write(status)
                    os.replace(ack + ".tmp", ack)
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
          "gifs": gifs, "manifest": os.path.join(out, "manifest.json"), **({"errors": errors[:5]} if errors else {})})
    if not ok:
        sys.exit(1)


def cmd_log(a, ed):
    """read_log: level letters i info, w warning, E error, g engine output (the editor's own lines and the engine's prints)."""
    args = {"level": a.level, "limit": a.limit}
    if a.since is not None:
        args["since_index"] = a.since
    if a.contains:
        args["contains"] = a.contains
    if a.category:
        args["category"] = a.category
    res = ed.call("read_log", args)
    lines = res.get("lines", res.get("entries", []))
    emit({"next_index": res.get("next_index"), "lines": [{"i": l.get("index"), "l": {"info": "i", "warning": "w", "error": "E", "engine": "g"}.get(l.get("level", ""), "?"),
                                                          "t": l.get("text", "")[:a.cut] if a.cut else l.get("text", "")} for l in lines]})


def cmd_save(a, ed):
    emit(ed.call("save_scene", {"path": a.path} if a.path else {}))


# --- the rest of the editor's MCP tools, one compact line each -------------------------------------------------------------
def selector(text):
    """An entity id (digits) or an entity name -> the MCP selector."""
    return {"id": int(text)} if re.fullmatch(r"\d+", str(text)) else {"name": str(text)}


def short_entity(e):
    out = {"id": e["id"], "name": e["name"], "type": e["type"], "pos": [round(v, 3) + 0.0 for v in e.get("position", [])]}
    if e.get("parent"):
        out["parent"] = e["parent"]
    if e.get("visible") is False:
        out["hidden"] = True
    return out


SCENE_LIST_TYPES = {"model", "light", "terrain", "actor", "empty", "folder", "shape", "reflection capture", "player start",
                    "audio emitter", "audio volume"}   # the enum of scene_list's `type` (engine notes B2); other types are filtered here


def list_entities(ed, etype=None, **args):
    """scene_list with the type filter done by the editor when its enum knows the type, here (on the `type` of each record) when not
    (camera, post volume, instances, water, ...)."""
    norm = lambda t: str(t).lower().replace("_", " ").replace("-", " ").strip()
    if etype and norm(etype) in SCENE_LIST_TYPES:
        args["type"] = norm(etype)
        return ed.call("scene_list", args)
    res = ed.call("scene_list", args)
    if etype:
        keep = [e for e in res.get("entities", []) if norm(e.get("type", "")) == norm(etype)]
        res = {**res, "entities": keep, "count": len(keep)}
    return res


def cmd_entities(a, ed):
    """scene_list: the entities of the open level, one short record each (id, name, type, position)."""
    args = {k: v for k, v in (("name_contains", a.name), ("parent", a.parent)) if v is not None}
    res = list_entities(ed, a.type, **args)
    ents = res.get("entities", [])
    if a.count:
        by_type = {}
        for e in ents:
            by_type[e["type"]] = by_type.get(e["type"], 0) + 1
        emit({"count": len(ents), "byType": by_type})
        return
    emit({"count": res.get("count", len(ents)), "shown": min(len(ents), a.limit),
          "entities": ents[:a.limit] if a.full else [short_entity(e) for e in ents[:a.limit]]})


def cmd_entity(a, ed):
    """entity_get / entity_modify / entity_add / entity_remove / scene_select with the usual conveniences."""
    if a.action == "get":
        emit(ed.call("entity_get", selector(a.target)))
    elif a.action == "set":
        args = {**load_json_arg(a.json), **selector(a.target)}
        res = ed.call("entity_modify", args)
        emit(res if a.full else {**short_entity(res), **{k: res[k] for k in ("world_bounds", "light") if k in res}})
    elif a.action == "add":
        args = load_json_arg(a.json)
        args["type"] = a.target
        res = ed.call("entity_add", args)
        emit(res if a.full else {**short_entity(res), **{k: res[k] for k in ("world_bounds", "instance_count") if k in res}})
    elif a.action == "rm":
        items = [a.target] + a.more
        ids = [int(t) for t in items if re.fullmatch(r"\d+", t)]
        names = [t for t in items if not re.fullmatch(r"\d+", t)]
        emit(ed.call("entity_remove", {**({"ids": ids} if ids else {}), **({"names": names} if names else {})}))
    elif a.action == "select":
        ids = [int(t) for t in ([a.target] + a.more if a.target else [])]
        emit({"selection": ed.call("scene_select", {"ids": ids})})


def cmd_assets(a, ed):
    """asset_search: project files by fuzzy name, best first."""
    args = {"query": a.query or "", "limit": a.limit}
    if a.type:
        args["type"] = a.type
    res = ed.call("asset_search", args)
    emit({"count": res.get("count"), "assets": [x["path"] if a.paths else {"path": x["path"], "type": x["type"]}
                                                 for x in res.get("assets", [])]})


def cmd_import(a, ed):
    """asset_import: models / textures / sounds from this computer into the project (optionally placed in the level)."""
    args = {"sources": [os.path.abspath(f) for f in a.files], "folder": a.folder}
    if a.place:
        args["place"] = True
    res = ed.call("asset_import", args)
    emit({"imported": res.get("imported"), "placed": [short_entity(e) for e in res.get("placed", [])]})


def cmd_commands(a, ed):
    """list_commands: the command-search commands run_command takes (id, label)."""
    args = {k: v for k, v in (("query", a.query), ("enabled_only", a.enabled or None)) if v}
    res = ed.call("list_commands", args)
    emit({"count": res.get("count"), "commands": [{"id": c["id"], "label": c["label"], **({} if c.get("enabled") else {"off": True})}
                                                   for c in res.get("commands", [])][:a.limit]})


def cmd_command(a, ed):
    """run_command: edit.undo, edit.redo, file.save, edit.focus_selection, add.shape_box, play.play_in_editor, ..."""
    res = ed.call("run_command", {"id": a.id})
    st = res.get("state", {})
    emit({"ran": res.get("ran"), "unsaved": st.get("unsaved_changes"), "play": st.get("play_state"),
          "entities": st.get("entity_count"), "undo": (st.get("undo") or {}).get("next"), "redo": (st.get("redo") or {}).get("next")})


def cmd_input(a, ed):
    """get_input_mapping / set_input_mapping (Config/Input.lua): read as Lua text, replace from a file."""
    if a.action == "get":
        res = ed.call("get_input_mapping")
        if a.out:
            os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
            open(a.out, "w", encoding="utf-8").write(res["lua"])
            emit({"actions": res["actions"], "contexts": res["contexts"], "written": a.out})
        else:
            emit(res)
    else:
        emit(ed.call("set_input_mapping", {"lua": open(a.file, encoding="utf-8").read()}))


def cmd_docs(a, ed):
    """list_documents / switch_document / open_document / close_document: the tabs of the editor."""
    if a.action == "list":
        emit(ed.call("list_documents"))
    elif a.action == "switch":
        emit(ed.call("switch_document", {"document": a.target}))
    elif a.action == "open":
        if a.target not in ("actor", "mesh", "preferences", "project"):
            raise McpError("docs open: actor | mesh | preferences | project")
        emit(ed.call("open_document", {"type": a.target, **({"path": a.path} if a.path else {})}))
    else:
        emit(ed.call("close_document", {"index": int(a.target), **({"discard": True} if a.discard else {})}))


def cmd_camera(a, ed):
    """Camera entities (docs/engine/CAMERA.md): list | add | pilot | stop | shot. `camera shot NAME out.png` looks through the camera,
    writes the viewport PNG and gives the viewport back (the lens of the camera: fov or physical focal length, depth of field, exposure)."""
    if a.action == "list":
        res = list_entities(ed, "camera")
        emit({"count": res.get("count"), "cameras": [short_entity(e) for e in res.get("entities", [])]})
    elif a.action == "add":
        if not a.name:
            raise McpError("camera add NAME --pos x,y,z [--target x,y,z | --rot pitch,roll,yaw] [--fov F | --focal MM] [--dof --fstop F --focus M]")
        pos = vec(a.pos) if a.pos else [0, 0, 2]
        args = {"type": "camera", "name": a.name, "position": pos,
                "rotation": nc_gds.look_rotation(pos, vec(a.target)) if a.target else (vec(a.rot) if a.rot else [0, 0, 0])}
        lens = {}
        if a.fov is not None:
            lens["fov"] = a.fov
        if a.focal is not None:
            lens.update({"physical": True, "focal_length": a.focal})
        if a.dof:
            lens.update({"depth_of_field": True, **({"f_stop": a.fstop} if a.fstop else {}), **({"focus_distance": a.focus} if a.focus else {})})
        if a.default_view:
            lens["default_view"] = True
        if lens:
            args["camera"] = lens
        if a.flags:
            args["render_flags"] = load_json_arg(a.flags)
        res = ed.call("entity_add", args)
        emit({**short_entity(res), "camera": ed.call("entity_get", {"id": res["id"]}).get("camera")})
    elif a.action == "pilot":
        emit(ed.call("camera_pilot", selector(a.name) if a.name else {}))
    elif a.action == "stop":
        emit(ed.call("camera_pilot", {"stop": True}))
    elif a.action == "shot":
        if not (a.name and a.out):
            raise McpError("camera shot NAME out.png")
        ed.call("camera_pilot", selector(a.name))
        try:
            shot = capture(ed, a.out, a.width)
        finally:
            ed.call("camera_pilot", {"stop": True})
        emit({"camera": a.name, **shot})


def cmd_post(a, ed):
    """Post Process Volumes (docs/rendering/POSTPROCESS.md): add | set | list. `post add Night --unbound --set bloom=true --blendable Content/Materials/PP_Outline.ncmat:0.8`.
    The settings are Lighting keys (null removes one); a blendable is a Post Process material (`material domain PATH --domain postProcess`)."""
    if a.action == "list":
        res = list_entities(ed, "post process volume")
        emit({"count": res.get("count"), "volumes": [short_entity(e) for e in res.get("entities", [])]})
        return
    pv = {}
    if a.unbound:
        pv["unbound"] = True
    if a.priority is not None:
        pv["priority"] = a.priority
    if a.blend_radius is not None:
        pv["blend_radius"] = a.blend_radius
    if a.weight is not None:
        pv["weight"] = a.weight
    if a.set:
        pv["settings"] = {}
        for kv in a.set:
            k, _, v = kv.partition("=")
            try:
                pv["settings"][k] = json.loads(v)
            except ValueError:
                pv["settings"][k] = v
    if a.blendable:
        bl = []
        for b in a.blendable:
            mat, _, w = b.partition(":")
            bl.append({"material": mat, "weight": float(w) if w else 1.0, "enabled": True})
        pv["blendables"] = bl
    if a.action == "add":
        args = {"type": "post_volume", "name": a.name or "PostVolume", "post_volume": pv}
        if a.pos:
            args["position"] = vec(a.pos)
        if a.size:
            args["scale"] = vec(a.size)
        res = ed.call("entity_add", args)
    else:
        if not a.name:
            raise McpError("post set NAME [--set k=v ...] [--blendable MAT:W ...]")
        res = ed.call("entity_modify", {**selector(a.name), "post_volume": pv})
    emit({**short_entity(res), "post_volume": ed.call("entity_get", {"id": res["id"]}).get("post_volume")})


def cmd_material(a, ed):
    """material_domain: read or set the Material Domain of a .ncmat (surface, decal, lightFunction, postProcess, volume, sky)."""
    args = {"path": a.path}
    for k, v in (("domain", a.domain), ("post_location", a.post_location), ("decal_blend", a.decal_blend), ("sky_blend", a.sky_blend)):
        if v:
            args[k] = v
    emit(ed.call("material_domain", args))


def kv_pairs(items):
    """`k=v` options -> a dict (JSON values: 0.5, true, "x"; anything else stays a string)."""
    out = {}
    for kv in items or []:
        k, _, v = kv.partition("=")
        try:
            out[k] = json.loads(v)
        except ValueError:
            out[k] = v
    return out


def cmd_weather(a, ed):
    """weather (docs/rendering/WEATHER.md): get | set | clear | strike. `weather set --preset Storm --time 19.5 --wind-heading 90 --wind-speed 12`
    writes into the level's World Settings (scope level, the default; marks the level dirty, `save` keeps it), the project (--scope project, saved at
    once) or the running game (--scope live, --blend seconds). Natives for scripts: SetWeather, SetTimeOfDay, SetWind, TriggerLightning ..."""
    args = {"action": a.action}
    if a.scope:
        args["scope"] = a.scope
    for k, v in (("preset", a.preset), ("blend", a.blend), ("time_of_day", a.time), ("latitude", a.latitude), ("day_length", a.day_length),
                 ("wind_heading", a.wind_heading), ("wind_speed", a.wind_speed), ("gustiness", a.gustiness),
                 ("precipitation", a.precipitation), ("surfaces", a.surfaces), ("lens_drops", a.lens_drops), ("thunder", a.thunder),
                 ("intensity", a.intensity)):
        if v is not None:
            args[k] = v
    if a.param:
        args["params"] = kv_pairs(a.param)
    res = ed.call("weather", args)
    if not a.full and isinstance(res, dict) and isinstance(res.get("live"), dict):   # short form: the blended values stay behind --full
        live = res["live"]
        res = {"level": res.get("level"), "projectKeys": sorted(res.get("project") or {}),
               "live": {k: live[k] for k in ("active", "preset", "progress", "time_of_day", "wind_heading", "describe") if k in live}}
    emit(res)


def cmd_destruction(a, ed):
    """destruction (docs/engine/PHYSICS.md "Destruction" and "Soft bodies and cloth"). Without Play: fracture | info | make-actor | make-cloth-actor
    (a .fracture file / an actor asset with a Destructible or Cloth component; place it with `entity add actor`). While Play runs: state | damage |
    break | set-health | ray | explode | cloth-wind. Positions are Z up, meters. `destruction fracture --model Content/Crate.glb --pieces 24`."""
    args = {"action": a.action.replace("-", "_")}
    named = (("model", a.model), ("file", a.file), ("output", a.output), ("path", a.path), ("pieces", a.pieces), ("seed", a.seed),
             ("clusters", a.clusters), ("irregularity", a.irregularity), ("health", a.health), ("impact_threshold", a.impact_threshold),
             ("dynamic", a.dynamic), ("staged", a.staged), ("lifetime", a.lifetime), ("fade", a.fade), ("shape", a.shape),
             ("width", a.width), ("height", a.height), ("radius", a.radius), ("pin", a.pin), ("pressure", a.pressure),
             ("destructible", a.destructible), ("entity", a.entity), ("cloth", a.cloth), ("amount", a.amount),
             ("impulse", a.impulse), ("radius_m", a.radius_m), ("force", a.force), ("drag", a.drag))
    for k, v in named:
        if v is not None:
            args[k] = v
    for k, v in (("color", a.color), ("position", a.position), ("direction", a.direction), ("from", getattr(a, "from")), ("to", a.to)):
        if v:
            args[k] = vec(v)
    if a.wind is not None:   # make-cloth-actor: true / false; cloth-wind: x,y,z m/s (omit: wind off)
        args["wind"] = (a.wind.lower() == "true") if a.wind.lower() in ("true", "false") else vec(a.wind)
    args.update(load_json_arg(a.json))
    emit(ed.call("destruction", args))


def cmd_memory(a, ed):
    """memory_stats (docs/performance/PROFILER.md "Memory by tag"): memory (CPU/GPU tags, video memory budget) | load (load timeline) | text."""
    args = {"action": a.action}
    if a.kind:
        args["kind"] = a.kind
    res = ed.call("memory_stats", args)
    emit(res if a.full or not isinstance(res, dict) else {k: (v[:a.limit] if isinstance(v, list) else v) for k, v in res.items()})


def cmd_play(a, ed):
    """play_control: start | stop | pause | resume | step (one frame while paused)."""
    emit(ed.call("play_control", {"action": a.action}))


def cmd_lua(a, ed):
    """run_lua in the editor's interpreter: ENGINE coordinates (Y up), not undoable, 5 s limit. Prints what the code printed."""
    code = open(a.code[1:], encoding="utf-8").read() if a.code.startswith("@") else a.code
    try:
        res = ed.call("run_lua", {"code": code})
        emit({"ok": res.get("ok", True), "output": [l.get("text", "")[:400] for l in res.get("output", [])]})
    except McpError as e:   # an error in the code: the tool answers isError with {"ok": false, "output": [{level, text}]}
        try:
            body = json.loads(str(e))
            emit({"ok": False, "output": [l.get("text", "")[:400] for l in body.get("output", [])]})
        except ValueError:
            emit({"ok": False, "error": str(e)[:800]})
        sys.exit(1)


def cmd_profile(a, ed):
    """profile_capture: start / stop / save the in-level profiler (a .ncprof under Saved/Profiling + CPU/GPU means, GPU passes)."""
    args = {"action": a.action}
    if a.path:
        args["path"] = a.path
    emit(ed.call("profile_capture", args))


def cmd_resources(a, ed):
    """resources/list and resources/read: the editor guide, the Lua modules games load, the project's text files."""
    if a.action == "list":
        res = ed.rpc("resources/list")
        emit({"resources": [{"uri": r["uri"], "name": r.get("name")} for r in res.get("resources", [])][:a.limit],
              "templates": ed.rpc("resources/templates/list").get("resourceTemplates", [])})
    else:
        res = ed.rpc("resources/read", {"uri": a.uri})
        text = "".join(c.get("text", "") for c in res.get("contents", []))
        if a.out:
            open(a.out, "w", encoding="utf-8").write(text)
            emit({"uri": a.uri, "bytes": len(text), "written": a.out})
        else:
            emit({"uri": a.uri, "text": text[:a.limit * 100]})


def cmd_tools(a, ed):
    """tools/list of the running editor: name, required and optional fields (the long descriptions stay in the editor)."""
    tools = ed.rpc("tools/list").get("tools", [])
    if a.name:
        t = next((t for t in tools if t["name"] == a.name), None)
        if not t:
            raise McpError("no such tool; ncli tools lists them")
        emit(t)
        return
    emit({"count": len(tools), "tools": {t["name"]: {"required": (t.get("inputSchema") or {}).get("required", []),
                                                     "fields": sorted((t.get("inputSchema") or {}).get("properties", {}))}
                                         for t in tools}})


# --- bench: one repeatable measurement of one level (nc_bench.py, tools/nucleon-bench) -------------------------------------
def cmd_bench(a):
    """bench --project P --view x,y,z,tx,ty,tz | --path file.json | --scenes file.json [--fps N] [--baseline F] [--update-baseline]:
    vsync off, a fixed camera or path, p50/p95/p99 of wall / CPU / GPU frame time, Present, draw calls, items, CPU or GPU bound,
    warnings that make the number untrustworthy, and the comparison with a stored baseline. The run takes the GPU + project lock itself."""
    import nc_bench
    if not a.project:
        raise McpError("bench needs --project")
    engine = a.engine or os.path.dirname(find_exe(a))
    a.name = a.name or "level"
    summary = nc_bench.run(a, engine)
    proj = os.path.abspath(a.project)
    out_dir = os.path.join(proj, "docs", "bench")
    base_path = a.baseline or os.path.join(out_dir, "%s.baseline.json" % a.name)
    res = {"name": a.name, "wall_ms": summary["wall_ms"], "cpu_ms": summary["cpu_ms"], "gpu_ms": summary["gpu_ms"],
           "present_ms": summary["present_ms"], "drawCalls": summary["drawCalls"], "bound": summary["bound"], "frames": summary["frames"]}
    verdict = "OK"
    if os.path.exists(base_path):
        cmp = nc_bench.compare(summary, json.load(open(base_path, encoding="utf-8")), a.tolerance)
        summary["compare"] = cmp
        res["compare"] = {"deltaPct": cmp["deltaPct"], "regress": cmp["regress"], "improved": cmp["improved"]}
        if cmp["regress"]:
            verdict = "REGRESSED"
    elif not a.update_baseline:
        summary.setdefault("warnings", []).append("no baseline at %s: this run is the first; pass --update-baseline to store it" % base_path)
    if "budget_ms" in summary:
        res["budget_ms"], res["overBudget"] = summary["budget_ms"], summary["overBudget"]
        if summary["overBudget"]:
            verdict = "OVER_BUDGET"
    untrusted = [w for w in summary["warnings"] if any(k in w for k in ("vsync", "another engine", "software", "frames", "did not finish"))]
    res["trusted"] = not untrusted
    res["warnings"] = summary["warnings"]
    path = os.path.join(out_dir, "%s-%s.json" % (a.name, time.strftime("%Y%m%d-%H%M%S")))
    write_json(path, summary)
    if a.update_baseline:
        write_json(base_path, summary)
        res["baselineWritten"] = base_path
    res["status"] = verdict if res["trusted"] else "UNTRUSTED"
    res["file"] = path
    emit(res)
    if res["status"] in ("REGRESSED", "OVER_BUDGET", "UNTRUSTED"):
        sys.exit(1)


# --- playthrough: the bot plays every bound input; the parent reads the shots (gds_playthrough.lua) -----------------------------
def cmd_playthrough(a, ed):
    """playthrough [--plan extra.json] [--seconds 240]: Play with real input events (templates/nucleon gds_playthrough.lua): every
    bound input of every action, a look, and the extra steps of the plan (the verbs of this game, with a watched value). Writes
    docs/gates/playthrough-NN.md: step / input / result / what changed / frame ms / shot, and the steps it could NOT drive, listed for
    the parent as engine_gap (never skipped). The parent still reads the shots."""
    proj = project_dir(a, ed)
    if not os.path.exists(os.path.join(proj, "Content", "Scripts", "gds_playthrough.lua")):
        raise McpError("run `ncli setup PROJECT --force` first (Content/Scripts/gds_playthrough.lua)")
    extra = json.load(open(a.plan, encoding="utf-8")) if a.plan else {}
    n = 1
    gates = os.path.join(proj, "docs", "gates")
    while os.path.exists(os.path.join(gates, "playthrough-%02d.md" % n)):
        n += 1
    shots_dir = "screenshots/playthrough-%02d" % n
    plan = {"out": shots_dir, "viaEditor": True, "hold": a.hold, "settle": a.settle, "extra": extra.get("steps", extra if isinstance(extra, list) else [])}
    plan_path = os.path.join(proj, "Saved", "gds-playthrough.lua")
    os.makedirs(os.path.dirname(plan_path), exist_ok=True)
    open(plan_path, "w", encoding="utf-8").write("return " + to_lua(plan) + "\n")
    os.makedirs(os.path.join(proj, shots_dir), exist_ok=True)
    before = ed.call("read_log", {"limit": 1}).get("next_index")
    ed.call("play_control", {"action": "start"})
    t0, cursor, served, steps, done, errors = time.time(), before, set(), [], None, []
    try:
        while time.time() - t0 < a.seconds and not done:
            time.sleep(0.25)
            res = ed.call("read_log", {"since_index": cursor, "contains": "GDS-", "limit": 300})
            cursor = res.get("next_index", cursor)
            for l in res.get("lines", []):
                text = l.get("text", "")
                m = re.match(r"GDS-CAPTURE ready (\d+) (\S+)", text)
                if m and m.group(1) not in served:
                    served.add(m.group(1))
                    try:
                        capture(ed, os.path.join(proj, m.group(2)), a.width)
                        status = "ok"
                    except McpError as e:
                        status = "failed"
                        errors.append(str(e)[:160])
                    ack = os.path.join(proj, "Saved", "gds-capture-ack-%s" % m.group(1))
                    with open(ack + ".tmp", "w") as f:
                        f.write(status)
                    os.replace(ack + ".tmp", ack)
                elif text.startswith("GDS-PLAY DONE"):
                    done = text
                elif text.startswith("GDS-PLAY {"):
                    try:
                        steps.append(json.loads(text[9:]))
                    except ValueError:
                        pass
    finally:
        ed.call("play_control", {"action": "stop"})
        try:
            os.remove(plan_path)
        except OSError:
            pass
    log_errors = [x.get("text", "")[:300] for x in ed.call("read_log", {"since_index": before, "limit": 200}).get("lines", [])
                  if x.get("level") == "error"]
    driven = [s for s in steps if s.get("status") == "driven"]
    undriv = [s for s in steps if s.get("status") == "undrivable"]
    failed = [s for s in steps if s.get("status") == "failed"]
    nochange = [s for s in driven if str(s.get("observed", "")).startswith("no visible change")]
    rows = ["| # | action | input | result | what changed | p95 ms | shot |", "|---|---|---|---|---|---|---|"]
    for s in steps:
        rows.append("| %s | %s | %s | %s | %s | %s | %s |" % (s.get("n"), s.get("action"), s.get("input"), s.get("status"),
                                                              str(s.get("observed", "")).replace("|", "/"), s.get("p95_ms", ""), s.get("shot") or ""))
    md = ["# Playthrough %02d" % n, "", "date: %s" % time.strftime("%Y-%m-%d %H:%M"),
          "status: %s" % ("PASS-PENDING-PARENT-READ" if done and not failed and not undriv and not log_errors else "NEEDS-PARENT"),
          "steps: %d (driven %d, undrivable %d, failed %d)" % (len(steps), len(driven), len(undriv), len(failed)),
          "log_errors: %d" % len(log_errors), "", "The bot cannot judge a picture: the parent opens every shot below, writes one line on what it shows, "
          "and decides as a player would.", ""] + rows + [""]
    if undriv:
        md += ["## Not driven (for the parent: each is an `engine_gap:` or a manual check, never a skip)", ""] + \
              ["- %s %s: %s" % (s.get("action"), s.get("input"), s.get("observed")) for s in undriv] + [""]
    if nochange:
        md += ["## Driven but nothing visible changed (look at the shot: a dead input, or a state the bot does not watch)", ""] + \
              ["- step %s %s %s" % (s.get("n"), s.get("action"), s.get("input")) for s in nochange] + [""]
    if failed or log_errors or errors:
        md += ["## Failures", ""] + ["- step %s %s: %s" % (s.get("n"), s.get("action"), s.get("observed")) for s in failed] + \
              ["- log: %s" % e for e in log_errors[:10]] + ["- capture: %s" % e for e in errors] + [""]
    path = os.path.join(gates, "playthrough-%02d.md" % n)
    os.makedirs(gates, exist_ok=True)
    open(path, "w", encoding="utf-8").write("\n".join(md))
    out = {"status": "NEEDS_PARENT" if (undriv or failed or log_errors or not done) else "READ_THE_SHOTS", "gate": path, "steps": len(steps),
           "driven": len(driven), "undrivable": len(undriv), "failed": len(failed), "noVisibleChange": len(nochange),
           "logErrors": len(log_errors), "done": bool(done)}
    if undriv:
        out["engine_gap"] = ["%s %s: %s" % (s.get("action"), s.get("input"), s.get("observed")) for s in undriv]
    emit(out)
    if failed or log_errors or not done:
        sys.exit(1)


# --- locks (no editor needed): see nc_proc.py ------------------------------------------------------------------------------
# Two locks. PROJECT: one editor driver per project (Saved/gds-nucleon.lock). MACHINE (GPU): one engine run at a time on the
# machine, whatever the project (a directory, made with mkdir like the bash tools do). Both are held per RUN of the engine
# (a play-test, a bench, a cycle), never per round of work, both record owner / pid / since / max hold, both are released on any
# exit and broken when the holder is dead or past its maximum hold.
DEFAULT_HOLD = 600


def lock_path(proj):
    return os.path.join(os.path.abspath(proj), "Saved", "gds-nucleon.lock")


def gpu_lock_path(a=None):
    """--gpu-lock, NCLI_GPU_LOCK, config.json paths.gpuLock, else ~/.game-developer/gpu.lock."""
    p = getattr(a, "gpu_lock", None) or os.environ.get("NCLI_GPU_LOCK")
    if not p:
        try:
            cfg = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
            p = json.load(open(cfg, encoding="utf-8")).get("paths", {}).get("gpuLock", "")
        except (OSError, ValueError):
            p = ""
    return p or os.path.join(os.path.expanduser("~"), ".game-developer", "gpu.lock")


def lock_acquire(proj, owner, wait, max_hold=DEFAULT_HOLD, pid=None, cmd=None):
    return nc_proc.lock_acquire(lock_path(proj), owner, wait, "file", max_hold, pid, cmd)


def lock_release(proj, owner, force=False):
    return nc_proc.lock_release(lock_path(proj), owner, "file", force)


def lock_targets(a):
    """[(name, kind, path)] in the one fixed order everything takes them in: the machine (GPU) lock, then the project's."""
    proj = a.project or os.getcwd()
    t = [] if getattr(a, "no_gpu", False) else [("gpu", "dir", gpu_lock_path(a))]
    return t + [("project", "file", lock_path(proj))]


def cmd_lock(a):
    """lock acquire|release|status: ONE lock for an engine run = the machine (GPU) lock and the project lock together (--no-gpu for
    a job that does not run the engine). `acquire` from the shell has no holder process left to check (this command ends at once):
    only --max-hold ends it. For the life of a command use `locked`; the run commands (play-test, capture, cycle, bench, run-game,
    lint --play, playthrough) take and release it themselves."""
    targets = lock_targets(a)
    if a.action == "status":
        out = {}
        for name, kind, path in targets:
            info = nc_proc.read_lock(path, kind)
            out[name] = {"locked": bool(info), **(nc_proc.describe(info) if info else {}), "stale": nc_proc.stale_reason(info) if info else None}
        emit(out)
        return
    if a.action == "release":
        res = {name: nc_proc.lock_release(path, a.owner, kind, a.force) for name, kind, path in reversed(targets)}
        emit(res)
        if not all(r.get("released") for r in res.values()):
            sys.exit(1)
        return
    got = []
    for name, kind, path in targets:
        r = nc_proc.lock_acquire(path, a.owner, a.wait, kind, a.max_hold, pid=0, cmd=a.holder_cmd or "ncli lock acquire")
        if not r.get("locked"):
            for n2, k2, p2 in reversed(got):
                nc_proc.lock_release(p2, a.owner, k2)
            emit({"locked": False, "busy": name, **r})
            sys.exit(1)
        got.append((name, kind, path))
    emit({"locked": True, "owner": a.owner, "locks": [g[0] for g in got]})


import contextlib  # noqa: E402


@contextlib.contextmanager
def run_lock(a, label):
    """Around ONE run of the engine: queue for the machine and project locks (saying who holds them), run, release. A caller that
    already holds them under the same name (`locked`, `lock acquire --owner`) is left in charge: nothing is taken or released."""
    owner = worker_name(a) or "ncli-%d" % os.getpid()
    hold = max(a.max_seconds, 1860) + 60
    taken = []
    try:
        for name, kind, path in lock_targets(argparse.Namespace(project=a.project, gpu_lock=getattr(a, "gpu_lock", None))):
            r = nc_proc.lock_acquire(path, owner, a.wait_lock, kind, hold, cmd="ncli " + label)
            if not r.get("locked"):
                raise McpError("%s lock busy: held by %s since %s (%ss ago, pid %s, %s); queued %ds, gave up. `ncli lock status` shows both; if the lock is yours (lock acquire --owner X) pass --as X" % (
                    name, r.get("heldBy"), r.get("since"), r.get("ageS"), r.get("pid"), r.get("cmd"), a.wait_lock))
            if not r.get("reentrant"):
                taken.append((kind, path))
        yield owner
    finally:
        for kind, path in reversed(taken):
            nc_proc.lock_release(path, owner, kind)


def needs_run_lock(a):
    if a.cmd in ("play-test", "cycle", "playthrough", "bench", "run-game"):
        return True
    if a.cmd == "capture":
        return not a.write_only
    if a.cmd == "lint":
        return bool(getattr(a, "play", False))
    return a.cmd == "exe" and a.what in ("build-gi", "hlod", "package")


def cmd_locked(a):
    """locked --owner O [--gpu] -- CMD ...: take the machine lock (--gpu) and the project lock, run CMD with a time limit (default
    the maximum hold), release both on ANY exit, break the process tree on timeout. The output goes to a log file (a pipe kept open
    by a grandchild cannot hang this command), the answer is one short JSON line with the tail."""
    cmd = list(a.cmdline)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        raise McpError("locked needs a command after --")
    if cmd[0] in ("ncli", "ncli.py"):
        cmd = [sys.executable, os.path.abspath(__file__)] + cmd[1:]
    taken = []
    text = " ".join(cmd)[:160]
    t0 = time.time()
    try:
        if not a.no_gpu:
            r = nc_proc.lock_acquire(gpu_lock_path(a), a.owner, a.wait, "dir", a.max_hold, cmd=text)
            if not r.get("locked"):
                emit({"ok": False, "error": "machine (GPU) lock busy", **r})
                sys.exit(1)
            taken.append("gpu")
        if a.project and not a.no_project_lock:
            r = nc_proc.lock_acquire(lock_path(a.project), a.owner, max(0, a.wait - (time.time() - t0)), "file", a.max_hold, cmd=text)
            if not r.get("locked"):
                emit({"ok": False, "error": "project lock busy", **r})
                sys.exit(1)
            taken.append("project")
        waited = round(time.time() - t0, 1)
        log = a.log or os.path.join(os.path.abspath(a.project or os.getcwd()), "Saved", "ncli-logs", "locked-%s-%d.log" % (
            re.sub(r"\W+", "_", a.owner), time.time()))
        res = nc_proc.run_bounded(cmd, a.cmd_timeout or a.max_hold, env=launch_env(), log_path=log, tail=a.tail)
    finally:
        for k in reversed(taken):
            if k == "gpu":
                nc_proc.lock_release(gpu_lock_path(a), a.owner, "dir")
            else:
                nc_proc.lock_release(lock_path(a.project), a.owner, "file")
    out = {"ok": res["code"] == 0, "exit": res["code"], "timedOut": res["timedOut"], "waitedS": waited, "ranS": res["seconds"],
           "locks": taken, "log": res["log"], "tail": res["tail"]}
    if res["timedOut"]:
        out["error"] = "killed after %ds (tree killed, locks released)" % (a.cmd_timeout or a.max_hold)
    emit(out)
    sys.exit(0 if out["ok"] else (124 if res["timedOut"] else (res["code"] or 1)))


# --- persistent session (one editor kept open for many commands) -----------------------------------------------------
def serve_argv(project, stdio, owner, no_lua=False, timeout=120):
    """The command line of the detached server, built from values (not copied from this process: restart_session reuses it)."""
    argv = [sys.executable, os.path.abspath(__file__), "--project", project, "--stdio", stdio, "--as", owner, "--timeout", str(timeout)]
    if no_lua:
        argv.append("--no-lua")
    if LAUNCH["pref_dir"]:
        argv += ["--pref-dir", LAUNCH["pref_dir"]]
    for kv in LAUNCH["env"]:
        argv += ["--env", kv]
    if LAUNCH["visible"]:
        argv.append("--visible")
    if LAUNCH["launcher"] is not None:
        argv += ["--launcher", LAUNCH["launcher"]]
    return argv + ["serve", "--foreground"]


def serve_detached(a, owner):
    """`serve` returns at once: the server runs as a detached process whose output goes to a log file, so a pipe
    (`ncli serve | tail`) or a caller that waits for EOF can never be held open by it (a worker once hung 23 minutes that way)."""
    log = os.path.join(os.path.abspath(a.project), "Saved", "ncli-serve.log")
    os.makedirs(os.path.dirname(log), exist_ok=True)
    argv = serve_argv(a.project, a.stdio, owner, a.no_lua, a.timeout)
    kw = {"creationflags": 0x00000008 | 0x00000200} if sys.platform.startswith("win") else {"start_new_session": True}
    with open(log, "wb") as lf:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=lf, stderr=subprocess.STDOUT, close_fds=True, **kw)
    deadline = time.time() + max(a.timeout, 240)
    while time.time() < deadline:
        sess = read_session(a.project)
        if sess:
            emit({"serving": True, "owner": owner, "port": sess["port"], "pid": sess.get("pid"), "log": log})
            return
        if proc.poll() is not None:
            tail = open(log, encoding="utf-8", errors="replace").read()[-400:]
            raise McpError("serve exited (%s): %s" % (proc.returncode, tail.strip()))
        time.sleep(0.5)
    nc_proc.kill_tree(proc.pid)
    raise McpError("serve did not come up in time (log: %s)" % log)


def cmd_serve(a):
    """--stdio EXE --project P serve: starts the editor once and serves its MCP on 127.0.0.1 for every later ncli call
    of this project (they find Saved/ncli-session.json). Saves 5-10 s of editor start per command. Stop: ncli session-stop.
    Runs detached (returns when ready); --foreground keeps it in this process."""
    import secrets
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    if not a.stdio or not a.project:
        raise McpError("serve needs --stdio <NucleonEditor> and --project")
    other = read_session(a.project)
    if other:
        raise McpError("a session is already running for this project, owned by '%s' (it stops it with `session-stop`; "
                       "you do not share it)" % other.get("owner", "?"))
    owner = worker_name(a)
    if not owner:
        raise McpError("serve needs a name: --as NAME (or NCLI_WORKER). The session belongs to the worker that starts it and no other "
                       "worker may play-test on it or stop it")
    if not a.foreground:
        return serve_detached(a, owner)
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
    write_json(session_path(a.project), {"port": port, "token": token, "pid": os.getpid(), "since": time.time(),
                                         "owner": owner, "stdio": a.stdio, "prefDir": LAUNCH["pref_dir"], "env": LAUNCH["env"]})
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
    owner = sess.get("owner")
    if owner and worker_name(a) != owner and getattr(a, "break_owner", None) != owner:
        raise McpError("refused: this session belongs to '%s'. Only its owner stops it. If that worker is gone, the parent can pass "
                       "--break %s (the exact owner name, so it is deliberate)" % (owner, owner))
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
    natives_json = os.path.join(repo, "docs", "api", "lua", "natives.json")
    warnings = []
    if a.from_editor:   # the registry of the BUILT editor (NC_NATIVES_DUMP), not the committed dump that can lag behind the sources
        import tempfile
        # `-run-lua` loads nc.natives from the PROJECT's nc/ folder (the runtime modules the editor copies in when it opens the project), not
        # from its embedded copy: no nc/natives.lua = no dump, an nc/ written by an older editor = the old registry (404 natives instead of 694
        # on 2026-10-29), silently.
        if not a.project:
            raise McpError("--from-editor needs --project: a project this editor has opened (docs: nucleon-loop.md, Snapshot gotcha)")
        exe = find_exe(a)
        nat_lua = os.path.join(os.path.abspath(a.project), "nc", "natives.lua")
        if not os.path.isfile(nat_lua):
            raise McpError("%s has no nc/natives.lua: open the project once with this editor first (any ncli command with --stdio %s --project %s, e.g. `ping`) so it copies its runtime modules in" % (a.project, exe, a.project))
        if os.path.getmtime(nat_lua) < os.path.getmtime(exe):
            warnings.append("nc/natives.lua is older than the editor: if the dump looks like an old registry, open the project once with this editor and run again")
        tmp = tempfile.mkdtemp(prefix="ncli-natives-")
        natives_json = os.path.join(tmp, "natives.json")
        script = os.path.join(tmp, "dump.lua")
        open(script, "w", encoding="utf-8").write('require("nc.natives")' + chr(10))
        env = launch_env()
        env["NC_NATIVES_DUMP"] = natives_json
        argv = launch_argv(exe, ["-run-lua", script, os.path.abspath(a.project)], env)
        subprocess.run(argv, cwd=tmp, env=env, capture_output=True, timeout=300)
        if not os.path.isfile(natives_json):
            raise McpError("the editor did not write the natives registry (NC_NATIVES_DUMP): is --exe / NUCLEON_EDITOR a current build?")
    src = json.load(open(natives_json, encoding="utf-8"))
    nat, fixes = {}, {"optionalByDoc": [], "varargsOptional": []}
    for n in src["natives"]:
        ps = n.get("params", [])
        # `ignore` of Raycast / RaycastAll / SphereCast / SphereCastAll is declared required since the first-person
        # natives (d241aa27) but the runtime takes nil (verified in Play): a ray without a shooter is legal
        doc_opt = [bool(p.get("optional") or p.get("name") == "ignore" or re.search(r"leave it out|optional|if omitted|can be omitted", p.get("doc", ""), re.I)) for p in ps]
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
    branch = subprocess.run(["git", "-C", repo, "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True).stdout.strip() or "main"
    path = os.path.join(DATA, "nucleon-api.json")
    old = json.load(open(path, encoding="utf-8"))["natives"] if os.path.exists(path) else {}
    diff = {"added": sorted(set(nat) - set(old)), "removed": sorted(set(old) - set(nat)),
            "arity": sorted(k for k in set(nat) & set(old) if (nat[k]["min"], nat[k]["max"]) != (old[k]["min"], old[k]["max"]))}
    if not a.dry_run:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "source": "NucleonEngine %s@%s docs/api/lua/natives.json + nucleon.lua" % (branch, rev),
                       "natives": nat, "legacy": legacy, "registryFixes": fixes}, f, separators=(",", ":"))
    emit({"natives": len(nat), "legacy": len(legacy), "engine": rev, **diff, "registryFixes": fixes, "written": not a.dry_run,
          **({"warnings": warnings} if warnings else {})})


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
    syntax = "luac" if luac else None
    if a.engine_syntax and not luac:   # no luac: the running editor's own Lua compiles every file (loadfile, nothing runs)
        try:
            ed = connect(a)
            try:
                table = "{" + ",".join(json.dumps(f.replace("\\", "/"), ensure_ascii=False) for f in lua_files(proj)) + "}"
                res = ed.call("run_lua", {"code": "for _, f in ipairs(" + table + ") do local fn, err = loadfile(f) "
                                                  "if not fn then print('NCSYNTAX ' .. err) end end print('NCSYNTAX-DONE')"})
            finally:
                ed.client.close()
            for l in res.get("output", []):
                t = l.get("text", "")
                if t.startswith("NCSYNTAX ") and not t.startswith("NCSYNTAX-DONE"):
                    msg = t[9:]
                    m = re.match(r"(.*?):(\d+): (.*)", msg)
                    rel = msg[:80]
                    if m:   # Lua shortens long chunk names to "...tail": find the file that ends with that tail
                        tail = m.group(1).lstrip(".").replace("\\", "/")
                        rel = next((os.path.relpath(f, proj).replace("\\", "/") for f in lua_files(proj)
                                    if f.replace("\\", "/").endswith(tail)), m.group(1))
                    problems.append({"file": rel, "syntax": (m.group(3) if m else msg)[:200], **({"line": int(m.group(2))} if m else {})})
            syntax = "editor"
        except McpError as e:
            syntax = "unavailable (%s)" % str(e)[:60]
    out = {"issues": len(problems), "files": files, "syntax": syntax, "luac": bool(luac), "problems": problems[:40], "api": api["source"]}
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
    """Headless editor modes (no MCP, no window): the engine's own command line, one JSON line out."""
    import shlex
    exe = find_exe(a)
    env = launch_env()
    extra = shlex.split(a.args) if a.args else []
    opt = []   # the modes that take options: the flags of this command, in the engine's spelling

    def flag(name, value):
        if value is not None:
            opt.extend([name, str(value)])
    if a.what == "compile-blueprints":
        argv = [exe, "-compile-blueprints", a.target]
    elif a.what == "package":
        flag("-config", a.config); flag("-platform", a.platform); flag("-runtime", a.runtime); flag("-key", a.key)
        flag("-ddc", a.ddc); flag("-geometry", a.geometry); flag("-report", a.report); flag("-log", a.log)
        if a.clean:
            opt.append("-clean")
        if a.strict:
            opt.append("-strict")
        argv = [exe, "-package", a.target, "-out", a.out or os.path.join(a.target, "Packaged")] + opt
    elif a.what == "run-lua":   # exe run-lua SCRIPT PROJECT  (or: exe run-lua PROJECT --script SCRIPT)
        script, proj = (a.target, a.extra) if a.extra else (a.script, a.target)
        argv = [exe, "-run-lua", script, proj]
    elif a.what == "migrate":
        argv = [exe, "-migrate", a.target] + (["--dry-run"] if a.dry_run else []) + (["--no-backup"] if a.no_backup else [])
    elif a.what == "hlod":      # exe hlod PROJECT LEVEL [--args "-type merged -distance 200 -cells 0,0;1,0"]
        argv = [exe, "-hlod", a.target, a.extra]
    elif a.what == "build-gi":  # the volume converges over a few hundred frames: it opens the runtime (hidden desktop)
        flag("-quality", a.quality)
        argv = [exe, "-build-gi", a.target, a.extra] + opt
    elif a.what == "optimize-level":   # UE-style ISM + partition of a big level for streaming (-dry-run lists first)
        argv = [exe, "-optimize-level", a.target, a.extra] + (["-dry-run"] if a.dry_run else []) + (["-out", a.out] if a.out else [])
    elif a.what == "upgrade-ddc":
        flag("-threads", a.threads)
        argv = [exe, "-upgrade-ddc"] + ([a.target] if a.target else []) + opt
    elif a.what == "raw":       # any NucleonEditor argument: exe raw -- -hlod P L
        argv = [exe]
    elif a.what == "new-project":
        env["NC_EDITOR_NEW_PROJECT"] = "%s:%s" % (a.template, os.path.abspath(a.target))
        if a.api:
            env["NC_EDITOR_NEW_PROJECT_API"] = a.api
        if not a.starter:   # the template's starter shapes are noise in a GDS project (the world replaces them)
            env["NC_EDITOR_NEW_PROJECT_STARTER"] = "0"
        argv = [exe]
    else:
        raise McpError("unknown exe command")
    argv = launch_argv(argv[0], argv[1:] + extra, env)
    log = os.path.join(os.path.abspath(a.project or os.getcwd()), "Saved", "ncli-logs", "exe-%s-%d.log" % (a.what, time.time()))
    res = nc_proc.run_bounded(argv, a.timeout, env=env, log_path=log, tail=a.tail)
    lines = [l.strip() for l in res["text"].splitlines() if l.strip()]
    errors = [l for l in lines if l.lower().startswith(("error", "[error]")) or " error" in l.lower()[:20]]
    emit({"ok": res["code"] == 0, "code": res["code"], "seconds": res["seconds"], "errors": errors[:15], "tail": res["tail"],
          "log": log, **({"timedOut": True} if res["timedOut"] else {})})
    if res["code"]:
        sys.exit(res["code"])


def cmd_run_game(a):
    """Runs a PACKAGED game (exe package): on the hidden desktop like the editor, from its own folder, with a time limit.
    --gds-test sets NC_GDS_TEST=1 NC_GDS_TEST_EXIT=1 NC_GDS_TEST_OUT=captures/test (the harness of ncli setup runs the
    test_*.lua scripts and the process exits 0 = all passed, 3 = a failure). The log is Saved/Logs/game.log: it only has
    the game's prints in a Debug / Development package (Shipping logs errors only), the console key (F8) too."""
    import shlex
    game = os.path.abspath(a.game)
    exe = game
    if os.path.isdir(game):
        win = sys.platform.startswith("win")
        cands = [f for f in os.listdir(game) if os.path.isfile(os.path.join(game, f)) and
                 (f.lower().endswith(".exe") if win else os.access(os.path.join(game, f), os.X_OK) and "." not in f)]
        if a.name:
            cands = [f for f in cands if os.path.splitext(f)[0] == a.name]
        cands = [f for f in cands if not f.lower().startswith(("unins", "crash", "dxc"))]
        if not cands:
            raise McpError("no game executable in %s (exe package first; --name for a game with several)" % game)
        exe = os.path.join(game, max(cands, key=lambda f: os.path.getsize(os.path.join(game, f))))
    folder = os.path.dirname(exe)
    env = launch_env()
    if a.gds_test:
        env["NC_GDS_TEST"] = a.gds_test if a.gds_test != "all" else "1"
        env["NC_GDS_TEST_EXIT"] = "1"
        env.setdefault("NC_GDS_TEST_OUT", os.path.join(folder, "captures", "test"))
        os.makedirs(env["NC_GDS_TEST_OUT"], exist_ok=True)
    log_path = os.path.join(folder, "Saved", "Logs", "game.log")
    if os.path.exists(log_path):
        try:
            os.remove(log_path)   # this run's lines only
        except OSError:
            pass
    argv = launch_argv(exe, shlex.split(a.args or ""), env)
    res = nc_proc.run_bounded(argv, a.seconds, env=env, cwd=folder,
                              log_path=os.path.join(folder, "Saved", "ncli-logs", "run-game-%d.log" % time.time()))
    timed_out, text = res["timedOut"], res["text"]
    t0 = time.time() - res["seconds"]
    if os.path.exists(log_path):
        text += "\n" + open(log_path, encoding="utf-8", errors="replace").read()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    errors, seen = [], set()
    for l in lines:
        low = l.lower()
        if (low.startswith(("[error]", "error")) or "attempt to" in low or "[lua] error" in low) and l not in seen:
            seen.add(l)
            errors.append(l[:240])
    tests = list(dict.fromkeys(l for l in lines if l.startswith("GDS-TEST")))   # stdout and game.log carry the same lines
    done = next((l for l in tests if l.startswith("GDS-TEST DONE")), None)
    shots = []
    for root in (env.get("NC_GDS_TEST_OUT"), os.path.join(folder, "Saved", "Screenshots")):
        if root and os.path.isdir(root):
            shots += [os.path.join(root, f) for f in sorted(os.listdir(root)) if f.lower().endswith(".png")][:20]
    code = None if timed_out else res["code"]
    ok = (not timed_out or a.allow_timeout) and not errors and (code == 0 or (timed_out and a.allow_timeout)) and \
        (not a.gds_test or (done is not None and " fail=0" in done))
    emit({"status": "PASS" if ok else "FAIL", "exe": os.path.basename(exe), "exit": code, "seconds": round(time.time() - t0, 1),
          "timedOut": timed_out, "errors": errors[:15], "gdsTest": tests[-6:], "log": log_path if os.path.exists(log_path) else None,
          "lines": len(lines), "shots": shots, "tail": lines[-a.tail:]})
    if not ok:
        sys.exit(1)


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
                             ("Content/Scripts/gds_playthrough.lua", "Content/Scripts/gds_playthrough.lua"),
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
    c.add_argument("--save", help="save after the build: a level path, or 'current' (refused through --stdio / serve unless --save-main-level)")
    c.add_argument("--save-main-level", action="store_true", help="allow --save current on a --stdio / serve editor")
    c.add_argument("--out")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--project", help="project folder (lock, reports, --stdio, session)")
    p.add_argument("--port", type=int)
    p.add_argument("--token")
    p.add_argument("--stdio", metavar="EXE", help="start EXE --mcp-stdio PROJECT for this command (or for `serve`)")
    p.add_argument("--no-lua", action="store_true", help="with --stdio: --mcp-no-lua")
    p.add_argument("--exe", help="NucleonEditor for exe/mcp-config")
    p.add_argument("--pref-dir", help="NC_EDITOR_PREF_DIR of the editor ncli starts (keeps your preferences untouched; "
                                      "also where HTTP mode reads port and token)")
    p.add_argument("--env", action="append", default=[], metavar="K=V", help="environment variable for the editor ncli starts "
                                                                              "(NC_GDS_TEST=1, NC_EDITOR_GAME_VIEW=1, NC_D3D12_RAYTRACING=0 ...); repeatable")
    p.add_argument("--visible", action="store_true", help="Windows: do not use the hidden desktop (nc_desktop_run.exe)")
    p.add_argument("--launcher", help="command prefix for the editor process (default on Windows: nc_desktop_run.exe -- ; '' = none)")
    p.add_argument("--timeout", type=float, default=120, help="seconds one MCP call may take")
    p.add_argument("--max-seconds", type=float, default=1800, help="watchdog: the whole command is killed (exit 124, locks released) after this; 0 = off")
    p.add_argument("--as", dest="worker", metavar="NAME", help="who you are (default NCLI_WORKER): owns the serve sessions you start and the locks you take")
    p.add_argument("--wait-lock", type=float, default=900, help="seconds a run command queues for the locks (the message says who holds them)")
    p.add_argument("--gpu-lock", help="the machine-wide GPU lock folder (default NCLI_GPU_LOCK, config.json paths.gpuLock, ~/.game-developer/gpu.lock)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping")
    sub.add_parser("state")
    c = sub.add_parser("call", help="one raw MCP tool", formatter_class=argparse.RawDescriptionHelpFormatter,
                       description="One MCP tool of the editor; prints its structuredContent.",
                       epilog="entity_modify / entity_get / entity_remove select the entity with `id` or `name`; "
                              "entity_modify RENAMES with `new_name` (`name` only selects):\n"
                              "  ncli call entity_modify '{\"name\": \"platform_floor\", \"new_name\": \"platform_slab\"}'\n"
                              "  ncli call entity_modify '{\"id\": 42, \"position\": [1, 2, 0]}'\n"
                              "JSON inline, or @file.json. The tools and their fields: ncli tools-check, docs/editor/MCP.md.")
    c.add_argument("tool", help="MCP tool name (editor_state, scene_list, entity_get, entity_modify, entity_add, ...)")
    c.add_argument("args", nargs="?", help="JSON arguments or @file.json (entity_modify: new_name renames, name/id select)")
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
    c.add_argument("--verbose", action="store_true", help="the whole log on stderr (it is always in Saved/ncli-logs/ too)")
    c.add_argument("--fresh", action="store_true", help="serve session: restart the editor first (clean input state; use for the gate evidence run)")
    c.add_argument("--until", help="stop as soon as a log line contains this (default: GDS-TEST DONE when --expect is a GDS-TEST line)")
    c.add_argument("--min-seconds", type=float, default=0)
    c.add_argument("--fps", type=float, help="frame budget: every GDS-PERF p95 must be under 1000/fps ms (GDD targetFps)")
    c = sub.add_parser("capture", help="store/trailer screenshots and GIF frames from a plan, in real Play")
    c.add_argument("plan")
    c.add_argument("--seconds", type=float, help="maximum Play time (default: last shot + 60 s)")
    c.add_argument("--width", type=int, default=1920, help="viewport capture width (store screenshots: 1920)")
    c.add_argument("--write-only", metavar="GAME_FOLDER", help="only write the plan for a packaged build (store-size shots)")
    c = sub.add_parser("log")
    c.add_argument("--level", default="error", choices=["info", "warning", "error"], help="minimum severity")
    c.add_argument("--category", help="Editor, Lua or Engine")
    c.add_argument("--since", type=int)
    c.add_argument("--limit", type=int, default=50)
    c.add_argument("--contains")
    c.add_argument("--cut", type=int, default=0, help="cut every line to N characters (default: the full text)")
    c = sub.add_parser("save")
    c.add_argument("path", nargs="?")
    c = sub.add_parser("lock", help="acquire | release | status of the engine-run lock (machine GPU lock + project lock, taken together)")
    c.add_argument("action", choices=["acquire", "release", "status"])
    c.add_argument("--owner", default="status")
    c.add_argument("--wait", type=float, default=600)
    c.add_argument("--force", action="store_true")
    c.add_argument("--no-gpu", action="store_true", help="the project lock only (a job that does not run the engine)")
    c.add_argument("--max-hold", type=float, default=DEFAULT_HOLD, help="seconds after which the lock counts as abandoned")
    c.add_argument("--cmd", dest="holder_cmd", help="what the holder is doing (shown to those who wait)")
    c = sub.add_parser("locked", help="locked --owner O -- CMD: run CMD under the locks (GPU + project), with a time limit, released on any exit")
    c.add_argument("--owner", required=True)
    c.add_argument("--no-gpu", action="store_true", help="skip the machine-wide GPU lock (a job that does not run the engine)")
    c.add_argument("--no-project-lock", action="store_true")
    c.add_argument("--wait", type=float, default=600, help="seconds to queue for the locks")
    c.add_argument("--max-hold", type=float, default=900, help="longest the locks may be held, and the default limit of CMD")
    c.add_argument("--cmd-timeout", type=float, help="limit of CMD (default --max-hold)")
    c.add_argument("--log", help="where CMD's output goes (default Saved/ncli-logs/)")
    c.add_argument("--tail", type=int, default=6)
    c.add_argument("cmdline", nargs=argparse.REMAINDER)
    c = sub.add_parser("serve", help="keep one editor open (--stdio EXE --project P) for every later ncli call")
    c.add_argument("--serve-port", type=int, default=0)
    c.add_argument("--foreground", action="store_true", help="stay in this process (default: detach and return when the editor is ready)")
    c = sub.add_parser("session-stop")
    c.add_argument("--save", action="store_true")
    c.add_argument("--break", dest="break_owner", metavar="OWNER", help="stop a session whose owner is gone: the owner's exact name")
    c = sub.add_parser("affected", help="tests to run for what changed since the last checkpoint commit")
    c.add_argument("--since", help="git ref (default: last commit whose message starts with 'checkpoint')")
    c = sub.add_parser("tools-check", help="the editor's MCP tools vs the snapshot this skill was verified with")
    c.add_argument("--update", action="store_true")
    c = sub.add_parser("api-refresh", help="rebuild the Lua API snapshot from an engine checkout")
    c.add_argument("--engine-repo", required=True, help="the engine checkout (docs/api/lua/nucleon.lua for the legacy list, the revision)")
    c.add_argument("--from-editor", action="store_true", help="the natives come from the built editor's registry (NC_NATIVES_DUMP through -run-lua) instead of the checkout's committed natives.json")
    c.add_argument("--dry-run", action="store_true")
    c = sub.add_parser("lua-check", help="game Lua vs the engine API: unknown calls, native arity, syntax (luac, or --engine-syntax)")
    c.add_argument("--engine-syntax", action="store_true", help="no luac on PATH: compile every file in the running editor (HTTP / session / --stdio) with loadfile")
    c.add_argument("--write")
    c.add_argument("--strict", action="store_true")
    c = sub.add_parser("exe", help="headless editor modes: compile-blueprints, package, run-lua, migrate, new-project, hlod, build-gi, optimize-level, upgrade-ddc, raw",
                       formatter_class=argparse.RawDescriptionHelpFormatter,
                       epilog="exe new-project DIR --template third-person [--api d3d12] [--starter]\n"
                              "exe compile-blueprints PROJECT            Blueprints (.ncbp) -> Generated/*.lua\n"
                              "exe package PROJECT --config Development --platform win64 --out DIR [--strict] [--report r.json]\n"
                              "exe run-lua SCRIPT PROJECT                 a Lua tool script with the project as working folder\n"
                              "exe hlod PROJECT LEVEL [--args \"-type merged -distance 200\"]   HLOD of the far world cells\n"
                              "exe build-gi PROJECT LEVEL [--quality high]  bake the GI probes\n"
                              "exe optimize-level PROJECT LEVEL [--dry-run] [--args \"-cell 128 -min-group 8\"]  ISM + streaming partition\n"
                              "exe upgrade-ddc [FOLDER] [--threads 6]     derived data cache to the coarse-first layout\n"
                              "exe raw --args \"-hlod P L\"                any NucleonEditor argument")
    c.add_argument("what", choices=["compile-blueprints", "package", "run-lua", "migrate", "new-project", "hlod", "build-gi",
                                    "optimize-level", "upgrade-ddc", "raw"])
    c.add_argument("target", nargs="?", default="", help="project folder (new-project: the new folder; run-lua: the script, then the project)")
    c.add_argument("extra", nargs="?", help="run-lua: the project folder; hlod / build-gi / optimize-level: the level (project relative)")
    c.add_argument("--script")
    c.add_argument("--out")
    c.add_argument("--config", help="package: build configuration (Debug / Development / Shipping or your own)")
    c.add_argument("--platform", help="package: linux64 | win64")
    c.add_argument("--runtime", help="package: the Nucleon runtime (default: next to the editor)")
    c.add_argument("--key", help="package: AES key (64 hex digits)")
    c.add_argument("--ddc", help="package: derived data cache folder (default PROJECT/Saved/DDC)")
    c.add_argument("--geometry", choices=["virtualized", "lod"], help="package: replaces the configuration's geometry")
    c.add_argument("--report", help="package: size report (.txt or .json)")
    c.add_argument("--log", help="package: log file")
    c.add_argument("--clean", action="store_true", help="package: rebuild everything")
    c.add_argument("--strict", action="store_true", help="package: warnings are errors")
    c.add_argument("--quality", help="build-gi: low | medium | high | ultra")
    c.add_argument("--threads", type=int, help="upgrade-ddc")
    c.add_argument("--api", choices=["d3d12", "vulkan", "opengl"], help="new-project: graphics API of the project")
    c.add_argument("--args", help="extra engine arguments, one string (shell syntax)")
    c.add_argument("--no-backup", action="store_true", help="migrate")
    c.add_argument("--template", default="third-person", help="new-project: empty | first-person | third-person | top-down")
    c.add_argument("--starter", action="store_true", help="new-project: keep the template's starter shapes")
    c.add_argument("--dry-run", action="store_true")
    c.add_argument("--tail", type=int, default=8)
    c = sub.add_parser("entities", help="scene_list: the entities of the level (id, name, type, position)")
    c.add_argument("--type", help="model, light, landscape, actor, empty, folder, shape, instances, water, player start, ... (scene_list type)")
    c.add_argument("--name", help="name contains")
    c.add_argument("--parent", type=int, help="inside this folder id (0 = root)")
    c.add_argument("--limit", type=int, default=200)
    c.add_argument("--count", action="store_true", help="only the counts by type")
    c.add_argument("--full", action="store_true", help="the raw scene_list records")
    c = sub.add_parser("entity", help="get / set / add / rm / select an entity (id or name)",
                       formatter_class=argparse.RawDescriptionHelpFormatter,
                       epilog="entity get ID|NAME\n"
                              "entity set ID|NAME '{\"position\":[1,2,0],\"light\":{\"intensity\":800}}'   (new_name renames)\n"
                              "entity add TYPE '{\"name\":\"Sun\",\"light\":{\"type\":\"directional\",\"atmosphere_sun\":true}}'\n"
                              "entity rm ID|NAME ...      entity select ID ...\n"
                              "TYPE: empty light shape playerstart reflection_capture audioemitter audiovolume folder model actor instances")
    c.add_argument("action", choices=["get", "set", "add", "rm", "select"])
    c.add_argument("target", nargs="?", default="", help="id or name (add: the entity type)")
    c.add_argument("json", nargs="?", help="set / add: JSON or @file.json")
    c.add_argument("more", nargs="*", help="rm / select: more ids or names")
    c.add_argument("--full", action="store_true")
    c = sub.add_parser("assets", help="asset_search: project files by fuzzy name")
    c.add_argument("query", nargs="?")
    c.add_argument("--type", help="Model, Texture, Script, Scene, Sound, Actor, Material, Material Graph, Animation Graph, Sequence, Blueprint, UI Document, Project, Other")
    c.add_argument("--limit", type=int, default=50)
    c.add_argument("--paths", action="store_true", help="only the paths")
    c = sub.add_parser("import", help="asset_import: models / textures / sounds into the project")
    c.add_argument("files", nargs="+")
    c.add_argument("--folder", default="Content/Imported")
    c.add_argument("--place", action="store_true", help="also place the models in the level")
    c = sub.add_parser("commands", help="list_commands: ids run_command takes")
    c.add_argument("query", nargs="?")
    c.add_argument("--enabled", action="store_true")
    c.add_argument("--limit", type=int, default=100)
    c = sub.add_parser("command", help="run_command ID (edit.undo, edit.redo, file.save, tools.build_reflection_captures, ...)")
    c.add_argument("id")
    c = sub.add_parser("input", help="get_input_mapping / set_input_mapping (Config/Input.lua)")
    c.add_argument("action", choices=["get", "set"])
    c.add_argument("file", nargs="?", help="set: the Lua file")
    c.add_argument("--out", help="get: write the Lua text here")
    c = sub.add_parser("docs", help="the editor's document tabs: list | switch X | open actor|mesh|preferences|project [--path P] | close INDEX")
    c.add_argument("action", choices=["list", "switch", "open", "close"])
    c.add_argument("target", nargs="?")
    c.add_argument("--path")
    c.add_argument("--discard", action="store_true")
    c = sub.add_parser("play", help="play_control: start | stop | pause | resume | step")
    c.add_argument("action", choices=["start", "stop", "pause", "resume", "step"])
    c = sub.add_parser("lua", help="run_lua (ENGINE coordinates, not undoable): ncli lua 'print(1+2)' | @file.lua")
    c.add_argument("code")
    c = sub.add_parser("profile", help="profile_capture: start | stop | save [--path Saved/Profiling/x.ncprof] (only when the owner authorizes profiling)")
    c.add_argument("action", choices=["start", "stop", "save"])
    c.add_argument("--path")
    c = sub.add_parser("resources", help="MCP resources: list | read URI (nucleon://docs/editor-guide, nucleon://lua-api/<module>.lua, nucleon://project/<path>)")
    c.add_argument("action", choices=["list", "read"])
    c.add_argument("uri", nargs="?")
    c.add_argument("--out")
    c.add_argument("--limit", type=int, default=60)
    c = sub.add_parser("tools", help="tools/list of the running editor (fields per tool); `tools NAME` = the whole schema")
    c.add_argument("name", nargs="?")
    c = sub.add_parser("camera", help="Camera entities: list | add NAME --pos --target --fov/--focal | pilot [NAME] | stop | shot NAME out.png",
                       formatter_class=argparse.RawDescriptionHelpFormatter,
                       epilog="camera add Hero --pos 0,-20,6 --target 0,0,2 --focal 35 --dof --fstop 2.8 --focus 20\n"
                              "camera shot Hero shots/hero.png   (pilots the camera, captures the viewport, stops piloting)")
    c.add_argument("action", choices=["list", "add", "pilot", "stop", "shot"])
    c.add_argument("name", nargs="?")
    c.add_argument("out", nargs="?", help="shot: the PNG")
    c.add_argument("--pos", help="add: x,y,z (display axes, Z up)")
    c.add_argument("--target", help="add: look at x,y,z (computes the rotation)")
    c.add_argument("--rot", help="add: pitch,roll,yaw in degrees (yaw counter-clockwise from above, 0 faces +Y)")
    c.add_argument("--fov", type=float, help="add: horizontal field of view in degrees")
    c.add_argument("--focal", type=float, help="add: physical lens, focal length in mm (the Cine camera)")
    c.add_argument("--dof", action="store_true", help="add: depth of field")
    c.add_argument("--fstop", type=float)
    c.add_argument("--focus", type=float, help="add: focus distance in metres")
    c.add_argument("--default-view", action="store_true", help="add: the game starts through this camera")
    c.add_argument("--flags", help="add: render_flags JSON")
    c.add_argument("--width", type=int, default=1280)
    c = sub.add_parser("post", help="Post Process Volumes: list | add NAME [--unbound --set k=v --blendable MAT:W] | set NAME ...")
    c.add_argument("action", choices=["list", "add", "set"])
    c.add_argument("name", nargs="?")
    c.add_argument("--pos", help="add: x,y,z")
    c.add_argument("--size", help="add: box size x,y,z in metres (the entity scale)")
    c.add_argument("--unbound", action="store_true", help="covers the whole level")
    c.add_argument("--priority", type=int)
    c.add_argument("--blend-radius", type=float)
    c.add_argument("--weight", type=float)
    c.add_argument("--set", action="append", help="a Lighting key: bloom=true, exposure=1.2 (JSON value; null removes)")
    c.add_argument("--blendable", action="append", help="Post Process material project path[:weight] (replaces the list)")
    c = sub.add_parser("material", help="material_domain of a .ncmat: material domain PATH [--domain postProcess --post-location afterTonemap]")
    c.add_argument("action", choices=["domain"])
    c.add_argument("path")
    c.add_argument("--domain", help="surface, decal, lightFunction, postProcess, volume, sky")
    c.add_argument("--post-location", help="beforeTonemap, afterTonemap, replaceTonemapper")
    c.add_argument("--decal-blend")
    c.add_argument("--sky-blend", help="replace, overAtmosphere")
    c = sub.add_parser("weather", help="weather + time of day + wind + lightning: get | set | clear | strike [--scope level|project|live]",
                       formatter_class=argparse.RawDescriptionHelpFormatter,
                       epilog="weather get\n"
                              "weather set --preset Rain --time 18.5 --wind-heading 90 --wind-speed 8 --param puddles=1\n"
                              "weather set --scope live --preset Storm --blend 30     (the running game only)\n"
                              "weather strike --intensity 1.5\n"
                              "presets: Clear Cloudy Overcast Rain Storm Snow Fog. params: cloud_coverage sun_scale sky_scale fog_scale rain snow "
                              "wetness puddles snow_cover wind_speed wind_gustiness lightning lens_rain")
    c.add_argument("action", choices=["get", "set", "clear", "strike"])
    c.add_argument("--scope", choices=["level", "project", "live"], help="where set / clear write (default level)")
    c.add_argument("--preset")
    c.add_argument("--blend", type=float, help="live: seconds to reach the weather")
    c.add_argument("--time", type=float, help="time of day, hours 0-24")
    c.add_argument("--latitude", type=float)
    c.add_argument("--day-length", type=float, help="real minutes per day (0: the clock stands still)")
    c.add_argument("--wind-heading", type=float, help="compass degrees the wind blows to")
    c.add_argument("--wind-speed", type=float, help="m/s (negative: the preset's)")
    c.add_argument("--gustiness", type=float)
    c.add_argument("--precipitation", type=float, help="density scale 0-2")
    c.add_argument("--surfaces", action=argparse.BooleanOptionalAction, default=None, help="wet ground, puddles, snow on materials")
    c.add_argument("--lens-drops", action=argparse.BooleanOptionalAction, default=None)
    c.add_argument("--thunder", help="thunder sound (project relative file or .lua cue)")
    c.add_argument("--param", action="append", metavar="K=V", help="a single weather value over the preset (rain=0.4); repeatable")
    c.add_argument("--intensity", type=float, help="strike: 0-2")
    c.add_argument("--full", action="store_true", help="the whole answer (current / target values, project table)")
    c = sub.add_parser("destruction", help="fracture models, destructible / cloth actors; in Play: damage, break, ray, explode, cloth wind",
                       formatter_class=argparse.RawDescriptionHelpFormatter,
                       epilog="destruction fracture --model Content/Crate.glb --pieces 24 --seed 3\n"
                              "destruction make-actor --model Content/Crate.glb --path Content/Actors/Crate.ncactor --health 40 --dynamic\n"
                              "destruction make-cloth-actor --path Content/Actors/Flag.ncactor --shape grid --width 2 --height 1.2 --pin left --wind true\n"
                              "destruction state | damage --entity Crate --amount 25 | break --entity Crate | ray --from 0,-5,1 --to 0,5,1 --amount 20 --impulse 4\n"
                              "destruction explode --position 0,0,1 --radius-m 6 --force 500 --amount 80 | cloth-wind --cloth 1 --wind 6,0,0")
    c.add_argument("action", choices=["fracture", "info", "make-actor", "make-cloth-actor", "state", "damage", "break", "set-health", "ray", "explode", "cloth-wind"])
    for opt, typ in (("--model", str), ("--file", str), ("--output", str), ("--path", str), ("--pieces", int), ("--seed", int), ("--clusters", int),
                     ("--irregularity", float), ("--health", float), ("--impact-threshold", float), ("--lifetime", float), ("--fade", float),
                     ("--shape", str), ("--width", float), ("--height", float), ("--radius", float), ("--pin", str), ("--pressure", float),
                     ("--destructible", int), ("--entity", str), ("--cloth", int), ("--amount", float), ("--impulse", float),
                     ("--radius-m", float), ("--force", float), ("--drag", float)):
        c.add_argument(opt, type=typ)
    c.add_argument("--dynamic", action=argparse.BooleanOptionalAction, default=None)
    c.add_argument("--staged", action=argparse.BooleanOptionalAction, default=None)
    for opt in ("--color", "--position", "--direction", "--from", "--to"):
        c.add_argument(opt, help="x,y,z (Z up, meters; color r,g,b 0..1)")
    c.add_argument("--wind", help="make-cloth-actor: true | false; cloth-wind: x,y,z m/s (omit: off)")
    c.add_argument("--json", help="more fields of the tool, JSON or @file.json")
    c = sub.add_parser("memory", help="memory_stats: memory | load | text (CPU/GPU tags, video memory, load timeline)")
    c.add_argument("action", nargs="?", default="memory", choices=["memory", "load", "text"])
    c.add_argument("--kind", choices=["all", "cpu", "gpu"])
    c.add_argument("--limit", type=int, default=40, help="list items kept per field")
    c.add_argument("--full", action="store_true")
    c = sub.add_parser("bench", help="one repeatable measurement of a level: vsync off, fixed camera / path, p50/p95/p99 wall CPU GPU, Present, draws, baseline compare")
    c.add_argument("--view", help="fixed camera x,y,z,tx,ty,tz (Z up)")
    c.add_argument("--path", help="a JSON file {points: [[pos, look], ...], speed} for a camera path")
    c.add_argument("--scenes", help="a tools/nucleon-bench scenes.json (+ --scenario NAME)")
    c.add_argument("--scenario")
    c.add_argument("--name", help="name of the measurement (the baseline file is docs/bench/<name>.baseline.json)")
    c.add_argument("--engine", help="folder of Nucleon.exe (default: next to paths.nucleon / --exe)")
    c.add_argument("--seconds", type=float, default=20, help="seconds of a --view (a --path takes its length / speed)")
    c.add_argument("--speed", type=float, default=6, help="m/s along a --path")
    c.add_argument("--warmup", type=float, default=5)
    c.add_argument("--load-wait", type=float, default=120)
    c.add_argument("--fps", type=float, help="target fps of the GDD: budget = 1000 / fps, compared with the wall p95")
    c.add_argument("--baseline", help="baseline JSON (default docs/bench/<name>.baseline.json)")
    c.add_argument("--update-baseline", action="store_true", help="store this run as the baseline")
    c.add_argument("--tolerance", type=float, default=10.0, help="percent a p95 may worsen before the run counts as a regression")
    c.add_argument("--min-frames", type=int, default=600)
    c.add_argument("--gpu-every", type=int, default=5, help="NC_GPU_PROFILE period in frames")
    c.add_argument("--quality", default=None, help="leave None: the bench never lowers the quality the project is set to")
    c = sub.add_parser("playthrough", help="Play with real input events: every bound input of every action + a look + the plan's steps; writes docs/gates/playthrough-NN.md")
    c.add_argument("--plan", help="JSON {steps: [{name, input: 'Key.R', seconds, watch: 'GetAmmo()', expect: 'after < before'}]}: the verbs of this game")
    c.add_argument("--seconds", type=float, default=240)
    c.add_argument("--hold", type=float, default=0.7, help="seconds each input is held")
    c.add_argument("--settle", type=float, default=1.5)
    c.add_argument("--width", type=int, default=1280)
    c = sub.add_parser("run-game", help="run a packaged game (hidden desktop, own folder, time limit): log, exit code, GDS tests, shots")
    c.add_argument("game", help="the packaged folder (exe package --out) or its executable")
    c.add_argument("--name", help="executable name when the folder has several")
    c.add_argument("--seconds", type=float, default=60, help="kill the game after this long")
    c.add_argument("--gds-test", nargs="?", const="all", metavar="NAMES", help="NC_GDS_TEST=1 (or a comma list) + NC_GDS_TEST_EXIT=1: exit 0 = all passed, 3 = failed")
    c.add_argument("--allow-timeout", action="store_true", help="a game that is still running at --seconds is fine (a smoke run)")
    c.add_argument("--args", help="game command line, one string")
    c.add_argument("--tail", type=int, default=6)
    c = sub.add_parser("setup", help="copy the GDS harnesses, example spec and folders into a Nucleon project")
    c.add_argument("target")
    c.add_argument("--force", action="store_true")
    sub.add_parser("mcp-config")
    argv, i = sys.argv[1:], 0
    while i < len(argv) - 1:   # `--pos -12,-14,8`: argparse reads a leading minus as an option
        if argv[i] in ("--pos", "--target", "--origin", "--position", "--direction", "--from", "--to", "--wind", "--color") and argv[i + 1].startswith("-"):
            argv[i:i + 2] = [argv[i] + "=" + argv[i + 1]]
        i += 1
    a = p.parse_args(argv)
    LAUNCH.update(visible=a.visible, launcher=a.launcher, pref_dir=a.pref_dir, env=a.env)
    if a.pref_dir:
        os.environ["NC_EDITOR_PREF_DIR"] = os.path.abspath(a.pref_dir)   # HTTP mode reads the settings from there too
    offline = {"lock": cmd_lock, "locked": cmd_locked, "setup": cmd_setup, "mcp-config": cmd_mcp_config, "serve": cmd_serve,
               "session-stop": cmd_session_stop, "affected": cmd_affected, "lua-check": cmd_lua_check,
               "api-refresh": cmd_api_refresh, "run-game": cmd_run_game, "bench": cmd_bench}
    def watchdog(seconds):
        emit({"ok": False, "error": "watchdog: %s ran over %ds, killed (children killed, locks released). Raise --max-seconds only for a "
                                    "job that is meant to take longer" % (a.cmd, seconds)})
        sys.stdout.flush()
    if a.cmd not in ("serve", "locked"):   # serve lives until session-stop; locked has its own limit
        nc_proc.start_watchdog(a.max_seconds if a.cmd != "exe" else max(a.max_seconds, 1860), watchdog)
    nc_proc.install_exit_hooks()
    try:
        if a.cmd == "exe":
            a.timeout = max(a.timeout, 1800)
        if needs_run_lock(a) and a.cmd not in ("locked",):
            with run_lock(a, a.cmd):
                return dispatch(a, offline)
        return dispatch(a, offline)
    except (McpError, ValueError) as e:
        emit({"ok": False, "error": str(e)})
        sys.exit(2)


def dispatch(a, offline):
    if True:
        if a.cmd == "exe":
            return cmd_exe(a)
        if a.cmd in offline:
            return offline[a.cmd](a)
        if a.cmd == "capture" and a.write_only:
            return cmd_capture(a, None)
        if a.cmd == "build" and a.dry_run:
            return cmd_build(a, None)
        if a.cmd == "play-test" and a.fresh and not a.stdio:
            note = restart_session(a)
            if note:
                sys.stderr.write(note + "\n")
        ed = connect(a)
        try:
            globals()["cmd_" + a.cmd.replace("-", "_")](a, ed)
        finally:
            ed.client.close()


if __name__ == "__main__":
    main()
