// GDS — Game Developer Skill editor helpers. Shared utilities.
// Called from CoplayDev unity-mcp `execute_code`, from GDS/* menu items, or from `unity -executeMethod`.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace GDS
{
    public static class Common
    {
        public const string ArtRoot = "Assets/_Game/Art";
        public const string KitsRoot = "Assets/_Game/Art/Kits";
        public const string PrefabsRoot = "Assets/_Game/Prefabs";
        public const string SettingsRoot = "Assets/_Game/Settings";
        public const string MaterialsRoot = "Assets/_Game/Art/Materials";

        /// <summary>Combined world bounds of MeshRenderer + SkinnedMeshRenderer under go. False if none.</summary>
        public static bool TryGetBounds(GameObject go, out Bounds b)
        {
            b = new Bounds();
            bool any = false;
            foreach (var r in go.GetComponentsInChildren<Renderer>(true))
            {
                if (!(r is MeshRenderer) && !(r is SkinnedMeshRenderer)) continue;
                if (!any) { b = r.bounds; any = true; }
                else b.Encapsulate(r.bounds);
            }
            return any;
        }

        /// <summary>Raycast down from above the object's bounds, ignoring the object itself. Returns the surface Y.</summary>
        public static bool GroundBelow(GameObject go, Bounds b, out float groundY, out string hitName, float maxDist = 200f)
        {
            groundY = 0f; hitName = null;
            Physics.SyncTransforms();
            var origin = new Vector3(b.center.x, b.max.y + 0.5f, b.center.z);
            var hits = Physics.RaycastAll(origin, Vector3.down, maxDist + b.size.y + 1f, ~0, QueryTriggerInteraction.Ignore);
            RaycastHit best = default; bool found = false;
            foreach (var h in hits)
            {
                if (h.collider == null) continue;
                if (h.collider.transform == go.transform || h.collider.transform.IsChildOf(go.transform)) continue;
                if (!found || h.distance < best.distance) { best = h; found = true; }
            }
            if (!found) return false;
            groundY = best.point.y; hitName = best.collider.gameObject.name;
            return true;
        }

        public static void EnsureFolder(string assetPath)
        {
            if (AssetDatabase.IsValidFolder(assetPath)) return;
            var parts = assetPath.Split('/');
            string cur = parts[0];
            for (int i = 1; i < parts.Length; i++)
            {
                string next = cur + "/" + parts[i];
                if (!AssetDatabase.IsValidFolder(next)) AssetDatabase.CreateFolder(cur, parts[i]);
                cur = next;
            }
        }

        public static string ProjectDir => Directory.GetParent(Application.dataPath).FullName;

        public static void WriteProjectFile(string relPath, string content)
        {
            var full = Path.Combine(ProjectDir, relPath);
            Directory.CreateDirectory(Path.GetDirectoryName(full));
            File.WriteAllText(full, content);
        }

        public static string ReadProjectFile(string relPath)
        {
            var full = Path.Combine(ProjectDir, relPath);
            return File.Exists(full) ? File.ReadAllText(full) : null;
        }

        public static Color Hex(string hex, Color fallback)
        {
            if (string.IsNullOrEmpty(hex)) return fallback;
            return ColorUtility.TryParseHtmlString(hex.StartsWith("#") ? hex : "#" + hex, out var c) ? c : fallback;
        }

        public static string HierarchyPath(Transform t)
        {
            var s = t.name;
            while (t.parent != null) { t = t.parent; s = t.name + "/" + s; }
            return s;
        }

        /// <summary>Load a model/prefab asset by path; if only a file name is given, search under root.</summary>
        public static GameObject LoadModel(string pathOrName, string searchRoot = KitsRoot)
        {
            if (string.IsNullOrEmpty(pathOrName)) return null;
            var go = AssetDatabase.LoadAssetAtPath<GameObject>(pathOrName);
            if (go != null) return go;
            string name = Path.GetFileNameWithoutExtension(pathOrName);
            foreach (var guid in AssetDatabase.FindAssets(name, new[] { searchRoot }))
            {
                var p = AssetDatabase.GUIDToAssetPath(guid);
                if (!string.Equals(Path.GetFileNameWithoutExtension(p), name, StringComparison.OrdinalIgnoreCase)) continue;
                var ext = Path.GetExtension(p).ToLowerInvariant();
                if (ext == ".fbx" || ext == ".glb" || ext == ".gltf" || ext == ".obj" || ext == ".prefab")
                {
                    go = AssetDatabase.LoadAssetAtPath<GameObject>(p);
                    if (go != null) return go;
                }
            }
            return null;
        }

        public static GameObject Spawn(GameObject asset, Transform parent, string name = null)
        {
            GameObject inst;
            if (PrefabUtility.IsPartOfPrefabAsset(asset) || PrefabUtility.GetPrefabAssetType(asset) != PrefabAssetType.NotAPrefab)
                inst = (GameObject)PrefabUtility.InstantiatePrefab(asset);
            else
                inst = UnityEngine.Object.Instantiate(asset);
            if (inst == null) return null;
            if (parent != null) inst.transform.SetParent(parent, true);
            if (!string.IsNullOrEmpty(name)) inst.name = name;
            StripLightsAndCameras(inst);
            Undo.RegisterCreatedObjectUndo(inst, "GDS Spawn");
            return inst;
        }

        public static void StripLightsAndCameras(GameObject inst)
        {
            foreach (var l in inst.GetComponentsInChildren<Light>(true)) UnityEngine.Object.DestroyImmediate(l.gameObject.GetComponent<Light>());
            foreach (var c in inst.GetComponentsInChildren<Camera>(true)) UnityEngine.Object.DestroyImmediate(c.gameObject.GetComponent<Camera>());
        }

        /// <summary>Move the instance so that its bounds bottom-center sits exactly at target (pivot-agnostic placement).</summary>
        public static void AlignBottomCenter(GameObject inst, Vector3 target)
        {
            if (!TryGetBounds(inst, out var b)) { inst.transform.position = target; return; }
            var bottomCenter = new Vector3(b.center.x, b.min.y, b.center.z);
            inst.transform.position += target - bottomCenter;
        }

        /// <summary>Add a BoxCollider fitted to the renderer bounds if the object has no collider at all.</summary>
        public static bool EnsureCollider(GameObject inst, bool convexMesh = false, bool meshCollider = false)
        {
            if (inst.GetComponentInChildren<Collider>(true) != null) return false;
            if (convexMesh || meshCollider)
            {
                foreach (var mf in inst.GetComponentsInChildren<MeshFilter>(true))
                {
                    if (mf.sharedMesh == null) continue;
                    var mc = mf.gameObject.AddComponent<MeshCollider>();
                    mc.sharedMesh = mf.sharedMesh; mc.convex = convexMesh && !meshCollider;   // mesh = exact static collider (hero buildings)
                }
                return true;
            }
            if (!TryGetBounds(inst, out var b)) return false;
            var box = inst.AddComponent<BoxCollider>();
            var t = inst.transform;
            var localCenter = t.InverseTransformPoint(b.center);
            var ls = t.lossyScale;
            // approximate for axis-aligned / 90-degree rotations (the modular case)
            var rot = Quaternion.Inverse(t.rotation) * b.size;
            var size = new Vector3(Mathf.Abs(rot.x) / Mathf.Max(ls.x, 1e-4f), Mathf.Abs(rot.y) / Mathf.Max(ls.y, 1e-4f), Mathf.Abs(rot.z) / Mathf.Max(ls.z, 1e-4f));
            box.center = localCenter; box.size = size;
            return true;
        }

        public static Transform GetOrCreateGroup(string path)
        {
            Transform cur = null;
            foreach (var part in path.Split('/'))
            {
                Transform next = null;
                if (cur == null)
                {
                    var found = GameObject.Find(part);
                    if (found != null && found.transform.parent == null) next = found.transform;
                }
                else next = cur.Find(part);
                if (next == null)
                {
                    var go = new GameObject(part);
                    Undo.RegisterCreatedObjectUndo(go, "GDS Group");
                    if (cur != null) go.transform.SetParent(cur, false);
                    next = go.transform;
                }
                cur = next;
            }
            return cur;
        }

        /// <summary>Grey URP/Lit (or Standard when no SRP) material for shells built without an explicit material. Never pink.</summary>
        public static Material DefaultShellMaterial()
        {
            const string path = MaterialsRoot + "/Mat_Shell_Default.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            bool srp = UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline != null;
            if (m != null && m.shader != null && !m.shader.name.Contains("InternalErrorShader") && (!srp || m.shader.name.StartsWith("Universal Render Pipeline/"))) return m;
            if (m != null) AssetDatabase.DeleteAsset(path);   // pipeline changed since it was created: rebuild it
            var sh = srp ? Shader.Find("Universal Render Pipeline/Lit") : null;
            if (sh == null) sh = Shader.Find("Standard");
            if (sh == null) sh = Shader.Find("Universal Render Pipeline/Lit");
            m = new Material(sh);
            var grey = new Color(0.62f, 0.60f, 0.57f);
            if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", grey); else m.color = grey;
            if (m.HasProperty("_Smoothness")) m.SetFloat("_Smoothness", 0.15f);
            EnsureFolder(MaterialsRoot);
            AssetDatabase.CreateAsset(m, path);
            return m;
        }

        /// <summary>Mat_Palette_N from GDS.LookDev.ApplyPalette if it exists, else a generated URP/Lit material with the fallback color (never pink).</summary>
        public static Material PaletteMaterial(int index, Color fallback, string tag)
        {
            var pal = AssetDatabase.LoadAssetAtPath<Material>($"{MaterialsRoot}/Mat_Palette_{index}.mat");
            bool srp = UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline != null;
            if (pal != null && pal.shader != null && (!srp || pal.shader.name.StartsWith("Universal Render Pipeline/"))) return pal;
            string path = $"{MaterialsRoot}/Mat_Shell_{tag}.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m != null && m.shader != null && (!srp || m.shader.name.StartsWith("Universal Render Pipeline/"))) return m;
            if (m != null) AssetDatabase.DeleteAsset(path);
            var sh = srp ? Shader.Find("Universal Render Pipeline/Lit") : null; if (sh == null) sh = Shader.Find("Standard"); if (sh == null) sh = Shader.Find("Universal Render Pipeline/Lit");
            m = new Material(sh);
            if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", fallback); else m.color = fallback;
            if (m.HasProperty("_Smoothness")) m.SetFloat("_Smoothness", 0.15f);
            EnsureFolder(MaterialsRoot); AssetDatabase.CreateAsset(m, path);
            return m;
        }

        public static string Esc(string s) => s == null ? "" : s.Replace("\\", "\\\\").Replace("\"", "\\\"");
    }
}
