#!/usr/bin/env python3
"""Unit tests of the offline parts of ncli.py (standard library only):  python scripts/tests/test_ncli.py  [-v]
Covers: the flat under a "ground" origin, ground-level floors, room parts from a blueprint, and which floating objects
the lint keeps (the Play probe itself runs in the engine: references/scene-lint.md "Nucleon")."""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import ncli  # noqa: E402

TOL = 0.05


def box(i, name, lo, hi, typ="shape", parent=None):
    e = {"id": i, "name": name, "type": typ, "world_bounds": {"min": list(lo), "max": list(hi)}}
    if parent is not None:
        e["parent"] = parent
    return e


def fl(e, gap=1.0):
    return {"name": e["name"], "id": e["id"], "gap": gap}


class FlatUnder(unittest.TestCase):
    FLATS = [
        {"x": -200, "y": -140, "r": 180, "z": 11.852, "id": "town"},
        {"x": -260, "y": -364, "r": 40, "z": 15.624, "id": "station"},
        {"x": -216.0, "y": -32.0, "r": 167.04, "z": 11.852, "id": "north_lot", "lot": [-376, -80, 320, 96]},
        {"x": -216.0, "y": -252.0, "r": 169.52, "z": 11.852, "id": "south_lot", "lot": [-376, -308, 320, 112]},
    ]

    def test_lot_corner_is_inside(self):
        # hypot(160, 48) = 167.045 > r 167.04 (the rounded half diagonal): the old circle test missed the corner
        f, how = ncli.flat_under(self.FLATS, -376, -80)
        self.assertEqual((f["id"], how), ("north_lot", "lot"))

    def test_overlapping_circle_does_not_win_by_file_order(self):
        # the south lot's circle contains the station origin, its rectangle does not: the station flat is the one
        f, _ = ncli.flat_under(self.FLATS, -284, -376)
        self.assertEqual(f["id"], "station")
        self.assertAlmostEqual(f["z"], 15.624)

    def test_nearest_centre_relative_to_radius(self):
        flats = [{"x": 0, "y": 0, "r": 100, "z": 1.0, "id": "big"}, {"x": 50, "y": 0, "r": 10, "z": 2.0, "id": "small"}]
        self.assertEqual(ncli.flat_under(flats, 52, 0)[0]["id"], "small")
        self.assertEqual(ncli.flat_under(flats, -20, 0)[0]["id"], "big")
        self.assertEqual(ncli.flat_under(flats, 500, 0), (None, None))

    def test_ground_origin_reads_layouts(self):
        d = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(d, "art", "world"))
            with open(os.path.join(d, "art", "world", "w.layout.json"), "w", encoding="utf-8") as f:
                json.dump({"flats": self.FLATS}, f)
            z, info = ncli.ground_origin(d, -376, -80)
            self.assertEqual((z, info["id"], info["how"]), (11.852, "north_lot", "lot"))
            with self.assertRaises(ncli.McpError):
                ncli.ground_origin(d, 900, 900)
        finally:
            shutil.rmtree(d)


class GroundLevel(unittest.TestCase):
    def test_upper_floor_is_not_ground(self):
        solids = [
            box(1, "Terrain", (-500, -500, -10), (500, 500, 30), "landscape"),
            box(2, "flat_floor", (0, 0, -0.2), (4, 4, 0)),            # ground floor slab
            box(3, "flat_wallS0", (0, 0, 0), (4, 0.2, 2.8)),          # its wall
            box(4, "flat1_floor", (0, 0, 2.8), (4, 4, 3.0)),          # the floor of the storey above, on the wall
            box(5, "road_seg3", (10, 0, -0.1), (20, 6, 0)),
            box(6, "tower_deck_floor", (30, 0, 4), (32, 2, 4.2)),     # a deck on legs
            box(7, "tower_leg0", (30, 0, 0), (30.2, 0.2, 4)),
        ]
        ids, upper = ncli.ground_level_ids(solids, re.compile(r"ground|floor|terrain|landscape|road|path", re.I), TOL)
        self.assertEqual(sorted(ids), [1, 2, 5])
        self.assertEqual(sorted(upper), ["flat1_floor", "tower_deck_floor"])


