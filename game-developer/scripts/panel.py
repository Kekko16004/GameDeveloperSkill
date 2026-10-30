#!/usr/bin/env python3
"""Local web panel of a game project: what is running, what comes next, media, performance, launch.

  python panel.py [--project DIR] [--port N]     serve on 127.0.0.1 only, print the URL
  python panel.py --project DIR --heartbeat [S]  parent: mark Claude as listening (once, or every 30 s for S seconds)
  python panel.py --project DIR --drain          parent: print and empty the command queue, one JSON per line

Standard library only. Every value is read from the project on each request; nothing is stored.
The server writes one file only, .gds/panel-commands.jsonl, and only while the parent is listening.
It never executes a command: the parent reads the queue and decides. See references/panel.md.
"""
import argparse
import json
import mimetypes
import os
import re
import secrets
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "..", "templates", "panel", "index.html")
HEARTBEAT = os.path.join(".gds", "panel-listening")
QUEUE = os.path.join(".gds", "panel-commands.jsonl")
STALE_SECONDS = 120
MEDIA_ROOTS = ("screenshots", "captures", os.path.join("docs", "screens"))
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif")
LAUNCH_PAGES = ("STATUS.html", "REPORT.html")
LAUNCH_SKILL = "game-launch-strategist"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
TYPES = (  # guessed from file names; the page says so
    ("Weapons", r"wpn|weapon|gun|rifle|pistol|sword|grip|recoil"),
    ("UI", r"ui|hud|menu|screen|settings|pause"),
    ("Effects", r"fx|vfx|impact|muzzle|particle|explosion"),
    ("Environment", r"look|world|level|env|terrain|hall|map|scene|greybox|lane|room|building"),
    ("Characters", r"char|hero|enemy|npc|arms|body|anim"),
    ("Tests", r"test|batch|gate|smoke|bench|playtest|probe"),
)


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0


def when(t):
    """A file time for display: HH:MM today, else day month HH:MM."""
    if not t:
        return ""
    a, b = time.localtime(t), time.localtime()
    hm = time.strftime("%H:%M", a)
    return hm if a[:3] == b[:3] else "%d %s %s" % (a.tm_mday, MONTHS[a.tm_mon - 1], hm)


def day(t):
    a = time.localtime(t)
    return "%d %s" % (a.tm_mday, MONTHS[a.tm_mon - 1])


def listing(folder):
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    return [(n, os.path.join(folder, n)) for n in sorted(names) if os.path.isfile(os.path.join(folder, n))]


def clip(text, size):
    return text if len(text) <= size else text[:size - 3].rsplit(" ", 1)[0] + "..."


def short_title(text):
    text = re.sub(r"^\[[A-Z-]+\]\s*", "", text).strip()
    head = re.split(r":\s", text, maxsplit=1)[0]
    return clip(head, 70)


# ---------------------------------------------------------------- tasks

def parse_rows(text):
    """Rows of the task table. Columns come from its header; the skill's templates differ in column count."""
    cols, rows = None, []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in re.split(r"(?<=\s)\|(?=\s|$)", line.strip()[1:].strip())]
        low = [c.lower() for c in cells]
        if low and low[0] == "id" and any(c in ("stato", "status") for c in low):
            cols = {}
            for i, c in enumerate(low):
                for key, names in (("name", ("descri", "task", "name")), ("evidence", ("evidenz", "evidence")),
                                   ("deps", ("dipend", "depend")), ("status", ("stato", "status")), ("note", ("note",))):
                    if key not in cols and any(c.startswith(n) for n in names):
                        cols[key] = i
            continue
        if cols is None or not cells[0].startswith("TASK-") or len(cells) <= cols.get("status", 99):
            continue
        get = lambda k: cells[cols[k]] if k in cols and cols[k] < len(cells) else ""
        rows.append({"id": cells[0][5:], "name": get("name"), "title": short_title(get("name")), "evidence": get("evidence"),
                     "deps": get("deps"), "status": get("status"), "note": get("note")})
    return rows


