#!/usr/bin/env python3
"""Processes and locks for ncli (standard library only): the two things that hung a whole team once.

* run_bounded: a child with a hard time limit. Its output goes to a FILE (a pipe held open by an orphaned grandchild blocks
  `communicate()` forever, even after the timeout killed the launcher) and the whole process TREE is killed on timeout.
* locks: a project lock (a JSON file, one editor driver at a time) and a machine lock (a directory made with mkdir, the same
  shape the bash tools use, so both kinds of caller exclude each other). A lock records who, since when, the pid and the longest
  time the holder may keep it; a dead pid or an exceeded hold time makes it stale. Waiting for one says who holds it and since
  when. Every lock taken here is released on ANY exit of the process (normal, exception, SIGINT/SIGTERM) and when the
  process is killed by the watchdog.
"""
import atexit
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

WIN = sys.platform.startswith("win")
CHILDREN = set()          # Popen objects started through this module (the watchdog kills them)
HELD = []                 # [(kind, path, owner)] locks this process holds
_hooks = {"installed": False}


# ----------------------------------------------------------------------------------------------------------- processes
def pid_alive(pid):
    """True / False; None when unknown (no pid). Never sends a signal: os.kill(pid, 0) would TERMINATE a process on Windows."""
    if not pid:
        return None
    pid = int(pid)
    if WIN:
        import ctypes
        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(0x1000, False, pid)           # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return k32.GetLastError() == 5               # access denied = it exists
        try:
            code = ctypes.c_ulong()
            return bool(k32.GetExitCodeProcess(h, ctypes.byref(code))) and code.value == 259   # STILL_ACTIVE
        finally:
            k32.CloseHandle(h)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def kill_tree(pid):
    """Kills a process and everything it started."""
    try:
        if WIN:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=20)
        else:
            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                os.kill(pid, signal.SIGKILL)
    except Exception:
        pass


def popen(argv, **kw):
    """Popen in its own process group / session so the tree can be killed; registered for the watchdog."""
    if WIN:
        kw["creationflags"] = kw.get("creationflags", 0) | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kw.setdefault("start_new_session", True)
    p = subprocess.Popen(argv, **kw)
    CHILDREN.add(p)
    return p


def kill_children():
    for p in list(CHILDREN):
        if p.poll() is None:
            kill_tree(p.pid)
        CHILDREN.discard(p)