class GroundNamed(unittest.TestCase):
    def test_word_not_inside_a_word(self):
        rx = re.compile(r"ground|floor|terrain|landscape|road|path", re.I)
        for name in ("Ground", "floor_1_0", "R1_road_051", "flatA1_floor", "block1_s0_core1_floor_slab0", "MainFloor",
                     "GroundPlane", "TERRAIN"):
            self.assertTrue(ncli.ground_named(name, rx), name)
        for name in ("playground_sandbox", "ZZ_LINTTEST_underground", "footpath_sign", "crate"):
            self.assertFalse(ncli.ground_named(name, rx), name)


class RoomParts(unittest.TestCase):
    def test_from_blueprint_and_names(self):
        d = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(d, "art", "blueprints"))
            spec = {"name": "house", "rooms": [{"name": "hall", "x": 0, "y": 0, "w": 6, "d": 4, "h": 3, "ceiling": True,
                                                "doors": [{"side": "S", "at": 0.5, "width": 1.2, "height": 2.2}]}]}
            with open(os.path.join(d, "art", "blueprints", "house.json"), "w", encoding="utf-8") as f:
                json.dump(spec, f)
            ents = [{"id": 100, "name": "BP_house", "type": "folder"},
                    {"id": 1, "name": "hall_floor", "type": "shape", "parent": 100},
                    {"id": 2, "name": "hall_wallS0", "type": "shape", "parent": 100},
                    {"id": 3, "name": "hall_wallS1", "type": "shape", "parent": 100},   # the lintel over the door
                    {"id": 4, "name": "hall_ceiling", "type": "shape", "parent": 100},
                    {"id": 5, "name": "shed_wallE2", "type": "shape"},                  # no blueprint: by name
                    {"id": 6, "name": "crate", "type": "shape", "parent": 100}]
            idx = ncli.room_parts_index(d, ents)
            self.assertEqual(idx[1], ("house/hall", "floor"))
            self.assertEqual(idx[2], ("house/hall", "wall"))
            self.assertEqual(idx[3], ("house/hall", "lintel"))
            self.assertEqual(idx[4], ("house/hall", "ceiling"))
            self.assertEqual(idx[5], ("/shed", "wall"))
            self.assertNotIn(6, idx)
        finally:
            shutil.rmtree(d)


