#!/usr/bin/env python3
"""Nucleon performance bench: measure, find the cause, write the fix plan (GameDeveloperSkill tools/nucleon-bench).

  python bench.py grab-view NAME --project P --scenes scenes.json   the editor's current camera -> a "view" scenario
  python bench.py run --engine <bin dir> --project P --scenes scenes.json [--only H1,H2] [--repeat 2] [--out results/x]
  python bench.py analyze results/x                                  -> results/x/REPORT.md + results.json
  python bench.py plan results/x                                     -> results/x/EXECUTION-PLAN.md (briefs for Claude Code)

`run` starts the game (Nucleon -nosetup, the project's main.lua or nc.game.run) once per config of configs.json: the base,
then one change per hypothesis H1-H9. gds_bench.lua (copied into Content/Scripts for the run, removed after) drives the camera
through the scenarios of scenes.json and writes one CSV row per frame; the engine's NC_GPU_PROFILE lines give the GPU passes of
each scenario window and NC_PROFILE_REPORT the slowest frames with their CPU zones. On Windows nc_desktop_run.exe (next to
Nucleon.exe) runs every game on a hidden desktop; without it the window shows (do not touch the PC while it runs).
Standard library only. The project is not modified (saves and DDC go to the out folder; the two GDS files are removed).
"""
import argparse
import csv
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_SCRIPTS = os.path.join(os.path.dirname(HERE), "..", "game-developer", "scripts")


# ------------------------------------------------------------------------------------------------ helpers
LUA_KEYWORDS = {"and", "break", "do", "else", "elseif", "end", "false", "for", "function", "goto", "if", "in", "local", "nil", "not",
                "or", "repeat", "return", "then", "true", "until", "while"}


def to_lua(v):
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
    return "{" + ", ".join(("%s = %s" % (k, to_lua(x))) if re.match(r"^[A-Za-z_]\w*$", k) and k not in LUA_KEYWORDS else "[%s] = %s" % (json.dumps(k), to_lua(x))
                           for k, x in v.items()) + "}"


def find_runtime(engine):
    e = os.path.abspath(engine)
    if os.path.isfile(e):
        e = os.path.dirname(e)
    for name in ("Nucleon.exe", "Nucleon"):
        if os.path.isfile(os.path.join(e, name)):
            return os.path.join(e, name), (os.path.join(e, "nc_desktop_run.exe") if os.path.isfile(os.path.join(e, "nc_desktop_run.exe")) else None)
    raise SystemExit("no Nucleon runtime in %s (pass the folder of Nucleon.exe, e.g. build-msvc/bin)" % e)


def pct(a, b):
    return None if not b else round(100.0 * (a - b) / b, 1)