def state_of(status):
    s = status.lower()
    if s.startswith("[x]"):
        return "done"
    if s.startswith(("[/]", "[~]")):
        return "active"
    if s.startswith("[!]"):
        return "blocked"
    if "built" in s:
        return "built"
    return "open"


def progress_files(project, ids):
    """task id -> docs/progress files; a file belongs to the longest id its name starts with or contains."""
    out, ordered = {}, sorted(ids, key=len, reverse=True)
    for name, path in listing(os.path.join(project, "docs", "progress")):
        stem = os.path.splitext(name)[0]
        for i in ordered:
            if re.search(r"(^|[-_])" + re.escape(i) + r"([-_]|$)", stem, re.I):
                out.setdefault(i, []).append(path)
                break
    return out


def tasks(project):
    rows = parse_rows(read(os.path.join(project, "GAME_TASKS.md")))
    ids = {r["id"] for r in rows}
    states = {r["id"]: state_of(r["status"]) for r in rows}
    progress = progress_files(project, ids)
    for r in rows:
        r["state"] = states[r["id"]]
        files = sorted(progress.get(r["id"], []), key=mtime)
        r["progress"] = files[-1] if files else None
        ev = [os.path.join(project, *m.split("/")) for m in re.findall(r"docs/[\w./-]+\.\w+", r["evidence"])]
        times = [mtime(p) for p in ev + files]
        r["fileTime"] = max(times) if times else 0
        tokens = [t.replace("TASK-", "") for t in re.split(r"[,;\s]+", r["deps"])]
        r["waits"] = [t for t in tokens if t in ids and states[t] not in ("done", "built")]

    active, inferred, blocked, built, nxt, done, needs = [], [], [], [], [], [], []
    for r in rows:
        waits_user = "[WAIT-USER]" in r["name"] or re.search(
            r"\b(owner|user|utente|proprietario)\b.{0,30}\b(picks?|chooses?|decides?|answers?|sceglie|decide)\b", r["note"], re.I)
        if waits_user and r["state"] != "done":
            needs.append({"task": r["id"], "question": r["note"] or r["title"], "title": r["title"]})
        item = {"id": r["id"], "title": r["title"]}
        if r["state"] == "done":
            done.append(dict(item, time=when(r["fileTime"]), t=r["fileTime"]))
        elif r["state"] == "active":
            active.append(dict(item, detail="marked in the registry"))
        elif r["state"] == "blocked":
            blocked.append(dict(item, reason=r["note"] or "no reason in the registry"))
        elif r["state"] == "built":
            built.append(dict(item, detail=r["status"]))
        elif r["progress"]:
            line = re.search(r"^\**(?:status|stato)\**\s*:\s*(.+)$", read(r["progress"]), re.I | re.M)
            inferred.append(dict(item, detail=(clip(line.group(1).strip(), 90) if line else ""), time=when(mtime(r["progress"]))))
        else:
            nxt.append(dict(item, waits=r["waits"]))
    nxt.sort(key=lambda x: bool(x["waits"]))  # stable: ready first, each part in registry order
    done.sort(key=lambda x: -x["t"])
    for d in done:
        del d["t"]
    return {"exists": bool(rows), "total": len(rows), "done": done, "active": active, "inferred": inferred, "blocked": blocked,
            "built": built, "next": nxt, "needs": needs, "open": sum(1 for r in rows if r["state"] in ("open", "active", "blocked"))}


def gates(project):
    out = []
    for name, path in listing(os.path.join(project, "docs", "gates")):
        if not name.endswith(".md"):
            continue
        text = read(path)
        status = re.search(r"^\**status\**\s*:\s*`?([A-Za-z_-]+)", text, re.I | re.M)
        title = re.search(r"^#\s+(.+)$", text, re.M)
        out.append({"name": name, "title": title.group(1) if title else name, "status": status.group(1) if status else "",
                    "t": mtime(path), "time": when(mtime(path))})
    out.sort(key=lambda g: -g["t"])
    return out


def decisions(project):
    lines = [l[2:].strip() for l in read(os.path.join(project, "DECISIONI.md")).splitlines() if l.startswith("- ")]
    return lines[::-1]


