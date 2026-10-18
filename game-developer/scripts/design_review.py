#!/usr/bin/env python3
"""design_review.py: numbers for the design review (references/design-review.md). Standard library only.

screens  SCREEN_MAP.md [--before OLD.md] [--json]
    Reads the ```screens block of a screen/menu discoverability map and computes, from the roots:
    reachable / unreachable (orphans), clicks from the root (depth), screens with a single entry point,
    dead ends (no way out). With --before (the map before a redesign): ORPHANED FEATURES = places that were
    reachable before and are not any more, or that lost entry points. Exit 1 if an orphan is not marked hidden-ok.

    Block format (one item per line, '#' comments allowed):
        root: MainMenu                       # entry points (boot, auto-open); several allowed
        screen: Shop | UI/Shop/Shop.uxml     # optional declaration (a place with no edges must be declared)
        screen: Roulette | UI/Roulette.uxml | hidden-ok: off in the beta (owner)
        MainMenu -> Options : click Options
        Pause -> Options : Esc > Options
        Van -> CateringCart : buy the perk   # places can be features and items, not only screens
        Fired -> MainMenu : auto             # 'auto' = the game opens it by itself

runs  RUNS.md [--before OLD.md] [--json]
    Reads timed simulated runs: every `## ` heading is one run; table rows whose first cell is a time
    (m:ss or m:ss-m:ss) are moments. Tags anywhere in the row:
        [MORTO]  dead time (lasts until the next row)     [TOP]      fun peak / clip moment
        [FRUSTRA] frustration                             [ABBANDONO] likely quit point
        [CONFUSO] the player does not know what to do     [TROPPA-UI:n] n panels/notices at once
        [SPIRALE] failure feeding failure
    Reports per run: length, dead seconds, longest stretch without a [TOP], max UI at once, counts.
    With --before: the delta (the before/after of a gate).

self-test    built-in checks
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict, deque

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# ------------------------------------------------------------------------------------------------- screens
def parse_screens(text: str) -> dict:
    m = re.search(r"```screens\s*\n(.*?)```", text, re.S)
    if not m:
        raise ValueError("no ```screens block found (see design-review.md §2)")
    roots, nodes, edges = [], {}, []
    for raw in m.group(1).splitlines():
        line = re.sub(r"\s+#.*$", "", raw).strip()
        if not line or line.startswith("#"):
            continue
        r = re.match(r"^root\s*:\s*(.+)$", line, re.I)
        if r:
            roots += [x.strip() for x in r.group(1).split(",") if x.strip()]
            continue
        s = re.match(r"^(?:screen|place|feature)\s*:\s*(.+)$", line, re.I)
        if s:
            parts = [x.strip() for x in s.group(1).split("|")]
            n = nodes.setdefault(parts[0], {"file": "", "hidden_ok": ""})
            for p in parts[1:]:
                h = re.match(r"hidden-ok\s*:?\s*(.*)$", p, re.I)
                if h:
                    n["hidden_ok"] = h.group(1) or "yes"
                elif p:
                    n["file"] = p
            continue
        e = re.match(r"^(.+?)\s*->\s*(.+?)(?:\s*:\s*(.*))?$", line)
        if e:
            a, b, how = e.group(1).strip(), e.group(2).strip(), (e.group(3) or "").strip()
            edges.append((a, b, how))
            nodes.setdefault(a, {"file": "", "hidden_ok": ""})
            nodes.setdefault(b, {"file": "", "hidden_ok": ""})
            continue
        raise ValueError(f"unreadable line in screens block: {raw.strip()}")
    if not roots:
        raise ValueError("screens block has no 'root:' line")
    for r in roots:
        nodes.setdefault(r, {"file": "", "hidden_ok": ""})
    return {"roots": roots, "nodes": nodes, "edges": edges}


def analyse_screens(g: dict) -> dict:
    out_e, in_e = defaultdict(list), defaultdict(list)
    for a, b, how in g["edges"]:
        out_e[a].append((b, how))
        in_e[b].append((a, how))
    depth = {r: 0 for r in g["roots"]}
    q = deque(g["roots"])
    while q:
        n = q.popleft()
        for b, how in out_e[n]:
            if b not in depth:  # 'auto' edges cost no click
                depth[b] = depth[n] + (0 if how.lower().startswith("auto") else 1)
                q.append(b)
    unreachable = sorted(n for n in g["nodes"] if n not in depth)
    orphans = [n for n in unreachable if not g["nodes"][n]["hidden_ok"]]
    single = sorted(n for n in depth if n not in g["roots"] and len({a for a, _ in in_e[n] if a in depth}) == 1)
    dead = sorted(n for n in depth if not out_e[n])
    return {"roots": g["roots"], "count": len(g["nodes"]), "reachable": len(depth),
            "depth": dict(sorted(depth.items(), key=lambda kv: (kv[1], kv[0]))),
            "unreachable": unreachable, "orphans": orphans,
            "hidden_ok": {n: g["nodes"][n]["hidden_ok"] for n in unreachable if g["nodes"][n]["hidden_ok"]},
            "single_entry": single, "dead_ends": dead,
            "entries": {n: sorted({f"{a} ({how})" if how else a for a, how in in_e[n]}) for n in g["nodes"]}}


def cmd_screens(a) -> int:
    now = analyse_screens(parse_screens(open(a.map, encoding="utf-8").read()))
    lost, fewer = [], []
    if a.before:
        old = analyse_screens(parse_screens(open(a.before, encoding="utf-8").read()))
        for n, d in old["depth"].items():
            if n not in now["depth"]:
                lost.append(n)
            elif len(now["entries"].get(n, [])) < len(old["entries"].get(n, [])):
                fewer.append((n, old["entries"][n], now["entries"][n]))
        gone = sorted(set(old["entries"]) - set(now["entries"]))
    else:
        gone = []
    res = dict(now, lost_entry=sorted(lost), fewer_entries=[f[0] for f in fewer], removed=gone)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        print(f"Posti: {now['count']} · raggiungibili: {now['reachable']} · radici: {', '.join(now['roots'])}")
        print("Click dalla radice: " + ", ".join(f"{n} {d}" for n, d in now["depth"].items()))
        if now["orphans"]:
            print("❌ ORFANI (nessun ingresso dalla radice): " + ", ".join(now["orphans"]))
        for n, why in now["hidden_ok"].items():
            print(f"ℹ nascosto per scelta: {n} ({why})")
        if lost:
            print("❌ HANNO PERSO L'INGRESSO dopo il cambio: " + ", ".join(sorted(lost)))
        for n, o, c in fewer:
            print(f"⚠ meno ingressi: {n}: prima {o} · ora {c}")
        if gone:
            print("ℹ tolti dalla mappa (verificare che sia voluto): " + ", ".join(gone))
        if now["single_entry"]:
            print("⚠ un solo ingresso (fragile a un redesign): " + ", ".join(now["single_entry"]))
        if now["dead_ends"]:
            print("ℹ senza uscita nella mappa (ok se è il gioco o una fine): " + ", ".join(now["dead_ends"]))
        if not now["orphans"] and not lost:
            print("✅ nessun orfano")
    return 1 if (now["orphans"] or lost) else 0


# ------------------------------------------------------------------------------------------------- runs
TIME = re.compile(r"^\s*(\d+):(\d{2})(?:\s*[-–]\s*(\d+):(\d{2}))?")
TAGS = ("MORTO", "TOP", "FRUSTRA", "ABBANDONO", "CONFUSO", "SPIRALE")


def parse_runs(text: str) -> list[dict]:
    runs, cur = [], None
    for line in text.splitlines():
        h = re.match(r"^##\s+(.+)$", line)
        if h:
            cur = {"name": h.group(1).strip(), "rows": []}
            runs.append(cur)
            continue
        if cur is None or not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells:
            continue
        m = TIME.match(cells[0].replace("*", ""))
        if not m:
            continue
        t0 = int(m.group(1)) * 60 + int(m.group(2))
        t1 = int(m.group(3)) * 60 + int(m.group(4)) if m.group(3) else None
        tags = {t: len(re.findall(r"\[" + t + r"\]", line, re.I)) for t in TAGS}
        ui = [int(x) for x in re.findall(r"\[TROPPA-UI\s*:\s*(\d+)\]", line, re.I)]
        cur["rows"].append({"t0": t0, "t1": t1, "tags": tags, "ui": max(ui) if ui else 0})
    return [r for r in runs if r["rows"]]


def analyse_run(r: dict) -> dict:
    rows = sorted(r["rows"], key=lambda x: x["t0"])
    end = max((x["t1"] or x["t0"]) for x in rows)
    dead, tops = 0, [0]
    for i, x in enumerate(rows):
        if x["tags"]["MORTO"]:
            stop = x["t1"] if x["t1"] is not None else (rows[i + 1]["t0"] if i + 1 < len(rows) else x["t0"])
            dead += max(0, stop - x["t0"])
        if x["tags"]["TOP"]:
            tops.append(x["t0"])
    tops.append(end)
    gap = max(b - a for a, b in zip(tops, tops[1:])) if len(tops) > 1 else end
    return {"run": r["name"], "length_s": end, "dead_s": dead, "dead_pct": round(100 * dead / end, 1) if end else 0,
            "longest_without_top_s": gap, "max_ui": max(x["ui"] for x in rows),
            **{t.lower(): sum(x["tags"][t] for x in rows) for t in TAGS if t != "MORTO"},
            "moments": len(rows)}


def fmt(s: int) -> str:
    return f"{s // 60}:{s % 60:02d}"


def cmd_runs(a) -> int:
    now = [analyse_run(r) for r in parse_runs(open(a.runs, encoding="utf-8").read())]
    if not now:
        print("Nessuna run trovata: servono '## ' per run e righe di tabella che iniziano con m:ss.")
        return 1
    before = {}
    if a.before:
        before = {x["run"]: x for x in (analyse_run(r) for r in parse_runs(open(a.before, encoding="utf-8").read()))}
    if a.json:
        print(json.dumps({"runs": now, "before": list(before.values())}, ensure_ascii=False, indent=1))
        return 0
    cols = ["length_s", "dead_s", "longest_without_top_s", "max_ui", "top", "frustra", "confuso", "spirale",
            "abbandono"]
    head = ["Run", "Durata", "Morti", "Max senza picco", "UI insieme", "Picchi", "Frustr.", "Confuso",
            "Spirale", "Abbandono"]
    print("| " + " | ".join(head) + " |")
    print("|" + "---|" * len(head))
    for x in now:
        b = before.get(x["run"])

        def cell(k):
            v = x[k]
            s = fmt(v) if k.endswith("_s") else str(v)
            if b is not None and b[k] != v:
                d = v - b[k]
                s += f" ({'+' if d > 0 else '−'}{fmt(abs(d)) if k.endswith('_s') else abs(d)})"
            return s
        print(f"| {x['run'][:40]} | " + " | ".join(cell(k) for k in cols) + " |")
    if a.before:
        missing = sorted(set(before) - {x["run"] for x in now})
        if missing:
            print("⚠ run del 'prima' senza 'dopo' (stesso titolo `## `): " + ", ".join(missing))
    return 0


# ------------------------------------------------------------------------------------------------- self-test
def self_test() -> int:
    before = """```screens
root: Menu
Menu -> Options : click
Menu -> Shop : click Shop
Van -> Shop : button
Menu -> Van : auto
screen: Roulette | UI/R.uxml | hidden-ok: off in beta
```"""
    after = """```screens
root: Menu
Menu -> Options : click
Menu -> Van : auto
screen: Shop | UI/Shop.uxml
screen: Roulette | UI/R.uxml | hidden-ok: off in beta
```"""
    g = analyse_screens(parse_screens(before))
    assert g["orphans"] == [] and g["depth"]["Shop"] == 1 and g["depth"]["Van"] == 0, g
    h = analyse_screens(parse_screens(after))
    assert h["orphans"] == ["Shop"] and "Roulette" in h["hidden_ok"], h

    class A:
        pass
    import os
    import tempfile
    import io
    import contextlib
    d = tempfile.mkdtemp()
    try:
        pb, pa = os.path.join(d, "b.md"), os.path.join(d, "a.md")
        open(pb, "w", encoding="utf-8").write(before)
        open(pa, "w", encoding="utf-8").write(after)
        A.map, A.before, A.json = pa, pb, True
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cmd_screens(A)
        res = json.loads(buf.getvalue())
        assert rc == 1 and res["lost_entry"] == ["Shop"], res
        runs = """## Run 1 — nuovo
