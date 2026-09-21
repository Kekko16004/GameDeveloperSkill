// GDS LevelBuilder v2 — JSON blueprint → assembled building / props / scatter in ONE call.
// Composite footprints (L / T / U via `volumes`), interior partitions with doors, wall attachments (lanterns, signs,
// awnings, flower boxes), fences along polylines, stairs, floor holes, per-volume roofs. Pivot-agnostic: every piece is
// aligned by its measured bounds, so Kenney / KayKit / Quaternius / Synty all snap. Missing roles are reported, never faked.
// Usage (execute_code):
//   return GDS.LevelBuilder.BuildFromFile("art/blueprints/house_a.json");
// Schema: references/level-builder.md
using System;
using System.Collections.Generic;
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
        [Serializable] public class Scatter
        {
            public string file; public int count = 10; public float minX = -20, maxX = 20, minZ = -20, maxZ = 20;
            public float minDist = 2f; public int seed = 1; public bool randomRotY = true; public float scaleMin = 1f, scaleMax = 1f;
            public float avoidRadius = 0f; public List<V3> avoidPoints = new List<V3>(); public float avoidPointRadius = 4f;
            public string collider = "box";
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
            public string material;                     // probuilder/primitives shell material
            public string prefabOut;
            public List<Prop> props = new List<Prop>();
            public List<Scatter> scatter = new List<Scatter>();
        }
        [Serializable] public class Result
        {
            public string name; public string status = "PASS"; public int pieces; public int props; public int scattered; public int attached; public int fencePieces;
            public float boundsX, boundsY, boundsZ; public List<string> missingRoles = new List<string>(); public List<string> warnings = new List<string>();
        }

        /// <summary>Wall segment of the composite footprint (world-space centre at floor level).</summary>
        public class Seg { public int volume; public string side; public int index; public int floor; public Vector3 center; public bool alongX; public Vector3 normal; public Opening opening; public float length; }

        /// <summary>Registered by GDS.Editor.ProBuilder when com.unity.probuilder is installed.</summary>
        public static Func<Blueprint, List<Volume>, List<Seg>, Transform, Result, int> ProBuilderShell;

        public static string BuildFromFile(string projectRelJson)
        {
            var json = Common.ReadProjectFile(projectRelJson);
            if (json == null) return "{\"status\":\"FAIL\",\"error\":\"blueprint not found: " + Common.Esc(projectRelJson) + "\"}";
            return BuildFromJson(json);
        }

        public static string BuildFromJson(string json)
        {
            Blueprint bp;
            try { bp = JsonUtility.FromJson<Blueprint>(json); }
            catch (Exception e) { return "{\"status\":\"FAIL\",\"error\":\"bad json: " + Common.Esc(e.Message) + "\"}"; }
            var res = Build(bp);
            var outJson = JsonUtility.ToJson(res, true);
            Common.WriteProjectFile($"docs/lint/build-{Sanitize(bp.name)}.json", outJson);
            return outJson;
        }

        public static List<Volume> Volumes(Blueprint bp)
        {
            if (bp.volumes != null && bp.volumes.Count > 0) return bp.volumes;
            return new List<Volume> { new Volume { x = 0, z = 0, cellsX = bp.cellsX, cellsZ = bp.cellsZ, floors = bp.floors, roof = bp.roof } };
        }

        public static Result Build(Blueprint bp)
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
            var segs = WallSegments(bp, vols);

            string mode = (bp.mode ?? "kit").ToLowerInvariant();
            if (mode != "props" && vols.Any(v => v.cellsX > 0 && v.cellsZ > 0 && v.floors > 0))
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
                    if (Role("floor") != null)
                        for (int i = 0; i < v.cellsX; i++) for (int j = 0; j < v.cellsZ; j++)
                            {
                                if (HasHole(bp, vi, i, j, f)) continue;
                                var l = new Vector3(v.x + (i + 0.5f) * M, f * bp.wallHeight, v.z + (j + 0.5f) * M);
                                if (LowerWingTiled(vols, vi, M, l, f)) continue;
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
                if (roofPiece != null)
                    for (int i = 0; i < v.cellsX; i++) for (int j = 0; j < v.cellsZ; j++)
                        {
                            var l = new Vector3(v.x + (i + 0.5f) * M, v.floors * bp.wallHeight, v.z + (j + 0.5f) * M);
                            if (TallerWingAbove(vols, vi, M, l)) continue;
                            Put(roofPiece, roofT, o + l, 0, "X", $"roof_{i}_{j}"); count++;
                        }
            }
            var wallsT = new GameObject("Walls").transform; wallsT.SetParent(shell, false);
            foreach (var s in segs)
            {
                string role = "wall";
                if (s.opening != null)
                {
                    role = s.opening.type == "window" ? "wallWindow" : s.opening.type == "none" ? null : "wallDoor";
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
                for (int f = 0; f < v.floors; f++)
                    for (int i = 0; i < v.cellsX; i++) for (int j = 0; j < v.cellsZ; j++)
                        {
                            if (HasHole(bp, vi, i, j, f)) continue;
                            var l = new Vector3(v.x + (i + 0.5f) * M, f * H - 0.1f, v.z + (j + 0.5f) * M);
                            if (LowerWingTiled(vols, vi, M, l, f)) continue;
                            box($"slab_v{vi}_{i}_{j}_f{f}", o + l, new Vector3(M, 0.2f, M));
                        }
                string roof = (string.IsNullOrEmpty(v.roof) ? bp.roof : v.roof).ToLowerInvariant();
                if (roof != "none")
                    for (int i = 0; i < v.cellsX; i++) for (int j = 0; j < v.cellsZ; j++)
                        {
                            var l = new Vector3(v.x + (i + 0.5f) * M, v.floors * H + 0.1f, v.z + (j + 0.5f) * M);
                            if (TallerWingAbove(vols, vi, M, l)) continue;
                            box($"roof_v{vi}_{i}_{j}", o + l, new Vector3(M + (i == 0 || i == v.cellsX - 1 ? T : 0), 0.2f, M + (j == 0 || j == v.cellsZ - 1 ? T : 0)));
                        }
            }
            foreach (var s in segs) WallSegmentBoxes(s, H, T, box);
            foreach (var p in bp.partitions)
            {
                var a = o + new Vector3(p.x0, p.floor * H, p.z0); var b = o + new Vector3(p.x1, p.floor * H, p.z1);
                float len = Vector3.Distance(a, b); if (len < 0.1f) continue;
                bool alongX = Mathf.Abs(b.x - a.x) >= Mathf.Abs(b.z - a.z); var c = (a + b) / 2f;
                var seg = new Seg { center = new Vector3(c.x, a.y, c.z), alongX = alongX, length = len, side = "P", opening = p.door >= 0 ? new Opening { type = "door" } : null };
                WallSegmentBoxes(seg, H, 0.15f, box, p.door < 0 ? 0.5f : p.door);
            }
        }

        static void WallSegmentBoxes(Seg s, float H, float T, Func<string, Vector3, Vector3, GameObject> box, float doorT = 0.5f)
        {
            const float doorW = 1.0f, doorH = 2.2f, winW = 1.2f, winH = 1.2f, winSill = 1.0f;
            Vector3 Along(float len) => s.alongX ? new Vector3(len, 0, 0) : new Vector3(0, 0, len);
            Vector3 Size(float len, float h) => s.alongX ? new Vector3(len, h, T) : new Vector3(T, h, len);
            string nm = $"wall_v{s.volume}_{s.side}{s.index}_f{s.floor}"; var c = s.center; float L = s.length;
            if (s.opening == null) { box(nm, c + Vector3.up * H / 2, Size(L + T, H)); return; }
            if (s.opening.type == "none") return;
            bool win = s.opening.type == "window"; float ow = win ? winW : doorW;
            float offset = (doorT - 0.5f) * L;
            var dc = c + Along(offset);
            float legL = (L / 2 + offset) - ow / 2, legR = (L / 2 - offset) - ow / 2;
            if (legL > 0.05f) box(nm + "_L", c - Along(L / 2) + Along(legL / 2) + Vector3.up * H / 2, Size(legL + (s.side == "P" ? 0 : T / 2), H));
            if (legR > 0.05f) box(nm + "_R", c + Along(L / 2) - Along(legR / 2) + Vector3.up * H / 2, Size(legR + (s.side == "P" ? 0 : T / 2), H));
            if (win)
            {
                box(nm + "_sill", dc + Vector3.up * winSill / 2, Size(ow, winSill));
                float topH = H - winSill - winH; box(nm + "_top", dc + Vector3.up * (H - topH / 2), Size(ow, topH));
            }
            else { float lint = H - doorH; box(nm + "_lintel", dc + Vector3.up * (H - lint / 2), Size(ow, lint)); }
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
                var inst = Common.Spawn(asset, g, asset.name + "_" + ok);
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
            if (!string.IsNullOrEmpty(path)) Debug.Log(BuildFromJson(System.IO.File.ReadAllText(path)));
        }
    }
}