def engine_gaps(project):
    out = []
    for folder in ("progress", "gates"):
        for name, path in listing(os.path.join(project, "docs", folder)):
            for m in re.finditer(r"engine_issues:\s*(.+)", read(path)):
                value = m.group(1).strip().strip("`")
                if value and value.lower() not in ("[]", "none", "nessuno", "-") and "engine_issues" not in value:
                    out.append({"text": value[:160], "source": name})
    return out


# ---------------------------------------------------------------- media

def media_index(project):
    files = []
    for root in MEDIA_ROOTS:
        base = os.path.join(project, root)
        real = media_root(project, root)
        if not real:
            continue
        for folder, _, names in os.walk(base):
            for n in names:
                p = os.path.join(folder, n)
                if n.lower().endswith(IMAGE_EXT) and inside(p, real):
                    files.append((os.path.relpath(p, project).replace(os.sep, "/"), mtime(p), n))
    return files


def media_root(project, root):
    """The real path of a media folder, or None when it is a link leading out of the project."""
    real = os.path.realpath(os.path.join(project, root))
    return real if inside(real, os.path.realpath(project)) else None


def inside(path, real_root):
    try:
        return os.path.commonpath([os.path.realpath(path), real_root]) == real_root
    except ValueError:
        return False


def kind_of(name):
    low = name.lower().split("/", 1)[-1]  # the root folder ("screenshots") says nothing about the image
    for label, pattern in TYPES:
        if re.search(r"(^|[-_/.\d])(" + pattern + r")", low):
            return label
    return "Other"


def media(project, task_ids):
    files = media_index(project)
    docs = [(n, read(p), mtime(p)) for n, p in listing(os.path.join(project, "docs", "progress")) if n.endswith(".md")]
    groups, attribution = {}, {}
    items = []
    for rel, t, name in files:
        stem = os.path.splitext(name)[0]
        parts = rel.split("/")
        nested = parts[1] if len(parts) > 2 else None
        prefix = nested or re.split(r"[-_.]", stem)[0] or stem
        rest = stem if nested else stem[len(prefix):].lstrip("-_.") or stem
        task = None
        literal = re.search(r"TASK-([A-Za-z0-9-]+?)(?:[_.]|$)", stem)
        if literal and literal.group(1) in task_ids:
            task = literal.group(1)
        else:
            if prefix not in attribution:
                attribution[prefix] = doc_task(prefix, docs, task_ids)
            task = attribution[prefix]
        items.append({"p": rel, "name": name, "caption": rest.replace("-", " ").replace("_", " "), "group": prefix, "task": task,
                      "kind": kind_of(rel), "t": t, "time": when(t), "day": day(t), "key": rest.lower()})
        g = groups.setdefault(prefix, {"name": prefix, "task": task, "count": 0, "t": 0})
        g["count"] += 1
        g["t"] = max(g["t"], t)
    items.sort(key=lambda i: (-i["t"], i["name"]))
    for g in groups.values():
        g["time"] = when(g["t"])
    return {"items": items, "groups": sorted(groups.values(), key=lambda g: -g["t"])}


def doc_task(prefix, docs, task_ids):
    """The task whose newest progress note names this file prefix ("wpn-..."); inferred, the page says so."""
    if len(prefix) < 3:
        return None
    pattern = re.compile(r"(?<![\w-])" + re.escape(prefix) + r"-")
    best, best_t = None, 0
    for name, text, t in docs:
        if t > best_t and pattern.search(text):
            stem = os.path.splitext(name)[0]
            found = [i for i in task_ids if re.search(r"(^|[-_])" + re.escape(i) + r"([-_]|$)", stem, re.I)]
            if found:
                best, best_t = max(found, key=len), t
    return best


# ---------------------------------------------------------------- performance

def target_fps(project):
    for name in ("GDD.md", "GAME_CONTEXT.md"):
        m = re.search(r"targetFps\D{0,5}(\d{2,3})|target\s+(\d{2,3})\s*fps", read(os.path.join(project, name)), re.I)
        if m:
            return int(m.group(1) or m.group(2)), name
    return None, None


