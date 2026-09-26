// GDS EditMode tests — shared walls / floors between blueprints + SceneLint overlappingWalls / overlappingFloors.
// Run: Window > General > Test Runner > EditMode, or `unity test` / `unity command run_tests` (assembly GDS.Editor.Tests).
// Every test builds in a temporary scene (primitives mode: no ProBuilder / kit needed) and closes it afterwards.
using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace GDS.Tests
{
    public class SharedGeometryTests
    {
        Scene _scene, _prev;
        bool _additive;
        string _group;

        [SetUp]
        public void SetUp()
        {
            _prev = SceneManager.GetActiveScene();
            // additive keeps the user's scene loaded; an untitled scene can't coexist with a new one → single
            _additive = _prev.IsValid() && !string.IsNullOrEmpty(_prev.path);
            _scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, _additive ? NewSceneMode.Additive : NewSceneMode.Single);
            SceneManager.SetActiveScene(_scene);
            _group = "GDSTest_" + Guid.NewGuid().ToString("N").Substring(0, 8) + "/Rooms";
        }

        [TearDown]
        public void TearDown()
        {
            if (_additive)
            {
                if (_prev.IsValid()) SceneManager.SetActiveScene(_prev);
                EditorSceneManager.CloseScene(_scene, true);
            }
        }

        LevelBuilder.Blueprint Room(string name, float x, float z, int cx, int cz, params (string side, int index, string type)[] openings)
        {
            var bp = new LevelBuilder.Blueprint { name = name, group = _group, mode = "primitives", module = 4f, wallHeight = 3f, wallThickness = 0.2f, cellsX = cx, cellsZ = cz, floors = 1, roof = "flat", corners = false };
            bp.origin = new LevelBuilder.V3 { x = x, y = 0f, z = z };
            foreach (var o in openings) bp.openings.Add(new LevelBuilder.Opening { side = o.side, index = o.index, type = o.type });
            return bp;
        }

        static List<LevelBuilder.Seg> Resolve(LevelBuilder.Blueprint bp, params LevelBuilder.Blueprint[] neighbours)
            => LevelBuilder.ResolveSharedWalls(bp, LevelBuilder.WallSegments(bp, LevelBuilder.Volumes(bp)), neighbours.ToList(), new LevelBuilder.Result());

        /// <summary>Visible wall pieces (not wainscot) whose centre line is x = lineX (walls along Z), as "name@z" strings.</summary>
        static List<Renderer> WallPiecesOnLineX(float lineX)
        {
            var list = new List<Renderer>();
            foreach (var root in SceneManager.GetActiveScene().GetRootGameObjects())
                foreach (var r in root.GetComponentsInChildren<MeshRenderer>())
                {
                    var n = r.gameObject.name;
                    if (!n.StartsWith("wall_") || n.Contains("wainscot")) continue;
                    var b = r.bounds;
                    if (b.size.x > 0.5f || Mathf.Abs(b.center.x - lineX) > 0.15f) continue;
                    list.Add(r);
                }
            return list;
        }

        static string Snapshot(IEnumerable<Renderer> rs) =>
            string.Join("|", rs.Select(r => $"{r.bounds.center.x:F2},{r.bounds.center.y:F2},{r.bounds.center.z:F2}/{r.bounds.size.x:F2},{r.bounds.size.y:F2},{r.bounds.size.z:F2}").OrderBy(s => s, StringComparer.Ordinal));

        // A: x 0..8, door on its E wall cell 0 (z 0..4). B: x 8..16, door on its W wall cell 1 (z 4..8). Shared line x = 8.
        LevelBuilder.Blueprint A() => Room("T_RoomA", 0, 0, 2, 2, ("E", 0, "door"));
        LevelBuilder.Blueprint B() => Room("T_RoomB", 8, 0, 2, 2, ("W", 1, "door"));

        [Test]
        public void SharedWall_ResolvedOnce_WithBothDoors_OrderIndependent()
        {
            var a = A(); var b = B();
            var segA = Resolve(a, b); var segB = Resolve(b, a);
            // exactly one side builds the line (T_RoomA < T_RoomB by name, same height)
            var aE = segA.Where(s => s.side == "E" && !s.faceOnly).ToList();
            var bW = segB.Where(s => s.side == "W" && !s.faceOnly).ToList();
            Assert.AreEqual(2, aE.Count, "owner keeps both cells of the shared line");
            Assert.AreEqual(0, bW.Count, "the other side builds nothing on the shared line");
            // both doors end up in the owner's wall: its own on E0, the neighbour's on E1
            Assert.IsTrue(aE.Single(s => s.index == 0).holes.Any(h => h.type == "door"), "own door on E0");
            Assert.IsTrue(aE.Single(s => s.index == 1).holes.Any(h => h.type == "door"), "neighbour door merged into E1");
            // ownership is antisymmetric
            Assert.AreNotEqual(LevelBuilder.Owns(a, b), LevelBuilder.Owns(b, a));
        }

        [Test]
        public void SharedWall_Scene_OneWallBothDoors_SameResultInEitherBuildOrder()
        {
            var a = A(); var b = B();
            LevelBuilder.Build(a, new List<LevelBuilder.Blueprint> { b });
            LevelBuilder.Build(b, new List<LevelBuilder.Blueprint> { a });
            var first = WallPiecesOnLineX(8f);
            Assert.AreEqual(2, first.Count(r => r.gameObject.name.Contains("_lintel")), "one lintel per door on the shared line");
            Assert.AreEqual(0, first.Count(r => r.gameObject.name.StartsWith("wall_v0_W")), "RoomB built no wall on the shared line");
            var snapAB = Snapshot(first);

            // rebuild in the other order (in place, same names) → identical geometry
            LevelBuilder.Build(b, new List<LevelBuilder.Blueprint> { a });
            LevelBuilder.Build(a, new List<LevelBuilder.Blueprint> { b });
            Assert.AreEqual(snapAB, Snapshot(WallPiecesOnLineX(8f)), "build order / rebuild changes the shared wall");

            var rep = SceneLint.Run();
            Assert.AreEqual(0, rep.overlappingWalls, "lint: " + string.Join("; ", rep.list.Where(i => i.type == "overlappingWalls").Select(i => i.obj)));
            Assert.AreEqual(0, rep.overlappingFloors, "lint: " + string.Join("; ", rep.list.Where(i => i.type == "overlappingFloors").Select(i => i.obj)));
        }

        [Test]
        public void NoneOpening_FacingPlainWall_KeepsTheWall_FacingDoor_GivesTheDoor()
        {
            // corridor-style: B says "none" on both W cells, A has a door on E0 only → E0 door, E1 solid (not a 4 m gap)
            var a = A(); var b = Room("T_RoomB", 8, 0, 2, 2, ("W", 0, "none"), ("W", 1, "none"));
            var owner = LevelBuilder.Owns(a, b) ? Resolve(a, b).Where(s => s.side == "E" && !s.faceOnly) : Resolve(b, a).Where(s => s.side == "W" && !s.faceOnly);
            var cells = owner.OrderBy(s => s.center.z).ToList();
            Assert.AreEqual(2, cells.Count);
            Assert.IsTrue(cells[0].holes.Any(h => h.type == "door") && cells[0].holes.All(h => h.type != "none"), "z 0..4: the door wins over none");
            Assert.AreEqual(0, cells[1].holes.Count, "z 4..8: none facing a plain wall = plain wall");
        }

        [Test]
        public void Floors_DoNotOverlap_AndGroundSitsBelowFloors()
        {
            var ground = GameObject.CreatePrimitive(PrimitiveType.Cube);
            ground.name = "Ground"; ground.transform.position = new Vector3(0f, -0.1f, 0f); ground.transform.localScale = new Vector3(60f, 0.2f, 60f);
            // overlapping footprints: C covers x 4..12 over A's x 0..8 → one slab per spot
            var a = Room("T_RoomA", 0, 0, 2, 2); var c = Room("T_RoomC", 4, 0, 2, 2);
            var ra = LevelBuilder.Build(a, new List<LevelBuilder.Blueprint> { c });
            var rc = LevelBuilder.Build(c, new List<LevelBuilder.Blueprint> { a });
            Assert.Greater(ra.slabsClipped + rc.slabsClipped, 0, "one side clipped its slabs");

            var slabs = new List<Bounds>();
            foreach (var root in SceneManager.GetActiveScene().GetRootGameObjects())
                foreach (var r in root.GetComponentsInChildren<MeshRenderer>())
                    if (r.gameObject.name.StartsWith("slab_")) slabs.Add(r.bounds);
            for (int i = 0; i < slabs.Count; i++)
                for (int j = i + 1; j < slabs.Count; j++)
                {
                    float ox = Mathf.Min(slabs[i].max.x, slabs[j].max.x) - Mathf.Max(slabs[i].min.x, slabs[j].min.x);
                    float oz = Mathf.Min(slabs[i].max.z, slabs[j].max.z) - Mathf.Max(slabs[i].min.z, slabs[j].min.z);
                    Assert.IsFalse(ox > 0.3f && oz > 0.3f, $"slabs overlap: {slabs[i]} / {slabs[j]}");
                }
            // floor tops stay at FFL 0, the ground was lowered under them
            Assert.AreEqual(0f, slabs.Max(s => s.max.y), 0.001f);
            Assert.Less(ground.GetComponent<Renderer>().bounds.max.y, -0.01f, "ground top must be below the floors");

            var rep = SceneLint.Run();
            Assert.AreEqual(0, rep.overlappingFloors, "lint: " + string.Join("; ", rep.list.Where(i => i.type == "overlappingFloors").Select(i => i.obj)));
        }

        [Test]
        public void Lint_Flags_DuplicatedWall_And_DuplicatedFloor()
        {
            GameObject Cube(string n, Vector3 p, Vector3 s) { var g = GameObject.CreatePrimitive(PrimitiveType.Cube); g.name = n; g.transform.position = p; g.transform.localScale = s; return g; }
            Cube("wall_dup_a", new Vector3(0f, 1.5f, 10f), new Vector3(4f, 3f, 0.2f));
            Cube("wall_dup_b", new Vector3(0.1f, 1.5f, 10.05f), new Vector3(4f, 3f, 0.2f));
            Cube("slab_dup_a", new Vector3(0f, -0.1f, 20f), new Vector3(4f, 0.2f, 4f));
            Cube("slab_dup_b", new Vector3(0.5f, -0.1f, 20f), new Vector3(4f, 0.2f, 4f));
            // not duplicates: corner contact, rug on a floor
            Cube("wall_corner", new Vector3(2.1f, 1.5f, 12f), new Vector3(0.2f, 3f, 4f));
            Cube("floor_rug", new Vector3(0f, 0.01f, 20f), new Vector3(2f, 0.02f, 2f));

            var rep = SceneLint.Run();
            Assert.AreEqual(1, rep.overlappingWalls, "lint walls: " + string.Join("; ", rep.list.Where(i => i.type == "overlappingWalls").Select(i => i.obj)));
            Assert.AreEqual(1, rep.overlappingFloors, "lint floors: " + string.Join("; ", rep.list.Where(i => i.type == "overlappingFloors").Select(i => i.obj)));
            Assert.GreaterOrEqual(rep.issues, 2);
        }

        [Test]
        public void Lint_Flags_LegacyBuild_WithSharingOff()
        {
            var a = A(); var b = B(); a.wallOwner = "off"; b.wallOwner = "off";
            LevelBuilder.Build(a, new List<LevelBuilder.Blueprint> { b });
            LevelBuilder.Build(b, new List<LevelBuilder.Blueprint> { a });
            Assert.Greater(SceneLint.Run().overlappingWalls, 0, "two walls on x = 8 must be reported");
        }
    }
}
