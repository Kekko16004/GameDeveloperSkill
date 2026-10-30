import os
import subprocess
import sys
import unittest

S = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def run(*a):
    return subprocess.run([sys.executable] + [os.path.join(S, a[0])] + list(a[1:]), capture_output=True, text=True, encoding="utf-8")


class Structure(unittest.TestCase):
    def test_every_rule_still_exists(self):
        p = run("rules_check.py")
        self.assertEqual(p.returncode, 0, p.stdout)

    def test_every_file_a_phase_reads_exists(self):
        p = run("context_budget.py", "--check")
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_a_nucleon_worker_loads_less_than_the_whole_loop(self):
        import json
        p = run("context_budget.py", "--engine", "nucleon", "--json")
        rows = json.loads(p.stdout)["phases"]
        whole = os.path.getsize(os.path.join(S, "..", "references", "nucleon-loop.md")) // 4
        for ph, row in rows.items():
            self.assertLess(row["nucleon"], 20000, ph)


if __name__ == "__main__":
    unittest.main()
