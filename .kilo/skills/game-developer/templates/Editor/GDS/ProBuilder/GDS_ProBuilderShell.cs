// GDS ProBuilder shell — compiled only when com.unity.probuilder is installed (asmdef define constraint).
// Builds rooms / buildings / towers / stairs as real ProBuilder meshes from C#, so the LLM never edits face indices.
// Registered into LevelBuilder.ProBuilderShell at load. Extra helpers callable from execute_code:
//   GDS.PB.Room(new Vector3(0,0,0), 8, 3, 6, "S:1", material)   // w,h,d in metres; door on south wall segment 1
//   GDS.PB.Tower(center, radius, height, sides)
//   GDS.PB.Stairs(pos, width, height, depth, steps, rotY)
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.ProBuilder;
using UnityEngine.ProBuilder.MeshOperations;

namespace GDS
{
    [InitializeOnLoad]
    public static class PB
    {
        static PB() { LevelBuilder.ProBuilderShell = Shell; }

        static Material LoadMat(string path) => string.IsNullOrEmpty(path) ? null : AssetDatabase.LoadAssetAtPath<Material>(path);

        public static GameObject Box(string name, Vector3 center, Vector3 size, Transform parent, Material mat = null)
        {
            var pb = ShapeGenerator.GenerateCube(PivotLocation.Center, size);
            var go = pb.gameObject; go.name = name;
            if (parent != null) go.transform.SetParent(parent, false);
            go.transform.position = center;
            Finish(pb, mat);
            return go;
        }

        static void Finish(ProBuilderMesh pb, Material mat)
        {
            pb.ToMesh(); pb.Refresh();
            var mr = pb.GetComponent<MeshRenderer>();
            if (mr != null) mr.sharedMaterial = mat != null ? mat : Common.DefaultShellMaterial();
            var mc = pb.GetComponent<MeshCollider>(); if (mc == null) mc = pb.gameObject.AddComponent<MeshCollider>();
            mc.sharedMesh = pb.GetComponent<MeshFilter>().sharedMesh;
            GameObjectUtility.SetStaticEditorFlags(pb.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.ContributeGI | StaticEditorFlags.OccluderStatic);
            Undo.RegisterCreatedObjectUndo(pb.gameObject, "GDS ProBuilder");
        }

        /// <summary>LevelBuilder hook: slabs + segmented walls (door/window gaps without CSG) + partitions + roofs (flat, or gable per volume).</summary>
        public static int Shell(LevelBuilder.Blueprint bp, List<LevelBuilder.Volume> vols, List<LevelBuilder.Seg> segs, Transform shell, LevelBuilder.Result res)
        {
            var mat = LoadMat(bp.material); if (mat == null) mat = Common.PaletteMaterial(1, new Color(0.80f, 0.74f, 0.62f), "Wall");
            var roofMat = Common.PaletteMaterial(2, new Color(0.48f, 0.24f, 0.18f), "Roof");
            int c = 0;
            GameObject B(string n, Vector3 center, Vector3 size) { c++; return Box(n, center, size, shell, n.StartsWith("roof") ? roofMat : mat); }
            // flat roofs / slabs / walls come from the shared box layout; gable volumes get their flat roof replaced below
            var gableVols = new HashSet<int>();
            for (int i = 0; i < vols.Count; i++) if ((string.IsNullOrEmpty(vols[i].roof) ? bp.roof : vols[i].roof).ToLowerInvariant() == "gable") { gableVols.Add(i); vols[i].roof = "none"; }
            LevelBuilder.ShellBoxes(bp, vols, segs, B);
            foreach (int vi in gableVols)
            {
                var v = vols[vi]; v.roof = "gable"; float M = bp.module, T = bp.wallThickness;
                float W = v.cellsX * M, D = v.cellsZ * M; var o = bp.origin.V;
                var ridgeBase = o + new Vector3(v.x + W / 2, v.floors * bp.wallHeight, v.z + D / 2);
                if (W >= D) Gable(ridgeBase, W + T + 0.6f, D + T + 0.6f, D * 0.32f, true, shell, mat, roofMat, ref c);
                else Gable(ridgeBase, W + T + 0.6f, D + T + 0.6f, W * 0.32f, false, shell, mat, roofMat, ref c);
            }
            return c;
        }

        /// <summary>Single room: w × h × d metres, walls 4 m module, openings "S:1,N:0:window".</summary>
        public static string Room(Vector3 origin, float w, float h, float d, string openings = "", string materialPath = null, string name = "Room", float module = 4f)
        {
            var bp = new LevelBuilder.Blueprint { name = name, mode = "probuilder", origin = new LevelBuilder.V3 { x = origin.x, y = origin.y, z = origin.z }, module = module, wallHeight = h, cellsX = Mathf.Max(1, Mathf.RoundToInt(w / module)), cellsZ = Mathf.Max(1, Mathf.RoundToInt(d / module)), material = materialPath, roof = "flat" };
            foreach (var tok in (openings ?? "").Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries))
            {
                var p = tok.Trim().Split(':');
                bp.openings.Add(new LevelBuilder.Opening { side = p[0], index = p.Length > 1 ? int.Parse(p[1]) : 0, type = p.Length > 2 ? p[2] : "door" });
            }
            return JsonUtility.ToJson(LevelBuilder.Build(bp), true);
        }

