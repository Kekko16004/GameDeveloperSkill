#!/usr/bin/env python3
"""gds_bisect: find the commit that broke a test, checkpoint by checkpoint, then inside the guilty range (any engine).

  python gds_bisect.py --project PROJECT --test "<command that exits 0 when good>" [--good REF] [--bad HEAD]

The skill commits a checkpoint every 10 tasks ("checkpoint TASK-..."), so the search is cheap: first the checkpoint
commits only (each one compiled and passed its tests when it was made), then `git bisect run` between the last good
checkpoint and the first bad one. The working tree must be clean (it is restored at the end, whatever happens).
Examples of --test:
  Nucleon:  "NC_GDS_TEST=door_opens python <skill>/scripts/ncli.py --project . --stdio <editor> play-test --seconds 120 --expect \\"GDS-TEST DONE pass=1 fail=0\\""
  Unity:    "unity test . --mode EditMode --filter Interact_OpensDoor --format json"
Output: one JSON line {"first_bad": sha, "subject": ..., "files": [...], "steps": n}; the gate of the fix cites it.
"""
import argparse
import json
import subprocess
import sys


def git(proj, *args, check=True):
    r = subprocess.run(["git", "-C", proj] + list(args), capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit("git %s: %s" % (" ".join(args), r.stderr.strip()))
    return r.stdout.strip()


def passes(proj, test, timeout):
    try:
        return subprocess.run(test, shell=True, cwd=proj, timeout=timeout, capture_output=True).returncode == 0
    except subprocess.TimeoutExpired:
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".")
    ap.add_argument("--test", required=True)
    ap.add_argument("--good", help="a ref known good (default: the oldest checkpoint commit)")
    ap.add_argument("--bad", default="HEAD")
    ap.add_argument("--timeout", type=float, default=900)
    a = ap.parse_args()
    proj = a.project
    if git(proj, "status", "--porcelain"):
        raise SystemExit("the working tree has changes: commit or stash them first")
    start = git(proj, "rev-parse", "--abbrev-ref", "HEAD")
    if start == "HEAD":
        start = git(proj, "rev-parse", "HEAD")
    bad = git(proj, "rev-parse", a.bad)
    steps = 0
    try:
        checkpoints = git(proj, "log", "--grep=^checkpoint", "--format=%H", bad).split()
        good = git(proj, "rev-parse", a.good) if a.good else (checkpoints[-1] if checkpoints else None)
        if not good:
            raise SystemExit("no --good and no checkpoint commit")
        # 1. newest checkpoint first: the first one that passes is the last good one
        lo = good
        for c in checkpoints:
            if c == bad:
                continue
            git(proj, "checkout", "-q", c)
            steps += 1
            if passes(proj, a.test, a.timeout):
                lo = c
                break
        # 2. git bisect between that checkpoint and bad
        git(proj, "checkout", "-q", bad)
        git(proj, "bisect", "start", bad, lo)
        r = subprocess.run(["git", "-C", proj, "bisect", "run", "sh", "-c", a.test], capture_output=True, text=True,
                           timeout=a.timeout * 40)
        first = None
        for line in r.stdout.splitlines():
            if line.endswith("is the first bad commit"):
                first = line.split()[0]
        steps += r.stdout.count("running")
    finally:
        git(proj, "bisect", "reset", check=False)
        git(proj, "checkout", "-q", start, check=False)
    if not first:
        print(json.dumps({"first_bad": None, "good": lo, "bad": bad, "steps": steps, "note": "bisect did not converge"}))
        sys.exit(1)
    print(json.dumps({"first_bad": first, "subject": git(proj, "log", "-1", "--format=%s", first),
                      "files": git(proj, "show", "--name-only", "--format=", first).split(), "last_good": lo, "steps": steps}))


if __name__ == "__main__":
    main()
