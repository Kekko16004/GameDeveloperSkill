#!/usr/bin/env python3
"""`ncli bench`: one repeatable measurement of one level, to compare against a stored baseline (standard library only).

It reuses tools/nucleon-bench (bench.py `run_one` starts the game on the hidden desktop with vsync off and the engine's profile
lines, gds_bench.lua drives the camera and writes one CSV row per frame) and adds what a single measurement needs: one scenario,
percentiles of wall / CPU / GPU frame time, Present time, draw calls, items, a CPU / GPU attribution, the warnings that make a
number untrustworthy (another engine run alive, vsync-locked numbers, software renderer, too few frames) and the comparison
with a baseline file. Pure functions are unit tested; the run itself needs a real GPU.
"""
import argparse
import csv
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
THREADS_LINE = re.compile(r"\[threads\] frames \d+: interval ([\d.]+) ms.*?submit ([\d.]+) present ([\d.]+) ms")
CPU_FULL = re.compile(r"Modern CPU frame \d+: frame ([\d.]+) ms.*?(\d+) items.*?(\d+) draw calls.*?GPU frame ([\d.]+) ms")
SOFTWARE = re.compile(r"llvmpipe|lavapipe|swiftshader|Microsoft Basic Render|WARP|software render", re.I)
COMMON_REFRESH = (24, 30, 48, 50, 60, 72, 75, 90, 100, 120, 144, 165, 240)


def q(xs, p):
    if not xs:
        return 0.0
    s = sorted(xs)
    k = (len(s) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def dist(xs):
    if not xs:
        return None
    return {"p50": round(q(xs, .5), 2), "p95": round(q(xs, .95), 2), "p99": round(q(xs, .99), 2), "max": round(max(xs), 2)}


def find_bench_module():
    """tools/nucleon-bench/bench.py: next to the skill folder in the repository, inside it once installed."""
    skill = os.path.dirname(HERE)
    for cand in (os.path.join(skill, "tools", "nucleon-bench"), os.path.join(os.path.dirname(skill), "tools", "nucleon-bench")):
        if os.path.isfile(os.path.join(cand, "bench.py")):
            sys.path.insert(0, cand)
            import bench  # noqa: E402
            return bench
    raise RuntimeError("tools/nucleon-bench/bench.py not found next to the skill")


def engine_processes():
    """[(image, pid)] of the engine processes alive now (Nucleon, NucleonEditor)."""
    try:
        if sys.platform.startswith("win"):
            out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=20).stdout
            rows = [r.strip('"').split('","') for r in out.splitlines() if r.strip()]
            return [(r[0], int(r[1])) for r in rows if len(r) > 1 and r[0].lower() in ("nucleon.exe", "nucleoneditor.exe")]
        out = subprocess.run(["ps", "-eo", "comm=,pid="], capture_output=True, text=True, timeout=20).stdout
        return [(l.split()[0], int(l.split()[1])) for l in out.splitlines() if l.split() and l.split()[0] in ("Nucleon", "NucleonEditor")]
    except Exception:
        return []


def looks_vsynced(wall, gpu=None):
    """Frame times that sit on a refresh interval with no spread while the GPU has room to spare: the frame limiter, not the cost."""
    if not wall or len(wall) < 30:
        return None
    p50, p95 = q(wall, .5), q(wall, .95)
    for hz in COMMON_REFRESH:
        iv = 1000.0 / hz
        if abs(p50 - iv) / iv < 0.04 and (p95 - p50) / p50 < 0.06:
            if gpu and q(gpu, .5) > 0.85 * p50:
                return None          # the GPU really takes the whole interval: a cost, not a lock
            return "wall p50 %.2f ms is the %d Hz interval with almost no spread" % (p50, hz)
    return None


