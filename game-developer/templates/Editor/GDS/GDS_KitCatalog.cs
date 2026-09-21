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
            public string root; public int count; public string suggestedModule; public string notes;
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
                    cat.entries.Add(e);
                    UnityEngine.Object.DestroyImmediate(inst);
                }
            }
            finally { UnityEngine.Object.DestroyImmediate(temp); }

            cat.count = cat.entries.Count;
            var floors = cat.entries.Where(x => x.role == "floor" && x.sizeX > 0.2f).Select(x => Mathf.Max(x.sizeX, x.sizeZ)).ToList();
            var walls = cat.entries.Where(x => x.role == "wall" && x.sizeX > 0.2f).Select(x => Mathf.Max(x.sizeX, x.sizeZ)).ToList();
            float module = floors.Count > 0 ? Median(floors) : walls.Count > 0 ? Median(walls) : 0f;
            cat.suggestedModule = module > 0 ? module.ToString("F2") : "unknown";
            var doors = cat.entries.Where(x => x.role == "wallDoor").ToList();
            float doorH = doors.Count > 0 ? doors.Max(d => d.sizeY) : 0f;
            cat.notes = doorH > 0 && (doorH < 1.5f || doorH > 4.5f)
                ? $"door piece height {doorH:F2} m — kit is not in metres, run SetImportScale(folder, {(2.4f / doorH):F3})"
                : "scale looks metric";
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

        /// <summary>One import scale for a whole kit folder (never per piece).</summary>
        public static string SetImportScale(string folder, float scale, bool generateColliders = false)
        {
            int n = 0;
            foreach (var g in AssetDatabase.FindAssets("t:Model", new[] { folder }))
            {
                var p = AssetDatabase.GUIDToAssetPath(g);
                if (AssetImporter.GetAtPath(p) is ModelImporter mi)
                {
                    mi.useFileScale = false; mi.globalScale = scale; mi.addCollider = generateColliders;
                    mi.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
                    mi.SaveAndReimport(); n++;
                }
            }
            return $"{{\"reimported\":{n},\"scale\":{scale}}}";
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
