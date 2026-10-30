#!/usr/bin/env python3
"""Tests of panel.py (readers, listening, queue, HTTP safety):  python scripts/tests/test_panel.py [-v]"""
import json
import os
import re
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import panel  # noqa: E402

PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000001"
                    "e221bc330000000049454e44ae426082")
REGISTRY = """# Tasks
| Other | table |
| TASK-999 | not a task table |

| ID | Fase | Descrizione | Spec | Evidenza | Dipende | Ed | Stato | Inizio | Durata | Note |
|---|---|---|---|---|---|---|---|---|---|---|
| TASK-001 | a | First thing: long tail | s | docs/gates/g1.md | - | x | [x] | | | |
| TASK-002 | a | Running thing | s | | TASK-001 | x | [/] | | | |
| TASK-003 | a | Noted thing | s | | TASK-001 | x | [ ] | | | |
| TASK-004 | a | Stuck thing | s | | - | x | [!] | | | no licence |
| TASK-005 | a | Built thing | s | | - | x | built, test pending | | | owner picks the colour |
| TASK-006 | a | Ready thing | s | | TASK-001 | x | [ ] | | | |
| TASK-007 | a | Waiting thing | s | | TASK-006 | x | [ ] | | | |
"""


def write(root, rel, content="", mode="w"):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
        f.write(content)
    return path


def filled(root):
    write(root, "GAME_TASKS.md", REGISTRY)
    write(root, "DECISIONI.md", "# D\n- older\n- newer about the store\n")
    write(root, "GDD.md", "target 60 fps stable\n")
    write(root, "docs/gates/g1.md", "# Gate one\nstatus: PASS\nbuild abc1234 GPU 12.5 ms / CPU 9.5 ms\nforward 8.5 (was 6.0)\n")
    write(root, "docs/progress/TASK-003.md", "Status: half way\nimages rig-side.png\n")
    write(root, "docs/progress/TASK-001.md", "engine_issues: the raycast misses\n")
    write(root, "screenshots/rig-side.png", PNG, "wb")
    write(root, "screenshots/TASK-006_ui.png", PNG, "wb")
    write(root, "secret.png", PNG, "wb")
    write(root, "screenshots/notes.txt", "not an image")