def performance(project):
    points = []
    for folder in ("gates", "progress"):
        for name, path in listing(os.path.join(project, "docs", folder)):
            if not name.endswith(".md"):
                continue
            text = read(path)
            for m in re.finditer(r"GPU\s*([\d.]+)\s*ms\s*[/,]?\s*CPU\s*([\d.]+)\s*ms", text):
                build = re.search(r"build\s+`?([0-9a-f]{7,40})`?[^.\n]{0,20}$", text[max(0, m.start() - 60):m.start()])
                points.append({"gpu": float(m.group(1)), "cpu": float(m.group(2)), "build": build.group(1) if build else "",
                               "source": "docs/%s/%s" % (folder, name), "t": mtime(path), "text": text})
    docs = os.path.join(project, "docs")
    for folder, _, names in os.walk(docs):
        for n in names:
            if n.endswith(".json") and re.search(r"bench|perf", n, re.I):
                p = os.path.join(folder, n)
                try:
                    data = json.loads(read(p))
                    gpu, cpu = data["gpu_ms"]["p50"], data["cpu_ms"]["p50"]
                except (ValueError, KeyError, TypeError):
                    continue
                points.append({"gpu": float(gpu), "cpu": float(cpu), "build": data.get("build", ""), "t": mtime(p), "text": "",
                               "source": os.path.relpath(p, project).replace(os.sep, "/"), "vsyncOff": data.get("vsync") == "off"})
    points.sort(key=lambda x: x["t"])  # stable: file order inside one document
    seen, unique = set(), []
    for p in points:
        if (p["gpu"], p["cpu"]) not in seen:
            seen.add((p["gpu"], p["cpu"]))
            unique.append(p)
    fps, fps_source = target_fps(project)
    out = {"points": [], "targetFps": fps, "targetSource": fps_source, "targetMs": round(1000.0 / fps, 2) if fps else None, "passes": []}
    if unique:
        last = unique[-1]
        out["passes"] = sorted(({"name": n, "now": float(a), "before": float(b)} for n, a, b in
                                re.findall(r"([A-Za-z][\w-]*) (\d+(?:\.\d+)?) \(was (\d+(?:\.\d+)?)\)", last["text"])),
                               key=lambda x: -x["now"])[:4]
        out["time"] = when(last["t"])
        out["source"] = last["source"]
        refresh = [1000.0 / hz for hz in (30, 60, 75, 90, 120, 144, 165, 240)]
        out["maybeVsync"] = not last.get("vsyncOff") and any(abs(last["cpu"] - r) < 0.25 for r in refresh)
        out["points"] = [{k: p[k] for k in ("gpu", "cpu", "build")} for p in unique[-12:]]
    return out


# ---------------------------------------------------------------- launch

def launch_skill_installed():
    home = os.path.expanduser("~")
    for root in ((".agents", "skills"), (".claude", "skills"), (".config", "opencode", "skills"), (".config", "kilo", "skills")):
        if os.path.isfile(os.path.join(home, *root, LAUNCH_SKILL, "SKILL.md")):
            return True
    return False


def launch(project):
    base = os.path.join(project, "launch")
    out = {"exists": os.path.isdir(base), "skillInstalled": launch_skill_installed(), "steps": [], "pages": [], "headline": "", "decisions": []}
    out["decisions"] = [d for d in decisions(project) if re.search(r"\b(launch|lancio|store|steam|itch|private)\b", d, re.I)][-2:]
    if not out["exists"]:
        return out
    status = read(os.path.join(base, "STATUS.md")).splitlines()
    out["headline"] = next((l.strip() for l in status[1:] if l.strip() and not l.startswith("#")), "")
    raw = os.path.isdir(os.path.join(base, "_raw")) or any(n.startswith("02-platform") for n, _ in listing(base))
    waves = [n for n, _ in listing(os.path.join(base, "fg", "waves")) if re.search(r"sintesi", n)]
    timeline = os.path.join(base, "fg", "timeline.md")
    fg = "Not started"
    if waves:
        fg = "%d wave%s" % (len(waves), "" if len(waves) == 1 else "s")
    elif os.path.isdir(os.path.join(base, "fg")):
        fg = "Started"
    todo = read(os.path.join(base, "TODO.md"))
    open_todo = len(re.findall(r"^\s*- \[ \]", todo, re.M))
    done_todo = len(re.findall(r"^\s*- \[x\]", todo, re.M | re.I))
    out["steps"] = [
        {"name": "Market check", "state": "Data on disk" if raw else "Not started"},
        {"name": "Focus group", "state": fg},
        {"name": "Launch todo", "state": "%d open, %d done" % (open_todo, done_todo) if todo else "Not started"},
    ]
    if os.path.isfile(timeline):
        rows = [l.strip() for l in read(timeline).splitlines() if l.strip().startswith(("-", "|")) and "---" not in l]
        if rows:
            out["latestWave"] = clip(re.sub(r"\s*\|\s*", ", ", rows[-1].strip("-| ")), 140)
    out["pages"] = [p for p in LAUNCH_PAGES if os.path.isfile(os.path.join(base, p))]
    return out


