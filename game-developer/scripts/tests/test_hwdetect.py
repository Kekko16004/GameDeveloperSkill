#!/usr/bin/env python3
"""Offline tests of hwdetect.py (parsers, tiers, the GDD override):  python scripts/tests/test_hwdetect.py  [-v]"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import hwdetect  # noqa: E402


class Parsers(unittest.TestCase):
    def test_nvidia_smi_largest_first(self):
        g = hwdetect.parse_nvidia_smi("NVIDIA GeForce GTX 1050, 2048\nNVIDIA GeForce RTX 3060, 12288\n")
        self.assertEqual(g[0], ("NVIDIA GeForce RTX 3060", 12.0))
        self.assertEqual(len(g), 2)

    def test_windows_json_prefers_qword_memory(self):
        j = '[{"Name":"NVIDIA GeForce RTX 5060","AdapterRAM":4293918720,"QwMem":8589934592}]'
        self.assertEqual(hwdetect.parse_windows_json(j), [("NVIDIA GeForce RTX 5060", 8.0)])

    def test_windows_json_capped_adapter_ram_is_unknown(self):
        j = '{"Name":"Some GPU","AdapterRAM":4293918720,"QwMem":null}'
        self.assertEqual(hwdetect.parse_windows_json(j), [("Some GPU", None)])

    def test_garbage_is_empty(self):
        self.assertEqual(hwdetect.parse_windows_json("not json"), [])
        self.assertEqual(hwdetect.parse_nvidia_smi(""), [])

    def test_lspci(self):
        t = "00:02.0 VGA compatible controller: Intel Corporation UHD\n01:00.0 3D controller: NVIDIA Corporation GA107\n"
        self.assertEqual(len(hwdetect.parse_lspci(t)), 2)


class Tiers(unittest.TestCase):
    def test_tiers(self):
        self.assertEqual(hwdetect.build("NVIDIA GeForce RTX 3070", 8.0)["tier"], "high")
        self.assertEqual(hwdetect.build("NVIDIA GeForce GTX 1660 SUPER", 6.0)["tier"], "mid")
        self.assertEqual(hwdetect.build("Intel UHD", 2.0)["tier"], "low")
        self.assertEqual(hwdetect.build("", None)["tier"], "unknown")
        self.assertEqual(hwdetect.build("AMD Radeon", None)["tier"], "unknown")

    def test_gen3d_local_needs_nvidia_and_8gb(self):
        self.assertTrue(hwdetect.build("NVIDIA GeForce RTX 3070", 8.0)["gen3dLocalEligible"])
        self.assertFalse(hwdetect.build("NVIDIA GeForce GTX 1660 SUPER", 6.0)["gen3dLocalEligible"])
        self.assertFalse(hwdetect.build("AMD Radeon RX 7800 XT", 16.0)["gen3dLocalEligible"])


class Override(unittest.TestCase):
    def test_old_gdd_fields_still_read(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "GDD.md")
            open(p, "w", encoding="utf-8").write("genre: fps\ngpu: GTX 1660 Super   # old\nvram: 6\n")
            self.assertEqual(hwdetect.read_gdd_override(p), ("GTX 1660 Super", 6.0))

    def test_gdd_without_fields(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "GDD.md")
            open(p, "w", encoding="utf-8").write("genre: fps\n")
            self.assertEqual(hwdetect.read_gdd_override(p), (None, None))


if __name__ == "__main__":
    unittest.main()