class SettleFloating(unittest.TestCase):
    def setUp(self):
        self.terrain = box(1, "Terrain", (-500, -500, -10), (500, 500, 30), "landscape")

    def settle(self, solids, floating, rooms=None, ground=(1,)):
        flagged = [f["id"] for f in floating]
        return ncli.settle_floating(solids, floating, flagged, set(ground), rooms or {}, TOL)

    def room(self, z=0.0, prefix="r", base=10):
        """A 4 x 4 room: floor, S wall left / right of a door and the lintel over it, N wall, ceiling."""
        return [box(base + 0, prefix + "_floor", (0, 0, z - 0.2), (4, 4, z)),
                box(base + 1, prefix + "_wallS0", (0, 0, z), (1.4, 0.2, z + 2.8)),
                box(base + 2, prefix + "_wallS2", (2.6, 0, z), (4, 0.2, z + 2.8)),
                box(base + 3, prefix + "_wallS1", (1.4, 0, z + 2.2), (2.6, 0.2, z + 2.8)),   # lintel
                box(base + 4, prefix + "_wallN0", (0, 3.8, z), (4, 4, z + 2.8)),
                box(base + 5, prefix + "_ceiling", (0, 0, z + 2.8), (4, 4, z + 3.0))]

    def rooms_of(self, parts, key="bp/r"):
        roles = {"floor": "floor", "wallS1": "lintel", "ceiling": "ceiling"}
        return {e["id"]: (key, roles.get(e["name"].split("_", 1)[1], "wall")) for e in parts}

    def test_lintel_and_ceiling_held_by_their_room(self):
        parts = self.room()
        lintel, ceiling = parts[3], parts[5]
        kept, held = self.settle([self.terrain] + parts, [fl(lintel, 2.2), fl(ceiling, 3.0)], self.rooms_of(parts))
        self.assertEqual(kept, [])
        self.assertEqual({h["name"]: h["how"] for h in held}, {"r_wallS1": "room", "r_ceiling": "restsOn"})

    def test_room_floor_floating_is_kept_and_its_walls_do_not_hold_it(self):
        parts = self.room(z=1.0)     # the whole room 1 m above the terrain
        floor = parts[0]
        floating = [fl(floor, 0.8), fl(parts[3], 2.2)]
        kept, _ = self.settle([self.terrain] + parts, floating, self.rooms_of(parts))
        self.assertEqual(sorted(f["name"] for f in kept), ["r_floor", "r_wallS1"])

    def test_lintel_of_another_room_does_not_hold(self):
        parts = self.room()
        lone = box(50, "x_wallS1", (1.4, -0.4, 2.2), (2.6, -0.2, 2.8))   # touches room r's wall, belongs to room x
        rooms = self.rooms_of(parts)
        rooms[50] = ("bp/x", "lintel")
        kept, _ = self.settle([self.terrain] + parts + [lone], [fl(lone, 2.2)], rooms)
        self.assertEqual([f["name"] for f in kept], ["x_wallS1"])

    def test_roof_on_posts_and_sign_on_post(self):
        posts = [box(20 + k, "shelter_post%d" % k, (x, y, 0), (x + 0.15, y + 0.15, 2.5))
                 for k, (x, y) in enumerate(((0, 0), (3.85, 0), (0, 2.85), (3.85, 2.85)))]
        roof = box(30, "shelter_roof", (-0.2, -0.2, 2.5), (4.2, 3.2, 2.6))
        pole = box(31, "sign_pole", (10, 0, 0), (10.1, 0.1, 3))
        plate = box(32, "sign_plate", (10.1, -0.3, 2.0), (10.12, 0.4, 2.6))
        kept, held = self.settle([self.terrain] + posts + [roof, pole, plate], [fl(roof, 2.5), fl(plate, 2.0)])
        self.assertEqual(kept, [])
        self.assertEqual({h["name"]: h["how"] for h in held}, {"shelter_roof": "restsOn", "sign_plate": "attached"})

    def test_really_floating_box_is_kept(self):
        parts = self.room()
        free = box(40, "crate_air", (1.5, 1.5, 1.0), (2.5, 2.5, 2.0))       # in the room, touching nothing
        sky = box(41, "crate_sky", (50, 50, 5.0), (51, 51, 6.0))           # over open ground
        kept, _ = self.settle([self.terrain] + parts + [free, sky], [fl(free, 1.0), fl(sky, 5.0)], self.rooms_of(parts))
        self.assertEqual(sorted(f["name"] for f in kept), ["crate_air", "crate_sky"])

    def test_hanging_from_a_line_through_its_poles(self):
        # the line passes through its poles (their tops are higher): it stands on nothing, it is fixed to them; the
        # washing hangs from the line (top at the line's bottom) - neither floats, nor does a trolley under its beam
        poles = [box(70, "wash_poleA", (-0.05, -0.05, 0), (0.05, 0.05, 2.3)), box(71, "wash_poleB", (7.95, -0.05, 0), (8.05, 0.05, 2.3))]
        line = box(72, "wash_line", (0, -0.01, 2.0), (8, 0.01, 2.02))
        cloth = box(73, "wash_cloth", (2.5, -0.01, 1.4), (5.5, 0.01, 2.0))
        col = box(74, "crane_col", (20, 0, 0), (20.5, 0.5, 6))
        beam = box(75, "crane_beam", (20, 0, 6), (40, 0.5, 6.5))
        trolley = box(76, "crane_trolley", (25, -0.5, 5.2), (27, 1.0, 6.0))
        kept, held = self.settle([self.terrain] + poles + [line, cloth, col, beam, trolley], [fl(cloth, 1.4), fl(trolley, 5.2)])
        self.assertEqual(kept, [])
        self.assertEqual({h["name"]: h["how"] for h in held}, {"wash_cloth": "hangsFrom", "crane_trolley": "hangsFrom"})

    def test_gap_under_the_beam_is_kept(self):
        col = box(74, "crane_col", (20, 0, 0), (20.5, 0.5, 6))
        beam = box(75, "crane_beam", (20, 0, 6), (40, 0.5, 6.5))
        trolley = box(76, "crane_trolley", (25, -0.5, 5.0), (27, 1.0, 5.8))   # 0.2 m under the beam: floats
        kept, _ = self.settle([self.terrain, col, beam, trolley], [fl(trolley, 5.0)])
        self.assertEqual([f["name"] for f in kept], ["crane_trolley"])

    def test_mezzanine_floor_held_by_the_hall_not_by_its_own_walls(self):
        hall_wall = box(80, "hall_wallN0", (0, 10, 0), (20, 10.3, 9))
        floor = box(81, "office_floor", (0, 6, 4.8), (6, 10, 5.0))           # against the hall wall, 4.8 m up
        wall = box(82, "office_wallS0", (0, 6, 5.0), (6, 6.2, 7.8))
        rooms = {81: ("bp/office", "floor"), 82: ("bp/office", "wall")}
        kept, held = self.settle([self.terrain, hall_wall, floor, wall], [fl(floor, 4.8)], rooms)
        self.assertEqual(kept, [])
        self.assertEqual(held[0]["how"], "attached")
        lone = box(83, "loft_floor", (30, 6, 4.8), (36, 10, 5.0))           # the same office in open air
        lwall = box(84, "loft_wallS0", (30, 6, 5.0), (36, 6.2, 7.8))
        rooms = {83: ("bp/loft", "floor"), 84: ("bp/loft", "wall")}
        kept, _ = self.settle([self.terrain, lone, lwall], [fl(lone, 4.8)], rooms)
        self.assertEqual([f["name"] for f in kept], ["loft_floor"])

    def test_stack_on_a_floating_box_reports_the_root_only(self):
        base = box(60, "pallet", (0, 0, 1.0), (1, 1, 1.2))      # floats 1 m
        top = box(61, "crate", (0.1, 0.1, 1.2), (0.9, 0.9, 2.0))  # rests on the pallet: the probe says fine
        kept, held = self.settle([self.terrain, base, top], [fl(base, 1.0)])
        self.assertEqual([f["name"] for f in kept], ["pallet"])
        self.assertEqual(held, [])


