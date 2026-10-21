#!/usr/bin/env python3
"""gate_link.py: the developer side of the game-developer <-> game-launch-strategist contract (launch-link.md v3).

Standard library only. Works with or without `launch/` (then it only validates gates).

A development gate (docs/gates/NN-slug.md) starts with a machine-readable header between two `---` lines:

  ---
  gate: 57
  title: Scheda Stasera, spirale fermata
  date: 2026-10-19
  status: PASS                       # PASS | PARTIAL | FAIL
  source: [launch/fg/waves/w09-sintesi.md]
  wave: w09                          # wave that asked for the work, or none
  closes: [new-too-much-ui]          # issue keys of launch/issue_status.json -> "risolto"
  verify: [new-hidden-rules]         # touched, but real players must confirm -> "da_verificare"
  todo: ["Gate 57 (ondata 9, n. 1)"] # words matching ONE open line of launch/TODO.md
  decisions: [D-012]                 # DECISIONI.md ids applied or respected, or none
  files:
    - Assets/_Game/Scripts/UI/TonightCard.cs
  screenshots:
    - docs/screens/57/01-tonight.png
  risks:
    - "Scheda Stasera copre il timer a 150 %: ricontrollare"
  owner_try:
    - "Inizia il piano 1: una sola scheda, poi niente per 10 s"
  design_changes:
    - "Avviso del buffet al 40 % invece che al 35 % | perché: arrivava tardi | decided_by: implementer"
  saves: backup + restore identical  # or: not touched
  build: none                        # or the build path, only if the owner asked
  tests: not run (DECISIONI D-006)   # or the summary
  ---

Commands (paths are relative to --project, default: current directory):
  check  [GATE.md ...]                validate headers (default: every docs/gates/*.md that has one; --all = also
                                      report gates without a header). Exit 1 on errors.
  since  [--wave N | --since DATE | --after-gate N] [--out FILE] [--json]
                                      gates done since the last focus-group wave: changelog for the next wave,
                                      the `fixes` array for the wave JSON, the risks to re-check, what to try.
  apply-status GATE.md [--write]      write closes/verify of the gate into launch/issue_status.json
                                      (dry run unless --write; never touches owner decisions or unknown keys)
  todo   GATE.md [--run]              the todo_track.py commands for the gate's `todo` items (--run executes them)
  detect                              which side is present: linked | launch-only | solo
  self-test                           built-in checks on a temporary project
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

try:  # UTF-8 console on Windows
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

REQUIRED = ["gate", "title", "date", "status", "source", "closes", "verify", "files", "screenshots",
            "risks", "owner_try", "design_changes", "saves", "build"]
LISTS = {"source", "closes", "verify", "todo", "decisions", "files", "screenshots", "risks", "owner_try",
         "design_changes"}
STATUSES = {"PASS", "PARTIAL", "FAIL"}
KNOWN = set(REQUIRED) | {"wave", "todo", "decisions", "tests"}
DECIDED = {"accettato", "non_problema", "pianificato", "sospeso"}  # owner decisions: never changed by a gate
NONE_RE = re.compile(r"^(none|nessun[oa]?)\b", re.I)
OWNER_SECTION = re.compile(r"^#{2,3}\s*Per il proprietario", re.I | re.M)


# ------------------------------------------------------------------------------------------------- parsing
def _strip_comment(line: str) -> str:
    q = None
    for i, ch in enumerate(line):
        if ch in "\"'":
            q = None if q == ch else (ch if q is None else q)
        elif ch == "#" and q is None and i > 0 and line[i - 1] in " \t":
            return line[:i].rstrip()
    return line.rstrip()


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def _inline_list(s: str) -> list[str]:
    inner = s.strip()[1:-1]
    out, cur, q = [], "", None
    for ch in inner:
        if ch in "\"'" and (q is None or q == ch):
            q = None if q == ch else ch
            cur += ch
        elif ch == "," and q is None:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return [_unquote(x) for x in out if x.strip()]


def parse_header(text: str) -> tuple[dict | None, str, list[str]]:
    """Returns (header or None, body, parse errors)."""
    lines = text.lstrip("﻿").splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text, []
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return None, text, ["header: closing '---' missing"]
    head, errs, key = {}, [], None
    for raw in lines[1:end]:
        line = _strip_comment(raw)
        if not line.strip():
            continue
        m = re.match(r"^\s+-\s+(.*)$", line)
        if m:
            if key is None or not isinstance(head.get(key), list):
                errs.append(f"header: list item without a key: {raw.strip()}")
                continue
            head[key].append(_unquote(m.group(1)))
            continue
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if not m:
            errs.append(f"header: unreadable line: {raw.strip()}")
            continue
        key, val = m.group(1), m.group(2).strip()
        if val == "":
            head[key] = []
        elif val.startswith("[") and val.endswith("]"):
            head[key] = _inline_list(val)
        else:
            head[key] = [_unquote(val)] if key in LISTS else _unquote(val)
    for k in LISTS:
        if k in head and isinstance(head[k], str):
            head[k] = [head[k]]
    return head, "\n".join(lines[end + 1:]), errs


def real_items(v) -> list[str]:
    """List items that are not a 'none: reason' placeholder."""
    return [x for x in (v or []) if not NONE_RE.match(x)]


# ------------------------------------------------------------------------------------------------- project
def gate_files(project: str) -> list[str]:
    files = glob.glob(os.path.join(project, "docs", "gates", "*.md"))

    def num(p):
        m = re.match(r"(\d+)", os.path.basename(p))
        return (int(m.group(1)) if m else 10 ** 6, os.path.basename(p))
    return sorted(files, key=num)


def load_json(path: str):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def todo_lines(path: str) -> list[tuple[bool, str]]:
    if not os.path.exists(path):
        return []
    out = []
    for ln in open(path, encoding="utf-8").read().splitlines():
        m = re.match(r"^\s*[-*]\s*\[( |x|X|-)\]\s*(.+)$", ln)
        if m:
            out.append((m.group(1) == " ", m.group(2)))
    return out


def check_gate(path: str, project: str, launch: str) -> tuple[list[str], list[str], dict | None]:
    errs, warns = [], []
    text = open(path, encoding="utf-8").read()
    head, body, perr = parse_header(text)
    errs += perr
    if head is None:
        return ["no machine-readable header (--- ... --- at the top): see launch-link.md §6"], [], None
    for k in REQUIRED:
        if k not in head:
            errs.append(f"missing key '{k}'")
    for k in head:
        if k not in KNOWN:
            warns.append(f"unknown key '{k}' (typo? known: {', '.join(sorted(KNOWN))})")
    g = str(head.get("gate", ""))
    m = re.match(r"(\d+)", os.path.basename(path))
    if g and not g.isdigit():
        errs.append(f"gate must be a number, got '{g}'")
    elif g and m and int(m.group(1)) != int(g):
        errs.append(f"gate {g} does not match the file name ({os.path.basename(path)})")
    if "date" in head and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(head["date"])):
        errs.append(f"date must be YYYY-MM-DD, got '{head['date']}'")
    st = str(head.get("status", ""))
    if st and st not in STATUSES:
        errs.append(f"status must be PASS | PARTIAL | FAIL, got '{st}'")
    for k in ("risks", "owner_try"):
        if k in head and not head[k]:
            errs.append(f"'{k}' is empty: list at least one item (or 'nessuno: <motivo>')")
    if st == "PASS" and "screenshots" in head and not head["screenshots"]:
        errs.append("PASS without screenshots: list them (looked at) or 'none: <why the change is not visible>'")
    for k in ("files", "screenshots"):
        for p in real_items(head.get(k)):
            clean = re.sub(r"\s*\(.*\)$", "", p).strip()
            norm = clean.replace("\\", "/")
            if re.search(r"(^|/)(Temp|Library)/", norm):
                errs.append(f"{k}: '{p}' is under Temp/ or Library/ (Unity wipes them)")
            if "*" in clean or "{" in clean:
                if k == "screenshots" and not glob.glob(os.path.join(project, clean)):
                    warns.append(f"{k}: pattern '{clean}' matches nothing")
                continue
            if "(removed)" in p or "(rimosso)" in p:
                continue
            if not os.path.exists(os.path.join(project, clean)):
                (errs if k == "screenshots" else warns).append(f"{k}: '{clean}' not found on disk")
    for item in real_items(head.get("design_changes")):
        mm = re.search(r"decided_by\s*:\s*(\w+)(.*)$", item)
        if not mm:
            errs.append(f"design_changes: '{item[:60]}' has no 'decided_by: owner (<source>) | implementer'")
        elif mm.group(1).lower() == "owner" and not re.search(r"\(.+\)", mm.group(2)):
            errs.append(f"design_changes: '{item[:60]}' says owner without the source in parentheses "
                        "(brief/chat date/D-NNN): never attribute a choice to the owner without it")
        elif mm.group(1).lower() not in ("owner", "implementer"):
            errs.append(f"design_changes: decided_by must be owner or implementer, got '{mm.group(1)}'")
    if not OWNER_SECTION.search(body):
        errs.append("body has no '## Per il proprietario' section (what changed + what to try, plain words)")
    status_file = load_json(os.path.join(launch, "issue_status.json")) if launch else None
    if status_file is not None:
        both = set(real_items(head.get("closes"))) & set(real_items(head.get("verify")))
        if both:
            errs.append(f"keys both in closes and verify: {sorted(both)}")
        for k in real_items(head.get("closes")) + real_items(head.get("verify")):
            e = status_file.get(k)
            if not isinstance(e, dict):
                warns.append(f"issue key '{k}' is not in launch/issue_status.json (typo, or a new key the "
                             "strategist must create)")
            elif e.get("status") in DECIDED:
                errs.append(f"issue key '{k}' is an owner decision ({e.get('status')}): a gate cannot close it")
        if st != "PASS" and real_items(head.get("closes")):
            errs.append("only a PASS gate can close issue keys (use verify, or fix the status)")
    todos = todo_lines(os.path.join(launch, "TODO.md")) if launch else []
    if todos:
        for pat in real_items(head.get("todo")):
            hits = [t for t in todos if pat.lower() in t[1].lower()]
            open_hits = [t for t in hits if t[0]]
            if len(open_hits) > 1:
                errs.append(f"todo '{pat}' matches {len(open_hits)} open lines of launch/TODO.md: make it unique")
            elif not hits:
                warns.append(f"todo '{pat}' matches no line of launch/TODO.md")
    return errs, warns, head


# ------------------------------------------------------------------------------------------------- waves
def waves(launch: str) -> list[dict]:
    """[{n, date, files}] from launch/fg/waves/wNN-*."""
    out = {}
    for p in glob.glob(os.path.join(launch, "fg", "waves", "w[0-9]*")):
        b = os.path.basename(p)
        m = re.match(r"w(\d+)-", b)
        if not m:
            continue
        n = int(m.group(1))
        w = out.setdefault(n, {"n": n, "date": None, "files": []})
        w["files"].append(p)
        d = re.search(r"(\d{4}-\d{2}-\d{2})", b)
        if d and (w["date"] is None or d.group(1) > w["date"]):
            w["date"] = d.group(1)
    for w in out.values():
        if w["date"] is None:  # date from the sintesi/brief title "(2026-10-18)"
            for p in w["files"]:
                if p.endswith(".md"):
                    d = re.search(r"\((\d{4}-\d{2}-\d{2})\)", open(p, encoding="utf-8").read(400))
                    if d:
                        w["date"] = d.group(1)
                        break
    return [out[k] for k in sorted(out)]


def gates_cited(w: dict) -> set[int]:
    """Development gates the wave already saw (cited as 'gate NN' in its sintesi/brief/JSON)."""
    cited = set()
    for p in w["files"]:
        if re.search(r"-(sintesi|brief)\.md$|\d{4}-\d{2}-\d{2}.*\.json$", p):
            txt = open(p, encoding="utf-8", errors="replace").read()
            cited |= {int(x) for x in re.findall(r"\bgate\s+(\d{1,3})\b", txt, re.I)}
    return cited


def cmd_since(a) -> int:
    project, launch = a.project, os.path.join(a.project, a.launch_dir)
    ws = waves(launch)
    rule, ref_wave = "", None
    gates = []
    for p in gate_files(project):
        head, _, _ = parse_header(open(p, encoding="utf-8").read())
        if head:
            gates.append((p, head))
    if a.after_gate is not None:
        sel = [(p, h) for p, h in gates if int(h.get("gate", 0)) > a.after_gate]
        rule = f"gate > {a.after_gate}"
    else:
        if a.since:
            since, cited = a.since, set()
            rule = f"date >= {since}"
        else:
            if a.wave is not None:
                ref_wave = next((w for w in ws if w["n"] == a.wave), None)
            elif ws:
                ref_wave = ws[-1]
            if not ref_wave or not ref_wave["date"]:
                print("Nessuna ondata trovata in launch/fg/waves: uso tutti i gate con intestazione.", file=sys.stderr)
                since, cited = "0000-00-00", set()
                rule = "all"
            else:
                since, cited = ref_wave["date"], gates_cited(ref_wave)
                rule = f"after wave w{ref_wave['n']:02d} ({since}); same-day gates only if the wave does not cite them"
        sel = []
        for p, h in gates:
            d = str(h.get("date", ""))
            if d > since or (d == since and int(h.get("gate", 0)) not in cited):
                sel.append((p, h))
    fixes, risks, tries, changes = [], [], [], []
    for p, h in sel:
        g, t = h.get("gate"), h.get("title", "")
        rel = os.path.relpath(p, project).replace("\\", "/")
        for k in real_items(h.get("closes")):
            fixes.append({"issue": k, "what": f"gate {g}: {t}", "gate_dev": int(g), "status": "risolto"})
        for k in real_items(h.get("verify")):
            fixes.append({"issue": k, "what": f"gate {g} (da verificare con persone vere): {t}",
                          "gate_dev": int(g), "status": "da_verificare"})
        for r in real_items(h.get("risks")):
            risks.append({"gate_dev": int(g), "risk": r})
        for o in real_items(h.get("owner_try")):
            tries.append({"gate_dev": int(g), "try": o})
        for c in real_items(h.get("design_changes")):
            changes.append({"gate_dev": int(g), "change": c})
    nxt = (ref_wave["n"] + 1) if ref_wave else None
    data = {"rule": rule, "next_wave": nxt, "gates": [
        {"gate": int(h.get("gate", 0)), "title": h.get("title"), "date": h.get("date"), "status": h.get("status"),
         "path": os.path.relpath(p, project).replace("\\", "/")} for p, h in sel],
        "fixes": fixes, "risks_to_recheck": risks, "owner_try": tries, "design_changes": changes}
    if a.json:
        print(json.dumps(data, ensure_ascii=False, indent=1))
        return 0
    title = f"Cambiato dal gioco dopo l'ondata {ref_wave['n']}" if ref_wave else "Cambiato nel gioco"
    md = [f"# {title} (generato {dt.date.today().isoformat()} da gate_link.py since)", "",
          f"> Regola: {rule}. Questo è lo **stato attuale** che la prossima ondata legge (launch-link.md §6.2). "
          "Le voci `da_verificare` restano aperte finché non le confermano persone vere.", ""]
    if not sel:
        md.append("Nessun gate nuovo.")
    for x in data["gates"]:
        md.append(f"- **Gate {x['gate']}** ({x['date']}, {x['status']}): {x['title']} — `{x['path']}`")
    if fixes:
        md += ["", "## Criticità toccate", "| Chiave | Esito | Gate | Cosa |", "|---|---|---|---|"]
        md += [f"| `{f['issue']}` | {f['status']} | {f['gate_dev']} | {f['what']} |" for f in fixes]
    if risks:
        md += ["", "## Rischi introdotti da ricontrollare nell'ondata (loop di regressione)"]
        md += [f"- gate {r['gate_dev']}: {r['risk']}" for r in risks]
    if changes:
        md += ["", "## Scelte di design cambiate dall'implementazione"]
        md += [f"- gate {c['gate_dev']}: {c['change']}" for c in changes]
    if tries:
        md += ["", "## Da provare (proprietario)"]
        md += [f"- gate {o['gate_dev']}: {o['try']}" for o in tries]
    md += ["", "## `fixes` per il JSON dell'ondata", "```json",
           json.dumps([{"issue": f["issue"], "what": f["what"]} for f in fixes], ensure_ascii=False, indent=1),
           "```", ""]
    out = "\n".join(md)
    if a.out:
        os.makedirs(os.path.dirname(os.path.join(project, a.out)) or ".", exist_ok=True)
        with open(os.path.join(project, a.out), "w", encoding="utf-8", newline="\n") as f:
            f.write(out)
        print(f"scritto {a.out} ({len(sel)} gate, {len(fixes)} chiavi, {len(risks)} rischi)")
    else:
        print(out)
    return 0


# ------------------------------------------------------------------------------------------------- status
def cmd_apply_status(a) -> int:
    project, launch = a.project, os.path.join(a.project, a.launch_dir)
    path = os.path.join(launch, "issue_status.json")
    data = load_json(path)
    if data is None:
        print("launch/issue_status.json non c'è: niente da aggiornare (modalità solo).")
        return 0
    gp = a.gate if os.path.isabs(a.gate) else os.path.join(project, a.gate)
    errs, _, head = check_gate(gp, project, launch)
    if head is None or errs:
        print("Il gate non è valido, non aggiorno nulla:\n  - " + "\n  - ".join(errs))
        return 1
    g, date, title = head["gate"], head["date"], head["title"]
    rel = os.path.relpath(gp, project).replace("\\", "/")
    changes = []
    for k, new in [(k, "risolto") for k in real_items(head.get("closes"))] + \
                  [(k, "da_verificare") for k in real_items(head.get("verify"))]:
        e = data.get(k)
        if not isinstance(e, dict):
            print(f"  salto '{k}': chiave assente (la crea la skill launch con l'ondata)")
            continue
        if e.get("status") in DECIDED:
            print(f"  salto '{k}': è una decisione del proprietario ({e['status']})")
            continue
        if e.get("gate") == rel and e.get("status") == new:
            print(f"  '{k}': già aggiornata")
            continue
        old = e.get("status")
        e["status"] = new
        prefix = f"Gate {g} ({date}): {title}."
        e["note"] = prefix + (" · " + e["note"] if e.get("note") else "")
        e["gate"] = rel
        if new == "risolto":
            e["resolved"] = date
        changes.append(f"{k}: {old} -> {new}")
    if not changes:
        print("Nessuna modifica.")
        return 0
    print(("SCRITTO" if a.write else "PROVA (aggiungi --write)") + f": {len(changes)} chiavi")
    for c in changes:
        print("  " + c)
    if a.write:
        bak = path + ".bak"
        shutil.copyfile(path, bak)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.write("\n")
        print(f"backup: {os.path.relpath(bak, project)}. Poi la skill launch rigenera STATUS.html.")
    return 0


# ------------------------------------------------------------------------------------------------- todo
def find_todo_track() -> str | None:
    home = os.path.expanduser("~")
    cands = [os.environ.get("GLS_RESEARCH_SCRIPTS", "")]
    for base in (os.path.join(home, ".claude", "skills"), os.path.join(home, ".agents", "skills")):
        cands.append(os.path.join(base, "game-launch-strategist", "scripts", "research"))
    for c in cands:
        if c and os.path.exists(os.path.join(c, "todo_track.py")):
            return os.path.join(c, "todo_track.py")
    return None


def cmd_todo(a) -> int:
    project, launch = a.project, os.path.join(a.project, a.launch_dir)
    gp = a.gate if os.path.isabs(a.gate) else os.path.join(project, a.gate)
    head, _, _ = parse_header(open(gp, encoding="utf-8").read())
    if head is None:
        print("gate senza intestazione")
        return 1
    items = real_items(head.get("todo"))
    if not items:
        print("Il gate non ha voci `todo`.")
        return 0
    tt = find_todo_track()
    todo_md = os.path.join(launch, "TODO.md")
    if not os.path.exists(todo_md):
        print("launch/TODO.md non c'è: niente da spuntare (modalità solo).")
        return 0
    note = f"gate {head['gate']}"
    cmds = [[sys.executable, tt or "todo_track.py", "--file", todo_md, "done", it, "--by", "claude",
             "--note", note, "--date", str(head["date"])] for it in items]
    rc = 0
    for c in cmds:
        print(" ".join(f'"{x}"' if " " in x else x for x in c))
        if a.run:
            if not tt:
                print("todo_track.py non trovato (skill launch assente?): spunta a mano o installa la skill.")
                return 1
            rc |= subprocess.call(c)
    return rc


def cmd_detect(a) -> int:
    home = os.path.expanduser("~")
    skill = any(os.path.exists(os.path.join(b, "game-launch-strategist", "SKILL.md"))
                for b in (os.path.join(home, ".claude", "skills"), os.path.join(home, ".agents", "skills")))
    launch = os.path.isdir(os.path.join(a.project, a.launch_dir))
    mode = "linked" if launch else "solo"
    if launch and not skill:
        mode = "launch-only"
    print(json.dumps({"mode": mode, "launch_dir": launch, "strategist_skill": skill,
                      "todo_track": find_todo_track()}, ensure_ascii=False))
    return 0


def cmd_check(a) -> int:
    launch = os.path.join(a.project, a.launch_dir)
    paths = [p if os.path.isabs(p) else os.path.join(a.project, p) for p in a.gates] or gate_files(a.project)
    bad, seen = 0, 0
    for p in paths:
        txt = open(p, encoding="utf-8").read()
        if not a.gates and not a.all and not txt.lstrip("﻿").startswith("---"):
            continue  # legacy gate without header
        seen += 1
        errs, warns, _ = check_gate(p, a.project, launch)
        name = os.path.relpath(p, a.project)
        print(("❌ " if errs else "✅ ") + name)
        for e in errs:
            print("   ERR  " + e)
        for w in warns:
            print("   warn " + w)
        bad += bool(errs)
    if seen == 0:
        print("Nessun gate con intestazione (i gate vecchi non si toccano; i nuovi usano templates/gate.md).")
    return 1 if bad else 0


# ------------------------------------------------------------------------------------------------- self-test
def self_test() -> int:
    tmp = tempfile.mkdtemp(prefix="gate_link_")
    try:
        j = lambda *p: os.path.join(tmp, *p)
        for d in ("docs/gates", "docs/screens/57", "launch/fg/waves", "Assets"):
            os.makedirs(j(*d.split("/")), exist_ok=True)
        open(j("docs", "screens", "57", "01.png"), "wb").write(b"png")
        open(j("Assets", "A.cs"), "w").write("//")
        json.dump({"_note": "x", "ui-chaos": {"status": "aperto", "note": "old"},
                   "rules-hidden": {"status": "aperto"}, "deck": {"status": "non_problema"}},
                  open(j("launch", "issue_status.json"), "w", encoding="utf-8"))
        open(j("launch", "TODO.md"), "w", encoding="utf-8").write(
            "# TODO\nAggiornato: 2026-10-18\n## Dev\n- [ ] 🤖 **Gate 57 n. 1** scheda — 2026-10-25 — 3 h\n")
        open(j("launch", "fg", "waves", "w09-sintesi.md"), "w", encoding="utf-8").write(
            "# Ondata 9 — Sintesi (2026-10-18)\nDopo il gate 56.\n")
        good = """---
