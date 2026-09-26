// GDS KitCatalog — measures every model in a kit folder so the agent never guesses sizes / pivots / roles.
// Output: art/kit-catalog.json (+ returned string). The LevelBuilder reads roles from this file.
// Usage (execute_code): return GDS.KitCatalog.BuildJson("Assets/_Game/Art/Kits/kenney/kenney_castle-kit");
//                       return GDS.KitCatalog.SetImportScale("Assets/_Game/Art/Kits/kenney", 1f);
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

namespace GDS
{
    public static class KitCatalog
    {
        [Serializable] public class Entry
        {
            public string path; public string name; public string role;
            public float sizeX, sizeY, sizeZ;          // world metres at import scale
            public float pivotBottomOffset;             // bounds.min.y relative to pivot (0 = pivot on the ground)
            public float pivotCenterOffsetX, pivotCenterOffsetZ; // bounds.center xz relative to pivot
            public int tris; public bool hasCollider;
        }
        [Serializable] public class Catalog
        {
            public string root; public int count; public string suggestedModule; public float suggestedScale = 1f; public string notes;
            public List<string> materials = new List<string>();   // embedded material names: targets for gds_recolor
            public List<Entry> entries = new List<Entry>();
        }

        static readonly (string role, string re)[] RoleRules =
        {
            ("wallDoor",   @"(?i)door(way)?|gate|entrance|arch"),
            ("wallWindow", @"(?i)window"),
            ("stair",      @"(?i)stair|steps"),
            ("corner",     @"(?i)corner|column|pillar|post"),
            ("roof",       @"(?i)roof|gable"),
            ("floor",      @"(?i)floor|tile|ground|plate|path|road"),
            ("wall",       @"(?i)wall|fence|rail"),
            ("tree",       @"(?i)tree|bush|foliage|plant|grass|flower"),
            ("rock",       @"(?i)rock|stone|boulder|cliff"),
            ("char",       @"(?i)character|char_|knight|skeleton|zombie|survivor|rogue|mage|barbarian|npc"),
            ("prop",       @"(?i).*"),
        };

        public static Catalog Build(string folder)
        {
            var cat = new Catalog { root = folder };
            if (!AssetDatabase.IsValidFolder(folder)) { cat.notes = "folder not found"; return cat; }
            var guids = AssetDatabase.FindAssets("t:Model t:Prefab", new[] { folder });
            var seen = new HashSet<string>();
            var temp = new GameObject("GDS_CatalogTemp");
            try
            {
                foreach (var g in guids)
                {
                    var p = AssetDatabase.GUIDToAssetPath(g);
                    var ext = Path.GetExtension(p).ToLowerInvariant();
                    if (ext != ".fbx" && ext != ".glb" && ext != ".gltf" && ext != ".obj" && ext != ".prefab") continue;
                    var name = Path.GetFileNameWithoutExtension(p);
                    if (!seen.Add(name)) continue; // FBX + OBJ + glTF variants of the same piece: keep the first
                    var asset = AssetDatabase.LoadAssetAtPath<GameObject>(p);
                    if (asset == null) continue;
                    var inst = UnityEngine.Object.Instantiate(asset, temp.transform);
                    inst.transform.localPosition = Vector3.zero; inst.transform.localRotation = Quaternion.identity;
                    var e = new Entry { path = p, name = name, role = GuessRole(name) };
                    if (Common.TryGetBounds(inst, out var b))
                    {
                        e.sizeX = R(b.size.x); e.sizeY = R(b.size.y); e.sizeZ = R(b.size.z);
                        e.pivotBottomOffset = R(b.min.y); e.pivotCenterOffsetX = R(b.center.x); e.pivotCenterOffsetZ = R(b.center.z);
                    }
                    e.tris = inst.GetComponentsInChildren<MeshFilter>(true).Where(m => m.sharedMesh != null).Sum(m => m.sharedMesh.triangles.Length / 3);
                    e.hasCollider = inst.GetComponentInChildren<Collider>(true) != null;
                    foreach (var r in inst.GetComponentsInChildren<Renderer>(true))
                        foreach (var m in r.sharedMaterials)
                            if (m != null && !cat.materials.Contains(m.name)) cat.materials.Add(m.name);
                    cat.entries.Add(e);
                    UnityEngine.Object.DestroyImmediate(inst);
                }
            }
            finally { UnityEngine.Object.DestroyImmediate(temp); }

            cat.count = cat.entries.Count;
            var floors = cat.entries.Where(x => x.role == "floor" && x.sizeX > 0.2f).Select(x => Mathf.Max(x.sizeX, x.sizeZ)).ToList();
            var walls = cat.entries.Where(x => x.role == "wall" && x.sizeX > 0.2f).Select(x => Mathf.Max(x.sizeX, x.sizeZ)).ToList();
            float module = floors.Count > 0 ? Median(floors) : walls.Count > 0 ? Median(walls) : 0f;
            cat.suggestedModule = module > 0 ? module.ToString("F2", System.Globalization.CultureInfo.InvariantCulture) : "unknown";
            // scale from several real-world references (median), so one odd piece (a 35 cm fence "gate") cannot decide it
            var byCat = new Dictionary<string, List<float>>();
            void Ref(string k, float v) { if (!byCat.ContainsKey(k)) byCat[k] = new List<float>(); byCat[k].Add(v); }
            foreach (var x in cat.entries)
            {
                var n = x.name.ToLowerInvariant(); float longSide = Mathf.Max(x.sizeX, x.sizeZ);
                if (n.Contains("door") && !n.Contains("frame") && x.sizeY > 0.05f) Ref("door", 2.2f / x.sizeY);
                else if ((n == "bed" || n.StartsWith("bed_") || n.StartsWith("bed")) && longSide > 0.05f) Ref("bed", 2.0f / longSide);
                else if (n.StartsWith("fence") && x.sizeY > 0.05f) Ref("fence", 1.1f / x.sizeY);
                else if ((n.StartsWith("chair") || n.Contains("_chair")) && x.sizeY > 0.05f) Ref("chair", 0.95f / x.sizeY);
                else if ((n.StartsWith("table") || n.Contains("_table")) && x.sizeY > 0.05f) Ref("table", 0.78f / x.sizeY);
                else if (x.role == "tree" && x.sizeY > 0.8f) Ref("tree", 6f / x.sizeY);
            }
            // one vote per category (70 trees must not outvote 1 door and 2 beds)
            var refs = byCat.Values.Select(v => Median(v)).ToList();
            int nRefs = byCat.Values.Sum(v => v.Count);
            float scale = refs.Count >= 2 ? Median(refs) : refs.Count == 1 && nRefs >= 3 ? refs[0] : 1f;
            bool metric = (refs.Count < 2 && nRefs < 3) || (scale > 0.7f && scale < 1.4f);
            cat.suggestedScale = metric ? 1f : R(scale);
            cat.notes = metric
                ? (nRefs < 3 ? "scale looks metric (few references to check)" : "scale looks metric")
                : string.Format(System.Globalization.CultureInfo.InvariantCulture,
                    "kit is not in metres ({0} reference categories: {2}; factor {1:F2}): run SetImportScale(folder, {1:F2}) once, then rebuild the catalog", refs.Count, scale, string.Join(",", byCat.Keys));
            return cat;
        }

