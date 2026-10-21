#!/usr/bin/env python3
"""telemetry_report: playtest CSVs (gds_telemetry.lua, any engine writing the same columns) -> what players did.

  python telemetry_report.py <folder or csv...> [--cell 8] [--out docs/playtest/telemetry.md] [--json out.json]

Columns: t,event,level,x,y,z,value,extra (t = seconds of play; x,y,z Z up). Standard library only.
Answers the questions a focus-group wave and the design review need, with numbers instead of impressions:
  sessions, play time, quit points (where and when the last event of a session is), deaths per area (grid cells of
  --cell metres) and their cause, idle spots (20 s without moving), time to each custom event's first occurrence
  (first objective, first pickup), the areas where players spend the most time, and the areas nobody visits.
The JSON is what game-launch-strategist reads as "real test" data (launch-link.md: real critiques stay separate from
simulated ones).
"""
import argparse
import csv
import glob
import json
import os
import statistics
from collections import Counter, defaultdict


def load(paths):
    files = []
    for p in paths:
        files += sorted(glob.glob(os.path.join(p, "**", "*.csv"), recursive=True)) if os.path.isdir(p) else [p]
    sessions = []
    for f in files:
        rows = []
        with open(f, newline="", encoding="utf-8", errors="replace") as h:
            for r in csv.DictReader(h):
                try:
                    r["t"] = float(r["t"])
                    r["x"], r["y"], r["z"] = float(r["x"]), float(r["y"]), float(r["z"])
                except (KeyError, ValueError):
                    continue
                rows.append(r)
        if rows:
            sessions.append({"file": os.path.basename(f), "rows": rows})
    return sessions


def cell_of(r, size):
    return (int(r["x"] // size), int(r["y"] // size))


def report(sessions, size):
    out = {"sessions": len(sessions), "cell_m": size}
    if not sessions:
        return out
    lengths = [s["rows"][-1]["t"] for s in sessions]
    out["play_seconds"] = {"median": round(statistics.median(lengths), 1), "min": round(min(lengths), 1),
                           "max": round(max(lengths), 1)}
    quits, deaths, idles, time_in, firsts = [], Counter(), Counter(), Counter(), defaultdict(list)
    causes = defaultdict(Counter)
    visited = set()
    for s in sessions:
        last = s["rows"][-1]
        quits.append({"t": round(last["t"], 1), "cell": cell_of(last, size), "event": last["event"]})
        seen = set()
        prev = None
        for r in s["rows"]:
            c = cell_of(r, size)
            if r["event"] == "pos":
                visited.add(c)
                if prev is not None:
                    time_in[c] += r["t"] - prev
                prev = r["t"]
            elif r["event"] == "death":
                deaths[c] += 1
                causes[c][(dict(kv.split("=", 1) for kv in r.get("extra", "").split(";") if "=" in kv).get("cause") or r.get("value") or "?")] += 1
            elif r["event"] == "idle":
                idles[c] += 1
            if r["event"] not in ("pos", "level", "session_start", "quit", "idle") and r["event"] not in seen:
                seen.add(r["event"])
                firsts[r["event"]].append(r["t"])
    out["quit_points"] = Counter(q["cell"] for q in quits).most_common(5)
    out["quit_times_s"] = sorted(q["t"] for q in quits)
    out["deaths"] = [{"cell": c, "count": n, "causes": dict(causes[c].most_common(3))} for c, n in deaths.most_common(8)]
    out["idle_spots"] = idles.most_common(5)
    out["most_time"] = [{"cell": c, "seconds": round(v, 1)} for c, v in time_in.most_common(6)]
    out["first_time_s"] = {e: {"median": round(statistics.median(v), 1), "reached": "%d/%d" % (len(v), len(sessions))}
                           for e, v in sorted(firsts.items())}
    if visited:
        xs, ys = [c[0] for c in visited], [c[1] for c in visited]
        grid = {(i, j) for i in range(min(xs), max(xs) + 1) for j in range(min(ys), max(ys) + 1)}
        out["never_visited_cells"] = len(grid - visited)
        out["visited_cells"] = len(visited)
    return out


def to_md(r):
    L = ["# Playtest telemetry", "", "Sessions: **%d** · cells of %g m" % (r["sessions"], r["cell_m"]), ""]
    if not r["sessions"]:
        return "\n".join(L + ["No sessions."]) + "\n"
    p = r["play_seconds"]
    L += ["Play time: median %ss (min %s, max %s)" % (p["median"], p["min"], p["max"]), "",
          "| What | Where (cell x,y) | How many |", "|---|---|---|"]
    for c, n in r["quit_points"]:
        L.append("| quit | %s | %d |" % (c, n))
    for d in r["deaths"]:
        L.append("| death (%s) | %s | %d |" % (", ".join("%s %d" % kv for kv in d["causes"].items()), d["cell"], d["count"]))
    for c, n in r["idle_spots"]:
        L.append("| idle 20 s | %s | %d |" % (c, n))
    L += ["", "First time each event happens (median, players who got there):", ""]
    for e, v in r["first_time_s"].items():
        L.append("- `%s`: %ss (%s)" % (e, v["median"], v["reached"]))
    if "visited_cells" in r:
        L += ["", "Visited cells: %d · never visited inside the played area: %d" % (r["visited_cells"], r["never_visited_cells"])]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--cell", type=float, default=8)
    ap.add_argument("--out")
    ap.add_argument("--json")
    a = ap.parse_args()
    r = report(load(a.paths), a.cell)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        open(a.out, "w", encoding="utf-8").write(to_md(r))
    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
        json.dump(r, open(a.json, "w", encoding="utf-8"), indent=1, default=list)
    print(json.dumps({k: r[k] for k in r if k in ("sessions", "play_seconds", "quit_points", "deaths", "first_time_s",
                                                  "never_visited_cells")}, default=list))


if __name__ == "__main__":
    main()