def run_bounded(argv, timeout, env=None, cwd=None, log_path=None, tail=8):
    """Runs argv for at most `timeout` seconds. Output to log_path (a temp file when None). On timeout the tree is killed.
    -> {"code", "timedOut", "seconds", "log", "tail": [last lines]}"""
    own = log_path is None
    if own:
        fd, log_path = tempfile.mkstemp(prefix="ncli-run-", suffix=".log")
        os.close(fd)
    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
    t0, timed_out = time.time(), False
    with open(log_path, "wb") as lf:
        p = popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=lf, stderr=subprocess.STDOUT)
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            kill_tree(p.pid)
            try:
                p.wait(timeout=15)
            except subprocess.TimeoutExpired:
                pass
        CHILDREN.discard(p)
    with open(log_path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    lines = [l.rstrip() for l in text.splitlines() if l.strip()]
    res = {"code": 124 if timed_out else p.returncode, "timedOut": timed_out, "seconds": round(time.time() - t0, 1),
           "log": log_path, "tail": lines[-tail:], "text": text}
    return res


# ----------------------------------------------------------------------------------------------------------------- locks
def install_exit_hooks():
    """Release every held lock and kill every child on any exit of this process."""
    if _hooks["installed"]:
        return
    _hooks["installed"] = True
    atexit.register(release_all)

    def on_signal(signum, _frame):
        kill_children()
        release_all()
        os._exit(128 + (signum if isinstance(signum, int) else 2))
    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        sig = getattr(signal, name, None)
        if sig is not None:
            try:
                signal.signal(sig, on_signal)
            except (ValueError, OSError):    # not the main thread
                pass


def release_all():
    for kind, path, owner in list(HELD):
        lock_release(path, owner, kind=kind, force=True)


def _info_file(path, kind):
    return path if kind == "file" else os.path.join(path, "info.json")


def read_lock(path, kind="file"):
    """The holder's record, or None when the lock is free. A foreign directory lock (made by a bash tool) has no info.json:
    its `owner` file is read as the name and the directory time as 'since'."""
    if not os.path.exists(path):
        return None
    try:
        with open(_info_file(path, kind), encoding="utf-8") as f:
            info = json.load(f)
        info["foreign"] = False
        return info
    except (OSError, ValueError):
        pass
    name = ""
    if kind == "dir":
        try:
            with open(os.path.join(path, "owner"), encoding="utf-8", errors="replace") as f:
                name = f.read().strip()
        except OSError:
            pass
    try:
        since = os.path.getmtime(path)
    except OSError:
        since = time.time()
    return {"owner": name or "?", "since": since, "foreign": True}


def stale_reason(info, now=None):
    """Why the holder's lock may be broken, or None. Only locks made by this module (with a record) are judged: a foreign one is
    its tool's business (dead pid or a hold time are unknown)."""
    now = now or time.time()
    if info.get("foreign"):
        return None
    if info.get("pid") and pid_alive(info["pid"]) is False:
        return "holder pid %s is dead" % info["pid"]
    mh = info.get("max_hold")
    if mh and now - info.get("since", now) > mh:
        return "held for %ds, over its maximum of %ds" % (now - info["since"], mh)
    return None


def describe(info, now=None):
    now = now or time.time()
    return {"heldBy": info.get("owner"), "since": time.strftime("%H:%M:%S", time.localtime(info.get("since", now))),
            "ageS": round(now - info.get("since", now)), "pid": info.get("pid"), "cmd": info.get("cmd"),
            "maxHoldS": info.get("max_hold")}


def lock_acquire(path, owner, wait=0, kind="file", max_hold=600, pid=None, cmd=None, notify=15, say=None, poll=1.0):
    """Takes the lock (kind 'file': O_EXCL JSON file; 'dir': mkdir + info.json, `owner` file = the bare name so a bash caller
    that reads a pid from field 2 never mistakes it for a dead one). pid defaults to this process; pass pid=0 for a lock whose
    holder is a later command (ncli lock acquire ...: only the hold time applies)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    pid = os.getpid() if pid is None else pid
    record = {"owner": owner, "since": time.time(), "pid": pid or None, "max_hold": max_hold, "cmd": cmd}
    deadline, last_say = time.time() + wait, 0
    say = say or (lambda m: sys.stderr.write(m + "\n"))
    while True:
        try:
            if kind == "file":
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, json.dumps(record).encode())
                os.close(fd)
            else:
                os.mkdir(path)
                with open(os.path.join(path, "owner"), "w", encoding="utf-8") as f:
                    f.write(owner)
                with open(os.path.join(path, "info.json"), "w", encoding="utf-8") as f:
                    json.dump(record, f)
            if pid == os.getpid():
                HELD.append((kind, path, owner))
                install_exit_hooks()
            return {"locked": True, "owner": owner}
        except FileExistsError:
            pass
        info = read_lock(path, kind)
        if info is None:
            continue                                   # released between our attempt and the read
        if info.get("owner") == owner:
            return {"locked": True, "owner": owner, "reentrant": True}
        why = stale_reason(info)
        if why:
            say("lock %s: taking it over (%s; was %s)" % (os.path.basename(path), why, info.get("owner")))
            lock_release(path, info.get("owner"), kind=kind, force=True)
            continue
        if time.time() >= deadline:
            return {"locked": False, **describe(info)}
        if time.time() - last_say >= notify:
            d = describe(info)
            say("waiting for lock %s: held by %s since %s (%ds ago, pid %s, %s)" % (
                os.path.basename(path), d["heldBy"], d["since"], d["ageS"], d["pid"], d["cmd"] or "no command recorded"))
            last_say = time.time()
        time.sleep(poll)


def lock_release(path, owner, kind="file", force=False):
    info = read_lock(path, kind)
    if info is None:
        return {"released": True, "was": "free"}
    if info.get("owner") != owner and not force:
        return {"released": False, **describe(info)}
    try:
        if kind == "file":
            os.remove(path)
        else:
            shutil.rmtree(path, ignore_errors=True)
    except OSError:
        pass
    HELD[:] = [h for h in HELD if not (h[1] == path and h[2] == owner)]
    return {"released": True}


# -------------------------------------------------------------------------------------------------------------- watchdog
def start_watchdog(seconds, on_fire):
    """After `seconds` the process reports, kills its children, releases its locks and exits 124: no command hangs forever."""
    if not seconds or seconds <= 0:
        return None

    def fire():
        try:
            on_fire(seconds)
            sys.stdout.flush()
            sys.stderr.flush()
        finally:
            kill_children()
            release_all()
            os._exit(124)
    t = threading.Timer(seconds, fire)
    t.daemon = True
    t.start()
    return t