class CamerasPostFlags(unittest.TestCase):
    """The spec keys added for the camera entity, render flags and post process volumes (docs/engine/CAMERA.md, RENDER_FLAGS.md)."""

    def calls(self, spec):
        import nc_gds
        return nc_gds.build_calls(spec, None)

    def test_camera_looks_at_target(self):
        import nc_gds
        # +Y is north and yaw 0 faces +Y; a target to the east (+X) is a clockwise turn = negative yaw; below = negative pitch
        self.assertEqual(nc_gds.look_rotation([0, 0, 0], [0, 10, 0]), [0.0, 0.0, 0.0])
        self.assertEqual(nc_gds.look_rotation([0, 0, 0], [10, 0, 0])[2], 270.0)
        self.assertEqual(nc_gds.look_rotation([0, 0, 0], [-10, 0, 0])[2], 90.0)
        self.assertEqual(nc_gds.look_rotation([0, 0, 10], [0, 10, 0])[0], -45.0)

    def test_camera_entry_becomes_entity_add(self):
        calls, warnings = self.calls({"origin": [10, 0, 0], "cameras": [
            {"name": "Hero", "position": [0, -5, 2], "target": [0, 0, 2], "focalLength": 35, "depthOfField": True, "fStop": 2.8,
             "renderFlags": {"hiddenInGame": True}}]})
        cam = calls[0]
        self.assertEqual(cam["type"], "camera")
        self.assertEqual(cam["position"], [10.0, -5.0, 2.0])
        self.assertEqual(cam["camera"], {"focal_length": 35, "depth_of_field": True, "f_stop": 2.8})
        self.assertNotIn("render_flags", cam)           # a camera has no render flags
        self.assertTrue(any("no render flags" in w for w in warnings))

    def test_render_flags_names_and_shape_cast_shadow(self):
        calls, warnings = self.calls({"shapes": [
            {"name": "post", "position": [0, 0, 1], "shape": {"kind": "box", "width": 1, "depth": 1, "height": 1},
             "renderFlags": {"castShadow": False, "affectGI": False, "hiddenInGame": True}}]})
        # castShadow works on a shape since a58cb429 (verified): it is sent, no warning
        self.assertEqual(calls[0]["render_flags"], {"cast_shadow": False, "affect_indirect_lighting": False, "hidden_in_game": True})
        self.assertFalse(any("castShadow" in w for w in warnings))

    def test_post_volume_entry(self):
        calls, _ = self.calls({"postVolumes": [{"name": "Night", "unbound": True, "priority": 2, "blendRadius": 3,
                                                 "settings": {"bloom": True}, "blendables": [{"material": "Content/Materials/PP.ncmat", "weight": 0.5}]}]})
        self.assertEqual(calls[0]["type"], "post_volume")
        self.assertEqual(calls[0]["post_volume"], {"unbound": True, "priority": 2, "blend_radius": 3, "settings": {"bloom": True},
                                                   "blendables": [{"material": "Content/Materials/PP.ncmat", "weight": 0.5}]})