def quantile(xs, q):
    if not xs:
        return 0.0
    s = sorted(xs)
    k = (len(s) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


# ------------------------------------------------------------------------------------------------ grab-view
def cmd_grab_view(a):
    sys.path.insert(0, os.path.abspath(SKILL_SCRIPTS))
    import ncli   # the skill's MCP client (HTTP to the open editor, or --stdio)
    args = argparse.Namespace(project=a.project, port=None, token=None, stdio=a.stdio, no_lua=False, timeout=60)
    ed = ncli.connect(args)
    st = ed.call("editor_state")
    cam = st.get("camera") or {}
    pos, fwd = cam.get("position"), cam.get("forward")
    if not pos or not fwd:
        raise SystemExit("editor_state has no camera")
    look = [pos[i] + fwd[i] * 10 for i in range(3)]
    scenes = json.load(open(a.scenes, encoding="utf-8")) if os.path.exists(a.scenes) else {"scenarios": []}
    scenes["scenarios"] = [s for s in scenes["scenarios"] if s.get("name") != a.name]
    entry = {"name": a.name, "kind": "view", "position": [round(x, 3) for x in pos], "lookAt": [round(x, 3) for x in look], "seconds": a.seconds}
    scenes["scenarios"].append(entry)
    json.dump(scenes, open(a.scenes, "w", encoding="utf-8"), indent=1)
    print(json.dumps({"added": entry, "scenes": a.scenes}))


# ------------------------------------------------------------------------------------------------ run
def matrix(configs, only):
    shots = any(h.get("shots") for hid, h in configs["hypotheses"].items() if not only or hid in only)
    rows = [("base", "base", dict(configs["base"], shots=shots))]
    for hid, h in configs["hypotheses"].items():
        if only and hid not in only:
            continue
        for name, cfg in h["configs"].items():
            rows.append((hid, name, dict(cfg, shots=h.get("shots", False))))
    return rows


def run_one(a, runtime, desktop, label, cfg, scenes, out_dir, run_idx):
    proj = os.path.abspath(a.project)
    rundir = os.path.join(out_dir, label)
    os.makedirs(rundir, exist_ok=True)
    scripts = os.path.join(proj, "Content", "Scripts")
    os.makedirs(scripts, exist_ok=True)
    bench_lua = os.path.join(scripts, "zz_gds_bench.lua")
    plan_path = os.path.join(proj, "Saved", "gds-bench.lua")
    os.makedirs(os.path.dirname(plan_path), exist_ok=True)
    launcher = os.path.join(proj, "gds_bench_main.lua")
    shutil.copyfile(os.path.join(HERE, "gds_bench.lua"), bench_lua)
    rel_out = "Saved/gds-bench-%s-%d" % (label, run_idx)
    plan = {"label": label, "out": rel_out, "warmup": a.warmup, "maxLoadWait": a.load_wait, "scenarios": scenes["scenarios"],
            "quality": a.quality}
    for k in ("lighting", "virtual", "lodBias", "graphics", "resolutionScale", "gi", "reflections", "upscaling"):
        if k in cfg:
            plan[k] = cfg[k]
    if cfg.get("shots"):
        plan["shot"] = rel_out + ".png"
    open(plan_path, "w", encoding="utf-8").write("return " + to_lua(plan) + "\n")
    has_main = os.path.exists(os.path.join(proj, "main.lua"))
    open(launcher, "w", encoding="utf-8").write(
        "-- GameDeveloperSkill bench launcher (removed after the run)\n" +
        ('dofile("main.lua")\n' if has_main else 'require("nc.game").run()\n'))
    env = dict(os.environ)
    env.update({"NC_GPU_PROFILE": str(a.gpu_every), "NC_D3D12_VSYNC": "0", "NC_LOAD_BACKGROUND": "1",
                "NC_SAVE_DIR": os.path.join(out_dir, "_save"), "NC_DDC_DIR": os.path.join(out_dir, "_ddc"),
                "NC_PROFILE_REPORT": os.path.join(rundir, "profile-%d.txt" % run_idx), "NC_PROFILE_REPORT_SKIP": "0",
                "NC_PROFILE_REPORT_FRAMES": "100000", "NC_PROFILE_REPORT_SLOW": "12"})
    env.update({k: str(v) for k, v in cfg.get("env", {}).items()})
    cmd = [runtime, "-nosetup", launcher]
    if desktop:
        env["NC_UNATTENDED"] = "1"
        cmd = [desktop, "--"] + cmd
    elif a.xvfb and shutil.which("xvfb-run"):
        env["NC_UNATTENDED"] = "1"
        cmd = ["xvfb-run", "-a", "-s", "-screen 0 1920x1080x24"] + cmd
    log_path = os.path.join(rundir, "run-%d.log" % run_idx)
    t0 = time.time()
    try:
        with open(log_path, "wb") as lf:
            p = subprocess.run(cmd, cwd=proj, env=env, stdout=lf, stderr=subprocess.STDOUT, timeout=a.timeout)
        code = p.returncode
    except subprocess.TimeoutExpired:
        code = "timeout"
    finally:
        for f in (bench_lua, launcher, plan_path):
            try:
                os.remove(f)
            except OSError:
                pass
    for ext in (".csv", ".png"):
        src = os.path.join(proj, rel_out + ext)
        if os.path.exists(src):
            shutil.move(src, os.path.join(rundir, "frames-%d%s" % (run_idx, ext)))
    log = open(log_path, encoding="utf-8", errors="replace").read()
    done = "GDS-BENCH DONE" in log
    return {"label": label, "run": run_idx, "code": code, "seconds": round(time.time() - t0, 1), "done": done,
            "started": "GDS-BENCH start" in log, "errors": re.findall(r"GDS-BENCH (?:error|skip) .*", log)[:5]}


def cmd_run(a):
    runtime, desktop = find_runtime(a.engine)
    configs = json.load(open(a.configs, encoding="utf-8"))
    scenes = json.load(open(a.scenes, encoding="utf-8"))
    out_dir = os.path.abspath(a.out or os.path.join(HERE, "results", time.strftime("%Y%m%d-%H%M")))
    os.makedirs(out_dir, exist_ok=True)
    only = set(a.only.split(",")) if a.only else None
    rows = matrix(configs, only)
    json.dump({"project": os.path.abspath(a.project), "engine": runtime, "scenes": scenes, "configs": configs, "rows": [r[:2] for r in rows],
               "quality": a.quality, "repeat": a.repeat, "date": time.strftime("%Y-%m-%d %H:%M")},
              open(os.path.join(out_dir, "meta.json"), "w"), indent=1)
    if a.warm_run:   # one unmeasured run first: shader cache and DDC (the first cook would look like a hitch storm)
        print(json.dumps({"warm": run_one(a, runtime, desktop, "_warm", configs["base"], scenes, out_dir, 0)}))
    status = []
    for rep in range(1, a.repeat + 1):
        for hid, label, cfg in rows:
            r = run_one(a, runtime, desktop, label, cfg, scenes, out_dir, rep)
            r["hypothesis"] = hid
            status.append(r)
            print(json.dumps(r))
            if not r["started"] and not r["errors"]:
                print(json.dumps({"warning": "the bench script did not start: the project's main.lua does not run Content/Scripts "
                                             "(nc.game.run). See README 'Projects with their own main.lua'."}))
    json.dump(status, open(os.path.join(out_dir, "status.json"), "w"), indent=1)
    print(json.dumps({"out": out_dir, "runs": len(status), "ok": sum(1 for s in status if s["done"]),
                      "next": "python bench.py analyze %s && python bench.py plan %s" % (out_dir, out_dir)}))


# ------------------------------------------------------------------------------------------------ analyze
GPU_LINE = re.compile(r"GPU timings at frame \d+: (.*)$")
CPU_LINE = re.compile(r"Modern CPU frame \d+: frame ([\d.]+) ms")


def parse_gpu_items(text):
    """'frame 747.84 ms,   sky 40.57 ms,     shadow-sun 38.81 ms, ...' -> (frame ms, {top level pass: ms}); the depth is the indent."""
    frame, passes = None, {}
    for item in text.split(","):
        m = re.match(r"^( *)(.+?) (\d+(?:\.\d+)?) ms\s*$", item)
        if not m:
            continue
        name, ms, indent = m.group(2).strip(), float(m.group(3)), len(m.group(1))
        if frame is None and name == "frame":
            frame = ms
        elif indent <= 3:
            passes[name] = passes.get(name, 0.0) + ms
    return frame, passes


def parse_log(path):
    """{scenario: {"gpu": [frame ms], "cpu": [ms], "passes": {name: [ms]}}} from the windows marked by gds_bench.lua."""
    out, cur = {}, None
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        m = re.search(r"GDS-BENCH begin (\S+)", line)
        if m:
            cur = m.group(1)
            out.setdefault(cur, {"gpu": [], "cpu": [], "passes": {}})
            continue
        if "GDS-BENCH end " in line:
            cur = None
            continue
        if cur is None:
            continue
        m = CPU_LINE.search(line)
        if m:
            out[cur]["cpu"].append(float(m.group(1)))
            continue
        m = GPU_LINE.search(line)
        if m:
            frame, passes = parse_gpu_items(m.group(1))
            if frame is not None:
                out[cur]["gpu"].append(frame)
            for k, v in passes.items():
                out[cur]["passes"].setdefault(k, []).append(v)
    return out


def parse_slow(path):
    """The 'slowest frames' block of NC_PROFILE_REPORT (main thread zones of the worst frames), cut short."""
    if not os.path.exists(path):
        return []
    lines, take = [], False
    for l in open(path, encoding="utf-8", errors="replace"):
        if l.startswith("slowest frames"):
            take = True
            continue
        if take:
            if not l.strip():
                break
            lines.append(l.rstrip()[:220])
    return lines[:12]


def parse_counters(path):
    """The 'counters' block of NC_PROFILE_REPORT -> {"group: name": [avg per frame, max]} (names that are not text are skipped)."""
    out = {}
    if not os.path.exists(path):
        return out
    take = False
    for l in open(path, encoding="utf-8", errors="replace"):
        if l.startswith("counters"):
            take = True
            continue
        if not take:
            continue
        m = re.match(r"^  ([^:]+): (.*)$", l.rstrip())
        if not m:
            continue
        for part in m.group(2).split(";"):
            p = re.match(r"^\s*(.+?) ([\d.]+)(?: ms| MB)? \(max ([\d.]+)", part)
            if p and p.group(1).isprintable() and "\ufffd" not in p.group(1):
                out["%s: %s" % (m.group(1), p.group(1))] = [float(p.group(2)), float(p.group(3))]
    return out


WATCH_COUNTERS = ("modern: srgb copies (readback)", "async update: model texture rebuilds", "scene model: first draw KB made",
                  "pipelines: made over 20 ms", "gd: list rebuilds", "sun shadow: pages drawn whole (no cache)")


def frame_stats(rows):
    ms = [float(r["ms"]) for r in rows]
    if not ms:
        return None
    p50 = quantile(ms, 0.5)
    hitch_th = max(2 * p50, p50 + 10)
    hitch = [r for r in rows if float(r["ms"]) > hitch_th]
    dur = sum(ms) / 1000.0
    prev_up = None
    tex_up_frames, page_frames = set(), set()
    for r in rows:   # texture uploads are cumulative: a frame "uploads" when the counter moved
        up = int(float(r["texUploads"] or 0))
        if prev_up is not None and up > prev_up:
            tex_up_frames.add(r["frame"])
        prev_up = up
        if int(float(r["pageLoads"] or 0)) > 0:
            page_frames.add(r["frame"])
    hf = {r["frame"] for r in hitch}
    nf = {r["frame"] for r in rows} - hf

    def share(frames, sel):
        return round(100.0 * len(frames & sel) / len(sel), 1) if sel else 0.0
    worst = sorted(rows, key=lambda r: -float(r["ms"]))[:5]
    return {"frames": len(ms), "seconds": round(dur, 2), "mean_ms": round(statistics.mean(ms), 2), "p50_ms": round(p50, 2),
            "p95_ms": round(quantile(ms, 0.95), 2), "p99_ms": round(quantile(ms, 0.99), 2), "max_ms": round(max(ms), 2),
            "fps": round(1000.0 / statistics.mean(ms), 1), "hitches": len(hitch), "hitches_per_10s": round(10 * len(hitch) / dur, 2) if dur else 0,
            "hitch_threshold_ms": round(hitch_th, 1),
            "hitch_with_texture_uploads_pct": share(tex_up_frames, hf), "other_with_texture_uploads_pct": share(tex_up_frames, nf),
            "hitch_with_page_loads_pct": share(page_frames, hf), "other_with_page_loads_pct": share(page_frames, nf),
            "pool_used_mb_max": round(max(float(r["poolUsedMB"] or 0) for r in rows), 1),
            "texture_mb_max": round(max(float(r["texMB"] or 0) for r in rows), 1),
            "worst": [{"frame": int(r["frame"]), "ms": round(float(r["ms"]), 1), "pageLoads": int(float(r["pageLoads"] or 0)),
                       "texUploads": int(float(r["texUploads"] or 0)), "streamingTextures": int(float(r["streamingTextures"] or 0))} for r in worst]}


def scenario_kind(name, scenes):
    base = name.split("#")[0]
    for s in scenes["scenarios"]:
        if s["name"] == base:
            return s["kind"]
    return "view"


def load_label(out_dir, label):
    """Median over repeats of the per scenario stats + GPU passes of one config."""
    d = os.path.join(out_dir, label)
    per = {}
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        m = re.match(r"frames-(\d+)\.csv$", f)
        if not m:
            continue
        run = m.group(1)
        rows = list(csv.DictReader(open(os.path.join(d, f), encoding="utf-8")))
        by = {}
        for r in rows:
            by.setdefault(r["scenario"], []).append(r)
        gpu = parse_log(os.path.join(d, "run-%s.log" % run)) if os.path.exists(os.path.join(d, "run-%s.log" % run)) else {}
        for sc, rr in by.items():
            st = frame_stats(rr)
            g = gpu.get(sc, {})
            st["gpu_frame_ms"] = round(statistics.median(g["gpu"]), 2) if g.get("gpu") else None
            st["cpu_render_ms"] = round(statistics.median(g["cpu"]), 2) if g.get("cpu") else None
            st["gpu_passes_ms"] = {k: round(statistics.median(v), 2) for k, v in sorted(g.get("passes", {}).items(),
                                                                                       key=lambda kv: -statistics.median(kv[1]))[:12]}
            per.setdefault(sc, []).append(st)
    merged = {}
    for sc, runs in per.items():
        if len(runs) == 1:
            merged[sc] = runs[0]
            continue
        m = dict(runs[0])
        for k in ("mean_ms", "p50_ms", "p95_ms", "p99_ms", "max_ms", "fps", "hitches", "hitches_per_10s"):
            m[k] = round(statistics.median([r[k] for r in runs]), 2)
        m["runs"] = len(runs)
        merged[sc] = m
    slow, counters = [], {}
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if f.startswith("profile-"):
            slow = parse_slow(os.path.join(d, f))
            allc = parse_counters(os.path.join(d, f))
            counters = {k: v for k, v in allc.items() if k in WATCH_COUNTERS}
            break
    return merged, slow, counters


def verdicts(res, configs, scenes):
    base = res["base"]["scenarios"]
    out = {}

    def delta(label, kinds, key):
        """mean % change of `key` over the scenarios of those kinds (negative = better)."""
        if label not in res:
            return None
        ds = []
        for sc, st in res[label]["scenarios"].items():
            if scenario_kind(sc, scenes) in kinds and sc in base and base[sc].get(key):
                ds.append(pct(st[key], base[sc][key]))
        ds = [x for x in ds if x is not None]
        return round(statistics.mean(ds), 1) if ds else None

    def corr(kind_list, key_hit, key_other):
        vals = [(st[key_hit], st[key_other]) for sc, st in base.items() if scenario_kind(sc, scenes) in kind_list and st["hitches"] >= 3]
        return (round(statistics.mean(v[0] for v in vals), 1), round(statistics.mean(v[1] for v in vals), 1)) if vals else (None, None)

    def gpu_share(names):
        shares = []
        for sc, st in base.items():
            gp, tot = st.get("gpu_passes_ms") or {}, st.get("gpu_frame_ms")
            if gp and tot:
                shares.append(100.0 * sum(v for k, v in gp.items() if any(n in k.lower() for n in names)) / tot)
        return round(statistics.mean(shares), 1) if shares else None

    hit, oth = corr(["approach"], "hitch_with_texture_uploads_pct", "other_with_texture_uploads_pct")
    h1 = delta("tex-low", ["approach"], "hitches")
    srgb = res["base"].get("counters", {}).get("modern: srgb copies (readback)")
    sr = delta("srgb-readback", ["approach"], "hitches")
    out["H1"] = {"confirmed": bool((h1 is not None and h1 <= -50) or (hit is not None and hit >= 50 and oth <= 20)),
                 "srgb_readback": bool(srgb and srgb[1] >= 1 and sr is not None and sr >= 25),
                 "evidence": {"tex-low hitches %": h1, "tex-upload-budget hitches %": delta("tex-upload-budget", ["approach"], "hitches"),
                              "base srgb readback copies [avg/frame, max]": srgb, "srgb-readback (NC_SRGB_VIEW=0) hitches %": sr,
                              "approach hitch frames with texture uploads %": hit, "other frames %": oth}}
    hp, op = corr(["approach", "fly"], "hitch_with_page_loads_pct", "other_with_page_loads_pct")
    r = delta("vgeo-resident", ["approach", "fly"], "hitches")
    p = delta("vgeo-pool-512", ["approach", "fly"], "hitches")
    out["H2"] = {"confirmed": bool(min([x for x in (r, p) if x is not None] or [0]) <= -50 or (hp is not None and hp >= 50 and op <= 25)),
                 "evidence": {"vgeo-resident hitches %": r, "vgeo-pool-512 hitches %": p, "vgeo-loads-64 hitches %": delta("vgeo-loads-64", ["approach", "fly"], "hitches"),
                              "hitch frames with page loads %": hp, "other frames %": op}}
    v = delta("vgeo-off", ["view", "approach"], "p50_ms")
    out["H3"] = {"confirmed": v is not None and v <= -15, "refuted": v is not None and v >= 15,
                 "evidence": {"vgeo-off p50 %": v, "vgeo-forward p50 %": delta("vgeo-forward", ["view", "approach"], "p50_ms")}}
    s = delta("shadows-off", ["view", "fly"], "p50_ms")
    sh = gpu_share(["shadow", "vsm", "cascade"])
    out["H4"] = {"confirmed": bool((s is not None and s <= -25) or (sh is not None and sh >= 30)),
                 "evidence": {"shadows-off p50 % (bound)": s, "shadow passes % of GPU frame": sh,
                              **{"%s p50 %%" % k: delta(k, ["view", "fly"], "p50_ms") for k in ("shadows-low", "vshadows-classic", "gd-shadow-plan-off", "wind-off", "wind-shadow-15m")}}}
    l = delta("lod-coarsest", ["view", "fly"], "p50_ms")
    out["H5"] = {"confirmed": l is not None and l <= -25,
                 "evidence": {"lod-coarsest p50 % (bound)": l, "lod-bias-2 p50 %": delta("lod-bias-2", ["view", "fly"], "p50_ms"),
                              "gpu-lod p50 %": delta("gpu-lod", ["view", "fly"], "p50_ms")}}
    fo = delta("foliage-low", ["view"], "p50_ms")
    rs = delta("resolution-50", ["view"], "p50_ms")
    out["H6"] = {"confirmed": bool(fo is not None and fo <= -20 and rs is not None and rs <= -20),
                 "evidence": {"foliage-low p50 % (bound)": fo, "resolution-50 p50 %": rs,
                              "prepass-masked-on p50 %": delta("prepass-masked-on", ["view"], "p50_ms"),
                              "prepass-masked-off p50 %": delta("prepass-masked-off", ["view"], "p50_ms")}}
    g = delta("gi-off", ["view"], "p50_ms")
    out["H7"] = {"confirmed": g is not None and g <= -15,
                 "evidence": {"gi-off p50 % (bound)": g, "gi-no-vegetation p50 %": delta("gi-no-vegetation", ["view"], "p50_ms"),
                              "reflections-ssr p50 %": delta("reflections-ssr", ["view"], "p50_ms"), "GI/Lumen % of GPU frame": gpu_share(["gi", "lumen", "probe"])}}
    u = delta("vgeo-unified", ["view"], "p50_ms")
    diff = res.get("_shots", {}).get("instancing-off")
    gdiff = res.get("_shots", {}).get("gpu-driven-off")
    out["H8"] = {"confirmed": bool((u is not None and u <= -10) or (diff is not None and diff > 1.0)),
                 "a1_path": None if diff is None or diff <= 1.0 else ("gpu-driven" if gdiff is not None and gdiff > 1.0 else "instance classes / instanced shaders"),
                 "evidence": {"vgeo-unified p50 %": u, "instancing-off p50 %": delta("instancing-off", ["view"], "p50_ms"),
                              "gpu-driven-off p50 %": delta("gpu-driven-off", ["view"], "p50_ms"),
                              "gpu-driven-off vs base picture difference %": gdiff,
                              "retained-off p50 %": delta("retained-off", ["view"], "p50_ms"), "gpu-occlusion p50 %": delta("gpu-occlusion", ["view"], "p50_ms"),
                              "instancing-off vs base picture difference %": diff}}
    mo = delta("models-off", ["view", "fly"], "p50_ms")
    so = delta("sets-off", ["view", "fly"], "p50_ms")
    out["H10"] = {"confirmed": bool((mo is not None and mo <= -10) or (so is not None and so <= -5)),
                  "evidence": {"models-off p50 % (bound)": mo, "sets-off p50 %": so, "wpo-off p50 %": delta("wpo-off", ["view", "fly"], "p50_ms"),
                               "layers-off p50 %": delta("layers-off", ["view", "fly"], "p50_ms"),
                               "deferred-models-off p50 %": delta("deferred-models-off", ["view", "fly"], "p50_ms"),
                               "models-off vs base picture difference %": res.get("_shots", {}).get("models-off")}}
    out["H9"] = {"pixel_bound": rs is not None and rs <= -30, "cpu_or_geometry_bound": rs is not None and rs > -10,
                 "evidence": {"resolution-50 p50 %": rs, "fsr-quality p50 %": delta("fsr-quality", ["view"], "p50_ms"),
                              "fsr-performance p50 %": delta("fsr-performance", ["view"], "p50_ms")}}
    for hid in out:
        out[hid]["title"] = configs["hypotheses"].get(hid, {}).get("title", hid)
    return out


def png_diff(a, b):
    """% of pixels that differ by more than 24/255 (Pillow if installed; None otherwise)."""
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return None
    if not (os.path.exists(a) and os.path.exists(b)):
        return None
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        ib = ib.resize(ia.size)
    d = ImageChops.difference(ia, ib).convert("L").point(lambda x: 255 if x > 24 else 0)
    return round(100.0 * sum(1 for p in d.getdata() if p) / (ia.size[0] * ia.size[1]), 2)


def cmd_analyze(a):
    out_dir = os.path.abspath(a.out)
    meta = json.load(open(os.path.join(out_dir, "meta.json"), encoding="utf-8"))
    res = {}
    for hid, label in meta["rows"]:
        sc, slow, counters = load_label(out_dir, label)
        if sc:
            res[label] = {"hypothesis": hid, "scenarios": sc, "slow_frames": slow, "counters": counters}
    if "base" not in res:
        raise SystemExit("no measured base run in %s" % out_dir)
    shots = {}
    base_png = os.path.join(out_dir, "base", "frames-1.png")
    for label in res:
        p = os.path.join(out_dir, label, "frames-1.png")
        if label != "base" and os.path.exists(p):
            shots[label] = png_diff(base_png, p)
    res["_shots"] = shots
    v = verdicts(res, meta["configs"], meta["scenes"])
    json.dump({"meta": meta, "results": res, "verdicts": v}, open(os.path.join(out_dir, "results.json"), "w"), indent=1)
    L = ["# Nucleon bench report", "", "Project `%s` · %s · quality %s · %d run(s) per config" % (meta["project"], meta["date"], meta["quality"], meta["repeat"]), ""]
    L += ["## Base", "", "| scenario | fps | p50 ms | p95 ms | p99 ms | max ms | hitches/10 s | GPU frame ms | top GPU passes (ms) |", "|---|---|---|---|---|---|---|---|---|"]
    for sc, st in res["base"]["scenarios"].items():
        top = ", ".join("%s %.1f" % kv for kv in list((st.get("gpu_passes_ms") or {}).items())[:4])
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (sc, st["fps"], st["p50_ms"], st["p95_ms"], st["p99_ms"], st["max_ms"],
                                                                st["hitches_per_10s"], st.get("gpu_frame_ms"), top))
    L += ["", "## Verdicts", ""]
    for hid, vv in v.items():
        flag = "CONFIRMED" if vv.get("confirmed") else ("REFUTED" if vv.get("refuted") else ("PIXEL BOUND" if vv.get("pixel_bound") else
               ("CPU/GEOMETRY BOUND" if vv.get("cpu_or_geometry_bound") else "not confirmed")))
        L.append("- **%s %s** — %s · %s" % (hid, flag, vv["title"], json.dumps(vv["evidence"])))
    L += ["", "## Every config against base (p50 / hitches, %)", "", "| config | hypothesis | " + " | ".join(res["base"]["scenarios"]) + " |",
          "|---|---|" + "---|" * len(res["base"]["scenarios"])]
    for label, r in res.items():
        if label in ("base", "_shots"):
            continue
        cells = []
        for sc, bst in res["base"]["scenarios"].items():
            st = r["scenarios"].get(sc)
            cells.append("%s / %s" % (pct(st["p50_ms"], bst["p50_ms"]), pct(st["hitches"], bst["hitches"]) if bst["hitches"] else "-") if st else "-")
        L.append("| %s | %s | %s |" % (label, r["hypothesis"], " | ".join(cells)))
    if res["base"].get("counters"):
        L += ["", "## Watched engine counters of base (avg per frame / max)", ""] + ["- %s: %s / %s" % (k, v[0], v[1]) for k, v in res["base"]["counters"].items()]
    if res["base"].get("slow_frames"):
        L += ["", "## Slowest frames of base (NC_PROFILE_REPORT)", "", "```"] + res["base"]["slow_frames"] + ["```"]
    L += ["", "Next: `python bench.py plan %s` writes EXECUTION-PLAN.md with the briefs of the confirmed causes only." % out_dir]
    open(os.path.join(out_dir, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(json.dumps({"report": os.path.join(out_dir, "REPORT.md"), "confirmed": [h for h, x in v.items() if x.get("confirmed")]}))


# ------------------------------------------------------------------------------------------------ plan
def cmd_plan(a):
    out_dir = os.path.abspath(a.out)
    data = json.load(open(os.path.join(out_dir, "results.json"), encoding="utf-8"))
    briefs = json.load(open(os.path.join(HERE, "briefs.json"), encoding="utf-8"))
    v = data["verdicts"]
    base = data["results"]["base"]["scenarios"]

    def gain(hid):   # order by the best measured improvement of the hypothesis' configs
        best = 0
        for label, r in data["results"].items():
            if label.startswith("_") or r.get("hypothesis") != hid:
                continue
            for sc, st in r["scenarios"].items():
                b = base.get(sc)
                if b:
                    best = min(best, pct(st["p50_ms"], b["p50_ms"]) or 0, pct(st["hitches"], b["hitches"]) or 0 if b["hitches"] else 0)
        return best
    chosen = [h for h in v if v[h].get("confirmed")]
    if not a.no_known:
        chosen += [k for k in briefs if k.startswith("K") and k not in chosen]
    chosen.sort(key=lambda h: gain(h) if h.startswith("H") else -1000)   # known bugs first, then by measured gain
    if v.get("H9", {}).get("pixel_bound"):
        bound = "the frame is **pixel bound** (half resolution: %s %% on p50): GPU passes and overdraw first." % v["H9"]["evidence"]["resolution-50 p50 %"]
    elif v.get("H9", {}).get("cpu_or_geometry_bound"):
        bound = "the frame is **CPU or geometry bound** (half resolution changes little): culling, draw submission, LOD, CPU zones first."
    else:
        bound = "between pixel and geometry bound (see H9)."
    L = ["# Nucleon — execution plan from the bench (%s)" % data["meta"]["date"], "",
         "Generated by `tools/nucleon-bench/bench.py plan` from `%s/results.json`. Only the causes the numbers confirmed are here, in order of measured gain; "
         "each section is a brief to paste into Claude Code **in the NucleonEngine repository** (it follows the repo's CLAUDE.md)." % out_dir, "",
         "Shape of the frame: " + bound, "",
         "## Rules for every brief (from the engine's CLAUDE.md and the owner's workflow)", "",
         "- One branch + one PR per brief (`perf/<id>-<slug>`), merged when the owner says so; commit messages in English with the harness attribution.",
         "- Every change keeps a switch back to the old code (`NC_<NAME>=0`), as the ForestDemo waves do, and is measured A/B in one run (`NC_AB_FLIP`) when possible.",
         "- Verify on Windows (MSVC Release, D3D12): `tools/verify/windows.ps1 -Changed -BuildDir build-msvc`; never GitHub Actions.",
         "- Done = the acceptance numbers below, re-measured with `python tools/nucleon-bench/bench.py run ... --only <H>` (GameDeveloperSkill) on the same scene and GPU, "
         "plus the screenshots unchanged (`tests/cook/pngdiff.py`). Report what was not verified.", ""]
    for hid in chosen:
        b = briefs.get(hid)
        if not b:
            continue
        ev = v.get(hid, {}).get("evidence", {})
        L += ["## %s — %s" % (hid, b["title"]), "",
              "**Why (measured):** " + (json.dumps(ev) if ev else b.get("evidence", "")), "",
              "**Where:** " + ", ".join("`%s`" % f for f in b["files"]), "",
              "**What to do:**", ""] + ["%d. %s" % (i + 1, s) for i, s in enumerate(b["steps"])] + [
              "", "**Acceptance:**", ""] + ["- " + s for s in b["acceptance"]] + [
              "", "**Branch:** `%s`" % b["branch"], "", "<details><summary>Prompt for Claude Code</summary>", "", "```text", b["prompt"].format(evidence=json.dumps(ev)), "```", "", "</details>", ""]
    if not [h for h in chosen if h.startswith("H")]:
        L += ["## No measured cause confirmed", "", "Check REPORT.md: the scenarios may not reproduce the problem (add the exact spot with `bench.py grab-view`), or the GPU was busy (repeat with --repeat 3)."]
    open(os.path.join(out_dir, "EXECUTION-PLAN.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(json.dumps({"plan": os.path.join(out_dir, "EXECUTION-PLAN.md"), "briefs": chosen}))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("grab-view")
    c.add_argument("name")
    c.add_argument("--project", required=True)
    c.add_argument("--scenes", default=os.path.join(HERE, "scenes.json"))
    c.add_argument("--seconds", type=float, default=8)
    c.add_argument("--stdio", help="NucleonEditor, when the editor is not open with the AI server on")
    c = sub.add_parser("run")
    c.add_argument("--engine", required=True, help="folder of Nucleon.exe (build-msvc/bin) or the exe")
    c.add_argument("--project", required=True)
    c.add_argument("--scenes", default=os.path.join(HERE, "scenes.json"))
    c.add_argument("--configs", default=os.path.join(HERE, "configs.json"))
    c.add_argument("--only", help="hypotheses, e.g. H1,H2 (default: all)")
    c.add_argument("--repeat", type=int, default=2)
    c.add_argument("--out")
    c.add_argument("--quality", default="High")
    c.add_argument("--warmup", type=float, default=6)
    c.add_argument("--load-wait", type=float, default=180)
    c.add_argument("--timeout", type=float, default=1200)
    c.add_argument("--gpu-every", type=int, default=5, help="NC_GPU_PROFILE period in frames")
    c.add_argument("--no-warm-run", dest="warm_run", action="store_false")
    c.add_argument("--xvfb", action="store_true", help="Linux: run under xvfb-run (software GL: numbers only check the kit)")
    c = sub.add_parser("analyze")
    c.add_argument("out")
    c = sub.add_parser("plan")
    c.add_argument("out")
    c.add_argument("--no-known", action="store_true", help="leave out the known items K1-K5 (A1 and the MCP / docs fixes)")
    a = p.parse_args()
    {"grab-view": cmd_grab_view, "run": cmd_run, "analyze": cmd_analyze, "plan": cmd_plan}[a.cmd](a)


if __name__ == "__main__":
    main()
