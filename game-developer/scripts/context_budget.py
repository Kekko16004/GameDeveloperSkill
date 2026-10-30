#!/usr/bin/env python3
"""What each worker phase (and the parent) has to read, in tokens (characters / 4), from config/phases.json.

  python scripts/context_budget.py                 table for the engine rows in the manifest
  python scripts/context_budget.py --engine nucleon --json
  python scripts/context_budget.py --manifest other.json --check   exit 1 when a listed file or section does not exist

A manifest entry is `file` (the whole file), `file#Heading` (from the first line that starts with `#`s then that text, up to the next
heading of the same or a higher level) or `file#` + a line prefix. Files are relative to the skill folder (`docs/...` to its repo
parent). A phase reads: its prompt parts (contract + its own phase file/section), its own references, and the engine sections it
names under `engine.<engine>`. The numbers are the contract of the skill: a change that makes a phase load more than it did is a
regression, `--check --max` makes it a failure.
"""
import argparse
import json
import os
import re
import sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve(path):
    p = os.path.join(SKILL, path)
    if not os.path.exists(p) and path.startswith("docs/"):
        p = os.path.join(os.path.dirname(SKILL), path)
    return p


def section(text, name):
    lines = text.splitlines()
    start = None
    level = 0
    for i, l in enumerate(lines):
        m = re.match(r"^(#+)\s*(.*)$", l)
        if m and m.group(2).startswith(name):
            start, level = i, len(m.group(1))
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        m = re.match(r"^(#+)\s", lines[j])
        if m and len(m.group(1)) <= level:
            end = j
            break
    return "\n".join(lines[start:end])


def load(entry):
    """-> (text or None)"""
    path, _, sec = entry.partition("#")
    p = resolve(path)
    if not os.path.exists(p):
        return None
    text = open(p, encoding="utf-8").read()
    return section(text, sec) if sec else text


def tokens(entries):
    total, missing, per = 0, [], {}
    for e in entries:
        t = load(e)
        if t is None:
            missing.append(e)
            continue
        per[e] = len(t) // 4
        total += len(t) // 4
    return total, missing, per


def phase_entries(m, phase, engine):
    spec = m["phases"][phase]
    out = list(m.get("prompt", [])) + spec.get("prompt", []) + spec.get("reads", [])
    if spec.get("engine", True) and engine in spec.get("engineFiles", {}):
        out += spec["engineFiles"][engine]
    elif spec.get("engine", True):
        out += m["engine"].get(engine, {}).get(spec.get("engineSections", "default"), m["engine"].get(engine, {}).get("default", []))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", default=os.path.join(SKILL, "config", "phases.json"))
    ap.add_argument("--engine", action="append")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--detail", help="one phase: its files and tokens")
    ap.add_argument("--reads", help="one phase: print the list of files its worker reads (paste into the prompt), with --engine")
    a = ap.parse_args()
    m = json.load(open(a.manifest, encoding="utf-8"))
    engines = a.engine or list(m["engine"])
    if a.reads:
        spec = m["phases"][a.reads]
        e = engines[0]
        print("READ:")
        for f in spec.get("reads", []) + (spec["engineFiles"][e] if e in spec.get("engineFiles", {}) else (m["engine"].get(e, {}).get(spec.get("engineSections", "default"), m["engine"].get(e, {}).get("default", [])) if spec.get("engine", True) else [])):
            print(" -", f)
        for f in spec.get("engineOptional", {}).get(e, []):
            print(" - (only if the GDD needs it)", f)
        return
    result = {"parent": tokens(m["parent"])[0], "phases": {}}
    bad = []
    t, miss, _ = tokens(m["parent"])
    bad += miss
    for ph in m["phases"]:
        row = {}
        for e in engines:
            tot, miss, per = tokens(phase_entries(m, ph, e))
            row[e] = tot
            bad += miss
            if a.detail == ph:
                print(ph, e, json.dumps(per, indent=1))
        result["phases"][ph] = row
    if a.json:
        print(json.dumps(result))
    else:
        print("%-20s %s" % ("phase", "  ".join("%9s" % e for e in engines)))
        print("%-20s %s" % ("PARENT (SKILL+playbook)", ""), result["parent"])
        sums = {e: 0 for e in engines}
        for ph, row in result["phases"].items():
            print("%-20s %s" % (ph, "  ".join("%9d" % row[e] for e in engines)))
            for e in engines:
                sums[e] += row[e]
        print("%-20s %s" % ("mean", "  ".join("%9d" % (sums[e] // max(1, len(result["phases"]))) for e in engines)))
    if bad:
        print("MISSING:", sorted(set(bad)), file=sys.stderr)
    if a.check and bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
