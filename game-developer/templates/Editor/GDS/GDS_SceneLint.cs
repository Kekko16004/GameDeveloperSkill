// GDS SceneLint — deterministic scene QA. Replaces "the parent looks at the screenshot".
// Detects: buried / floating props, missing colliders, pink (error) materials, non-URP shaders,
// empty meshes, objects far from origin, missing ground hit.
// Usage (execute_code):   return GDS.SceneLint.RunJson();            // report only
//                         return GDS.SceneLint.RunJson(autoFix:true); // snap to ground + add box colliders
// Gate rule: issues == 0 (after autoFix, re-run report and require 0).
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace GDS
{
    public static class SceneLint
    {
        [Serializable] public class Issue { public string type; public string obj; public float value; public string fix; public bool isFixed; }
        [Serializable] public class Report
        {
            public string scene; public int checkedObjects; public int issues;
            public int buried, floating, noGround, noCollider, pinkMaterial, nonUrpShader, emptyMesh, outOfBounds;
            public List<Issue> list = new List<Issue>();
        }

        // Environment shells (ground, ProBuilder rooms, walls) are not props: skip their ground test.
        public static string EnvRegex = @"(?i)^(ground|floor|terrain|slab|env_|room|wall|ceiling|roof|corner|stair|ramp|platform|road|plaza|pb_|probuilder|building_shell|gable|partition|global_volume|directional|light|camera|player|main camera|eventsystem|ui|hud|audiomanager|navmesh|spawn|trigger|volume)";

        public static Report Run(float buriedTol = 0.02f, float floatTol = 0.05f, float worldRadius = 500f, bool autoFix = false)
        {
            var rep = new Report { scene = EditorSceneManager.GetActiveScene().name };
            var candidates = new List<GameObject>();
            foreach (var root in EditorSceneManager.GetActiveScene().GetRootGameObjects()) Collect(root.transform, candidates);
            rep.checkedObjects = candidates.Count;

            bool urp = GraphicsSettings.currentRenderPipeline != null;
            var envRe = new Regex(EnvRegex);
            var reimportModels = new HashSet<string>();

            foreach (var go in candidates)
            {
                string path = Common.HierarchyPath(go.transform);
                bool isEnv = envRe.IsMatch(go.name) || go.isStatic && go.GetComponent<Collider>() != null && Common.TryGetBounds(go, out var eb) && (eb.size.x >= 8f || eb.size.z >= 8f);

                // materials
                foreach (var r in go.GetComponentsInChildren<Renderer>(true))
                {
                    if (r is ParticleSystemRenderer) continue;
                    foreach (var m in r.sharedMaterials)
                    {
                        if (m == null || m.shader == null || m.shader.name.Contains("InternalErrorShader"))
                        { Add(rep, "pinkMaterial", path + " :: " + r.name, 0, "assign URP/Lit material"); rep.pinkMaterial++; break; }
                        if (urp && IsNonUrp(m))
                        {
                            var iss = Add(rep, "nonUrpShader", path + " :: " + m.name, 0, "convert to URP/Lit (autoFix: reimport model / swap shader / replace package material)"); rep.nonUrpShader++;
                            if (autoFix) iss.isFixed = FixNonUrp(r, m, reimportModels);
                            break;
                        }
                    }
                }
                foreach (var mf in go.GetComponentsInChildren<MeshFilter>(true))
                    if (mf.sharedMesh == null) { Add(rep, "emptyMesh", path + " :: " + mf.name, 0, "delete or reimport"); rep.emptyMesh++; }

                if (!Common.TryGetBounds(go, out var b)) continue;

                if (b.center.magnitude > worldRadius)
                { Add(rep, "outOfBounds", path, b.center.magnitude, "move inside the playable area"); rep.outOfBounds++; }

                if (go.GetComponentInChildren<Collider>(true) == null && go.GetComponentInChildren<CharacterController>(true) == null)
                {
                    var iss = Add(rep, "noCollider", path, 0, "add BoxCollider");
                    rep.noCollider++;
                    if (autoFix) { Undo.RecordObject(go, "GDS collider"); iss.isFixed = Common.EnsureCollider(go); }
                }

                if (isEnv) continue;

                if (!Common.GroundBelow(go, b, out float gy, out string hitName))
                { Add(rep, "noGround", path, b.min.y, "nothing with a collider under this object (missing ground collider or object outside the level)"); rep.noGround++; continue; }

                float delta = b.min.y - gy;
                if (delta < -buriedTol)
                {
                    var iss = Add(rep, "buried", path, delta, $"raise by {-delta:F3} m (surface: {hitName})"); rep.buried++;
                    if (autoFix) { Undo.RecordObject(go.transform, "GDS snap"); go.transform.position += Vector3.up * -delta; iss.isFixed = true; }
                }
                else if (delta > floatTol)
                {
                    var iss = Add(rep, "floating", path, delta, $"lower by {delta:F3} m (surface: {hitName})"); rep.floating++;
                    if (autoFix) { Undo.RecordObject(go.transform, "GDS snap"); go.transform.position -= Vector3.up * delta; iss.isFixed = true; }
                }
            }

            if (autoFix && reimportModels.Count > 0)
            {
                foreach (var mp in reimportModels) AssetDatabase.ImportAsset(mp, ImportAssetOptions.ForceUpdate);
                AssetDatabase.SaveAssets();
            }
            rep.issues = rep.list.Count(i => !i.isFixed);
            if (autoFix) EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
            return rep;
        }

        static bool IsNonUrp(Material m)
        {
            var n = m.shader.name;
            return n == "Standard" || n == "Standard (Specular setup)" || n.StartsWith("Legacy Shaders/") || n.StartsWith("Mobile/") || n.StartsWith("Nature/") || n.StartsWith("Particles/") || n == "Unlit/Color" || n == "Unlit/Texture";
        }

        /// <summary>Convert one non-URP material: editable .mat → swap shader in place; model sub-asset → reimport under URP; package/read-only → replace slot with the GDS default material.</summary>
        static bool FixNonUrp(Renderer r, Material m, HashSet<string> reimportModels)
        {
            var path = AssetDatabase.GetAssetPath(m);
            var lit = Shader.Find("Universal Render Pipeline/Lit"); if (lit == null) return false;
            if (!string.IsNullOrEmpty(path) && AssetDatabase.IsSubAsset(m) && !path.StartsWith("Packages/"))
            { reimportModels.Add(path); return true; }                       // FBX/OBJ imported before URP was active
            if (!string.IsNullOrEmpty(path) && !path.StartsWith("Packages/") && path.EndsWith(".mat"))
            {
                var col = m.HasProperty("_Color") ? m.GetColor("_Color") : Color.white; var tex = m.HasProperty("_MainTex") ? m.GetTexture("_MainTex") : null;
                float smooth = m.HasProperty("_Glossiness") ? m.GetFloat("_Glossiness") : 0.3f;
                Undo.RecordObject(m, "GDS URP convert"); m.shader = lit;
                m.SetColor("_BaseColor", col); if (tex != null) m.SetTexture("_BaseMap", tex); m.SetFloat("_Smoothness", smooth);
                EditorUtility.SetDirty(m); return true;
            }
            // package material (e.g. ProBuilder default) or scene-only material: replace the slot
            var mats = r.sharedMaterials; bool any = false;
            for (int i = 0; i < mats.Length; i++) if (mats[i] == m) { mats[i] = Common.DefaultShellMaterial(); any = true; }
            if (any) { Undo.RecordObject(r, "GDS URP material"); r.sharedMaterials = mats; }
            return any;
        }

        public static string RunJson(float buriedTol = 0.02f, float floatTol = 0.05f, float worldRadius = 500f, bool autoFix = false, string writeTo = "docs/lint/scene-lint.json")
        {
            var rep = Run(buriedTol, floatTol, worldRadius, autoFix);
            var json = JsonUtility.ToJson(rep, true);
            if (!string.IsNullOrEmpty(writeTo)) Common.WriteProjectFile(writeTo, json);
            Debug.Log($"[GDS SceneLint] {rep.issues} open issues (checked {rep.checkedObjects})");
            return json;
        }

        /// <summary>Snap one object (by hierarchy name) to the surface under it.</summary>
        public static string SnapToGround(string objectName)
        {
            var go = GameObject.Find(objectName);
            if (go == null) return "{\"error\":\"not found\"}";
            if (!Common.TryGetBounds(go, out var b)) return "{\"error\":\"no renderer\"}";
            if (!Common.GroundBelow(go, b, out float gy, out string hit)) return "{\"error\":\"no ground hit\"}";
            Undo.RecordObject(go.transform, "GDS snap");
            go.transform.position += Vector3.up * (gy - b.min.y);
            return $"{{\"snapped\":\"{Common.Esc(objectName)}\",\"surface\":\"{Common.Esc(hit)}\",\"y\":{go.transform.position.y:F4}}}";
        }

        static Issue Add(Report r, string type, string obj, float value, string fix)
        {
            var i = new Issue { type = type, obj = obj, value = value, fix = fix };
            r.list.Add(i); return i;
        }

        // A candidate is a prefab instance root, or the first object down a branch that owns a renderer.
        static void Collect(Transform t, List<GameObject> outList)
        {
            var go = t.gameObject;
            bool isPrefabRoot = PrefabUtility.IsAnyPrefabInstanceRoot(go);
            bool hasRenderer = go.GetComponent<MeshRenderer>() != null || go.GetComponent<SkinnedMeshRenderer>() != null;
            if (isPrefabRoot || hasRenderer) { outList.Add(go); return; }
            for (int i = 0; i < t.childCount; i++) Collect(t.GetChild(i), outList);
        }

        [MenuItem("GDS/Scene Lint/Report (docs/lint/scene-lint.json)")]
        static void MenuReport() => RunJson();
        [MenuItem("GDS/Scene Lint/Auto-fix (snap + colliders)")]
        static void MenuFix() => RunJson(autoFix: true);
    }
}