        public static string BuildJson(string folder, string writeTo = "art/kit-catalog.json")
        {
            var cat = Build(folder);
            var json = JsonUtility.ToJson(cat, true);
            if (!string.IsNullOrEmpty(writeTo)) Common.WriteProjectFile(writeTo, json);
            Debug.Log($"[GDS KitCatalog] {cat.count} pieces in {folder}; module≈{cat.suggestedModule}; {cat.notes}");
            return json;
        }

        /// <summary>Multiply the import scale of a whole kit folder by `scale` (the catalog suggestedScale). Relative, so running it twice doubles: rebuild the catalog after each run.</summary>
        public static string SetImportScale(string folder, float scale, bool generateColliders = false)
        {
            int n = 0;
            // one batched import pass instead of one reimport per model (329 Kenney pieces: minutes → seconds)
            AssetDatabase.StartAssetEditing();
            try
            {
                foreach (var g in AssetDatabase.FindAssets("t:Model", new[] { folder }))
                {
                    var p = AssetDatabase.GUIDToAssetPath(g);
                    if (AssetImporter.GetAtPath(p) is ModelImporter mi)
                    {
                        mi.globalScale = mi.globalScale * scale; mi.addCollider = generateColliders;   // relative: the catalog factor is measured on the current import
                        mi.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
                        mi.SaveAndReimport(); n++;
                    }
                }
            }
            finally { AssetDatabase.StopAssetEditing(); }
            return string.Format(System.Globalization.CultureInfo.InvariantCulture, "{{\"reimported\":{0},\"scale\":{1}}}", n, scale);
        }

        public static string GuessRole(string name)
        {
            foreach (var (role, re) in RoleRules) if (Regex.IsMatch(name, re)) return role;
            return "prop";
        }

        static float R(float v) => Mathf.Round(v * 1000f) / 1000f;
        static float Median(List<float> v) { v.Sort(); return v[v.Count / 2]; }

        [MenuItem("GDS/Kit Catalog (selected folder)")]
        static void Menu()
        {
            var sel = Selection.activeObject != null ? AssetDatabase.GetAssetPath(Selection.activeObject) : Common.KitsRoot;
            if (!AssetDatabase.IsValidFolder(sel)) sel = Path.GetDirectoryName(sel).Replace('\\', '/');
            BuildJson(sel);
        }
    }
}