class WorldFlats(unittest.TestCase):
    def test_flat_z_is_read_as_y(self):
        import nc_world
        w = {"name": "t", "mode": "terrain", "seed": 1, "terrain": {"size": 40, "resolution": 33, "flat": [{"x": 1, "z": 5, "r": 6, "spawn": True}]}}
        spec, layout, _ = nc_world.terrain_world(w, tempfile.mkdtemp(), None)
        self.assertEqual(layout["flats"][0]["y"], 5)


class ListEntities(unittest.TestCase):
    class Ed:
        def __init__(self):
            self.calls = []

        def call(self, tool, args=None):
            self.calls.append((tool, args))
            ents = [{"id": 1, "name": "Cam", "type": "camera"}, {"id": 2, "name": "Box", "type": "model"},
                    {"id": 3, "name": "PV", "type": "post volume"}]
            if args and args.get("type"):
                ents = [e for e in ents if e["type"] == args["type"]]
            return {"count": len(ents), "entities": ents}

    def test_known_type_is_filtered_by_the_editor(self):
        ed = self.Ed()
        self.assertEqual([e["name"] for e in ncli.list_entities(ed, "model")["entities"]], ["Box"])
        self.assertEqual(ed.calls[0][1], {"type": "model"})

    def test_unknown_type_is_filtered_here(self):
        ed = self.Ed()
        res = ncli.list_entities(ed, "post_volume")
        self.assertEqual([e["name"] for e in res["entities"]], ["PV"])
        self.assertNotIn("type", ed.calls[0][1])
        self.assertEqual(ncli.list_entities(ed, "camera")["count"], 1)