        public static GameObject Tower(Vector3 baseCenter, float radius, float height, int sides = 8, string materialPath = null, Transform parent = null, bool hollow = true, float wall = 0.3f)
        {
            var pts = new List<Vector3>();
            for (int i = 0; i < sides; i++) { float a = i * Mathf.PI * 2f / sides; pts.Add(new Vector3(Mathf.Cos(a) * radius, 0, Mathf.Sin(a) * radius)); }
            var pb = ProBuilderMesh.Create();
            pb.gameObject.name = "Tower";
            pb.CreateShapeFromPolygon(pts, height, false);
            pb.transform.position = baseCenter; if (parent) pb.transform.SetParent(parent, true);
            Finish(pb, LoadMat(materialPath));
            if (hollow)
            {
                // inner void as a second (flipped) prism so the player can stand inside; simple and CSG-free
                var inner = new List<Vector3>();
                float r2 = Mathf.Max(0.5f, radius - wall);
                for (int i = 0; i < sides; i++) { float a = i * Mathf.PI * 2f / sides; inner.Add(new Vector3(Mathf.Cos(a) * r2, 0, Mathf.Sin(a) * r2)); }
                var pbi = ProBuilderMesh.Create(); pbi.gameObject.name = "Tower_Inner";
                pbi.CreateShapeFromPolygon(inner, height - 0.2f, true);
                pbi.transform.position = baseCenter + Vector3.up * 0.2f; pbi.transform.SetParent(pb.transform, true);
                Finish(pbi, LoadMat(materialPath));
            }
            return pb.gameObject;
        }

        public static GameObject Stairs(Vector3 pos, float width, float height, float depth, int steps = 8, float rotY = 0, string materialPath = null, Transform parent = null)
        {
            var pb = ShapeGenerator.GenerateStair(PivotLocation.FirstVertex, new Vector3(width, height, depth), steps, true);
            pb.gameObject.name = "Stairs";
            pb.transform.position = pos; pb.transform.rotation = Quaternion.Euler(0, rotY, 0);
            if (parent) pb.transform.SetParent(parent, true);
            Finish(pb, LoadMat(materialPath));
            return pb.gameObject;
        }

        public static GameObject Arch(Vector3 pos, float radius, float width, float depth, float rotY = 0, string materialPath = null, Transform parent = null)
        {
            var pb = ShapeGenerator.GenerateArch(PivotLocation.Center, 180f, radius, width, depth, 8, true, true, true, true, true);
            pb.gameObject.name = "Arch";
            pb.transform.position = pos; pb.transform.rotation = Quaternion.Euler(0, rotY, 0);
            if (parent) pb.transform.SetParent(parent, true);
            Finish(pb, LoadMat(materialPath));
            return pb.gameObject;
        }

        static void Gable(Vector3 ridgeBase, float w, float d, float rise, bool ridgeAlongX, Transform parent, Material mat, Material roofMat, ref int c)
        {
            // two sloped slabs meeting at the ridge + two triangular gable ends
            float span = ridgeAlongX ? d : w; float len = ridgeAlongX ? w : d;
            float half = span / 2f; float slope = Mathf.Sqrt(half * half + rise * rise); float ang = Mathf.Atan2(rise, half) * Mathf.Rad2Deg;
            foreach (var s in new[] { -1f, 1f })
            {
                var pb = ShapeGenerator.GenerateCube(PivotLocation.Center, ridgeAlongX ? new Vector3(len, 0.2f, slope) : new Vector3(slope, 0.2f, len));
                pb.gameObject.name = "roof_slope"; pb.transform.SetParent(parent, false);
                pb.transform.position = ridgeBase + new Vector3(ridgeAlongX ? 0 : s * half / 2f, rise / 2f + 0.1f, ridgeAlongX ? s * half / 2f : 0);
                pb.transform.rotation = ridgeAlongX ? Quaternion.Euler(s * ang, 0, 0) : Quaternion.Euler(0, 0, -s * ang);   // Unity is left-handed: +X rotation lowers +Z
                Finish(pb, roofMat); c++;
            }
            foreach (var s in new[] { -1f, 1f })
            {
                var pts = new List<Vector3>();
                if (ridgeAlongX) { float gx = ridgeBase.x + s * (len / 2f - 0.3f); pts.Add(new Vector3(gx, ridgeBase.y, ridgeBase.z - half + 0.3f)); pts.Add(new Vector3(gx, ridgeBase.y, ridgeBase.z + half - 0.3f)); pts.Add(new Vector3(gx, ridgeBase.y + rise, ridgeBase.z)); }
                else { float gz = ridgeBase.z + s * (len / 2f - 0.3f); pts.Add(new Vector3(ridgeBase.x - half + 0.3f, ridgeBase.y, gz)); pts.Add(new Vector3(ridgeBase.x + half - 0.3f, ridgeBase.y, gz)); pts.Add(new Vector3(ridgeBase.x, ridgeBase.y + rise, gz)); }
                var pb = ProBuilderMesh.Create(); pb.gameObject.name = "gable_end";
                // CreateShapeFromPolygon extrudes along the polygon normal; build the triangle in local space and extrude 0.2
                var local = pts.Select(p => p - pts[0]).ToList();
                pb.CreateShapeFromPolygon(local, 0.2f, false);
                pb.transform.position = pts[0]; pb.transform.SetParent(parent, true);
                Finish(pb, mat); c++;
            }
        }
    }
}