gate: 57
title: Scheda Stasera
date: 2026-10-19
status: PASS
source: [launch/fg/waves/w09-sintesi.md]
wave: w09
closes: [ui-chaos]
verify: [rules-hidden]
todo: ["Gate 57 n. 1"]
decisions: none
files:
  - Assets/A.cs
screenshots:
  - docs/screens/57/01.png
risks:
  - "la scheda copre il timer a 150 %"   # comment
owner_try:
  - "inizia il piano 1"
design_changes:
  - "avviso al 40 % | perché: tardi | decided_by: implementer"
saves: not touched
build: none
---
# Gate 57
## Per il proprietario
Prova.
"""
        open(j("docs", "gates", "57-stasera.md"), "w", encoding="utf-8").write(good)
        e, w, h = check_gate(j("docs", "gates", "57-stasera.md"), tmp, j("launch"))
        assert not e, e
        assert h["risks"] == ["la scheda copre il timer a 150 %"], h["risks"]
        assert h["decisions"] == ["none"]
        bad = good.replace("decided_by: implementer", "decided_by: owner").replace("closes: [ui-chaos]",
                                                                                   "closes: [deck]")
        bad = bad.replace("## Per il proprietario", "## Other").replace("docs/screens/57/01.png",
                                                                       "Temp/x.png")
        open(j("docs", "gates", "58-bad.md"), "w", encoding="utf-8").write(bad.replace("gate: 57", "gate: 58"))
        e, _, _ = check_gate(j("docs", "gates", "58-bad.md"), tmp, j("launch"))
        txt = " | ".join(e)
        for frag in ("without the source", "owner decision", "Per il proprietario", "Temp/"):
            assert frag in txt, (frag, txt)
        os.remove(j("docs", "gates", "58-bad.md"))

        class A:  # since
            project, launch_dir, wave, since, after_gate, out, json = tmp, "launch", None, None, None, None, True
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_since(A)
        d = json.loads(buf.getvalue())
        assert [g["gate"] for g in d["gates"]] == [57], d
        assert {f["issue"] for f in d["fixes"]} == {"ui-chaos", "rules-hidden"}
        assert d["risks_to_recheck"][0]["gate_dev"] == 57 and d["next_wave"] == 10

        class B:  # apply-status
            project, launch_dir, gate, write = tmp, "launch", "docs/gates/57-stasera.md", True
        with contextlib.redirect_stdout(io.StringIO()):
            cmd_apply_status(B)
        st = json.load(open(j("launch", "issue_status.json"), encoding="utf-8"))
        assert st["ui-chaos"]["status"] == "risolto" and st["ui-chaos"]["resolved"] == "2026-10-19"
        assert st["ui-chaos"]["note"].startswith("Gate 57") and st["ui-chaos"]["note"].endswith("old")
        assert st["rules-hidden"]["status"] == "da_verificare" and "resolved" not in st["rules-hidden"]
        assert st["deck"]["status"] == "non_problema"
        print("self-test OK (header parse, validation errors, since, apply-status)")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".", help="game project root (contains docs/gates and launch/)")
    ap.add_argument("--launch-dir", default="launch")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("gates", nargs="*")
    c.add_argument("--all", action="store_true")
    s = sub.add_parser("since")
    s.add_argument("--wave", type=int)
    s.add_argument("--since")
    s.add_argument("--after-gate", type=int)
    s.add_argument("--out")
    s.add_argument("--json", action="store_true")
    p = sub.add_parser("apply-status")
    p.add_argument("gate")
    p.add_argument("--write", action="store_true")
    t = sub.add_parser("todo")
    t.add_argument("gate")
    t.add_argument("--run", action="store_true")
    sub.add_parser("detect")
    sub.add_parser("self-test")
    a = ap.parse_args()
    a.project = os.path.abspath(a.project)
    return {"check": cmd_check, "since": cmd_since, "apply-status": cmd_apply_status, "todo": cmd_todo,
            "detect": cmd_detect, "self-test": lambda _a: self_test()}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
