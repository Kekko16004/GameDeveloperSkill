#!/usr/bin/env python3
"""Every hard rule and gate item of the skill must still exist somewhere after a restructure.

  python scripts/rules_check.py            check config/rules.json against all .md/.py/.lua/.json of the skill (exit 1 if a phrase is gone)
  python scripts/rules_check.py --make REF  (re)build config/rules.json from the files of git revision REF (gate items, contract items, hard rules)

A rule is stored as the first words of its line (markdown marks removed). Moving a rule to another file keeps the check green; deleting
or rewording it makes it fail, and the person restructuring either restores it or changes rules.json on purpose.
"""
import argparse
import json
import os
import re
import subprocess
import sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(SKILL, "config", "rules.json")
SOURCES = {
    "references/gates.md": r"^(\d+[a-z]?)\.\s+",
    "references/workers.md": r"^(\d+)\.\s+\*\*",
    "SKILL.md": r"^(\d+)\.\s+|^- \*\*",
    "references/playtest.md": r"^- \*\*|^\d+\.\s+",
}


def norm(t):
    t = re.sub(r"[*`_]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def corpus():
    out = []
    for root, _, files in os.walk(SKILL):
        if "__pycache__" in root or os.sep + "tests" in root:
            continue
        for f in files:
            if f.endswith((".md", ".py", ".lua", ".json", ".ps1")) and f != "rules.json":
                with open(os.path.join(root, f), encoding="utf-8", errors="replace") as h:
                    out.append(norm(h.read()))
    return "\n".join(out)


def make(ref):
    rules = []
    for path, pat in SOURCES.items():
        txt = subprocess.run(["git", "show", "%s:game-developer/%s" % (ref, path)], capture_output=True, text=True, cwd=SKILL, encoding="utf-8").stdout
        for line in txt.splitlines():
            m = re.match(pat, line)
            if m:
                body = norm(re.sub(pat, "", line, count=1))
                words = body.split(" ")
                phrase = " ".join(words[:7])
                if len(phrase) >= 18:
                    rules.append({"file": path, "phrase": phrase})
    json.dump({"_doc": "first words of every gate item / contract item / hard rule; see scripts/rules_check.py", "rules": rules}, open(RULES, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(len(rules), "rules")


def check():
    text = corpus()
    data = json.load(open(RULES, encoding="utf-8"))
    gone = [r for r in data["rules"] if r["phrase"] not in text]
    for r in gone:
        print("MISSING (was in %s): %s" % (r["file"], r["phrase"]))
    print("%d rules, %d missing" % (len(data["rules"]), len(gone)))
    return 1 if gone else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--make")
    a = ap.parse_args()
    if a.make:
        make(a.make)
    else:
        sys.exit(check())
