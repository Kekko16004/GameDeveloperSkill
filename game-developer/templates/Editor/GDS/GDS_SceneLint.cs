// GDS SceneLint — deterministic scene QA. Replaces "the parent looks at the screenshot".
// Detects: buried / floating props, missing colliders, pink (error) materials, non-URP shaders,
// empty meshes, objects far from origin, missing ground hit, duplicated / interpenetrating walls (overlappingWalls),
// duplicated / coplanar floor, ceiling and ground slabs (overlappingFloors).
// Usage (execute_code):   return GDS.SceneLint.RunJson();            // report only
//                         return GDS.SceneLint.RunJson(autoFix:true); // snap to ground + add box colliders
// Gate rule: issues == 0 (after autoFix, re-run report and require 0). overlappingWalls / overlappingFloors have no auto-fix:
// fix the blueprint (or omit / wallOwner) and rebuild — LevelBuilder shares wall lines and clips slabs between blueprints.
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
            public int buried, floating, noGround, noCollider, pinkMaterial, nonUrpShader, emptyMesh, outOfBounds, overlappingWalls, overlappingFloors;
            public List<Issue> list = new List<Issue>();
        }

        // Environment shells (ground, ProBuilder rooms, walls) are not props: skip their ground test.
        public static string EnvRegex = @"(?i)^(ground|floor|terrain|slab|env_|room|wall|ceiling|roof|corner|stair|ramp|platform|road|plaza|pb_|probuilder|building_shell|gable|partition|global_volume|directional|light|camera|player|main camera|eventsystem|ui|hud|audiomanager|navmesh|spawn|trigger|volume|attach_|water|chunk_|voxelworld|cave|dungeon)";

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

                bool deco = go.name.StartsWith("deco_", StringComparison.OrdinalIgnoreCase);   // walk-through dressing (grass, flowers): ground check yes, collider no
                if (!deco && go.GetComponentInChildren<Collider>(true) == null && go.GetComponentInChildren<CharacterController>(true) == null)
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

            CheckOverlappingWalls(rep);
            CheckOverlappingFloors(rep);

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

        // ---------------- overlappingWalls: one wall per line ----------------
        // Two wall pieces (GDS builds, ProBuilder shells, kit walls, collision-only walls) that are parallel, interpenetrate in
        // thickness (centre-lines closer than the mean thickness), overlap > 50% of the shorter one's length and > 50% of the
        // lower one's height = the same wall built twice (z-fighting, doubled thickness, doors to align twice).
        // Corner contacts, touching faces and wainscot panels are not reported. No auto-fix: disabling one copy would drop that
        // side's doors/windows — rebuild the blueprints (LevelBuilder resolves shared walls) or set "omit"/"wallOwner".
        public static string WallRegex = @"(?i)wall|partition";

        class WallBox { public GameObject go; public string path; public Bounds b; public bool alongX; public float thick, len, perp, a0, a1; }

        static bool WallBounds(GameObject go, out Bounds b)
        {
            b = new Bounds(); bool any = false;
            foreach (var r in go.GetComponentsInChildren<Renderer>(false))
            {
                if (!r.enabled || !(r is MeshRenderer)) continue;
                if (!any) { b = r.bounds; any = true; } else b.Encapsulate(r.bounds);
            }
            if (any) return true;
            foreach (var c in go.GetComponentsInChildren<Collider>(false))   // invisible collision walls
            {
                if (!c.enabled || c.isTrigger) continue;
                if (!any) { b = c.bounds; any = true; } else b.Encapsulate(c.bounds);
            }
            return any;
        }

        static void CollectWalls(Transform t, Regex re, List<WallBox> outList)
        {
            var go = t.gameObject; if (!go.activeInHierarchy) return;
            if (go.name.IndexOf("wainscot", StringComparison.OrdinalIgnoreCase) >= 0) return;
            bool candidate = re.IsMatch(go.name) || go.GetComponent("ProBuilderMesh") != null;
            if (candidate && WallBounds(go, out var b))
            {
                var s = b.size; float thick = Mathf.Min(s.x, s.z), len = Mathf.Max(s.x, s.z);
                // wall-like: thin horizontally, long, not a slab; a container ("Walls", a whole room) is not → look at its children
                if (thick <= 0.8f && len >= 0.3f && len >= 1.5f * thick && s.y >= 0.3f)
                {
                    bool ax = s.x >= s.z;
                    outList.Add(new WallBox { go = go, path = Common.HierarchyPath(t), b = b, alongX = ax, thick = thick, len = len,
                        perp = ax ? b.center.z : b.center.x, a0 = ax ? b.min.x : b.min.z, a1 = ax ? b.max.x : b.max.z });
                    return;
                }
            }
            for (int i = 0; i < t.childCount; i++) CollectWalls(t.GetChild(i), re, outList);
        }

        static void CheckOverlappingWalls(Report rep)
        {
            Physics.SyncTransforms();
            var walls = new List<WallBox>(); var re = new Regex(WallRegex);
            foreach (var root in EditorSceneManager.GetActiveScene().GetRootGameObjects()) CollectWalls(root.transform, re, walls);
            foreach (var axis in new[] { true, false })
            {
                var w = walls.Where(x => x.alongX == axis).OrderBy(x => x.perp).ToList();
                for (int i = 0; i < w.Count; i++)
                    for (int j = i + 1; j < w.Count; j++)
                    {
                        var A = w[i]; var B = w[j];
                        if (B.perp - A.perp > 1f) break;                                            // sorted: farther lines cannot touch
                        if (B.perp - A.perp >= (A.thick + B.thick) / 2f - 0.01f) continue;             // touching / separate faces
                        if (A.go.transform.IsChildOf(B.go.transform) || B.go.transform.IsChildOf(A.go.transform)) continue;
                        float ov = Mathf.Min(A.a1, B.a1) - Mathf.Max(A.a0, B.a0);
                        if (ov <= 0.5f * Mathf.Min(A.len, B.len)) continue;                           // corner / end contact
                        float ovY = Mathf.Min(A.b.max.y, B.b.max.y) - Mathf.Max(A.b.min.y, B.b.min.y);
                        if (ovY <= 0.5f * Mathf.Min(A.b.size.y, B.b.size.y)) continue;                // lintel over a lower wall, other storey
                        Add(rep, "overlappingWalls", A.path + " <-> " + B.path, ov,
                            "same wall built twice: rebuild both blueprints (LevelBuilder shares the line: one owner, openings of both sides) or add \"omit\"/\"wallOwner\"; hand-made walls: delete one");
                        rep.overlappingWalls++;
                    }
            }
        }

        // ---------------- overlappingFloors: one slab per surface ----------------
        // Two horizontal slabs (floor / ceiling / roof / ground: renderers named slab_ floor_ ground roof ceiling terrain lawn plaza
        // road, or kit tiles under such a parent) whose TOP faces or BOTTOM faces are coplanar (±5 mm) and whose XZ overlap covers
        // > 50 % of the smaller one = z-fighting surface (two rooms' floors on the same spot, a Ground cube coplanar with a room
        // floor, two ceilings). A slab lying ON another (rug, dais, a floor 2 cm above the ground) is not reported. No auto-fix:
        // rebuild the blueprints (LevelBuilder clips slabs between blueprints and lowers a coplanar ground by groundGap).
        public static string FloorRegex = @"(?i)^(slab|floor|ground|roof|ceiling|terrain|lawn|grass|plaza|road)";

        class FloorBox { public string path; public Transform t; public Bounds b; }

        static void CheckOverlappingFloors(Report rep, float coplanarTol = 0.005f)
        {
            var re = new Regex(FloorRegex); var floors = new List<FloorBox>();
            foreach (var root in EditorSceneManager.GetActiveScene().GetRootGameObjects())
                foreach (var r in root.GetComponentsInChildren<MeshRenderer>(false))
                {
                    if (!r.enabled) continue;
                    var t = r.transform; string n = t.name;
                    if (n.IndexOf("wainscot", StringComparison.OrdinalIgnoreCase) >= 0) continue;
                    if (!re.IsMatch(n) && !(t.parent != null && re.IsMatch(t.parent.name))) continue;   // kit tile: instance floor_i_j, mesh child
                    var b = r.bounds; var s = b.size;
                    if (s.y > 0.6f || s.x < 0.3f || s.z < 0.3f) continue;                                    // horizontal slabs only
                    floors.Add(new FloorBox { path = Common.HierarchyPath(t), t = t, b = b });
                }
            floors.Sort((x, y) => x.b.max.y.CompareTo(y.b.max.y));
            for (int i = 0; i < floors.Count; i++)
                for (int j = i + 1; j < floors.Count; j++)
                {
                    var A = floors[i]; var B = floors[j];
                    if (B.b.max.y - A.b.max.y > 0.6f + coplanarTol) break;                              // sorted by top: bottoms can't match either
                    bool top = Mathf.Abs(A.b.max.y - B.b.max.y) <= coplanarTol, bottom = Mathf.Abs(A.b.min.y - B.b.min.y) <= coplanarTol;
                    if (!top && !bottom) continue;
                    if (A.t.IsChildOf(B.t) || B.t.IsChildOf(A.t)) continue;
                    float ox = Mathf.Min(A.b.max.x, B.b.max.x) - Mathf.Max(A.b.min.x, B.b.min.x), oz = Mathf.Min(A.b.max.z, B.b.max.z) - Mathf.Max(A.b.min.z, B.b.min.z);
                    if (ox <= 0f || oz <= 0f) continue;
                    float area = ox * oz, smaller = Mathf.Min(A.b.size.x * A.b.size.z, B.b.size.x * B.b.size.z);
                    if (area <= 0.5f * smaller) continue;                                                // edge / eave overlap
                    Add(rep, "overlappingFloors", A.path + " <-> " + B.path, area,
                        (top ? "coplanar top faces" : "coplanar bottom faces") + ": rebuild the blueprints (LevelBuilder clips slabs between blueprints, owner = wallOwner/taller/name; \"omit\":[\"floor\"|\"roof\"]) or lower the ground 2 cm under the floors (builder groundGap); hand-made slabs: delete one");
                    rep.overlappingFloors++;
                }
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
