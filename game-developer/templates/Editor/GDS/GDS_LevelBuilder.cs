// GDS LevelBuilder v2 — JSON blueprint → assembled building / props / scatter in ONE call.
// Composite footprints (L / T / U via `volumes`), interior partitions with doors, wall attachments (lanterns, signs,
// awnings, flower boxes), fences along polylines, stairs, floor holes, per-volume roofs. Pivot-agnostic: every piece is
// aligned by its measured bounds, so Kenney / KayKit / Quaternius / Synty all snap. Missing roles are reported, never faked.
// Party walls: blueprints in the same folder + group that share a wall line build it ONCE (deterministic owner, openings of
// both sides cut into it) — see "Shared walls" in references/level-builder.md.
// Usage (execute_code):
//   return GDS.LevelBuilder.BuildFromFile("art/blueprints/house_a.json");
// Schema: references/level-builder.md
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace GDS
{
    public static class LevelBuilder
    {
        [Serializable] public class V3 { public float x, y, z; public Vector3 V => new Vector3(x, y, z); }
        [Serializable] public class RoleFile { public string role; public string file; }
        [Serializable] public class Opening { public string side = "S"; public int index; public int floor; public int volume; public string type = "door"; }
        [Serializable] public class Volume { public float x, z; public int cellsX = 2, cellsZ = 2, floors = 1; public string roof = ""; }
        [Serializable] public class Partition { public int volume; public int floor; public float x0, z0, x1, z1; public float door = -1f; }
        [Serializable] public class Attach { public string file; public int volume; public string side = "S"; public int index; public int floor; public float y = 1.8f; public float outward = 0.15f; public float along; public float rotY; public string collider = "none"; }
        [Serializable] public class Fence { public string file; public List<V3> points = new List<V3>(); public float pieceLength; public string postFile; public string collider = "box"; }
        [Serializable] public class Stair { public string file; public float x, z, rotY; public int floor; }
        [Serializable] public class FloorHole { public int volume; public int cellX, cellZ, floor; }
        [Serializable] public class Prop
        {
            public string file; public string name; public float x, y, z, rotY; public float scale = 1f;
            public bool snap = true; public string collider = "box"; // box | convex | mesh | none
        }
        [Serializable] public class Block { public string name = "platform"; public float x, y, z; public float sx = 1f, sy = 0.3f, sz = 1f; public string material;
            public string shape = "box";      // box | sphere | cylinder (sphere/cylinder = Unity primitive, e.g. half-buried ellipsoid hills)
            public string collider = "";     // "" = primitive default | mesh (exact MeshCollider) | none
        }
        [Serializable] public class Marker { public string name; public float x, y, z, rotY; public string parent = "Markers"; }
        [Serializable] public class Scatter
        {
            public string file; public int count = 10; public float minX = -20, maxX = 20, minZ = -20, maxZ = 20;
            public float minDist = 2f; public int seed = 1; public bool randomRotY = true; public float scaleMin = 1f, scaleMax = 1f;
            public float avoidRadius = 0f; public List<V3> avoidPoints = new List<V3>(); public float avoidPointRadius = 4f;
            public string collider = "box";
            public string prefix = "";   // instance name prefix, e.g. "deco_" = walk-through dressing (lint: no collider needed)
        }
        [Serializable] public class Blueprint
        {
            public string name = "Building"; public string group = "Level/Buildings";
            public V3 origin = new V3(); public float rotY;
            public string mode = "kit";                 // kit | probuilder | primitives | props (no shell)
            public string kitRoot = Common.KitsRoot;
            public float module = 4f; public float wallHeight = 3f; public float wallThickness = 0.2f;
            public List<RoleFile> roles = new List<RoleFile>();
            public int cellsX = 2, cellsZ = 2, floors = 1;          // single-volume shorthand
            public List<Volume> volumes = new List<Volume>();       // composite footprint (overrides cellsX/Z/floors)
            public List<Opening> openings = new List<Opening>();
            public List<Partition> partitions = new List<Partition>();
            public List<Attach> attach = new List<Attach>();
            public List<Fence> fences = new List<Fence>();
            public List<Stair> stairs = new List<Stair>();
            public List<FloorHole> floorHoles = new List<FloorHole>();
            public string roof = "kit";                 // default for volumes: kit | flat | none | gable
            public bool corners = true;
            public string material;                     // probuilder/primitives shell material (walls)
            public string floorMaterial, roofMaterial, wainscotMaterial;   // optional per-part shell materials (slab_ / roof_ / wainscot)
            public float wainscotHeight = 0f;           // > 0: interior wainscot panels on every wall piece touching the floor
            public float windowWidth = 1.2f, windowHeight = 1.2f, windowSill = 1.0f;
            public List<Block> blocks = new List<Block>();   // free shell boxes (platforms, daises, counters) — local metres, x/z = centre, y = bottom
            public List<Marker> markers = new List<Marker>(); // named empties (sockets, slots, spawns) — local metres
            public string prefabOut;
            public List<Prop> props = new List<Prop>();
            public List<Scatter> scatter = new List<Scatter>();
            // ---- shared (party) walls between blueprints ----
            public string wallOwner = "auto";            // auto | self (claim shared lines + slabs) | neighbour (yield them) | off (legacy: no sharing, builds every wall/slab)
            public List<string> omit = new List<string>();        // never built: wall runs "N", "v1:E", "v0:W2" ([v<volume>:]<side>[<index>]); "floor" (no floor slabs); "roof" (no roof/ceiling)
            public List<string> neighbours = new List<string>();  // optional explicit neighbour files; default = every blueprint in the same folder with the same group
            public float groundGap = 0.02f;              // a foreign ground coplanar with this blueprint's floors is lowered by this much (0 = off)
        }
        [Serializable] public class Result
        {
            public string name; public string status = "PASS"; public int pieces; public int props; public int scattered; public int attached; public int fencePieces;
            public float boundsX, boundsY, boundsZ; public List<string> missingRoles = new List<string>(); public List<string> warnings = new List<string>();
            public int sharedOwned, sharedSkipped, omitted;          // wall cells built for a neighbour too / left to the neighbour / omitted by "omit"
            public int slabsClipped, groundLowered;                  // floor/roof slabs clipped or dropped under a neighbour's slab / foreign grounds moved below the floors
            public List<string> sharedWith = new List<string>();     // neighbour blueprint names that share at least one wall line or slab
        }

        /// <summary>Opening resolved on a wall segment: <c>at</c> = centre offset from the segment centre along its axis (metres).</summary>
        public class Hole { public string type = "door"; public float at, width = 1f, height = 2.2f, sill; public string from; }

        /// <summary>Wall segment of the composite footprint (world-space centre at floor level).</summary>
        public class Seg
        {
            public int volume; public string side; public int index; public int floor; public Vector3 center; public bool alongX; public Vector3 normal; public Opening opening; public float length;
            public float height, thickness;              // 0 = blueprint wallHeight / wallThickness (a shared wall takes the taller side's height)
            public bool extNeg = true, extPos = true;    // extend T/2 past each end (closes corners); false where a shared wall was cut
            public bool faceOnly;                        // wall line owned by a neighbour: only this side's wainscot is built
            public List<Hole> holes;                     // null = legacy single `opening`; set when openings were merged from a neighbour
            public string tag = "";                      // name suffix for split pieces
            public Seg Clone() { var s = (Seg)MemberwiseClone(); s.holes = holes?.Select(h => new Hole { type = h.type, at = h.at, width = h.width, height = h.height, sill = h.sill, from = h.from }).ToList(); return s; }
        }

        /// <summary>Registered by GDS.Editor.ProBuilder when com.unity.probuilder is installed.</summary>
        public static Func<Blueprint, List<Volume>, List<Seg>, Transform, Result, int> ProBuilderShell;
        public static Func<string, Vector3, Vector3, Transform, Material, GameObject> ProBuilderBox;

        /// <summary>Build one blueprint file. Shared walls / slabs are resolved against the other blueprints of the same folder + group
        /// (read from their JSON, never from the scene: other blueprints' objects are never touched).</summary>
        public static string BuildFromFile(string projectRelJson)
        {
            var json = Common.ReadProjectFile(projectRelJson);
            if (json == null) return "{\"status\":\"FAIL\",\"error\":\"blueprint not found: " + Common.Esc(projectRelJson) + "\"}";
            var dir = Path.GetDirectoryName(projectRelJson.Replace('\\', '/'))?.Replace('\\', '/');
            return BuildFromJson(json, string.IsNullOrEmpty(dir) ? "." : dir);
        }

        public static string BuildFromJson(string json, string blueprintDir = "art/blueprints")
        {
            Blueprint bp;
            try { bp = JsonUtility.FromJson<Blueprint>(json); }
            catch (Exception e) { return "{\"status\":\"FAIL\",\"error\":\"bad json: " + Common.Esc(e.Message) + "\"}"; }
            var res = Build(bp, LoadNeighbours(blueprintDir, bp));
            var outJson = JsonUtility.ToJson(res, true);
            Common.WriteProjectFile($"docs/lint/build-{Sanitize(bp.name)}.json", outJson);
            return outJson;
        }

        public static List<Volume> Volumes(Blueprint bp)
        {
            if (bp.volumes != null && bp.volumes.Count > 0) return bp.volumes;
            return new List<Volume> { new Volume { x = 0, z = 0, cellsX = bp.cellsX, cellsZ = bp.cellsZ, floors = bp.floors, roof = bp.roof } };
        }

        /// <summary>Build without neighbour lookup (Village lots, GDS.PB.Room): `omit` still applies, no shared-wall resolution.</summary>
        public static Result Build(Blueprint bp) => Build(bp, null);

        public static Result Build(Blueprint bp, List<Blueprint> neighbours)
        {
            var res = new Result { name = bp.name };
            Undo.IncrementCurrentGroup();
            var group = Common.GetOrCreateGroup(bp.group);
            var existing = group.Find(bp.name);
            if (existing != null) { Undo.DestroyObjectImmediate(existing.gameObject); res.warnings.Add("replaced existing " + bp.name); }
            var rootGo = new GameObject(bp.name);
            Undo.RegisterCreatedObjectUndo(rootGo, "GDS Build");
            rootGo.transform.SetParent(group, false);
            rootGo.transform.position = bp.origin.V;
            var shell = new GameObject("Shell").transform; shell.SetParent(rootGo.transform, false);
            var vols = Volumes(bp);
            var segs = ResolveSharedWalls(bp, WallSegments(bp, vols), neighbours, res);

            string mode = (bp.mode ?? "kit").ToLowerInvariant();
            if (mode != "props" && vols.Any(v => v.cellsX > 0 && v.cellsZ > 0 && v.floors > 0))
            {
                // slab clipping context: read by ShellBoxes / BuildKitShell (the ProBuilder hook signature stays unchanged)
                s_cutBp = bp; s_cuts = SlabCuts(bp, neighbours, res); s_cutRes = res;
                try
                {
                    switch (mode)
                    {
                        case "kit": res.pieces += BuildKitShell(bp, vols, segs, shell, res); break;
                        case "probuilder":
                            if (ProBuilderShell != null) res.pieces += ProBuilderShell(bp, vols, segs, shell, res);
                            else { res.warnings.Add("ProBuilder not installed → primitives shell (greybox only)"); res.pieces += BuildPrimitiveShell(bp, vols, segs, shell, res); }
                            break;
                        default: res.pieces += BuildPrimitiveShell(bp, vols, segs, shell, res); break;
                    }
                }
                finally { s_cutBp = null; s_cuts = null; s_cutRes = null; }
            }

            foreach (var bl in bp.blocks)
            {
                var bm = string.IsNullOrEmpty(bl.material) ? null : AssetDatabase.LoadAssetAtPath<Material>(bl.material);
                if (!string.IsNullOrEmpty(bl.material) && bm == null) res.warnings.Add("block material not found: " + bl.material);
                var center = bp.origin.V + new Vector3(bl.x, bl.y + bl.sy / 2f, bl.z); var size = new Vector3(bl.sx, bl.sy, bl.sz);
                GameObject g;
                string shp = (bl.shape ?? "box").ToLowerInvariant();
                if (mode == "probuilder" && ProBuilderBox != null && shp == "box") g = ProBuilderBox(bl.name, center, size, shell, bm);
                else
                {
                    g = GameObject.CreatePrimitive(shp == "sphere" ? PrimitiveType.Sphere : shp == "cylinder" ? PrimitiveType.Cylinder : PrimitiveType.Cube); g.name = bl.name; g.transform.SetParent(shell, false);
                    g.transform.position = center; g.transform.localScale = size;
                    if (bm != null) g.GetComponent<MeshRenderer>().sharedMaterial = bm;
                    if (shp == "cylinder") g.transform.localScale = new Vector3(size.x, size.y / 2f, size.z);   // Unity cylinder is 2 units tall
                    var cm = (bl.collider ?? "").ToLowerInvariant();
                    if (cm == "mesh" || cm == "none") { var pc = g.GetComponent<Collider>(); if (pc != null) UnityEngine.Object.DestroyImmediate(pc); }
                    if (cm == "mesh") g.AddComponent<MeshCollider>().sharedMesh = g.GetComponent<MeshFilter>().sharedMesh;
                    Undo.RegisterCreatedObjectUndo(g, "GDS Block");
                }
                res.pieces++;
            }
            if (bp.markers.Count > 0)
            {
                foreach (var mk in bp.markers)
                {
                    string pn = string.IsNullOrEmpty(mk.parent) ? "Markers" : mk.parent;
                    var pt = rootGo.transform.Find(pn);
                    if (pt == null) { pt = new GameObject(pn).transform; pt.SetParent(rootGo.transform, false); }
                    var e = new GameObject(string.IsNullOrEmpty(mk.name) ? "Marker" : mk.name);
                    Undo.RegisterCreatedObjectUndo(e, "GDS Marker");
                    e.transform.SetParent(pt, false);
                    e.transform.position = bp.origin.V + new Vector3(mk.x, mk.y, mk.z);
                    e.transform.rotation = Quaternion.Euler(0, mk.rotY, 0);
                }
            }

            // floors sit on the ground, never coplanar with it (z-fighting): measured with the final rotation, before props snap
            rootGo.transform.rotation = Quaternion.Euler(0, bp.rotY, 0);
            SeparateGround(rootGo, bp, res);
            rootGo.transform.rotation = Quaternion.identity;

            var propsT = new GameObject("Props").transform; propsT.SetParent(rootGo.transform, false);
            foreach (var a in bp.attach) if (PlaceAttach(bp, vols, a, propsT, res)) res.attached++;
            foreach (var f in bp.fences) res.fencePieces += BuildFence(bp, f, propsT, res);
            foreach (var p in bp.props) if (PlaceProp(bp, p, propsT, res)) res.props++;
            foreach (var s in bp.scatter) res.scattered += DoScatter(bp, s, propsT, res);

            rootGo.transform.rotation = Quaternion.Euler(0, bp.rotY, 0);
            foreach (var sr in rootGo.GetComponentsInChildren<Renderer>(true)) if (!sr.transform.IsChildOf(propsT)) GameObjectUtility.SetStaticEditorFlags(sr.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.ContributeGI);

            if (Common.TryGetBounds(rootGo, out var b)) { res.boundsX = b.size.x; res.boundsY = b.size.y; res.boundsZ = b.size.z; }
            if (!string.IsNullOrEmpty(bp.prefabOut))
            {
                Common.EnsureFolder(System.IO.Path.GetDirectoryName(bp.prefabOut).Replace('\\', '/'));
                PrefabUtility.SaveAsPrefabAssetAndConnect(rootGo, bp.prefabOut, InteractionMode.AutomatedAction);
            }
            if (res.missingRoles.Count > 0 && res.pieces == 0 && mode != "props") res.status = "FAIL";
            EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
            Debug.Log($"[GDS LevelBuilder] {bp.name}: {res.pieces} shell, {res.props} props, {res.attached} attached, {res.fencePieces} fence, {res.scattered} scattered; missing: {string.Join(",", res.missingRoles)}");
            return res;
        }

        // ---------------- geometry: wall segments of a composite footprint ----------------
        static bool InsideOther(List<Volume> vols, int self, float M, Vector3 local, int floor)
        {
            for (int i = 0; i < vols.Count; i++)
            {
                if (i == self) continue; var v = vols[i];
                if (floor >= v.floors) continue;
                float x0 = v.x, z0 = v.z, x1 = v.x + v.cellsX * M, z1 = v.z + v.cellsZ * M;
                if (local.x > x0 + 0.01f && local.x < x1 - 0.01f && local.z > z0 + 0.01f && local.z < z1 - 0.01f) return true;
            }
            return false;
        }

        static bool OnSharedBoundary(List<Volume> vols, int self, float M, Vector3 local, int floor)
        {
            for (int i = 0; i < vols.Count; i++)
            {
                if (i == self) continue; var v = vols[i];
                if (floor >= v.floors) continue;
                float x0 = v.x, z0 = v.z, x1 = v.x + v.cellsX * M, z1 = v.z + v.cellsZ * M;
                bool onX = (Mathf.Abs(local.x - x0) < 0.01f || Mathf.Abs(local.x - x1) < 0.01f) && local.z > z0 + 0.01f && local.z < z1 - 0.01f;
                bool onZ = (Mathf.Abs(local.z - z0) < 0.01f || Mathf.Abs(local.z - z1) < 0.01f) && local.x > x0 + 0.01f && local.x < x1 - 0.01f;
                if (onX || onZ) return true;
            }
            return false;
        }

        public static List<Seg> WallSegments(Blueprint bp, List<Volume> vols)
        {
            var list = new List<Seg>(); float M = bp.module; var o = bp.origin.V;
            for (int vi = 0; vi < vols.Count; vi++)
            {
                var v = vols[vi]; float W = v.cellsX * M, D = v.cellsZ * M;
                for (int f = 0; f < v.floors; f++)
                {
                    float y = f * bp.wallHeight;
                    void Run(string side, int n, Func<int, Vector3> local, bool alongX, Vector3 normal)
                    {
                        for (int i = 0; i < n; i++)
                        {
                            var l = local(i);
                            if (InsideOther(vols, vi, M, l, f)) continue;           // segment buried inside another wing
                            if (OnSharedBoundary(vols, vi, M, l, f)) continue;      // open between wings; partitions add walls with doors
                            var op = bp.openings.FirstOrDefault(x => x.volume == vi && x.floor == f && string.Equals(x.side, side, StringComparison.OrdinalIgnoreCase) && x.index == i);
                            list.Add(new Seg { volume = vi, side = side, index = i, floor = f, center = o + l, alongX = alongX, normal = normal, opening = op, length = M });
                        }
                    }
                    Run("S", v.cellsX, i => new Vector3(v.x + (i + 0.5f) * M, y, v.z), true, Vector3.back);
                    Run("N", v.cellsX, i => new Vector3(v.x + (i + 0.5f) * M, y, v.z + D), true, Vector3.forward);
                    Run("W", v.cellsZ, j => new Vector3(v.x, y, v.z + (j + 0.5f) * M), false, Vector3.left);
                    Run("E", v.cellsZ, j => new Vector3(v.x + W, y, v.z + (j + 0.5f) * M), false, Vector3.right);
                }
            }
            return list;
        }

        // ---------------- shared (party) walls between blueprints ----------------
        // One wall per line. Two blueprints whose wall runs are collinear (same axis, centre-lines closer than their mean
        // thickness, same storey, overlap longer than a wall thickness) share that portion: the OWNER builds it once, with the
        // openings of BOTH sides cut into it and the taller of the two heights; the other side skips it (splitting its run where
        // the overlap is partial) and only keeps its own wainscot on its face. Owner of a shared portion:
        //   1. a side listed in `omit` never builds it → the other side owns it;
        //   2. `wallOwner`: self > auto > neighbour;
        //   3. taller `wallHeight` (so the tall room's wall is never cut short);
        //   4. blueprint `name`, ordinal, first wins.
        // The decision reads only the JSON of both blueprints (never the scene) → build order and rebuilds never change the result.
        // Openings on a shared portion: every door / window of both sides is cut (overlaps: door > window). `none` means
        // "no wall from me here": it only leaves a gap where the other side is `none` too (or omits the wall) — a `none` facing
        // a plain wall of the neighbour gives a plain wall, a `none` facing a door gives that door.

        static bool IsOff(Blueprint bp) => string.Equals((bp.wallOwner ?? "").Trim(), "off", StringComparison.OrdinalIgnoreCase);
        static int OwnerRank(Blueprint bp)
        {
            var o = (bp.wallOwner ?? "auto").Trim().ToLowerInvariant();
            return o == "self" ? 2 : (o == "neighbour" || o == "neighbor" || o == "other") ? 0 : 1;
        }

        /// <summary>True when blueprint a builds the wall line / slab it shares with b. Antisymmetric for different names: Owns(a,b) == !Owns(b,a).</summary>
        public static bool Owns(Blueprint a, Blueprint b)
        {
            int ra = OwnerRank(a), rb = OwnerRank(b);
            if (ra != rb) return ra > rb;
            if (Mathf.Abs(a.wallHeight - b.wallHeight) > 0.01f) return a.wallHeight > b.wallHeight;
            return string.CompareOrdinal(a.name ?? "", b.name ?? "") < 0;
        }

        /// <summary>`omit` tokens: "N" (whole side, every volume), "v1:E" (side of volume 1), "v0:W2" / "W2" (one cell). "floor" / "roof" are handled by OmitsPart.</summary>
        public static bool IsOmitted(Blueprint bp, Seg s)
        {
            if (bp.omit == null || s.side == "P") return false;
            foreach (var raw in bp.omit)
            {
                if (string.IsNullOrWhiteSpace(raw)) continue;
                var t = raw.Trim().ToUpperInvariant(); int vol = -1, idx = -1;
                int k = t.IndexOf(':');
                if (k > 0) { if (!t.StartsWith("V") || !int.TryParse(t.Substring(1, k - 1), out vol)) continue; t = t.Substring(k + 1); }
                if (t.Length == 0) continue;
                if (t.Length > 1 && !int.TryParse(t.Substring(1), out idx)) continue;
                if (vol >= 0 && vol != s.volume) continue;
                if (!string.Equals(t.Substring(0, 1), s.side, StringComparison.OrdinalIgnoreCase)) continue;
                if (idx >= 0 && idx != s.index) continue;
                return true;
            }
            return false;
        }

        /// <summary>`omit` contains "floor" (no floor slabs / tiles) or "roof" (no roof / ceiling).</summary>
        public static bool OmitsPart(Blueprint bp, string part) =>
            bp.omit != null && bp.omit.Any(t => t != null && string.Equals(t.Trim(), part, StringComparison.OrdinalIgnoreCase));

        static int Prio(Hole h) => h.type == "door" ? 3 : h.type == "window" ? 2 : 1;
        static Hole CopyHole(Hole h) => new Hole { type = h.type, at = h.at, width = h.width, height = h.height, sill = h.sill, from = h.from };

        static List<Hole> OwnHoles(Blueprint bp, Seg s)
        {
            if (s.holes != null) return s.Clone().holes;
            var list = new List<Hole>(); var op = s.opening; if (op == null) return list;
            string type = string.IsNullOrEmpty(op.type) ? "door" : op.type.ToLowerInvariant();
            if (type == "none") list.Add(new Hole { type = "none", at = 0f, width = s.length, height = 0f, from = bp.name });
            else if (type == "window") list.Add(new Hole { type = "window", width = bp.windowWidth > 0.1f ? bp.windowWidth : 1.2f, height = bp.windowHeight > 0.1f ? bp.windowHeight : 1.2f, sill = bp.windowSill >= 0f ? bp.windowSill : 1f, from = bp.name });
            else list.Add(new Hole { type = "door", width = 1f, height = 2.2f, from = bp.name });
            return list;
        }

        /// <summary>Holes inside [lo,hi] (door/window by centre, none by intersection), clipped, overlaps resolved door &gt; window &gt; none, shifted by -shift.</summary>
        static List<Hole> MergeHoles(IEnumerable<Hole> hs, float lo, float hi, float shift = 0f)
        {
            var acc = new List<Hole>();
            foreach (var h in hs.OrderByDescending(Prio).ThenBy(h => h.at).ThenBy(h => h.from ?? "", StringComparer.Ordinal))
            {
                if (h.type != "none" && (h.at < lo - 0.001f || h.at > hi + 0.001f)) continue;
                float h0 = Mathf.Max(h.at - h.width / 2f, lo), h1 = Mathf.Min(h.at + h.width / 2f, hi);
                if (h1 - h0 < 0.05f) continue;
                if (acc.Any(a => h0 < a.at + a.width / 2f + 0.05f && h1 > a.at - a.width / 2f - 0.05f)) continue;
                acc.Add(new Hole { type = h.type, at = (h0 + h1) / 2f, width = h1 - h0, height = h.height, sill = h.sill, from = h.from });
            }
            foreach (var h in acc) h.at -= shift;
            return acc.OrderBy(h => h.at).ToList();
        }

        static bool InSpan(float x, float lo, float hi) => x >= lo - 0.001f && x <= hi + 0.001f;

        static List<(float lo, float hi)> NoneSpans(IEnumerable<Hole> hs, float lo, float hi)
        {
            var list = new List<(float lo, float hi)>();
            foreach (var h in hs)
            {
                if (h.type != "none") continue;
                float a = Mathf.Max(h.at - h.width / 2f, lo), b = Mathf.Min(h.at + h.width / 2f, hi);
                if (b - a > 0.05f) list.Add((a, b));
            }
            return list;
        }

        /// <summary>Openings of a shared portion [lo,hi] (both lists in the same offsets): doors/windows of both sides; `none` only where both sides are none (or the other side omits the wall).</summary>
        static List<Hole> SharedHoles(List<Hole> mine, List<Hole> theirs, float lo, float hi, bool theirsOmitted)
        {
            var list = new List<Hole>();
            foreach (var h in mine.Concat(theirs)) if (h.type != "none" && InSpan(h.at, lo, hi)) list.Add(CopyHole(h));
            var myNone = NoneSpans(mine, lo, hi);
            var theirNone = theirsOmitted ? new List<(float lo, float hi)> { (lo, hi) } : NoneSpans(theirs, lo, hi);
            foreach (var a in myNone)
                foreach (var b in theirNone)
                {
                    float h0 = Mathf.Max(a.lo, b.lo), h1 = Mathf.Min(a.hi, b.hi);
                    if (h1 - h0 > 0.05f) list.Add(new Hole { type = "none", at = (h0 + h1) / 2f, width = h1 - h0, from = "shared" });
                }
            return list;
        }

        /// <summary>This side's openings outside every shared portion (door/window by centre; none clipped).</summary>
        static List<Hole> OutsideHoles(List<Hole> mine, List<(float lo, float hi)> spans)
        {
            var list = new List<Hole>();
            foreach (var h in mine)
            {
                if (h.type != "none") { if (!spans.Any(p => InSpan(h.at, p.lo, p.hi))) list.Add(CopyHole(h)); continue; }
                var parts = new List<(float a, float b)> { (h.at - h.width / 2f, h.at + h.width / 2f) };
                foreach (var p in spans)
                {
                    var next = new List<(float a, float b)>();
                    foreach (var q in parts)
                    {
                        if (p.hi <= q.a || p.lo >= q.b) { next.Add(q); continue; }
                        if (p.lo > q.a) next.Add((q.a, p.lo));
                        if (p.hi < q.b) next.Add((p.hi, q.b));
                    }
                    parts = next;
                }
                foreach (var q in parts) if (q.b - q.a > 0.05f) list.Add(new Hole { type = "none", at = (q.a + q.b) / 2f, width = q.b - q.a, from = h.from });
            }
            return list;
        }

        class WLine { public Blueprint bp; public Seg seg; public bool worldX, omitted; public float perp, cAlong, sign, a, b, y0, y1, T; public List<Hole> holes; }
        class Portion { public float lo, hi; public bool own; public WLine n; public List<Hole> nh; }

        static bool Frame(Blueprint bp, out Quaternion rot)
        {
            float r = Mathf.Round(bp.rotY / 90f) * 90f; rot = Quaternion.Euler(0, r, 0);
            return Mathf.Abs(Mathf.DeltaAngle(bp.rotY, r)) < 0.5f;
        }

        /// <summary>A wall run in world XZ (the builder rotates the finished root by rotY around origin).</summary>
        static WLine Line(Blueprint bp, Quaternion rot, Seg s)
        {
            var o = bp.origin.V; var c = o + rot * (s.center - o); var ax = rot * (s.alongX ? Vector3.right : Vector3.forward);
            bool wx = Mathf.Abs(ax.x) > 0.5f; float ca = wx ? c.x : c.z;
            return new WLine
            {
                bp = bp, seg = s, worldX = wx, omitted = IsOmitted(bp, s), perp = wx ? c.z : c.x, cAlong = ca, sign = wx ? Mathf.Sign(ax.x) : Mathf.Sign(ax.z),
                a = ca - s.length / 2f, b = ca + s.length / 2f, y0 = c.y, y1 = c.y + (s.height > 0.01f ? s.height : bp.wallHeight),
                T = s.thickness > 0.001f ? s.thickness : bp.wallThickness, holes = OwnHoles(bp, s)
            };
        }

        /// <summary>nb takes part in wall / slab sharing with bp (different name, not "off", not a props-only blueprint, has a shell).</summary>
        static bool Shares(Blueprint bp, Blueprint nb) =>
            nb != null && nb.name != bp.name && !IsOff(nb) && !string.Equals(nb.mode, "props", StringComparison.OrdinalIgnoreCase)
            && Volumes(nb).Any(v => v.cellsX > 0 && v.cellsZ > 0 && v.floors > 0);

        /// <summary>Apply `omit`, then resolve wall runs shared with neighbour blueprints (see the rules above). neighbours null/empty → segs unchanged except `omit`.</summary>
        public static List<Seg> ResolveSharedWalls(Blueprint bp, List<Seg> segs, List<Blueprint> neighbours, Result res)
        {
            var outList = new List<Seg>();
            bool kit = string.IsNullOrEmpty(bp.mode) || string.Equals(bp.mode, "kit", StringComparison.OrdinalIgnoreCase);
            bool share = neighbours != null && neighbours.Count > 0 && !IsOff(bp);
            var rot = Quaternion.identity;
            if (share && !Frame(bp, out rot)) { res?.warnings.Add($"rotY {bp.rotY} is not a multiple of 90: shared walls not resolved (SceneLint overlappingWalls will report duplicates)"); share = false; }
            var others = new List<WLine>();
            if (share)
                foreach (var nb in neighbours)
                {
                    if (!Shares(bp, nb)) continue;
                    if (!Frame(nb, out var nrot)) { res?.warnings.Add($"neighbour {nb.name}: rotY not a multiple of 90 → ignored for shared walls"); continue; }
                    foreach (var ns in WallSegments(nb, Volumes(nb))) others.Add(Line(nb, nrot, ns));
                }
            var deferredTo = new HashSet<string>();
            foreach (var s in segs)
            {
                if (IsOmitted(bp, s)) { if (res != null) res.omitted++; continue; }
                if (others.Count == 0) { outList.Add(s); continue; }
                var L = Line(bp, rot, s); float half = s.length / 2f, ownH = L.y1 - L.y0, height = 0f;
                var portions = new List<Portion>();
                foreach (var n in others)
                {
                    if (n.worldX != L.worldX) continue;
                    if (Mathf.Abs(n.perp - L.perp) > (n.T + L.T) / 2f + 0.01f) continue;             // not on the same line
                    float vy = Mathf.Min(L.y1, n.y1) - Mathf.Max(L.y0, n.y0);
                    if (vy < 0.5f * Mathf.Min(L.y1 - L.y0, n.y1 - n.y0)) continue;                   // other storey
                    float lo = Mathf.Max(L.a, n.a), hi = Mathf.Min(L.b, n.b);
                    if (hi - lo <= Mathf.Max(L.T, n.T) + 0.01f) continue;                            // corner contact (≤ thickness) is fine
                    float o1 = (lo - L.cAlong) * L.sign, o2 = (hi - L.cAlong) * L.sign, ol = Mathf.Min(o1, o2), oh = Mathf.Max(o1, o2);
                    var nh = new List<Hole>();   // neighbour openings in this segment's offsets, inside the shared portion
                    foreach (var h in n.holes)
                    {
                        float at = (n.cAlong + n.sign * h.at - L.cAlong) * L.sign;
                        if (h.type == "none")
                        {
                            float h0 = Mathf.Max(at - h.width / 2f, ol), h1 = Mathf.Min(at + h.width / 2f, oh);
                            if (h1 - h0 > 0.05f) nh.Add(new Hole { type = "none", at = (h0 + h1) / 2f, width = h1 - h0, from = h.from });
                        }
                        else if (InSpan(at, ol, oh)) nh.Add(new Hole { type = h.type, at = at, width = h.width, height = h.height, sill = h.sill, from = h.from });
                    }
                    if (res != null && !res.sharedWith.Contains(n.bp.name)) res.sharedWith.Add(n.bp.name);
                    bool own = n.omitted || Owns(bp, n.bp);
                    portions.Add(new Portion { lo = ol, hi = oh, own = own, n = n, nh = nh });
                    if (own)
                    {
                        if (Mathf.Abs(n.y0 - L.y0) < 0.05f) height = Mathf.Max(height, n.y1 - n.y0);
                        if (res != null) res.sharedOwned++;
                    }
                    else deferredTo.Add(n.bp.name);
                }
                if (portions.Count == 0) { outList.Add(s); continue; }                              // untouched: legacy path, identical output

                var mine = L.holes;
                var holes = OutsideHoles(mine, portions.Select(p => (p.lo, p.hi)).ToList());
                foreach (var p in portions.Where(q => q.own)) holes.AddRange(SharedHoles(mine, p.nh, p.lo, p.hi, p.n.omitted));
                var allHoles = MergeHoles(holes, -half, half);
                bool taller = height > ownH + 0.01f;
                var cuts = portions.Where(p => !p.own).ToList();
                if (cuts.Count == 0)
                {
                    var ns = s.Clone(); ns.holes = allHoles;
                    if (taller) ns.height = height;
                    outList.Add(ns); continue;
                }
                if (res != null) res.sharedSkipped++;
                var merged = new List<(float lo, float hi)>();
                foreach (var sp in cuts.Select(c => (c.lo, c.hi)).OrderBy(c => c.lo))
                {
                    if (merged.Count > 0 && sp.lo <= merged[merged.Count - 1].hi + 0.001f) merged[merged.Count - 1] = (merged[merged.Count - 1].lo, Mathf.Max(merged[merged.Count - 1].hi, sp.hi));
                    else merged.Add(sp);
                }
                float covered = merged.Sum(m => m.hi - m.lo);
                if (kit)
                {
                    // kit pieces have a fixed length: drop the cell when the neighbour owns most of it, else keep it whole
                    if (covered >= 0.5f * s.length) continue;
                    res?.warnings.Add($"{s.side}{s.index} v{s.volume}: kit wall shares only {covered:F1}/{s.length:F1} m with a neighbour → kept whole");
                    var ks = s.Clone(); ks.holes = MergeHoles(holes.Concat(cuts.SelectMany(c => SharedHoles(mine, c.nh, c.lo, c.hi, false))), -half, half);
                    if (taller) ks.height = height;
                    outList.Add(ks); continue;
                }
                var axis = s.alongX ? Vector3.right : Vector3.forward;
                var pieces = new List<(float lo, float hi)>(); float cur = -half;
                foreach (var m in merged) { if (m.lo - cur > 0.05f) pieces.Add((cur, m.lo)); cur = Mathf.Max(cur, m.hi); }
                if (half - cur > 0.05f) pieces.Add((cur, half));
                int k = 0;
                foreach (var p in pieces)
                {
                    var ns = s.Clone(); float mid = (p.lo + p.hi) / 2f;
                    ns.center = s.center + axis * mid; ns.length = p.hi - p.lo;
                    ns.extNeg = s.extNeg && p.lo <= -half + 0.001f; ns.extPos = s.extPos && p.hi >= half - 0.001f;
                    ns.holes = MergeHoles(allHoles, p.lo, p.hi, mid);
                    if (taller) ns.height = height;
                    ns.tag = "_p" + k++; outList.Add(ns);
                }
                if (Mathf.Min(bp.wainscotHeight, bp.wallHeight) > 0.01f)
                    foreach (var c in cuts)
                    {
                        // the neighbour builds the wall; this side keeps its wainscot on its own face of that wall, with the same gaps
                        var fs = s.Clone(); float mid = (c.lo + c.hi) / 2f;
                        var perpShift = Quaternion.Inverse(rot) * ((L.worldX ? Vector3.forward : Vector3.right) * (c.n.perp - L.perp));
                        fs.center = s.center + axis * mid + new Vector3(perpShift.x, 0f, perpShift.z); fs.length = c.hi - c.lo; fs.extNeg = fs.extPos = false;
                        fs.faceOnly = true; fs.thickness = c.n.T; fs.holes = MergeHoles(SharedHoles(mine, c.nh, c.lo, c.hi, false), c.lo, c.hi, mid);
                        fs.tag = "_face" + k++; outList.Add(fs);
                    }
            }
            foreach (var n in deferredTo.OrderBy(x => x, StringComparer.Ordinal))
                if (FindBuilt(neighbours.First(x => x.name == n)) == null)
                    res?.warnings.Add($"shared wall: part of this blueprint's walls is built by {n}, which is not in the scene yet → build it (its wall will carry this side's openings)");
            return outList;
        }

        // ---------------- shared floors / ceilings between blueprints ----------------
        // Slabs never overlap another blueprint's slab. For every neighbour whose footprint overlaps this one on the same level:
        //   floor vs floor and roof vs roof (same level): the owner (same rule as walls: wallOwner, taller wallHeight, name) keeps
        //   its slab, the other side clips its own (rectangle difference; kit tiles are dropped when ≥ 50 % covered);
        //   roof vs a neighbour's FLOOR on the same level (a room stacked on top): that floor is the ceiling → the roof is dropped.
        // Overlaps thinner than 0.25 m (roof eaves over the wall line, corner contacts) are kept: they are edges, not duplicates.
        // A ground (Ground cube / plane / lawn block, not a GDS slab) coplanar with the floors is lowered by `groundGap` (SeparateGround).

        public class SlabCut { public bool roof; public float y; public Rect r; public string by; }

        static Blueprint s_cutBp; static List<SlabCut> s_cuts; static Result s_cutRes;
        const float SlabEdge = 0.25f;

        /// <summary>Neighbour slab rectangles (in this blueprint's pre-rotation frame: origin + local, x/z → Rect x/y) that clip this blueprint's floors / roofs.</summary>
        public static List<SlabCut> SlabCuts(Blueprint bp, List<Blueprint> neighbours, Result res)
        {
            var cuts = new List<SlabCut>();
            if (neighbours == null || neighbours.Count == 0 || IsOff(bp) || !Frame(bp, out var rot)) return cuts;
            var inv = Quaternion.Inverse(rot); var o = bp.origin.V;
            foreach (var nb in neighbours)
            {
                if (!Shares(bp, nb) || !Frame(nb, out var nrot)) continue;
                bool theyOwn = !Owns(bp, nb); var no = nb.origin.V; float nM = nb.module, nH = nb.wallHeight;
                bool nFloor = !OmitsPart(nb, "floor"), nRoof = !OmitsPart(nb, "roof");
                foreach (var v in Volumes(nb))
                {
                    if (v.cellsX <= 0 || v.cellsZ <= 0 || v.floors <= 0) continue;
                    var w0 = no + nrot * new Vector3(v.x, 0f, v.z); var w1 = no + nrot * new Vector3(v.x + v.cellsX * nM, 0f, v.z + v.cellsZ * nM);
                    var p0 = o + inv * (w0 - o); var p1 = o + inv * (w1 - o);
                    var r = Rect.MinMaxRect(Mathf.Min(p0.x, p1.x), Mathf.Min(p0.z, p1.z), Mathf.Max(p0.x, p1.x), Mathf.Max(p0.z, p1.z));
                    // roofs overhang the wall line by T/2 (eaves): a roof cut covers the eave too, so no sliver survives next to it
                    float e = Mathf.Max(bp.wallThickness, nb.wallThickness) / 2f;
                    var re = Rect.MinMaxRect(r.xMin - e, r.yMin - e, r.xMax + e, r.yMax + e);
                    for (int f = 0; f < v.floors && nFloor; f++)
                    {
                        float y = no.y + f * nH;
                        if (theyOwn) cuts.Add(new SlabCut { roof = false, y = y, r = r, by = nb.name });
                        cuts.Add(new SlabCut { roof = true, y = y, r = re, by = nb.name });           // their floor is my ceiling
                    }
                    string nroof = (string.IsNullOrEmpty(v.roof) ? nb.roof : v.roof) ?? "";
                    if (theyOwn && nRoof && !string.Equals(nroof, "none", StringComparison.OrdinalIgnoreCase))
                        cuts.Add(new SlabCut { roof = true, y = no.y + v.floors * nH, r = re, by = nb.name });
                }
            }
            return cuts;
        }

        static List<Rect> Subtract(Rect a, Rect b)
        {
            var list = new List<Rect>();
            float x0 = Mathf.Max(a.xMin, b.xMin), x1 = Mathf.Min(a.xMax, b.xMax), z0 = Mathf.Max(a.yMin, b.yMin), z1 = Mathf.Min(a.yMax, b.yMax);
            if (x1 - x0 <= SlabEdge || z1 - z0 <= SlabEdge) { list.Add(a); return list; }   // edge / corner contact: keep
            if (x0 - a.xMin > 0.05f) list.Add(Rect.MinMaxRect(a.xMin, a.yMin, x0, a.yMax));
            if (a.xMax - x1 > 0.05f) list.Add(Rect.MinMaxRect(x1, a.yMin, a.xMax, a.yMax));
            if (z0 - a.yMin > 0.05f) list.Add(Rect.MinMaxRect(x0, a.yMin, x1, z0));
            if (a.yMax - z1 > 0.05f) list.Add(Rect.MinMaxRect(x0, z1, x1, a.yMax));
            return list;
        }

        /// <summary>A slab rectangle (pre-rotation XZ as Rect x/y) minus the neighbour slabs on the same level (y = slab level: floor top / roof bottom). by == null → untouched.</summary>
        static List<Rect> ClipSlab(Blueprint bp, Rect r, float y, bool roof, out List<string> by)
        {
            var parts = new List<Rect> { r }; by = null;
            if (s_cutBp != bp || s_cuts == null) return parts;
            foreach (var c in s_cuts)
            {
                if (c.roof != roof || Mathf.Abs(c.y - y) > 0.05f) continue;
                var next = new List<Rect>(); bool changed = false;
                foreach (var p in parts) { var sub = Subtract(p, c.r); if (sub.Count != 1 || sub[0] != p) changed = true; next.AddRange(sub); }
                if (changed) { if (by == null) by = new List<string>(); if (!by.Contains(c.by)) by.Add(c.by); }
                parts = next;
            }
            if (by != null && s_cutRes != null)
            {
                s_cutRes.slabsClipped++;
                foreach (var n in by) if (!s_cutRes.sharedWith.Contains(n)) s_cutRes.sharedWith.Add(n);
            }
            return parts;
        }

        /// <summary>Kit tiles can't be cut: true when ≥ 50 % of the cell lies under a neighbour's slab on the same level.</summary>
        static bool KitCellClipped(Blueprint bp, Vector3 center, float M, float y, bool roof)
        {
            var parts = ClipSlab(bp, new Rect(center.x - M / 2f, center.z - M / 2f, M, M), y, roof, out var by);
            if (by == null) return false;
            if (parts.Sum(p => p.width * p.height) < 0.5f * M * M) return true;
            s_cutRes?.warnings.Add($"kit {(roof ? "roof" : "floor")} tile at ({center.x:F1},{center.z:F1}) partly under {string.Join(",", by)} → kept whole");
            return false;
        }

        /// <summary>Emit the (possibly clipped) slab boxes of one cell. Name unchanged when untouched, "_c{k}" suffix per clipped piece.</summary>
        static void SlabBoxes(Blueprint bp, string name, Vector3 center, Vector3 size, float level, bool roof, Func<string, Vector3, Vector3, GameObject> box)
        {
            var r = new Rect(center.x - size.x / 2f, center.z - size.z / 2f, size.x, size.z);
            var parts = ClipSlab(bp, r, level, roof, out var by);
            if (by == null) { box(name, center, size); return; }
            int k = 0;
            foreach (var p in parts)
            {
                if (p.width < 0.05f || p.height < 0.05f) continue;
                box(name + "_c" + k++, new Vector3(p.center.x, center.y, p.center.y), new Vector3(p.width, size.y, p.height));
            }
        }

        static bool IsFloorSurface(string n) => n.StartsWith("slab_", StringComparison.OrdinalIgnoreCase) || n.StartsWith("floor_", StringComparison.OrdinalIgnoreCase);
        static bool IsFloorSurface(Transform t) => IsFloorSurface(t.name) || (t.parent != null && IsFloorSurface(t.parent.name));   // kit tile: instance floor_i_j, mesh child
        static bool UnderProps(Transform t) { for (var p = t.parent; p != null; p = p.parent) if (p.name == "Props") return true; return false; }
        static bool InBlueprint(Transform t) { for (var p = t.parent; p != null; p = p.parent) if (p.Find("Shell") != null) return true; return false; }
        static bool GroundLike(Transform t, Bounds b)
        {
            var n = t.name;
            if (IsFloorSurface(t) || n.StartsWith("roof", StringComparison.OrdinalIgnoreCase) || n.IndexOf("wall", StringComparison.OrdinalIgnoreCase) >= 0 || UnderProps(t)) return false;
            return b.size.y <= 0.6f && b.size.x >= 2f && b.size.z >= 2f;
        }

        /// <summary>Floors never z-fight with the ground: a ground-like surface (not a GDS slab) whose top is coplanar with a floor slab
        /// it overlaps is lowered by groundGap — a plain ground (not part of any blueprint) under this blueprint, and this blueprint's
        /// own ground-like blocks (lawn, plaza) over another blueprint's floors. Other blueprints' objects are never moved.
        /// Idempotent and order-independent: once lowered it is no longer coplanar.</summary>
        static void SeparateGround(GameObject root, Blueprint bp, Result res)
        {
            float gap = bp.groundGap; if (gap <= 0f) return;
            float tol = Mathf.Min(0.005f, gap * 0.25f);
            var mySlabs = new List<Bounds>(); var myGround = new List<Renderer>();
            foreach (var r in root.GetComponentsInChildren<MeshRenderer>(true))
            {
                if (IsFloorSurface(r.transform)) mySlabs.Add(r.bounds);
                else if (r.transform.parent != null && r.transform.parent.name == "Shell" && GroundLike(r.transform, r.bounds)) myGround.Add(r);   // blocks
            }
            var theirSlabs = new List<Bounds>(); var theirGround = new List<Renderer>();
            foreach (var go in root.scene.GetRootGameObjects())
                foreach (var r in go.GetComponentsInChildren<MeshRenderer>(false))
                {
                    if (!r.enabled || r.transform.IsChildOf(root.transform)) continue;
                    if (IsFloorSurface(r.transform)) theirSlabs.Add(r.bounds);
                    else if (GroundLike(r.transform, r.bounds) && !InBlueprint(r.transform)) theirGround.Add(r);   // plain Ground cube / plane only
                }
            void Sink(List<Renderer> grounds, List<Bounds> slabs)
            {
                foreach (var g in grounds)
                {
                    var gb = g.bounds; float top = float.NegativeInfinity;
                    foreach (var sb in slabs)
                    {
                        if (Mathf.Abs(gb.max.y - sb.max.y) > tol) continue;                                 // not coplanar
                        if (gb.size.y > 0.002f && gb.min.y > sb.max.y - 0.02f) continue;                   // lies on the floor (rug, mat)
                        float ox = Mathf.Min(gb.max.x, sb.max.x) - Mathf.Max(gb.min.x, sb.min.x), oz = Mathf.Min(gb.max.z, sb.max.z) - Mathf.Max(gb.min.z, sb.min.z);
                        if (ox <= SlabEdge || oz <= SlabEdge) continue;
                        top = Mathf.Max(top, sb.max.y);
                    }
                    if (float.IsNegativeInfinity(top)) continue;
                    float d = gb.max.y - (top - gap); if (d <= 0f) continue;
                    Undo.RecordObject(g.transform, "GDS ground below floors");
                    g.transform.position += Vector3.down * d;
                    res.groundLowered++;
                    res.warnings.Add($"lowered {Common.HierarchyPath(g.transform)} by {d:F3} m: its top was coplanar with the floors (z-fighting)");
                }
            }
            Sink(theirGround, mySlabs);
            Sink(myGround, theirSlabs);
        }

        static bool LooksLikeBlueprint(string txt, bool needShell)
        {
            if (string.IsNullOrEmpty(txt) || !txt.Contains("\"name\"")) return false;
            if (txt.Contains("\"lots\"") || txt.Contains("\"roads\"")) return false;                // village spec, not a blueprint
            bool shell = txt.Contains("\"cellsX\"") || txt.Contains("\"volumes\"");
            return needShell ? shell : shell || txt.Contains("\"mode\"") || txt.Contains("\"props\"");
        }

        /// <summary>Blueprints that may share walls with bp: its explicit `neighbours` files, else every blueprint JSON in the same folder with the same `group`.</summary>
        public static List<Blueprint> LoadNeighbours(string blueprintDir, Blueprint bp)
        {
            var list = new List<Blueprint>();
            if (bp == null || IsOff(bp)) return list;
            string dir = string.IsNullOrEmpty(blueprintDir) ? "art/blueprints" : blueprintDir.TrimEnd('/');
            bool explicitList = bp.neighbours != null && bp.neighbours.Any(n => !string.IsNullOrWhiteSpace(n));
            var paths = new List<string>();
            if (explicitList) paths.AddRange(bp.neighbours.Where(n => !string.IsNullOrWhiteSpace(n)).Select(n => n.Contains("/") ? n : dir + "/" + n));
            else
            {
                var full = Path.Combine(Common.ProjectDir, dir);
                if (!Directory.Exists(full)) return list;
                paths.AddRange(Directory.GetFiles(full, "*.json").OrderBy(p => p, StringComparer.Ordinal).Select(p => dir + "/" + Path.GetFileName(p)));
            }
            foreach (var p in paths)
            {
                var txt = Common.ReadProjectFile(p); if (!LooksLikeBlueprint(txt, true)) continue;
                Blueprint nb; try { nb = JsonUtility.FromJson<Blueprint>(txt); } catch { continue; }
                if (nb == null || nb.name == bp.name || list.Any(x => x.name == nb.name)) continue;
                if (!explicitList && !string.Equals(nb.group ?? "", bp.group ?? "", StringComparison.OrdinalIgnoreCase)) continue;
                list.Add(nb);
            }
            return list;
        }

        /// <summary>The built root of a blueprint in the active scene (group path + name), or null.</summary>
        public static GameObject FindBuilt(Blueprint bp)
        {
            if (bp == null || string.IsNullOrEmpty(bp.name)) return null;
            var roots = EditorSceneManager.GetActiveScene().GetRootGameObjects();
            Transform cur = null;
            foreach (var part in (bp.group ?? "").Split(new[] { '/' }, StringSplitOptions.RemoveEmptyEntries))
            {
                cur = cur == null ? roots.FirstOrDefault(g => g.name == part)?.transform : cur.Find(part);
                if (cur == null) return null;
            }
            var t = cur == null ? roots.FirstOrDefault(g => g.name == bp.name)?.transform : cur.Find(bp.name);
            return t != null ? t.gameObject : null;
        }

        static bool HasHole(Blueprint bp, int vi, int cx, int cz, int f) => bp.floorHoles.Any(h => h.volume == vi && h.cellX == cx && h.cellZ == cz && h.floor == f);
        static bool TallerWingAbove(List<Volume> vols, int vi, float M, Vector3 local)
        {
            var v = vols[vi];
            for (int k = 0; k < vols.Count; k++)
            {
                if (k == vi) continue; var ov = vols[k];
                if (ov.floors <= v.floors) continue;
                if (local.x > ov.x && local.x < ov.x + ov.cellsX * M && local.z > ov.z && local.z < ov.z + ov.cellsZ * M) return true;
            }
            return false;
        }
        static bool LowerWingTiled(List<Volume> vols, int vi, float M, Vector3 local, int f)
        {
            for (int k = 0; k < vi; k++)
            {
                var ov = vols[k]; if (f >= ov.floors) continue;
                if (local.x > ov.x && local.x < ov.x + ov.cellsX * M && local.z > ov.z && local.z < ov.z + ov.cellsZ * M) return true;
            }
            return false;
        }

        // ---------------- kit shell ----------------
        static int BuildKitShell(Blueprint bp, List<Volume> vols, List<Seg> segs, Transform shell, Result res)
        {
            var roleMap = new Dictionary<string, GameObject>(StringComparer.OrdinalIgnoreCase);
            foreach (var rf in bp.roles)
            {
                var m = Common.LoadModel(rf.file, bp.kitRoot);
                if (m == null) res.warnings.Add($"role {rf.role}: file not found {rf.file}"); else roleMap[rf.role] = m;
            }
            GameObject Role(string r) { roleMap.TryGetValue(r, out var g); return g; }
            foreach (var need in new[] { "floor", "wall" }) if (Role(need) == null) res.missingRoles.Add(need);
            if (Role("wall") == null) return 0;
            int count = 0; float M = bp.module; var o = bp.origin.V;

            for (int vi = 0; vi < vols.Count; vi++)
            {
                var v = vols[vi];
                var volT = new GameObject($"Volume_{vi}").transform; volT.SetParent(shell, false);
                for (int f = 0; f < v.floors; f++)
                {
                    var floorT = new GameObject($"Floor_{f}").transform; floorT.SetParent(volT, false);
                    if (Role("floor") != null && !OmitsPart(bp, "floor"))
                        for (int i = 0; i < v.cellsX; i++) for (int j = 0; j < v.cellsZ; j++)
                            {
                                if (HasHole(bp, vi, i, j, f)) continue;
                                var l = new Vector3(v.x + (i + 0.5f) * M, f * bp.wallHeight, v.z + (j + 0.5f) * M);
                                if (LowerWingTiled(vols, vi, M, l, f)) continue;
                                if (KitCellClipped(bp, o + l, M, o.y + l.y, false)) continue;      // a neighbour's floor already covers this cell
                                Put(Role("floor"), floorT, o + l, 0, "X", $"floor_{i}_{j}"); count++;
                            }
                    if (bp.corners && Role("corner") != null)
                        foreach (var c in new[] { new Vector3(v.x, 0, v.z), new Vector3(v.x + v.cellsX * M, 0, v.z), new Vector3(v.x, 0, v.z + v.cellsZ * M), new Vector3(v.x + v.cellsX * M, 0, v.z + v.cellsZ * M) })
                        {
                            if (InsideOther(vols, vi, M, c, f)) continue;
                            Put(Role("corner"), floorT, o + c + Vector3.up * (f * bp.wallHeight), 0, null, "corner"); count++;
                        }
                }
                var roofT = new GameObject("Roof").transform; roofT.SetParent(volT, false);
                string roofMode = (string.IsNullOrEmpty(v.roof) ? bp.roof : v.roof).ToLowerInvariant();
                GameObject roofPiece = roofMode == "kit" ? Role("roof") : roofMode == "flat" ? Role("floor") : null;
                if (roofMode == "kit" && roofPiece == null) { res.warnings.Add($"volume {vi}: no roof role → flat roof from floor tiles"); roofPiece = Role("floor"); }
                if (roofPiece != null && !OmitsPart(bp, "roof"))
                    for (int i = 0; i < v.cellsX; i++) for (int j = 0; j < v.cellsZ; j++)
                        {
                            var l = new Vector3(v.x + (i + 0.5f) * M, v.floors * bp.wallHeight, v.z + (j + 0.5f) * M);
                            if (TallerWingAbove(vols, vi, M, l)) continue;
                            if (KitCellClipped(bp, o + l, M, o.y + l.y, true)) continue;       // neighbour roof / floor above covers it
                            Put(roofPiece, roofT, o + l, 0, "X", $"roof_{i}_{j}"); count++;
                        }
            }
            var wallsT = new GameObject("Walls").transform; wallsT.SetParent(shell, false);
            foreach (var s in segs)
            {
                if (s.faceOnly) continue;                    // wall built by the neighbour that owns this line
                string role = "wall";
                // merged openings (shared wall): the strongest one decides the kit piece — door > window > none
                var best = s.holes?.OrderByDescending(Prio).FirstOrDefault();
                var type = s.holes != null ? best?.type : s.opening?.type;
                if (s.holes != null ? best != null : s.opening != null)
                {
                    role = type == "window" ? "wallWindow" : type == "none" ? null : "wallDoor";
                    if (role != null && !roleMap.ContainsKey(role)) { res.warnings.Add($"{s.side}{s.index} wants {role} but kit has none → plain wall"); role = "wall"; }
                }
                if (role == null) continue;
                float rot = s.side == "S" ? 0 : s.side == "N" ? 180 : s.side == "W" ? 90 : -90;
                Put(roleMap[role], wallsT, s.center, rot, s.alongX ? "X" : "Z", $"{role}_v{s.volume}_{s.side}{s.index}_f{s.floor}"); count++;
            }
            foreach (var p in bp.partitions) count += KitPartition(bp, p, roleMap, wallsT);
            foreach (var st in bp.stairs)
            {
                var asset = string.IsNullOrEmpty(st.file) ? Role("stair") : Common.LoadModel(st.file, bp.kitRoot);
                if (asset == null) { res.warnings.Add("stair: no file/role"); continue; }
                Put(asset, shell, o + new Vector3(st.x, st.floor * bp.wallHeight, st.z), st.rotY, null, "stair"); count++;
            }
            return count;
        }

        static int KitPartition(Blueprint bp, Partition p, Dictionary<string, GameObject> roles, Transform parent)
        {
            if (!roles.ContainsKey("wall")) return 0;
            var o = bp.origin.V; float M = bp.module;
            var a = new Vector3(p.x0, 0, p.z0); var b = new Vector3(p.x1, 0, p.z1);
            float len = Vector3.Distance(a, b); if (len < 0.1f) return 0;
            int n = Mathf.Max(1, Mathf.RoundToInt(len / M)); var dir = (b - a).normalized; bool alongX = Mathf.Abs(dir.x) >= Mathf.Abs(dir.z);
            int c = 0;
            for (int i = 0; i < n; i++)
            {
                float t0 = (float)i / n, t1 = (float)(i + 1) / n;
                bool hasDoor = p.door >= 0 && p.door >= t0 && p.door < t1;
                string role = hasDoor && roles.ContainsKey("wallDoor") ? "wallDoor" : "wall";
                var center = o + a + dir * ((i + 0.5f) * len / n) + Vector3.up * (p.floor * bp.wallHeight);
                Put(roles[role], parent, center, alongX ? 0 : 90, alongX ? "X" : "Z", $"partition_{i}"); c++;
            }
            return c;
        }

        /// <summary>Spawn a piece, rotate, then align by measured bounds; auto-fix a 90° axis mismatch.</summary>
        static GameObject Put(GameObject asset, Transform parent, Vector3 bottomCenter, float rotY, string expectLongAxis, string name)
        {
            var inst = Common.Spawn(asset, parent, name);
            inst.transform.rotation = Quaternion.Euler(0, rotY, 0);
            if (expectLongAxis != null && Common.TryGetBounds(inst, out var b0))
            {
                bool longIsX = b0.size.x >= b0.size.z;
                if ((expectLongAxis == "X" && !longIsX) || (expectLongAxis == "Z" && longIsX))
                    inst.transform.rotation = Quaternion.Euler(0, rotY + 90f, 0);
            }
            Common.AlignBottomCenter(inst, bottomCenter);
            Common.EnsureCollider(inst, false);
            return inst;
        }

        // ---------------- primitives shell (greybox fallback) ----------------
        static int BuildPrimitiveShell(Blueprint bp, List<Volume> vols, List<Seg> segs, Transform shell, Result res)
        {
            var mat = string.IsNullOrEmpty(bp.material) ? null : AssetDatabase.LoadAssetAtPath<Material>(bp.material);
            if (mat == null) mat = Common.PaletteMaterial(1, new Color(0.80f, 0.74f, 0.62f), "Wall");
            var roofMat = Common.PaletteMaterial(2, new Color(0.48f, 0.24f, 0.18f), "Roof");
            int c = 0;
            GameObject Box(string n, Vector3 center, Vector3 size)
            {
                var g = GameObject.CreatePrimitive(PrimitiveType.Cube); g.name = n; g.transform.SetParent(shell, false);
                g.transform.position = center; g.transform.localScale = size;
                g.GetComponent<MeshRenderer>().sharedMaterial = n.StartsWith("roof") ? roofMat : mat;
                Undo.RegisterCreatedObjectUndo(g, "GDS Box"); c++; return g;
            }
            ShellBoxes(bp, vols, segs, Box);
            return c;
        }

        /// <summary>Slabs, wall segments (door/window gaps as legs + lintel/sill), partitions, flat roofs — shared by primitives and ProBuilder shells.</summary>
        public static void ShellBoxes(Blueprint bp, List<Volume> vols, List<Seg> segs, Func<string, Vector3, Vector3, GameObject> box)
        {
            float M = bp.module, H = bp.wallHeight, T = bp.wallThickness; var o = bp.origin.V;
            for (int vi = 0; vi < vols.Count; vi++)
            {
                var v = vols[vi];
                // slab top = floor level (FFL); clipped against neighbour slabs on the same level (SlabBoxes)
                for (int f = 0; f < v.floors && !OmitsPart(bp, "floor"); f++)
                    for (int i = 0; i < v.cellsX; i++) for (int j = 0; j < v.cellsZ; j++)
                        {
                            if (HasHole(bp, vi, i, j, f)) continue;
                            var l = new Vector3(v.x + (i + 0.5f) * M, f * H - 0.1f, v.z + (j + 0.5f) * M);
                            if (LowerWingTiled(vols, vi, M, l, f)) continue;
                            SlabBoxes(bp, $"slab_v{vi}_{i}_{j}_f{f}", o + l, new Vector3(M, 0.2f, M), o.y + f * H, false, box);
                        }
                string roof = (string.IsNullOrEmpty(v.roof) ? bp.roof : v.roof).ToLowerInvariant();
                if (roof != "none" && !OmitsPart(bp, "roof"))
                    for (int i = 0; i < v.cellsX; i++) for (int j = 0; j < v.cellsZ; j++)
                        {
                            var l = new Vector3(v.x + (i + 0.5f) * M, v.floors * H + 0.1f, v.z + (j + 0.5f) * M);
                            if (TallerWingAbove(vols, vi, M, l)) continue;
                            // edge cells overhang T/2 onto the wall line; SlabBoxes keeps overlaps thinner than 0.25 m
                            SlabBoxes(bp, $"roof_v{vi}_{i}_{j}", o + l, new Vector3(M + (i == 0 || i == v.cellsX - 1 ? T : 0), 0.2f, M + (j == 0 || j == v.cellsZ - 1 ? T : 0)), o.y + v.floors * H, true, box);
                        }
            }
            foreach (var s in segs) WallSegmentBoxes(s, H, T, box, 0.5f, bp);
            foreach (var p in bp.partitions)
            {
                var a = o + new Vector3(p.x0, p.floor * H, p.z0); var b = o + new Vector3(p.x1, p.floor * H, p.z1);
                float len = Vector3.Distance(a, b); if (len < 0.1f) continue;
                bool alongX = Mathf.Abs(b.x - a.x) >= Mathf.Abs(b.z - a.z); var c = (a + b) / 2f;
                var seg = new Seg { center = new Vector3(c.x, a.y, c.z), alongX = alongX, length = len, side = "P", opening = p.door >= 0 ? new Opening { type = "door" } : null };
                WallSegmentBoxes(seg, H, 0.15f, box, p.door < 0 ? 0.5f : p.door, bp);
            }
        }

        static void WallSegmentBoxes(Seg s, float H, float T, Func<string, Vector3, Vector3, GameObject> box, float doorT = 0.5f, Blueprint bp = null)
        {
            const float doorW = 1.0f, doorH = 2.2f;
            if (s.height > 0.01f) H = s.height;              // shared wall: taller of the two sides
            if (s.thickness > 0.001f) T = s.thickness;
            float winW = bp != null && bp.windowWidth > 0.1f ? bp.windowWidth : 1.2f;
            float winH = bp != null && bp.windowHeight > 0.1f ? bp.windowHeight : 1.2f;
            float winSill = bp != null && bp.windowSill >= 0f ? bp.windowSill : 1.0f;
            float wH = bp != null ? Mathf.Min(bp.wainscotHeight, bp.wallHeight) : 0f;
            if (s.faceOnly && (wH <= 0.01f || s.side == "P")) return;   // the neighbour builds this wall and there is no wainscot to add
            if (wH > 0.01f && s.side != "P")
            {
                // wrap: every wall piece that touches the floor also gets an interior wainscot panel (3 cm, inner face)
                // faceOnly (wall owned by a neighbour): only the panel is built, on this blueprint's side
                var inner = box; var inward = -s.normal; const float wt = 0.03f; bool faceOnly = s.faceOnly;
                box = (n, c0, sz) =>
                {
                    var g = faceOnly ? null : inner(n, c0, sz);
                    float bottom = c0.y - sz.y / 2f;
                    if (bottom < 0.01f + s.center.y)
                    {
                        float h = Mathf.Min(wH, sz.y);
                        var wc = new Vector3(c0.x, s.center.y + h / 2f, c0.z) + inward * (T / 2f + wt / 2f);
                        var wsz = s.alongX ? new Vector3(sz.x, h, wt) : new Vector3(wt, h, sz.z);
                        inner(n + "_wainscot", wc, wsz);
                    }
                    return g;
                };
            }
            Vector3 Along(float len) => s.alongX ? new Vector3(len, 0, 0) : new Vector3(0, 0, len);
            Vector3 Size(float len, float h) => s.alongX ? new Vector3(len, h, T) : new Vector3(T, h, len);
            string nm = $"wall_v{s.volume}_{s.side}{s.index}_f{s.floor}{s.tag}"; var c = s.center; float L = s.length;
            // legs extend T/2 past the segment end (closes the corner) but must stop exactly at the opening edge → opening = ow (1.0 m door);
            // no extension where a shared wall was cut (the neighbour's wall continues there)
            float eN = s.side == "P" || !s.extNeg ? 0f : T / 2, eP = s.side == "P" || !s.extPos ? 0f : T / 2;

            var holes = s.holes;
            if (holes == null)
            {
                holes = new List<Hole>();
                if (s.opening != null)
                {
                    string t = s.opening.type == "window" ? "window" : s.opening.type == "none" ? "none" : "door";
                    if (t == "none") holes.Add(new Hole { type = t, at = 0f, width = L });
                    else if (t == "window") holes.Add(new Hole { type = t, at = (doorT - 0.5f) * L, width = winW, height = winH, sill = winSill });
                    else holes.Add(new Hole { type = t, at = (doorT - 0.5f) * L, width = doorW, height = doorH });
                }
            }
            if (holes.Count == 0)
            {
                float full = s.side == "P" && s.extNeg && s.extPos ? L + T : L + eN + eP;   // partitions keep their legacy +T
                box(nm, c + Along((eP - eN) / 2f) + Vector3.up * H / 2, Size(full, H)); return;
            }
            float prevEnd = -L / 2f; int k = 0;
            foreach (var h in holes.OrderBy(x => x.at))
            {
                float h0 = Mathf.Max(h.at - h.width / 2f, -L / 2f), h1 = Mathf.Min(h.at + h.width / 2f, L / 2f);
                float core = h0 - prevEnd, start = k == 0 ? prevEnd - eN : prevEnd;
                if (core > 0.05f) box(nm + (k == 0 ? "_L" : "_M" + k), c + Along((start + h0) / 2f) + Vector3.up * H / 2, Size(h0 - start, H));
                string sfx = k == 0 ? "" : k.ToString(); var dc = c + Along((h0 + h1) / 2f); float ow = h1 - h0;
                if (h.type == "window")
                {
                    float sill = Mathf.Clamp(h.sill, 0f, H), topH = H - sill - h.height;
                    if (sill > 0.01f) box(nm + "_sill" + sfx, dc + Vector3.up * sill / 2, Size(ow, sill));
                    if (topH > 0.01f) box(nm + "_top" + sfx, dc + Vector3.up * (H - topH / 2), Size(ow, topH));
                }
                else if (h.type != "none")
                {
                    float lint = H - (h.height > 0.1f ? h.height : doorH);
                    if (lint > 0.01f) box(nm + "_lintel" + sfx, dc + Vector3.up * (H - lint / 2), Size(ow, lint));
                }
                prevEnd = Mathf.Max(prevEnd, h1); k++;
            }
            float coreR = L / 2f - prevEnd;
            if (coreR > 0.05f) box(nm + "_R", c + Along((prevEnd + L / 2f + eP) / 2f) + Vector3.up * H / 2, Size(L / 2f + eP - prevEnd, H));
        }

        // ---------------- attachments, fences, props & scatter ----------------
        static bool PlaceAttach(Blueprint bp, List<Volume> vols, Attach a, Transform parent, Result res)
        {
            var asset = Common.LoadModel(a.file, Common.ArtRoot);
            if (asset == null) { res.warnings.Add("attach not found: " + a.file); return false; }
            if (a.volume < 0 || a.volume >= vols.Count) { res.warnings.Add("attach: bad volume"); return false; }
            var v = vols[a.volume]; float M = bp.module; var o = bp.origin.V; float W = v.cellsX * M, D = v.cellsZ * M;
            Vector3 c, n; bool alongX;
            switch ((a.side ?? "S").ToUpperInvariant())
            {
                case "N": c = new Vector3(v.x + (a.index + 0.5f) * M, 0, v.z + D); n = Vector3.forward; alongX = true; break;
                case "W": c = new Vector3(v.x, 0, v.z + (a.index + 0.5f) * M); n = Vector3.left; alongX = false; break;
                case "E": c = new Vector3(v.x + W, 0, v.z + (a.index + 0.5f) * M); n = Vector3.right; alongX = false; break;
                default: c = new Vector3(v.x + (a.index + 0.5f) * M, 0, v.z); n = Vector3.back; alongX = true; break;
            }
            var pos = o + c + n * (bp.wallThickness / 2f + a.outward) + (alongX ? new Vector3(a.along, 0, 0) : new Vector3(0, 0, a.along)) + Vector3.up * (a.floor * bp.wallHeight + a.y);
            var inst = Common.Spawn(asset, parent, "attach_" + asset.name);
            inst.transform.rotation = Quaternion.LookRotation(n) * Quaternion.Euler(0, a.rotY, 0);
            if (Common.TryGetBounds(inst, out var b)) inst.transform.position += pos - new Vector3(b.center.x, b.min.y, b.center.z);
            else inst.transform.position = pos;
            if (a.collider != "none") Common.EnsureCollider(inst, a.collider == "convex");
            return true;
        }

        static int BuildFence(Blueprint bp, Fence f, Transform parent, Result res)
        {
            var asset = Common.LoadModel(f.file, Common.ArtRoot);
            if (asset == null || f.points.Count < 2) { res.warnings.Add("fence: file/points missing " + f.file); return 0; }
            var post = string.IsNullOrEmpty(f.postFile) ? null : Common.LoadModel(f.postFile, Common.ArtRoot);
            var g = new GameObject("Fence").transform; g.SetParent(parent, false);
            float pieceLen = f.pieceLength;
            if (pieceLen <= 0f)
            {
                var probe = Common.Spawn(asset, g, "probe");
                pieceLen = Common.TryGetBounds(probe, out var pb) ? Mathf.Max(pb.size.x, pb.size.z) : 2f;
                UnityEngine.Object.DestroyImmediate(probe);
            }
            int n = 0; var o = bp.origin.V;
            for (int i = 0; i < f.points.Count - 1; i++)
            {
                var a = o + f.points[i].V; var b = o + f.points[i + 1].V; var dir = b - a; float len = dir.magnitude; if (len < 0.05f) continue;
                dir /= len; int pieces = Mathf.Max(1, Mathf.RoundToInt(len / pieceLen)); float step = len / pieces;
                float rot = Mathf.Atan2(dir.x, dir.z) * Mathf.Rad2Deg - 90f;
                for (int k = 0; k < pieces; k++)
                {
                    var center = a + dir * ((k + 0.5f) * step);
                    var inst = Common.Spawn(asset, g, "fence_" + n);
                    inst.transform.rotation = Quaternion.Euler(0, rot, 0);
                    if (Common.TryGetBounds(inst, out var b0))
                    {
                        // long axis must follow dir; then stretch to the exact step so runs close without gaps
                        var longWorld = b0.size.x >= b0.size.z ? Vector3.right : Vector3.forward;
                        if (Mathf.Abs(Vector3.Dot(longWorld, dir)) < 0.7f) inst.transform.rotation = Quaternion.Euler(0, rot + 90f, 0);
                        if (Common.TryGetBounds(inst, out var b1))
                        {
                            float cur = Mathf.Abs(Vector3.Dot(b1.size, new Vector3(Mathf.Abs(dir.x), 0, Mathf.Abs(dir.z))));
                            if (cur > 0.01f)
                            {
                                var localDir = inst.transform.InverseTransformDirection(dir); var s = inst.transform.localScale;
                                int ax = Mathf.Abs(localDir.x) >= Mathf.Abs(localDir.z) ? 0 : 2; s[ax] *= step / cur; inst.transform.localScale = s;
                            }
                        }
                    }
                    Common.AlignBottomCenter(inst, center + Vector3.up * 50f);
                    if (Common.TryGetBounds(inst, out var b2) && Common.GroundBelow(inst, b2, out float gy, out _)) Common.AlignBottomCenter(inst, new Vector3(center.x, gy, center.z));
                    else Common.AlignBottomCenter(inst, center);
                    if (f.collider != "none") Common.EnsureCollider(inst, false);
                    n++;
                }
                if (post != null) foreach (var p in new[] { a, b }) { var pi = Common.Spawn(post, g, "post"); Common.AlignBottomCenter(pi, p); Common.EnsureCollider(pi, false); }
            }
            return n;
        }

        static bool PlaceProp(Blueprint bp, Prop p, Transform parent, Result res)
        {
            var asset = Common.LoadModel(p.file, Common.ArtRoot);
            if (asset == null) { res.warnings.Add("prop not found: " + p.file); return false; }
            var inst = Common.Spawn(asset, parent, string.IsNullOrEmpty(p.name) ? asset.name : p.name);
            inst.transform.localScale = Vector3.one * (p.scale <= 0 ? 1f : p.scale);
            inst.transform.rotation = Quaternion.Euler(0, p.rotY, 0);
            var target = bp.origin.V + new Vector3(p.x, p.y, p.z);
            Common.AlignBottomCenter(inst, target);
            if (p.collider != "none") Common.EnsureCollider(inst, p.collider == "convex", p.collider == "mesh");
            if (p.snap && Common.TryGetBounds(inst, out var b) && Common.GroundBelow(inst, b, out float gy, out _))
                inst.transform.position += Vector3.up * (gy - b.min.y);
            return true;
        }

        static int DoScatter(Blueprint bp, Scatter s, Transform parent, Result res)
        {
            var asset = Common.LoadModel(s.file, Common.ArtRoot);
            if (asset == null) { res.warnings.Add("scatter not found: " + s.file); return 0; }
            var rnd = new System.Random(s.seed); var placed = new List<Vector3>(); int ok = 0, tries = 0;
            var g = new GameObject("Scatter_" + asset.name).transform; g.SetParent(parent, false);
            while (ok < s.count && tries++ < s.count * 40)
            {
                float x = Mathf.Lerp(s.minX, s.maxX, (float)rnd.NextDouble()), z = Mathf.Lerp(s.minZ, s.maxZ, (float)rnd.NextDouble());
                var pos = bp.origin.V + new Vector3(x, 0, z); var p2 = new Vector2(pos.x, pos.z);
                if (s.avoidRadius > 0 && Vector2.Distance(p2, new Vector2(bp.origin.x, bp.origin.z)) < s.avoidRadius) continue;
                if (s.avoidPoints.Any(ap => Vector2.Distance(p2, new Vector2(bp.origin.x + ap.x, bp.origin.z + ap.z)) < s.avoidPointRadius)) continue;
                if (placed.Any(q => Vector2.Distance(new Vector2(q.x, q.z), p2) < s.minDist)) continue;
                var inst = Common.Spawn(asset, g, (s.prefix ?? "") + asset.name + "_" + ok);
                inst.transform.localScale = Vector3.one * Mathf.Lerp(s.scaleMin, s.scaleMax, (float)rnd.NextDouble());
                inst.transform.rotation = Quaternion.Euler(0, s.randomRotY ? (float)rnd.NextDouble() * 360f : 0f, 0);
                Common.AlignBottomCenter(inst, pos + Vector3.up * 50f);
                if (Common.TryGetBounds(inst, out var b) && Common.GroundBelow(inst, b, out float gy, out _)) Common.AlignBottomCenter(inst, new Vector3(pos.x, gy, pos.z));
                else { UnityEngine.Object.DestroyImmediate(inst); continue; }
                if (s.collider != "none") Common.EnsureCollider(inst, s.collider == "convex");
                placed.Add(inst.transform.position); ok++;
            }
            if (ok < s.count) res.warnings.Add($"scatter {asset.name}: placed {ok}/{s.count} (area too small or no ground collider)");
            return ok;
        }

        static string Sanitize(string s) => string.Concat((s ?? "x").Select(ch => char.IsLetterOrDigit(ch) ? ch : '_'));

        [MenuItem("GDS/Build Blueprint (art/blueprints/*.json)")]
        static void Menu()
        {
            var path = EditorUtility.OpenFilePanel("Blueprint JSON", System.IO.Path.Combine(Common.ProjectDir, "art/blueprints"), "json");
            if (string.IsNullOrEmpty(path)) return;
            var proj = Common.ProjectDir.Replace('\\', '/').TrimEnd('/') + "/"; var p = path.Replace('\\', '/');
            string dir = p.StartsWith(proj, StringComparison.OrdinalIgnoreCase) ? Path.GetDirectoryName(p.Substring(proj.Length)).Replace('\\', '/') : "art/blueprints";
            Debug.Log(BuildFromJson(File.ReadAllText(path), dir));
        }
    }
}