class Readers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        filled(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_task_states_and_labels(self):
        t = panel.tasks(self.root)
        self.assertEqual(t["total"], 7)  # the row of the other table is ignored
        self.assertEqual([x["id"] for x in t["done"]], ["001"])
        self.assertEqual([x["id"] for x in t["active"]], ["002"])
        self.assertEqual([x["id"] for x in t["inferred"]], ["003"])
        self.assertEqual(t["inferred"][0]["detail"], "half way")
        self.assertEqual(t["blocked"][0]["reason"], "no licence")
        self.assertEqual([x["id"] for x in t["built"]], ["005"])
        self.assertEqual(t["needs"][0]["task"], "005")
        self.assertEqual(t["open"], 5)
        self.assertEqual([(x["id"], x["waits"]) for x in t["next"]], [("006", []), ("007", ["006"])])
        self.assertEqual(t["done"][0]["title"], "First thing")

    def test_header_with_extra_column(self):
        rows = panel.parse_rows("| ID | Fase | Track | Task | Evidence | Depends | Status | Note |\n| TASK-1 | a | b | Name | e | - | [x] | n |\n")
        self.assertEqual((rows[0]["name"], rows[0]["status"], rows[0]["note"]), ("Name", "[x]", "n"))

    def test_other_sources(self):
        s = panel.build_state(self.root)
        self.assertEqual(s["decisions"][0], "newer about the store")
        self.assertEqual(s["gates"][0]["status"], "PASS")
        self.assertEqual(s["engineGaps"], [{"text": "the raycast misses", "source": "TASK-001.md"}])
        p = s["performance"]
        self.assertEqual((p["points"][0]["gpu"], p["points"][0]["build"], p["targetMs"]), (12.5, "abc1234", 16.67))
        self.assertEqual(p["passes"][0], {"name": "forward", "now": 8.5, "before": 6.0})

    def test_media(self):
        items = {i["name"]: i for i in panel.build_state(self.root)["media"]["items"]}
        self.assertEqual(set(items), {"rig-side.png", "TASK-006_ui.png"})
        self.assertEqual(items["TASK-006_ui.png"]["task"], "006")
        self.assertEqual(items["rig-side.png"]["task"], "003")  # the note names the file prefix

    def test_vsync_warning(self):
        write(self.root, "docs/gates/g1.md", "GPU 15 ms / CPU 16.67 ms\n")
        self.assertTrue(panel.performance(self.root)["maybeVsync"])

    def test_empty_project(self):
        with tempfile.TemporaryDirectory() as empty:
            s = panel.build_state(empty)
            self.assertFalse(s["tasks"]["exists"])
            self.assertEqual((s["gates"], s["decisions"], s["media"]["items"], s["performance"]["points"], s["lastActivity"]),
                             ([], [], [], [], None))
            self.assertFalse(s["launch"]["exists"])
            self.assertEqual(os.listdir(empty), [])  # reading writes nothing

    def test_launch(self):
        write(self.root, "launch/STATUS.md", "# Status\nGo with changes\n")
        write(self.root, "launch/TODO.md", "- [ ] a\n- [x] b\n- [ ] c\n")
        write(self.root, "launch/REPORT.html", "<p>r</p>")
        write(self.root, "launch/fg/waves/w01-sintesi.md", "x")
        info = panel.launch(self.root)
        self.assertEqual(info["headline"], "Go with changes")
        self.assertEqual(info["pages"], ["REPORT.html"])
        self.assertEqual({s["name"]: s["state"] for s in info["steps"]}["Launch todo"], "2 open, 1 done")
        self.assertEqual({s["name"]: s["state"] for s in info["steps"]}["Focus group"], "1 wave")


class Listening(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_heartbeat_goes_stale(self):
        self.assertFalse(panel.listening(self.root))
        panel.touch_heartbeat(self.root)
        self.assertTrue(panel.listening(self.root))
        old = time.time() - panel.STALE_SECONDS - 1
        os.utime(os.path.join(self.root, panel.HEARTBEAT), (old, old))
        self.assertFalse(panel.listening(self.root))

    def test_drain_empties_and_keeps_later_commands(self):
        panel.enqueue(self.root, {"type": "market_check"})
        lines = panel.drain(self.root)
        self.assertEqual(json.loads(lines[0])["type"], "market_check")
        self.assertEqual(panel.drain(self.root), [])
        panel.enqueue(self.root, {"type": "market_check"})
        self.assertEqual(len(panel.pending(self.root)), 1)


class Http(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.outer = self.tmp.name
        self.root = os.path.join(self.outer, "game")
        os.makedirs(self.root)
        filled(self.root)
        write(self.outer, "outside.png", PNG, "wb")
        self.server = panel.make_server(self.root, 0)
        self.port = self.server.server_address[1]
        self.token = self.server.RequestHandlerClass.token
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def call(self, path, data=None, headers=None):
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path), data=data, headers=headers or {})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def post(self, body, token=None):
        return self.call("/api/command", json.dumps(body).encode(), {"X-Panel-Token": token or self.token, "Content-Type": "application/json"})

    def test_binds_loopback_only(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_page_and_state(self):
        code, page = self.call("/")
        self.assertEqual(code, 200)
        self.assertIn(self.token.encode(), page)
        code, state = self.call("/api/state")
        self.assertEqual(json.loads(state)["tasks"]["total"], 7)

    def test_images_stay_inside(self):
        self.assertEqual(self.call("/img?p=screenshots/rig-side.png")[0], 200)
        for bad in ("secret.png", "screenshots/notes.txt", "screenshots/../secret.png", "../outside.png",
                    "screenshots/../../outside.png", "screenshots/..%5C..%5Coutside.png", os.path.join(self.outer, "outside.png"),
                    "screenshots/missing.png", ""):
            self.assertEqual(self.call("/img?p=" + bad)[0], 404, bad)

    def test_foreign_host_refused(self):
        self.assertEqual(self.call("/api/state", headers={"Host": "evil.example"})[0], 403)

    def test_commands(self):
        answer = {"type": "answer", "task": "005", "text": "red"}
        self.assertEqual(self.post(answer)[0], 409)  # not listening: view only
        self.assertFalse(os.path.exists(os.path.join(self.root, ".gds")))
        panel.touch_heartbeat(self.root)
        self.assertEqual(self.post(answer, "wrong")[0], 403)
        self.assertEqual(self.post({"type": "answer", "task": "006", "text": "x"})[0], 409)  # the registry does not ask this
        self.assertEqual(self.post({"type": "answer", "task": "005", "text": " "})[0], 409)
        self.assertEqual(self.post({"type": "shell", "cmd": "x"})[0], 409)
        self.assertEqual(self.post(answer)[0], 200)
        queued = panel.pending(self.root)
        self.assertEqual((queued[0]["type"], queued[0]["task"], queued[0]["text"]), ("answer", "005", "red"))
        self.assertEqual(queued[0]["question"], "owner picks the colour")
        self.assertEqual(self.call("/api/command", b"x" * 9000, {"X-Panel-Token": self.token})[0], 413)

    def test_launch_page_is_sandboxed(self):
        write(self.root, "launch/REPORT.html", "<p>r</p>")
        write(self.root, "launch/private.html", "<p>p</p>")
        req = urllib.request.Request("http://127.0.0.1:%d/launch/REPORT.html" % self.port)
        with urllib.request.urlopen(req) as r:
            self.assertIn("sandbox", r.headers["Content-Security-Policy"])
        self.assertEqual(self.call("/launch/private.html")[0], 404)


class NoGameData(unittest.TestCase):
    def test_page_has_placeholder_only(self):
        with open(panel.PAGE, encoding="utf-8") as f:
            page = f.read()
        self.assertIn("__TOKEN__", page)
        self.assertFalse(re.search(r"https?://", page))  # no outside request of any kind


if __name__ == "__main__":
    unittest.main()