# ---------------------------------------------------------------- listening and the queue

def listening(project):
    t = mtime(os.path.join(project, HEARTBEAT))
    return bool(t) and abs(time.time() - t) < STALE_SECONDS


def touch_heartbeat(project):
    path = os.path.join(project, HEARTBEAT)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8"):
        pass
    os.utime(path, None)


def pending(project):
    out = []
    for line in read(os.path.join(project, QUEUE)).splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def enqueue(project, command, lock=threading.Lock()):
    path = os.path.join(project, QUEUE)
    command = dict(command, id=uuid.uuid4().hex, ts=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with lock, open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(command, ensure_ascii=False) + "\n")
    return command["id"]


def drain(project):
    """Move the queue aside first, so a command sent meanwhile lands in a new file and is not lost."""
    path = os.path.join(project, QUEUE)
    work = path + ".draining"
    if os.path.exists(path) and not os.path.exists(work):
        for attempt in range(5):
            try:
                os.replace(path, work)
                break
            except PermissionError:
                time.sleep(0.1 * (attempt + 1))
    lines = [l for l in read(work).splitlines() if l.strip()]
    if os.path.exists(work):
        os.remove(work)
    return lines


def validate_command(project, body):
    """The server looks the request up in the live project: a client can only pick from what the page offers."""
    if not listening(project):
        return None, "Claude is not listening"
    kind = body.get("type")
    if kind == "answer":
        text = body.get("text")
        need = next((n for n in tasks(project)["needs"] if n["task"] == body.get("task")), None)
        if need is None or not isinstance(text, str) or not text.strip() or len(text) > 2000:
            return None, "unknown question or empty answer"
        return {"type": "answer", "task": need["task"], "question": need["question"], "text": text.strip()}, None
    if kind == "market_check":
        info = launch(project)
        if info["exists"] or not info["skillInstalled"]:
            return None, "market check is not available"
        return {"type": "market_check"}, None
    return None, "unknown command"


# ---------------------------------------------------------------- state and server

def build_state(project):
    t = tasks(project)
    m = media(project, {r["id"] for r in parse_rows(read(os.path.join(project, "GAME_TASKS.md")))})
    recent = [(mtime(p), n) for folder in ("progress", "gates") for n, p in listing(os.path.join(project, "docs", folder))]
    recent.append((mtime(os.path.join(project, "GAME_TASKS.md")), "GAME_TASKS.md"))
    recent.extend((i["t"], i["name"]) for i in m["items"][:1])
    last = max(recent, default=(0, ""))
    g = gates(project)
    return {"project": os.path.basename(os.path.abspath(project)), "tasks": t, "gates": g, "decisions": decisions(project),
            "engineGaps": engine_gaps(project), "media": m, "performance": performance(project), "launch": launch(project),
            "listening": listening(project), "pending": pending(project),
            "lastActivity": {"time": when(last[0]), "file": last[1]} if last[0] else None}