def summarize(rows, gpu, cpu, threads, name="bench", fps=None):
    """rows = CSV dicts of the window; gpu / cpu = lists from the profile lines; cpu items are dicts {ms, items, draws}."""
    wall = [float(r["ms"]) for r in rows]
    draw = [int(float(r["drawCalls"])) for r in rows if r.get("drawCalls") not in ("", None)] or [c["draws"] for c in cpu]
    inst = [int(float(r["instancedItems"])) for r in rows if r.get("instancedItems") not in ("", None)]
    cpu_ms = [c["ms"] for c in cpu] or [float(r["cpuFrameMs"]) for r in rows if r.get("cpuFrameMs") not in ("", None)]
    out = {"name": name, "vsync": "off", "frames": len(wall), "seconds": round(sum(wall) / 1000.0, 1),
           "wall_ms": {**(dist(wall) or {}), "fps": round(1000.0 / statistics.mean(wall), 1) if wall else 0},
           "cpu_ms": dist(cpu_ms), "gpu_ms": dist(gpu),
           "present_ms": {"mean": round(statistics.mean([t["present"] for t in threads]), 2), "max": round(max(t["present"] for t in threads), 2)} if threads else None,
           "drawCalls": {"p50": int(q(draw, .5)), "max": max(draw)} if draw else None,
           "items": {"p50": int(q([c["items"] for c in cpu], .5))} if cpu else None,
           "instancedItems": {"p50": int(q(inst, .5))} if inst else None}
    out["bound"] = attribute(out)
    if fps:
        out["budget_ms"] = round(1000.0 / fps, 2)
        out["overBudget"] = out["wall_ms"].get("p95", 0) > out["budget_ms"]
    return out


def attribute(s):
    """Where the frame goes: gpu | cpu | present (waiting on the swap chain / a limiter) | balanced."""
    wall = (s.get("wall_ms") or {}).get("p50") or 0
    g, c, p = (s.get("gpu_ms") or {}).get("p50"), (s.get("cpu_ms") or {}).get("p50"), (s.get("present_ms") or {}).get("mean")
    if p and wall and p > 0.3 * wall:
        return "present"
    if g and c:
        return "gpu" if g > 1.15 * c else ("cpu" if c > 1.15 * g else "balanced")
    return "gpu" if g else ("cpu" if c else "unknown")


METRICS = (("wall_ms", "p50"), ("wall_ms", "p95"), ("wall_ms", "p99"), ("cpu_ms", "p95"), ("gpu_ms", "p95"), ("drawCalls", "p50"))


def compare(cur, base, tol_pct=10.0):
    """delta in percent per metric (positive = slower / more); regress = the p95s that got worse by more than tol_pct."""
    deltas, regress, improved = {}, [], []
    for grp, key in METRICS:
        a, b = (cur.get(grp) or {}).get(key), (base.get(grp) or {}).get(key)
        if a is None or not b:
            continue
        d = round(100.0 * (a - b) / b, 1)
        deltas["%s.%s" % (grp, key)] = d
        if abs(d) > tol_pct and (key in ("p95", "p99") or grp == "drawCalls"):
            (regress if d > 0 else improved).append("%s.%s %+.1f%%" % (grp, key, d))
    return {"baseline": base.get("date") or base.get("name"), "deltaPct": deltas, "regress": regress, "improved": improved}


def parse_window(path, scenario):
    """gpu ms list, cpu dicts, [threads] dicts inside the GDS-BENCH begin/end window of the scenario."""
    gpu, cpu, threads, software = [], [], [], False
    inside = False
    bench = find_bench_module()
    for line in open(path, encoding="utf-8", errors="replace"):
        if SOFTWARE.search(line):
            software = True
        m = re.search(r"GDS-BENCH begin (\S+)", line)
        if m:
            inside = m.group(1) == scenario
            continue
        if "GDS-BENCH end " in line:
            inside = False
            continue
        if not inside:
            continue
        m = CPU_FULL.search(line)
        if m:
            cpu.append({"ms": float(m.group(1)), "items": int(m.group(2)), "draws": int(m.group(3))})
            continue
        m = bench.GPU_LINE.search(line)
        if m:
            frame, _ = bench.parse_gpu_items(m.group(1))
            if frame is not None:
                gpu.append(frame)
            continue
        m = THREADS_LINE.search(line)
        if m:
            threads.append({"interval": float(m.group(1)), "submit": float(m.group(2)), "present": float(m.group(3))})
    return gpu, cpu, threads, software