class ToolCommands(unittest.TestCase):
    """weather / destruction / memory: the argument list each command sends to its MCP tool (no editor)."""

    class Client:
        def close(self):
            pass

    class Ed:
        def __init__(self, reply=None):
            self.calls = []
            self.client = ToolCommands.Client()
            self.reply = reply or {"ok": True}

        def call(self, tool, args=None):
            self.calls.append((tool, args))
            return self.reply

    def run_cmd(self, *argv, reply=None):
        import io
        from contextlib import redirect_stdout
        ed = self.Ed(reply)
        old_argv, old_connect = sys.argv, ncli.connect
        sys.argv, ncli.connect = ["ncli.py"] + list(argv), lambda a: ed
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                ncli.main()
        finally:
            sys.argv, ncli.connect = old_argv, old_connect
        return ed.calls, json.loads(out.getvalue().strip().splitlines()[-1])

    def test_weather_set(self):
        calls, _ = self.run_cmd("weather", "set", "--preset", "Storm", "--time", "19.5", "--wind-heading", "90", "--wind-speed", "12",
                                "--no-surfaces", "--param", "puddles=1", "--param", "rain=0.4")
        self.assertEqual(calls, [("weather", {"action": "set", "preset": "Storm", "time_of_day": 19.5, "wind_heading": 90.0,
                                               "wind_speed": 12.0, "surfaces": False, "params": {"puddles": 1, "rain": 0.4}})])

    def test_weather_live_and_strike(self):
        calls, _ = self.run_cmd("weather", "set", "--scope", "live", "--preset", "Fog", "--blend", "30")
        self.assertEqual(calls[0][1], {"action": "set", "scope": "live", "preset": "Fog", "blend": 30.0})
        calls, _ = self.run_cmd("weather", "strike", "--intensity", "1.5")
        self.assertEqual(calls[0][1], {"action": "strike", "intensity": 1.5})

    def test_weather_get_drops_the_project_table(self):
        reply = {"level": {"preset": "Rain"}, "project": {"preset": "Clear", "timeOfDay": 9},
                 "live": {"active": True, "preset": "Rain", "progress": 1.0, "current": {"rain": 0.7}, "target": {"rain": 0.7}}}
        _, out = self.run_cmd("weather", "get", reply=reply)
        self.assertEqual(out, {"level": {"preset": "Rain"}, "projectKeys": ["preset", "timeOfDay"],
                               "live": {"active": True, "preset": "Rain", "progress": 1.0}})
        _, full = self.run_cmd("weather", "get", "--full", reply=reply)
        self.assertEqual(full, reply)

    def test_destruction_fracture_and_actor(self):
        calls, _ = self.run_cmd("destruction", "fracture", "--model", "Content/Crate.glb", "--pieces", "24", "--seed", "3")
        self.assertEqual(calls[0], ("destruction", {"action": "fracture", "model": "Content/Crate.glb", "pieces": 24, "seed": 3}))
        calls, _ = self.run_cmd("destruction", "make-actor", "--model", "Content/Crate.glb", "--path", "Content/Actors/Crate.ncactor",
                                "--health", "40", "--dynamic", "--no-staged")
        self.assertEqual(calls[0][1], {"action": "make_actor", "model": "Content/Crate.glb", "path": "Content/Actors/Crate.ncactor",
                                       "health": 40.0, "dynamic": True, "staged": False})

    def test_destruction_play_actions_take_z_up_vectors(self):
        calls, _ = self.run_cmd("destruction", "ray", "--from", "0,-5,1", "--to", "0,5,1", "--amount", "20", "--impulse", "4")
        self.assertEqual(calls[0][1], {"action": "ray", "amount": 20.0, "impulse": 4.0, "from": [0.0, -5.0, 1.0], "to": [0.0, 5.0, 1.0]})
        calls, _ = self.run_cmd("destruction", "explode", "--position", "-3,2,1", "--radius-m", "6", "--force", "500")
        self.assertEqual(calls[0][1], {"action": "explode", "radius_m": 6.0, "force": 500.0, "position": [-3.0, 2.0, 1.0]})
        calls, _ = self.run_cmd("destruction", "cloth-wind", "--cloth", "1", "--wind", "6,0,0")
        self.assertEqual(calls[0][1], {"action": "cloth_wind", "cloth": 1, "wind": [6.0, 0.0, 0.0]})
        calls, _ = self.run_cmd("destruction", "make-cloth-actor", "--path", "Content/Actors/Flag.ncactor", "--wind", "true")
        self.assertEqual(calls[0][1]["wind"], True)

    def test_memory(self):
        calls, _ = self.run_cmd("memory", "--kind", "gpu")
        self.assertEqual(calls[0], ("memory_stats", {"action": "memory", "kind": "gpu"}))

    def test_render_flags_new_names(self):
        import nc_gds
        args = {"type": "model", "name": "m"}
        nc_gds.flags_of({"renderFlags": {"receiveShadow": False, "customDepth": 3, "lightingChannels": 2}}, args)
        self.assertEqual(args["render_flags"], {"receive_shadow": False, "custom_depth_stencil": 3, "lighting_channels": 2})