class Handler(BaseHTTPRequestHandler):
    project = "."
    token = ""
    port = 0

    def log_message(self, *args):
        pass

    def host_ok(self):
        # A foreign site cannot reach the panel through DNS rebinding: only our own address is accepted.
        return self.headers.get("Host") in ("127.0.0.1:%d" % self.port, "localhost:%d" % self.port)

    def send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def fail(self, code, message):
        self.send(code, json.dumps({"error": message}).encode())

    def do_GET(self):
        if not self.host_ok():
            return self.fail(403, "bad host")
        url = urlparse(self.path)
        if url.path == "/favicon.ico":
            return self.send(204, b"", "image/x-icon")
        if url.path == "/":
            page = read(PAGE).replace("__TOKEN__", self.token).encode()
            csp = "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'"
            return self.send(200, page, "text/html; charset=utf-8", {"Content-Security-Policy": csp})
        if url.path == "/api/state":
            return self.send(200, json.dumps(build_state(self.project)).encode())
        if url.path == "/img":
            return self.image(parse_qs(url.query).get("p", [""])[0])
        if url.path.startswith("/launch/") and url.path[8:] in LAUNCH_PAGES:
            path = os.path.join(self.project, "launch", url.path[8:])
            if inside(path, os.path.realpath(os.path.join(self.project, "launch"))) and os.path.isfile(path):
                # Sandboxed: a generated page runs without our origin, so it cannot read the token.
                with open(path, "rb") as f:
                    return self.send(200, f.read(), "text/html; charset=utf-8", {"Content-Security-Policy": "sandbox allow-scripts"})
        self.fail(404, "not found")

    def image(self, rel):
        path = os.path.join(self.project, *rel.split("/"))
        allowed = any(media_root(self.project, r) and inside(path, media_root(self.project, r)) for r in MEDIA_ROOTS)
        if not rel or ".." in rel.split("/") or os.path.isabs(rel) or not rel.lower().endswith(IMAGE_EXT) or not allowed or not os.path.isfile(path):
            return self.fail(404, "not found")
        with open(path, "rb") as f:
            self.send(200, f.read(), mimetypes.guess_type(path)[0] or "application/octet-stream")

    def do_POST(self):
        if not self.host_ok() or self.headers.get("X-Panel-Token") != self.token:
            return self.fail(403, "forbidden")
        if urlparse(self.path).path != "/api/command":
            return self.fail(404, "not found")
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size > 8192:
                return self.fail(413, "too large")
            body = json.loads(self.rfile.read(size))
        except ValueError:
            return self.fail(400, "bad request")
        command, error = validate_command(self.project, body if isinstance(body, dict) else {})
        if error:
            return self.fail(409, error)
        self.send(200, json.dumps({"id": enqueue(self.project, command)}).encode())


def make_server(project, port):
    """Binds 127.0.0.1 only. Without an explicit port it takes the first free one from 8765."""
    token = secrets.token_urlsafe(24)
    last = None
    for candidate in ([port] if port else range(8765, 8785)):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate), type("PanelHandler", (Handler,), {}))
        except OSError as e:
            last = e
            continue
        h = server.RequestHandlerClass
        h.project, h.token, h.port = os.path.abspath(project), token, server.server_address[1]
        return server
    raise SystemExit("no free port: %s" % last)


def main():
    ap = argparse.ArgumentParser(description="Local web panel of a game project (127.0.0.1 only).")
    ap.add_argument("--project", default=".", help="game project folder (default: current folder)")
    ap.add_argument("--port", type=int, default=0, help="port (default: first free from 8765)")
    ap.add_argument("--heartbeat", nargs="?", const=0, type=int, metavar="SECONDS",
                    help="mark Claude as listening: once, or every 30 s for SECONDS, then exit")
    ap.add_argument("--drain", action="store_true", help="print and empty the command queue")
    args = ap.parse_args()
    if not os.path.isdir(args.project):
        raise SystemExit("not a folder: %s" % args.project)
    if args.drain:
        for line in drain(args.project):
            print(line)
        return
    if args.heartbeat is not None:
        end = time.time() + args.heartbeat
        touch_heartbeat(args.project)
        while time.time() + 30 < end:
            time.sleep(30)
            touch_heartbeat(args.project)
        return
    server = make_server(args.project, args.port)
    print("http://127.0.0.1:%d/" % server.server_address[1], flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