def scenario_from(a):
    if a.scenes:
        scenes = json.load(open(a.scenes, encoding="utf-8"))
        sc = [s for s in scenes["scenarios"] if not a.scenario or s["name"] == a.scenario]
        if not sc:
            raise RuntimeError("no scenario %s in %s" % (a.scenario, a.scenes))
        return {"scenarios": sc[:1]}
    if a.path:
        d = json.load(open(a.path, encoding="utf-8"))
        return {"scenarios": [{"name": a.name, "kind": "fly", "points": d["points"], "speed": d.get("speed", a.speed)}]}
    if a.view:
        v = [float(x) for x in a.view.split(",")]
        if len(v) != 6:
            raise RuntimeError("--view x,y,z,tx,ty,tz (Z up)")
        return {"scenarios": [{"name": a.name, "kind": "view", "position": v[:3], "lookAt": v[3:], "seconds": a.seconds}]}
    raise RuntimeError("give the camera: --view x,y,z,tx,ty,tz, or --path file.json (points + speed), or --scenes file.json")


def run(a, engine_dir, say=print):
    """Runs the scenario and returns the summary dict (no printing)."""
    bench = find_bench_module()
    runtime, desktop = bench.find_runtime(engine_dir)
    proj = os.path.abspath(a.project)
    out_dir = os.path.join(proj, "Saved", "bench", time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(out_dir, exist_ok=True)
    scenes = scenario_from(a)
    name = scenes["scenarios"][0]["name"]
    ns = argparse.Namespace(project=proj, gpu_every=a.gpu_every, warmup=a.warmup, load_wait=a.load_wait, quality=a.quality,
                            timeout=a.timeout, xvfb=False)
    cfg = {"env": {"NC_THREAD_STATS": str(a.gpu_every * 6), "NC_D3D12_VSYNC": "0", "NC_UPSCALER": "off"}}
    before = engine_processes()
    r = bench.run_one(ns, runtime, desktop, "bench", cfg, scenes, out_dir, 1)
    during = engine_processes()
    rundir = os.path.join(out_dir, "bench")
    csv_path = os.path.join(rundir, "frames-1.csv")
    if not os.path.exists(csv_path):
        raise RuntimeError("the run produced no frames (started=%s done=%s errors=%s): see %s" % (r["started"], r["done"], r["errors"], rundir))
    rows = [x for x in csv.DictReader(open(csv_path, encoding="utf-8")) if x["scenario"] == name]
    gpu, cpu, threads, software = parse_window(os.path.join(rundir, "run-1.log"), name)
    summary = summarize(rows, gpu, cpu, threads, name, a.fps)
    summary.update({"date": time.strftime("%Y-%m-%d %H:%M"), "engine": runtime, "scenario": scenes["scenarios"][0], "run": rundir})
    w = []
    if before:
        w.append("another engine process was alive before the run (%s): the numbers may include its load" % ", ".join("%s:%d" % p for p in before))
    if len(during) > 1:
        w.append("%d engine processes were alive during the run: another run shared the GPU" % len(during))
    sync = looks_vsynced([float(x["ms"]) for x in rows], gpu)
    if sync:
        w.append("numbers look vsync-locked (%s): check NC_D3D12_VSYNC=0 reached the game and the display is not capping" % sync)
    if software:
        w.append("software renderer in the log: these numbers say nothing about a real GPU")
    if summary["frames"] < a.min_frames:
        w.append("only %d frames (< %d): p99 is not meaningful, raise --seconds" % (summary["frames"], a.min_frames))
    if not gpu:
        w.append("no GPU timings in the log (NC_GPU_PROFILE lines): gpu_ms is empty")
    if not r["done"]:
        w.append("the bench script did not finish (done=false): %s" % (r["errors"] or "see the log"))
    summary["warnings"] = w
    return summary