class Ownership(unittest.TestCase):
    """The incident: a worker's play-test attached to another worker's serve session and its session-stop closed it."""

    def setUp(self):
        import argparse
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        self.argparse = argparse
        self.d = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.d, "Saved"))
        hits = self.hits = []

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _ok(self):
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

            def do_GET(self):
                self._ok()

            def do_POST(self):
                hits.append(self.path)
                self._ok()
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        with open(ncli.session_path(self.d), "w") as f:
            json.dump({"port": self.srv.server_address[1], "token": "t", "pid": os.getpid(), "owner": "w1", "stdio": "x"}, f)

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        shutil.rmtree(self.d, ignore_errors=True)

    def ns(self, cmd, worker=None, **kw):
        return self.argparse.Namespace(cmd=cmd, worker=worker, project=self.d, port=None, token=None, stdio=None, timeout=5,
                                       no_lua=False, save=False, break_owner=None, **kw)

    def test_other_worker_cannot_use_the_session_for_a_run(self):
        sess = ncli.read_session(self.d)
        for who in ("w2", None):
            with self.assertRaises(ncli.McpError) as cm:
                ncli.check_session_access(self.ns("play-test", who), sess)
            self.assertIn("belongs to 'w1'", str(cm.exception))
        ncli.check_session_access(self.ns("play-test", "w1"), sess)            # the owner is fine

    def test_reads_are_open_to_everyone(self):
        sess = ncli.read_session(self.d)
        ncli.check_session_access(self.ns("ping", "w2"), sess)
        ncli.check_session_access(self.ns("entity", "w2", action="get"), sess)
        with self.assertRaises(ncli.McpError):
            ncli.check_session_access(self.ns("entity", "w2", action="set"), sess)

    def test_connect_refuses_before_any_call(self):
        with self.assertRaises(ncli.McpError):
            ncli.connect(self.ns("play-test", "w2"))
        self.assertEqual(self.hits, [])

    def test_session_stop_is_owner_only(self):
        with self.assertRaises(ncli.McpError) as cm:
            ncli.cmd_session_stop(self.ns("session-stop", "w2"))
        self.assertIn("--break w1", str(cm.exception))
        self.assertEqual(self.hits, [])                                      # nothing reached the session
        a = self.ns("session-stop", "w2")
        a.break_owner = "w3"
        with self.assertRaises(ncli.McpError):
            ncli.cmd_session_stop(a)
        a.break_owner = "w1"                                                 # the parent, on purpose and by exact name
        ncli.cmd_session_stop(a)
        self.assertEqual(self.hits, ["/shutdown"])

    def test_owner_can_stop_its_own(self):
        ncli.cmd_session_stop(self.ns("session-stop", "w1"))
        self.assertEqual(self.hits, ["/shutdown"])

    def test_serve_needs_a_name_and_refuses_a_second_session(self):
        a = self.ns("serve", None, foreground=True)
        a.stdio = "editor.exe"
        with self.assertRaises(ncli.McpError) as cm:
            ncli.cmd_serve(a)
        self.assertIn("owned by 'w1'", str(cm.exception))
        os.remove(ncli.session_path(self.d))
        with self.assertRaises(ncli.McpError) as cm:
            ncli.cmd_serve(a)
        self.assertIn("needs a name", str(cm.exception))

    def test_save_current_through_a_session_or_stdio_is_refused(self):
        class Ed:
            transport = "session"
        a = self.argparse.Namespace(save="current", save_main_level=False)
        with self.assertRaises(ncli.McpError):
            ncli.refuse_main_level_save(Ed(), a)
        Ed.transport = "stdio"
        with self.assertRaises(ncli.McpError):
            ncli.refuse_main_level_save(Ed(), a)
        a.save_main_level = True
        ncli.refuse_main_level_save(Ed(), a)
        a.save_main_level, a.save = False, "Content/Levels/Scratch.nclevel"
        ncli.refuse_main_level_save(Ed(), a)
        Ed.transport, a.save = "http", "current"                             # the owner's own editor: his choice
        ncli.refuse_main_level_save(Ed(), a)