| Tempo | Dove | Azione |
|---|---|---|
| 0:00 | Menu | avvio |
| 0:10 | Sala | 9 cose insieme [TROPPA-UI:9] [CONFUSO] |
| 0:30-0:50 | corridoio | camminata vuota [MORTO] |
| 1:10 | Sala | Tommy 6 → 1 [TOP] |
| 2:00 | Sala | pila caduta, buffet vuoto, richiamo [SPIRALE] [FRUSTRA] |
| 3:00 | Fine | licenziato [ABBANDONO] |
"""
        r = analyse_run(parse_runs(runs)[0])
        assert r["length_s"] == 180 and r["dead_s"] == 20 and r["max_ui"] == 9, r
        assert r["longest_without_top_s"] == 110 and r["spirale"] == 1 and r["top"] == 1, r
        print("self-test OK (screens: depth, orphans, lost entry; runs: dead time, gaps, UI, tags)")
        return 0
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("screens")
    s.add_argument("map")
    s.add_argument("--before")
    s.add_argument("--json", action="store_true")
    r = sub.add_parser("runs")
    r.add_argument("runs")
    r.add_argument("--before")
    r.add_argument("--json", action="store_true")
    sub.add_parser("self-test")
    a = ap.parse_args()
    try:
        return {"screens": cmd_screens, "runs": cmd_runs, "self-test": lambda _a: self_test()}[a.cmd](a)
    except ValueError as e:
        print(f"ERRORE: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
