#!/usr/bin/env python3
"""Tests of nc_proc.py (bounded processes, locks, watchdog) and nc_bench.py (pure parts):  python scripts/tests/test_nc_proc.py [-v]"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..")
sys.path.insert(0, SCRIPTS)
import nc_bench  # noqa: E402
import nc_proc  # noqa: E402


def dead_pid():
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


class Processes(unittest.TestCase):
    def test_pid_alive(self):
        self.assertTrue(nc_proc.pid_alive(os.getpid()))
        self.assertFalse(nc_proc.pid_alive(dead_pid()))
        self.assertIsNone(nc_proc.pid_alive(0))

    def test_timeout_kills_the_whole_tree_and_returns(self):
        # a child that starts a grandchild holding the same output and sleeps: a pipe-based run would wait for the grandchild
        code = ("import subprocess,sys,time;"
                "subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);print('child up',flush=True);time.sleep(60)")
        t0 = time.time()
        res = nc_proc.run_bounded([sys.executable, "-c", code], timeout=3)
        self.assertTrue(res["timedOut"])
        self.assertEqual(res["code"], 124)
        self.assertLess(time.time() - t0, 25)
        self.assertIn("child up", res["text"])

    def test_normal_exit_code_and_tail(self):
        res = nc_proc.run_bounded([sys.executable, "-c", "print('a');print('b');raise SystemExit(3)"], timeout=20, tail=1)
        self.assertEqual((res["code"], res["timedOut"], res["tail"]), (3, False, ["b"]))


class Locks(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.file = os.path.join(self.d, "Saved", "p.lock")
        self.dir = os.path.join(self.d, "gpu.lock")
        self.said = []

    def tearDown(self):
        nc_proc.HELD[:] = []
        import shutil
        shutil.rmtree(self.d, ignore_errors=True)

    def acquire(self, path, owner, kind="file", **kw):
        return nc_proc.lock_acquire(path, owner, kind=kind, say=self.said.append, poll=0.05, **kw)

    def test_second_owner_is_refused_and_told_who_holds_it(self):
        self.assertTrue(self.acquire(self.file, "w1", cmd="play-test")["locked"])
        r = self.acquire(self.file, "w2", wait=0)
        self.assertFalse(r["locked"])
        self.assertEqual((r["heldBy"], r["cmd"]), ("w1", "play-test"))
        self.assertIn("ageS", r)

    def test_same_owner_is_reentrant_and_release_is_owner_only(self):
        self.acquire(self.file, "w1")
        self.assertTrue(self.acquire(self.file, "w1")["reentrant"])
        self.assertFalse(nc_proc.lock_release(self.file, "w2")["released"])
        self.assertTrue(nc_proc.lock_release(self.file, "w1")["released"])
        self.assertTrue(self.acquire(self.file, "w2")["locked"])

    def test_dead_holder_is_taken_over(self):
        nc_proc.lock_acquire(self.file, "ghost", pid=dead_pid(), say=self.said.append)
        r = self.acquire(self.file, "w2", wait=0)
        self.assertTrue(r["locked"])
        self.assertTrue(any("pid" in m and "dead" in m for m in self.said), self.said)

    def test_hold_time_is_a_maximum(self):
        nc_proc.lock_acquire(self.file, "slow", pid=0, max_hold=0.2, say=self.said.append)
        time.sleep(0.4)
        self.assertTrue(self.acquire(self.file, "w2", wait=0)["locked"])
        self.assertTrue(any("maximum" in m for m in self.said), self.said)

    def test_pid_less_lock_is_never_judged_by_pid(self):
        nc_proc.lock_acquire(self.file, "shell", pid=0, max_hold=600)
        self.assertIsNone(nc_proc.stale_reason(nc_proc.read_lock(self.file)))

    def test_waiting_names_the_holder(self):
        self.acquire(self.dir, "w1", "dir", cmd="bench level")
        r = nc_proc.lock_acquire(self.dir, "w2", wait=0.3, kind="dir", say=self.said.append, notify=0.05, poll=0.05)
        self.assertFalse(r["locked"])
        self.assertTrue(any("held by w1" in m and "bench level" in m for m in self.said), self.said)

    def test_directory_lock_is_readable_by_bash_tools(self):
        # the bash tools read field 2 of `owner` as a pid: ours is the bare name, so they never take it for a dead one
        self.acquire(self.dir, "worker-1", "dir")
        self.assertEqual(open(os.path.join(self.dir, "owner")).read(), "worker-1")
        self.assertTrue(os.path.exists(os.path.join(self.dir, "info.json")))

    def test_foreign_directory_lock_is_not_judged_or_broken(self):
        os.mkdir(self.dir)
        open(os.path.join(self.dir, "owner"), "w").write("fx075 4242")
        info = nc_proc.read_lock(self.dir, "dir")
        self.assertTrue(info["foreign"])
        self.assertIsNone(nc_proc.stale_reason(info))
        r = self.acquire(self.dir, "w2", "dir", wait=0)
        self.assertEqual(r["heldBy"], "fx075 4242")
        self.assertTrue(nc_proc.lock_release(self.dir, "x", "dir", force=True)["released"])

    def test_released_on_normal_exit_and_on_exception(self):
        for tail in ("pass", "raise RuntimeError('boom')"):
            path = os.path.join(self.d, "x-%d.lock" % len(tail))
            code = ("import sys;sys.path.insert(0,%r);import nc_proc;nc_proc.lock_acquire(%r,'w9');%s" % (SCRIPTS, path, tail))
            subprocess.run([sys.executable, "-c", code], capture_output=True)
            self.assertFalse(os.path.exists(path), "lock left behind after: " + tail)

    def test_watchdog_exits_124_and_releases(self):
        path = os.path.join(self.d, "w.lock")
        code = ("import sys,time;sys.path.insert(0,%r);import nc_proc;nc_proc.lock_acquire(%r,'w9');"
                "nc_proc.start_watchdog(1,lambda s:print('fired'));time.sleep(30)" % (SCRIPTS, path))
        t0 = time.time()
        p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=25)
        self.assertEqual(p.returncode, 124)
        self.assertLess(time.time() - t0, 20)
        self.assertIn("fired", p.stdout)
        self.assertFalse(os.path.exists(path))


class Bench(unittest.TestCase):
    def rows(self, ms, draws=100):
        return [{"ms": str(m), "drawCalls": str(draws), "instancedItems": "5", "cpuFrameMs": ""} for m in ms]

    def test_percentiles_and_attribution(self):
        wall = [10.0] * 90 + [30.0] * 10
        s = nc_bench.summarize(self.rows(wall), [9.0] * 20, [{"ms": 4.0, "items": 50, "draws": 80}] * 20,
                               [{"present": 0.4}], "lvl", fps=60)
        self.assertEqual(s["wall_ms"]["p50"], 10.0)
        self.assertEqual(s["wall_ms"]["p99"], 30.0)
        self.assertEqual(s["bound"], "gpu")
        self.assertEqual(s["budget_ms"], 16.67)
        self.assertTrue(s["overBudget"])           # p95 30 ms against 16.67
        self.assertEqual(s["drawCalls"]["p50"], 100)

    def test_cpu_bound_and_present_bound(self):
        base = dict(wall_ms={"p50": 10}, gpu_ms={"p50": 4}, cpu_ms={"p50": 9}, present_ms={"mean": 0.1})
        self.assertEqual(nc_bench.attribute(base), "cpu")
        base["present_ms"] = {"mean": 5}
        self.assertEqual(nc_bench.attribute(base), "present")

    def test_vsync_lock_is_detected_but_a_real_gpu_cost_is_not(self):
        locked = [16.67] * 200
        self.assertIn("60 Hz", nc_bench.looks_vsynced(locked, [6.0] * 50))
        self.assertIsNone(nc_bench.looks_vsynced(locked, [16.0] * 50))     # the GPU takes the whole interval: a cost
        self.assertIsNone(nc_bench.looks_vsynced([11.0 + (i % 7) for i in range(200)], [5.0] * 50))

    def test_compare_flags_only_p95_regressions_over_tolerance(self):
        base = {"wall_ms": {"p50": 10, "p95": 12, "p99": 14}, "gpu_ms": {"p95": 9}, "cpu_ms": {"p95": 5}, "drawCalls": {"p50": 1000}}
        cur = {"wall_ms": {"p50": 10.5, "p95": 14, "p99": 14.2}, "gpu_ms": {"p95": 9}, "cpu_ms": {"p95": 4}, "drawCalls": {"p50": 800}}
        c = nc_bench.compare(cur, base, 10)
        self.assertEqual([x.split(" ")[0] for x in c["regress"]], ["wall_ms.p95"])
        self.assertTrue(any(x.startswith("drawCalls") for x in c["improved"]))
        self.assertEqual(c["deltaPct"]["wall_ms.p50"], 5.0)

    def test_window_parser_reads_cpu_gpu_and_present(self):
        log = os.path.join(tempfile.mkdtemp(), "run.log")
        open(log, "w").write("\n".join([
            "Modern CPU frame 1: frame 1.0 ms (x); 9 items (0 gpu-driven in 0 classes), 7 draw calls, 0 indirect draws; GPU frame 1.0 ms",
            "GDS-BENCH begin v",
            "Modern CPU frame 2: frame 4.50 ms (c); 50 items (0 gpu-driven in 0 classes), 80 draw calls, 0 indirect draws; GPU frame 7.0 ms (complete)",
            "GPU timings at frame 5: frame 7.00 ms,   sky 1.00 ms",
            "[threads] frames 60: interval 8.00 ms (125.0 fps); main thread cpu 1; submit 0.30 present 0.45 ms; 8 job threads",
            "GDS-BENCH end v frames=3",
            "Modern CPU frame 3: frame 99.0 ms (c); 1 items (0 gpu-driven in 0 classes), 1 draw calls"]))
        gpu, cpu, th, soft = nc_bench.parse_window(log, "v")
        self.assertEqual((gpu, [c["draws"] for c in cpu], [t["present"] for t in th], soft), ([7.0], [80], [0.45], False))


if __name__ == "__main__":
    unittest.main()