class RunLock(unittest.TestCase):
    """One lock path for an engine run: GPU + project, taken by the run command itself, per run."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.gpu = os.path.join(self.d, "gpu.lock")

    def tearDown(self):
        import nc_proc
        nc_proc.HELD[:] = []
        shutil.rmtree(self.d, ignore_errors=True)

    def ns(self, worker, wait=0):
        import argparse
        return argparse.Namespace(cmd="play-test", worker=worker, project=self.d, gpu_lock=self.gpu, wait_lock=wait, max_seconds=1800)

    def test_a_run_takes_both_locks_and_frees_them(self):
        with ncli.run_lock(self.ns("w1"), "play-test"):
            self.assertTrue(os.path.isdir(self.gpu))
            self.assertTrue(os.path.exists(ncli.lock_path(self.d)))
        self.assertFalse(os.path.exists(self.gpu))
        self.assertFalse(os.path.exists(ncli.lock_path(self.d)))

    def test_a_second_worker_is_refused_with_the_holder_named(self):
        with ncli.run_lock(self.ns("w1"), "bench level"):
            with self.assertRaises(ncli.McpError) as cm:
                with ncli.run_lock(self.ns("w2"), "play-test"):
                    pass
        self.assertIn("held by w1", str(cm.exception))
        self.assertIn("bench level", str(cm.exception))

    def test_a_wrapper_that_holds_the_locks_stays_in_charge(self):
        with ncli.run_lock(self.ns("w1"), "locked"):
            with ncli.run_lock(self.ns("w1"), "play-test"):
                pass
            self.assertTrue(os.path.isdir(self.gpu))                         # the inner run did not release the outer's lock
        self.assertFalse(os.path.isdir(self.gpu))

    def test_which_commands_run_the_engine(self):
        import argparse

        def yes(**kw):
            return ncli.needs_run_lock(argparse.Namespace(**kw))
        self.assertTrue(yes(cmd="play-test"))
        self.assertTrue(yes(cmd="bench"))
        self.assertTrue(yes(cmd="lint", play=True))
        self.assertFalse(yes(cmd="lint", play=False))
        self.assertFalse(yes(cmd="capture", write_only="dir"))
        self.assertTrue(yes(cmd="exe", what="package"))
        self.assertFalse(yes(cmd="exe", what="new-project"))
        self.assertFalse(yes(cmd="ping"))

    def test_lock_command_takes_and_releases_both(self):
        import argparse
        a = argparse.Namespace(action="acquire", owner="w1", wait=0, max_hold=60, holder_cmd=None, cmd="lock", project=self.d, gpu_lock=self.gpu,
                               no_gpu=False, force=False)
        ncli.cmd_lock(a)
        self.assertTrue(os.path.isdir(self.gpu) and os.path.exists(ncli.lock_path(self.d)))
        b = argparse.Namespace(**{**vars(a), "owner": "w2"})
        with self.assertRaises(SystemExit):
            ncli.cmd_lock(b)
        self.assertFalse(os.path.exists(os.path.join(self.gpu, "..", "nothing")))
        a.action = "release"
        ncli.cmd_lock(a)
        self.assertFalse(os.path.isdir(self.gpu) or os.path.exists(ncli.lock_path(self.d)))


class CliSmoke(unittest.TestCase):
    """Through the real argument parser: a dest that clashes with a sub-command name once broke `lock` (no unit test saw it)."""

    def run_cli(self, *args, timeout=60):
        import subprocess
        p = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(ncli.__file__)), "ncli.py")] + list(args),
                           capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout.strip().splitlines() or [""])[-1], p.stderr

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.gpu = os.path.join(self.d, "gpu.lock")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_lock_status_acquire_release(self):
        rc, out, _ = self.run_cli("--project", self.d, "--gpu-lock", self.gpu, "lock", "status")
        self.assertEqual(rc, 0)
        self.assertFalse(json.loads(out)["project"]["locked"])
        rc, out, _ = self.run_cli("--project", self.d, "--gpu-lock", self.gpu, "lock", "acquire", "--owner", "w1", "--cmd", "bench")
        self.assertEqual((rc, json.loads(out)["locks"]), (0, ["gpu", "project"]))
        rc, out, _ = self.run_cli("--project", self.d, "--gpu-lock", self.gpu, "lock", "acquire", "--owner", "w2", "--wait", "0")
        self.assertEqual(rc, 1)
        self.assertEqual(json.loads(out)["heldBy"], "w1")
        rc, out, _ = self.run_cli("--project", self.d, "--gpu-lock", self.gpu, "lock", "release", "--owner", "w1")
        self.assertEqual(rc, 0)

    def test_play_test_without_a_name_cannot_enter_a_named_session(self):
        # no session here, so it falls through to HTTP and fails to connect: the point is that it is the parser that works
        rc, out, _ = self.run_cli("--project", self.d, "--gpu-lock", self.gpu, "--wait-lock", "0", "--port", "1", "play-test", "--seconds", "1")
        self.assertEqual(rc, 2)
        self.assertIn("not reachable", json.loads(out)["error"])
        self.assertFalse(os.path.exists(self.gpu))                                # and the run lock was released on the way out

    def test_locked_runs_a_command_releases_and_reports_a_timeout(self):
        rc, out, _ = self.run_cli("--project", self.d, "--gpu-lock", self.gpu, "locked", "--owner", "w1", "--", sys.executable, "-c", "print('hi')")
        res = json.loads(out)
        self.assertEqual((rc, res["ok"], res["locks"], res["tail"]), (0, True, ["gpu", "project"], ["hi"]))
        self.assertFalse(os.path.exists(self.gpu))
        rc, out, _ = self.run_cli("--project", self.d, "--gpu-lock", self.gpu, "locked", "--owner", "w1", "--cmd-timeout", "2", "--",
                                  sys.executable, "-c", "import time;time.sleep(60)")
        res = json.loads(out)
        self.assertEqual((rc, res["timedOut"]), (124, True))
        self.assertFalse(os.path.exists(self.gpu))

    def test_watchdog_reports_and_exits_124(self):
        rc, out, _ = self.run_cli("--project", self.d, "--max-seconds", "1", "--port", "9", "--timeout", "30", "tools-check")
        # nothing listens on port 9: it fails by itself, long before any watchdog; the watchdog flag must at least parse
        self.assertIn(rc, (2, 124))


if __name__ == "__main__":
    unittest.main()
