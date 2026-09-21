// GDS Village — world layout generator: terrain, roads, plaza, lots with buildings facing the street, street props,
// fences, outer scatter. One JSON → a coherent settlement in one call. Buildings are LevelBuilder blueprints or hero
// models from the Blender generator (FBX/GLB). Usage (execute_code):
//   return GDS.Village.BuildFromFile("art/blueprints/village_a.json");
// Schema: references/village.md
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace GDS
{
    public static class Village
    {
        [Serializable] public class P2 { public float x, z; }
        [Serializable] public class Road { public List<P2> points = new List<P2>(); public float width = 5f; }
        [Serializable] public class Plaza { public float x, z, w = 16, d = 16; public bool enabled = true; }
        [Serializable] public class TerrainSpec { public bool enabled = true; public float size = 200, height = 14, noiseScale = 0.018f, flattenRadius = 45; public List<string> layers = new List<string> { "#6B8E4E", "#8A7B5C" }; public int resolution = 257; }
        [Serializable] public class LotSpec { public float spacing = 14, setback = 3, minDistFromPlaza = 10, gate = 2.2f; public bool bothSides = true; }
        [Serializable] public class BuildingChoice { public string blueprint; public string file; public float weight = 1; public string collider = "mesh"; public float rotOffset; }
        [Serializable] public class StreetProp { public string file; public float every = 12, offset = 3.2f; public bool alternate = true; public bool faceRoad = true; public float jitter; public string collider = "box"; }
        [Serializable] public class PlazaProp { public string file; public float x, z, rotY; public string collider = "box"; }
        [Serializable] public class OuterScatter { public string file; public int count = 100; public float radius = 90, minDist = 4, avoidVillageRadius = 50, scaleMin = 0.9f, scaleMax = 1.3f; public string collider = "box"; }
        [Serializable] public class Spec
        {
            public string name = "Village"; public string group = "Level/Village"; public LevelBuilder.V3 origin = new LevelBuilder.V3(); public int seed = 7;
            public TerrainSpec terrain = new TerrainSpec();
            public List<Road> roads = new List<Road>(); public string roadMaterial; public string roadFile; public string plazaMaterial;
            public Plaza plaza = new Plaza();
            public LotSpec lots = new LotSpec();
            public List<BuildingChoice> buildings = new List<BuildingChoice>();
            public List<StreetProp> streetProps = new List<StreetProp>();
            public List<PlazaProp> plazaProps = new List<PlazaProp>();
            public string fenceFile;
            public List<OuterScatter> scatter = new List<OuterScatter>();
        }
        [Serializable] public class Result { public string name; public string status = "PASS"; public int buildings, roads, streetProps, fencePieces, scattered; public bool terrain; public List<string> warnings = new List<string>(); }

        class Lot { public Vector3 center; public float w, d; }

        public static string BuildFromFile(string projectRelJson)
        {
            var json = Common.ReadProjectFile(projectRelJson);
            if (json == null) return "{\"status\":\"FAIL\",\"error\":\"village spec not found\"}";
            return BuildFromJson(json);
        }

        public static string BuildFromJson(string json)
        {
            Spec sp; try { sp = JsonUtility.FromJson<Spec>(json); } catch (Exception e) { return "{\"status\":\"FAIL\",\"error\":\"bad json: " + Common.Esc(e.Message) + "\"}"; }
            var res = Build(sp);
            var outJson = JsonUtility.ToJson(res, true);
            Common.WriteProjectFile($"docs/lint/village-{sp.name}.json", outJson);
            return outJson;
        }

        public static Result Build(Spec sp)
        {
            var res = new Result { name = sp.name }; footprintCache.Clear();
            var rnd = new System.Random(sp.seed);
            var group = Common.GetOrCreateGroup(sp.group);
            var existing = group.Find(sp.name); if (existing != null) Undo.DestroyObjectImmediate(existing.gameObject);
            var root = new GameObject(sp.name).transform; root.SetParent(group, false); root.position = sp.origin.V;
            Undo.RegisterCreatedObjectUndo(root.gameObject, "GDS Village");
            var o = sp.origin.V;

            if (sp.terrain != null && sp.terrain.enabled) { res.terrain = BuildTerrain(sp, root, res); Physics.SyncTransforms(); }

            // roads + plaza
            var roadsT = new GameObject("Roads").transform; roadsT.SetParent(root, false);
            var roadMat = LoadMat(sp.roadMaterial, new Color(0.45f, 0.42f, 0.38f));
            var roadTile = string.IsNullOrEmpty(sp.roadFile) ? null : Common.LoadModel(sp.roadFile, Common.ArtRoot);
            foreach (var r in sp.roads) res.roads += BuildRoad(sp, r, roadsT, roadMat, roadTile);
            if (sp.plaza != null && sp.plaza.enabled)
            {
                var pm = LoadMat(sp.plazaMaterial, new Color(0.55f, 0.52f, 0.47f));
                var slab = Slab("Plaza", o + new Vector3(sp.plaza.x, 0.03f, sp.plaza.z), new Vector3(sp.plaza.w, 0.06f, sp.plaza.d), 0, roadsT, pm);
                foreach (var pp in sp.plazaProps)
                {
                    var a = Common.LoadModel(pp.file, Common.ArtRoot); if (a == null) { res.warnings.Add("plaza prop missing " + pp.file); continue; }
                    var inst = Common.Spawn(a, roadsT, "plaza_" + a.name); inst.transform.rotation = Quaternion.Euler(0, pp.rotY, 0);
                    Common.AlignBottomCenter(inst, o + new Vector3(sp.plaza.x + pp.x, 0.06f, sp.plaza.z + pp.z));
                    if (pp.collider != "none") Common.EnsureCollider(inst, pp.collider == "convex", pp.collider == "mesh");
                }
            }

            // lots along roads
            var lots = new List<Lot>(); var bT = new GameObject("Buildings").transform; bT.SetParent(root, false);
            float totalW = sp.buildings.Sum(b => Mathf.Max(0.01f, b.weight));
            foreach (var r in sp.roads)
            {
                for (int i = 0; i < r.points.Count - 1; i++)
                {
                    var a = new Vector3(r.points[i].x, 0, r.points[i].z); var b = new Vector3(r.points[i + 1].x, 0, r.points[i + 1].z);
                    var dir = (b - a); float len = dir.magnitude; if (len < 1f) continue; dir /= len;
                    var n = new Vector3(-dir.z, 0, dir.x);
                    for (float t = sp.lots.spacing * 0.5f; t < len - sp.lots.spacing * 0.3f; t += sp.lots.spacing)
                    {
                        foreach (float side in sp.lots.bothSides ? new[] { 1f, -1f } : new[] { 1f })
                        {
                            if (sp.buildings.Count == 0) break;
                            var choice = Pick(sp.buildings, totalW, rnd);
                            if (!Footprint(choice, out float W, out float D)) { res.warnings.Add("building has no footprint: " + (choice.blueprint ?? choice.file)); continue; }
                            var nn = n * side; var frontMid = a + dir * t + nn * (r.width / 2f + sp.lots.setback);
                            var center = frontMid + nn * (D / 2f);
                            var lot = new Lot { center = center, w = W, d = D };
                            if (sp.plaza != null && sp.plaza.enabled && Mathf.Abs(center.x - sp.plaza.x) < sp.plaza.w / 2 + D / 2 + sp.lots.minDistFromPlaza * 0.5f && Mathf.Abs(center.z - sp.plaza.z) < sp.plaza.d / 2 + D / 2 + sp.lots.minDistFromPlaza * 0.5f) continue;
                            if (lots.Any(l => Vector3.Distance(l.center, center) < (Mathf.Max(l.w, l.d) + Mathf.Max(W, D)) / 2f + 1.5f)) continue;
                            if (sp.roads.Any(rr => DistToRoad(rr, center) < rr.width / 2f + Mathf.Max(W, D) / 2f - 0.5f)) continue;
                            float rotY = Mathf.Atan2(nn.x, nn.z) * Mathf.Rad2Deg; // local +z points away from the road → door side (S, local -z) faces the road
                            if (PlaceBuilding(sp, choice, center, rotY, W, D, bT, res)) { lots.Add(lot); res.buildings++; }
                            // fences along the lot front, leaving a gate in the middle
                            if (!string.IsNullOrEmpty(sp.fenceFile))
                            {
                                var fenceBp = new LevelBuilder.Blueprint { name = "fence_" + res.buildings, mode = "props", group = sp.group + "/" + sp.name + "/Fences", origin = new LevelBuilder.V3 { x = o.x, y = o.y, z = o.z } };
                                var fl = frontMid - nn * 0.6f; var half = dir * (W / 2f + 1f); var gate = dir * (sp.lots.gate / 2f);
                                fenceBp.fences.Add(new LevelBuilder.Fence { file = sp.fenceFile, points = { V(fl - half), V(fl - gate) } });
                                fenceBp.fences.Add(new LevelBuilder.Fence { file = sp.fenceFile, points = { V(fl + gate), V(fl + half) } });
                                var fr = LevelBuilder.Build(fenceBp); res.fencePieces += fr.fencePieces;
                            }
                        }
                    }
                }
            }

            // street props (lanterns, barrels, carts) along road centre lines
            var spT = new GameObject("StreetProps").transform; spT.SetParent(root, false);
            foreach (var stp in sp.streetProps)
            {
                var asset = Common.LoadModel(stp.file, Common.ArtRoot); if (asset == null) { res.warnings.Add("street prop missing " + stp.file); continue; }
                int k = 0;
                foreach (var r in sp.roads)
                    for (int i = 0; i < r.points.Count - 1; i++)
                    {
                        var a = new Vector3(r.points[i].x, 0, r.points[i].z); var b = new Vector3(r.points[i + 1].x, 0, r.points[i + 1].z);
                        var dir = b - a; float len = dir.magnitude; if (len < 1f) continue; dir /= len; var n = new Vector3(-dir.z, 0, dir.x);
                        for (float t = stp.every * 0.5f; t < len; t += stp.every, k++)
                        {
                            float side = stp.alternate ? (k % 2 == 0 ? 1f : -1f) : 1f;
                            var pos = a + dir * t + n * side * (r.width / 2f + stp.offset) + (stp.jitter > 0 ? new Vector3((float)rnd.NextDouble() - 0.5f, 0, (float)rnd.NextDouble() - 0.5f) * stp.jitter : Vector3.zero);
                            if (lots.Any(l => Mathf.Abs(pos.x - l.center.x) < l.w / 2 + 0.5f && Mathf.Abs(pos.z - l.center.z) < l.d / 2 + 0.5f)) continue;
                            var inst = Common.Spawn(asset, spT, asset.name + "_" + k);
                            var face = -n * side; inst.transform.rotation = stp.faceRoad ? Quaternion.LookRotation(face) : Quaternion.Euler(0, (float)rnd.NextDouble() * 360f, 0);
                            Common.AlignBottomCenter(inst, o + pos + Vector3.up * 50f);
                            if (Common.TryGetBounds(inst, out var bb) && Common.GroundBelow(inst, bb, out float gy, out _)) Common.AlignBottomCenter(inst, o + new Vector3(pos.x, gy - o.y, pos.z));
                            else Common.AlignBottomCenter(inst, o + pos);
                            if (stp.collider != "none") Common.EnsureCollider(inst, stp.collider == "convex");
                            res.streetProps++;
                        }
                    }
            }

            // outer scatter (forest ring), avoiding roads and lots
            var scT = new GameObject("Scatter").transform; scT.SetParent(root, false);
            foreach (var sc in sp.scatter)
            {
                var asset = Common.LoadModel(sc.file, Common.ArtRoot); if (asset == null) { res.warnings.Add("scatter missing " + sc.file); continue; }
                var placed = new List<Vector3>(); int ok = 0, tries = 0;
                while (ok < sc.count && tries++ < sc.count * 30)
                {
                    float ang = (float)rnd.NextDouble() * Mathf.PI * 2f; float rad = Mathf.Lerp(sc.avoidVillageRadius, sc.radius, Mathf.Sqrt((float)rnd.NextDouble()));
                    var pos = new Vector3(Mathf.Cos(ang) * rad, 0, Mathf.Sin(ang) * rad);
                    if (sp.roads.Any(rr => DistToRoad(rr, pos) < rr.width / 2f + 2.5f)) continue;
                    if (lots.Any(l => Vector3.Distance(l.center, pos) < Mathf.Max(l.w, l.d))) continue;
                    if (placed.Any(q => Vector3.Distance(q, pos) < sc.minDist)) continue;
                    var inst = Common.Spawn(asset, scT, asset.name + "_" + ok);
                    inst.transform.localScale = Vector3.one * Mathf.Lerp(sc.scaleMin, sc.scaleMax, (float)rnd.NextDouble());
                    inst.transform.rotation = Quaternion.Euler(0, (float)rnd.NextDouble() * 360f, 0);
                    Common.AlignBottomCenter(inst, o + pos + Vector3.up * 80f);
                    if (Common.TryGetBounds(inst, out var bb) && Common.GroundBelow(inst, bb, out float gy, out _, 400f)) Common.AlignBottomCenter(inst, new Vector3(o.x + pos.x, gy, o.z + pos.z));
                    else { UnityEngine.Object.DestroyImmediate(inst); continue; }
                    if (sc.collider != "none") Common.EnsureCollider(inst, sc.collider == "convex");
                    placed.Add(pos); ok++; res.scattered++;
                }
            }

            EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
            Debug.Log($"[GDS Village] {sp.name}: {res.buildings} buildings, {res.roads} road pieces, {res.streetProps} street props, {res.fencePieces} fence, {res.scattered} scattered");
            return res;
        }

        static LevelBuilder.V3 V(Vector3 v) => new LevelBuilder.V3 { x = v.x, y = v.y, z = v.z };

        static BuildingChoice Pick(List<BuildingChoice> list, float total, System.Random rnd)
        {
            float r = (float)rnd.NextDouble() * total;
            foreach (var b in list) { r -= Mathf.Max(0.01f, b.weight); if (r <= 0) return b; }
            return list[list.Count - 1];
        }

        static readonly Dictionary<string, (float, float)> footprintCache = new Dictionary<string, (float, float)>();
        static bool Footprint(BuildingChoice c, out float w, out float d)
        {
            w = d = 0;
            string key = c.blueprint ?? c.file; if (key == null) return false;
            if (footprintCache.TryGetValue(key, out var fp)) { w = fp.Item1; d = fp.Item2; return true; }
            if (!string.IsNullOrEmpty(c.blueprint))
            {
                var json = Common.ReadProjectFile(c.blueprint); if (json == null) return false;
                var bp = JsonUtility.FromJson<LevelBuilder.Blueprint>(json); var vols = LevelBuilder.Volumes(bp);
                w = vols.Max(v => v.x + v.cellsX * bp.module) - vols.Min(v => v.x); d = vols.Max(v => v.z + v.cellsZ * bp.module) - vols.Min(v => v.z);
            }
            else
            {
                var asset = Common.LoadModel(c.file, Common.ArtRoot); if (asset == null) return false;
                var tmp = UnityEngine.Object.Instantiate(asset); bool ok = Common.TryGetBounds(tmp, out var b); UnityEngine.Object.DestroyImmediate(tmp);
                if (!ok) return false; w = b.size.x; d = b.size.z;
            }
            footprintCache[key] = (w, d); return true;
        }

        static bool PlaceBuilding(Spec sp, BuildingChoice c, Vector3 center, float rotY, float W, float D, Transform parent, Result res)
        {
            var o = sp.origin.V; var rot = Quaternion.Euler(0, rotY + c.rotOffset, 0);
            if (!string.IsNullOrEmpty(c.blueprint))
            {
                var json = Common.ReadProjectFile(c.blueprint); if (json == null) { res.warnings.Add("blueprint missing " + c.blueprint); return false; }
                var bp = JsonUtility.FromJson<LevelBuilder.Blueprint>(json);
                var vols = LevelBuilder.Volumes(bp); float minX = vols.Min(v => v.x), minZ = vols.Min(v => v.z);
                var cornerOffset = new Vector3(minX + W / 2f, 0, minZ + D / 2f);
                var origin = o + center - rot * cornerOffset;
                bp.name = $"{bp.name}_{res.buildings + 1}"; bp.group = sp.group + "/" + sp.name + "/Buildings";
                bp.origin = V(origin); bp.rotY = rotY + c.rotOffset;
                var r = LevelBuilder.Build(bp);
                if (r.status != "PASS") { res.warnings.Add($"{bp.name}: {string.Join(";", r.warnings)}"); return false; }
                return true;
            }
            var asset = Common.LoadModel(c.file, Common.ArtRoot); if (asset == null) { res.warnings.Add("building file missing " + c.file); return false; }
            var inst = Common.Spawn(asset, parent, asset.name + "_" + (res.buildings + 1));
            inst.transform.rotation = rot;
            Common.AlignBottomCenter(inst, o + center + Vector3.up * 50f);
            if (Common.TryGetBounds(inst, out var bb) && Common.GroundBelow(inst, bb, out float gy, out _)) Common.AlignBottomCenter(inst, new Vector3(o.x + center.x, gy, o.z + center.z));
            else Common.AlignBottomCenter(inst, o + center);
            Common.EnsureCollider(inst, c.collider == "convex", c.collider == "mesh");
            GameObjectUtility.SetStaticEditorFlags(inst, StaticEditorFlags.BatchingStatic | StaticEditorFlags.ContributeGI | StaticEditorFlags.OccluderStatic);
            return true;
        }

        static float DistToRoad(Road r, Vector3 p)
        {
            float best = float.MaxValue;
            for (int i = 0; i < r.points.Count - 1; i++)
            {
                var a = new Vector3(r.points[i].x, 0, r.points[i].z); var b = new Vector3(r.points[i + 1].x, 0, r.points[i + 1].z);
                var ab = b - a; float t = Mathf.Clamp01(Vector3.Dot(p - a, ab) / Mathf.Max(ab.sqrMagnitude, 1e-4f));
                best = Mathf.Min(best, Vector3.Distance(p, a + ab * t));
            }
            return best;
        }

        static Material LoadMat(string path, Color fallback)
        {
            var m = string.IsNullOrEmpty(path) ? null : AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m != null) return m;
            Common.EnsureFolder(Common.MaterialsRoot);
            string p = $"{Common.MaterialsRoot}/Mat_Village_{ColorUtility.ToHtmlStringRGB(fallback)}.mat";
            m = AssetDatabase.LoadAssetAtPath<Material>(p); if (m != null) return m;
            var sh = Shader.Find("Universal Render Pipeline/Lit"); if (sh == null) sh = Shader.Find("Standard");
            m = new Material(sh); if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", fallback); else m.color = fallback;
            if (m.HasProperty("_Smoothness")) m.SetFloat("_Smoothness", 0.1f);
            AssetDatabase.CreateAsset(m, p); return m;
        }

        static GameObject Slab(string name, Vector3 center, Vector3 size, float rotY, Transform parent, Material mat)
        {
            var g = GameObject.CreatePrimitive(PrimitiveType.Cube); g.name = name; g.transform.SetParent(parent, false);
            g.transform.position = center; g.transform.rotation = Quaternion.Euler(0, rotY, 0); g.transform.localScale = size;
            g.GetComponent<MeshRenderer>().sharedMaterial = mat;
            GameObjectUtility.SetStaticEditorFlags(g, StaticEditorFlags.BatchingStatic | StaticEditorFlags.ContributeGI);
            Undo.RegisterCreatedObjectUndo(g, "GDS Slab"); return g;
        }

        static int BuildRoad(Spec sp, Road r, Transform parent, Material mat, GameObject tile)
        {
            int n = 0; var o = sp.origin.V;
            for (int i = 0; i < r.points.Count - 1; i++)
            {
                var a = o + new Vector3(r.points[i].x, 0, r.points[i].z); var b = o + new Vector3(r.points[i + 1].x, 0, r.points[i + 1].z);
                var dir = b - a; float len = dir.magnitude; if (len < 0.5f) continue; dir /= len;
                float rotY = Mathf.Atan2(dir.x, dir.z) * Mathf.Rad2Deg;
                if (tile == null)
                {
                    Slab($"road_{n}", (a + b) / 2f + Vector3.up * 0.02f, new Vector3(r.width, 0.04f, len + r.width), rotY, parent, mat); n++;
                }
                else
                {
                    var probe = Common.Spawn(tile, parent, "probe"); float tl = Common.TryGetBounds(probe, out var pb) ? Mathf.Max(pb.size.x, pb.size.z) : 4f; UnityEngine.Object.DestroyImmediate(probe);
                    int count = Mathf.Max(1, Mathf.RoundToInt(len / tl));
                    for (int k = 0; k < count; k++)
                    {
                        var inst = Common.Spawn(tile, parent, $"road_{n}"); inst.transform.rotation = Quaternion.Euler(0, rotY, 0);
                        Common.AlignBottomCenter(inst, a + dir * ((k + 0.5f) * len / count) + Vector3.up * 0.01f); n++;
                    }
                }
            }
            return n;
        }

        // ---------------- terrain ----------------
        static bool BuildTerrain(Spec sp, Transform parent, Result res)
        {
            var t = sp.terrain; int resn = Mathf.Clamp(t.resolution, 33, 1025);
            var data = new TerrainData { heightmapResolution = resn, size = new Vector3(t.size, t.height, t.size) };
            Common.EnsureFolder(Common.SettingsRoot);
            var path = $"{Common.SettingsRoot}/Terrain_{sp.name}.asset";
            AssetDatabase.DeleteAsset(path); AssetDatabase.CreateAsset(data, path);
            float flatH = 0.35f; var rnd = new System.Random(sp.seed); float ox = (float)rnd.NextDouble() * 1000f, oz = (float)rnd.NextDouble() * 1000f;
            var h = new float[resn, resn];
            for (int y = 0; y < resn; y++) for (int x = 0; x < resn; x++)
                {
                    float wx = (x / (float)(resn - 1) - 0.5f) * t.size, wz = (y / (float)(resn - 1) - 0.5f) * t.size;
                    float nse = Mathf.PerlinNoise(ox + wx * t.noiseScale, oz + wz * t.noiseScale) * 0.7f + Mathf.PerlinNoise(ox + wx * t.noiseScale * 3.1f, oz + wz * t.noiseScale * 3.1f) * 0.3f;
                    float dist = Mathf.Sqrt(wx * wx + wz * wz); float k = Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(t.flattenRadius, t.flattenRadius * 1.7f, dist));
                    h[y, x] = Mathf.Lerp(flatH, flatH + (nse - 0.5f) * 0.9f, k);
                }
            data.SetHeights(0, 0, h);
            // layers: solid-color textures (or drop real PBR textures into Assets/_Game/Art/Terrain/ later)
            var layers = new List<TerrainLayer>();
            for (int i = 0; i < Mathf.Max(1, t.layers.Count); i++)
            {
                var col = Common.Hex(t.layers[i], Color.green); var tex = new Texture2D(64, 64); var px = new Color[64 * 64];
                for (int p = 0; p < px.Length; p++) { float v = ((p * 7919) % 13) / 13f * 0.06f - 0.03f; px[p] = new Color(Mathf.Clamp01(col.r + v), Mathf.Clamp01(col.g + v), Mathf.Clamp01(col.b + v)); }
                tex.SetPixels(px); tex.Apply();
                var texPath = $"{Common.SettingsRoot}/TerrainLayer_{sp.name}_{i}.png"; System.IO.File.WriteAllBytes(System.IO.Path.Combine(Common.ProjectDir, texPath), tex.EncodeToPNG()); AssetDatabase.ImportAsset(texPath);
                var layer = new TerrainLayer { diffuseTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(texPath), tileSize = new Vector2(8, 8) };
                var lp = $"{Common.SettingsRoot}/TerrainLayer_{sp.name}_{i}.terrainlayer"; AssetDatabase.DeleteAsset(lp); AssetDatabase.CreateAsset(layer, lp); layers.Add(AssetDatabase.LoadAssetAtPath<TerrainLayer>(lp));
            }
            data.terrainLayers = layers.ToArray();
            if (layers.Count > 1)
            {
                int ar = data.alphamapResolution; var alpha = new float[ar, ar, layers.Count];
                for (int y = 0; y < ar; y++) for (int x = 0; x < ar; x++)
                    {
                        float slope = data.GetSteepness(x / (float)(ar - 1), y / (float)(ar - 1)) / 90f; float s = Mathf.Clamp01((slope - 0.15f) * 4f);
                        alpha[y, x, 0] = 1f - s; alpha[y, x, 1] = s; for (int l = 2; l < layers.Count; l++) alpha[y, x, l] = 0;
                    }
                data.SetAlphamaps(0, 0, alpha);
            }
            var go = Terrain.CreateTerrainGameObject(data); go.name = "Terrain_" + sp.name; go.transform.SetParent(parent, false);
            go.transform.position = sp.origin.V + new Vector3(-t.size / 2f, -flatH * t.height, -t.size / 2f); // flat village area at y = 0
            var terr = go.GetComponent<Terrain>(); terr.materialTemplate = null;
            var urpTerrain = UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline != null ? Shader.Find("Universal Render Pipeline/Terrain/Lit") : null; if (urpTerrain != null) { var m = new Material(urpTerrain); var mp = $"{Common.SettingsRoot}/Mat_Terrain_{sp.name}.mat"; AssetDatabase.CreateAsset(m, mp); terr.materialTemplate = AssetDatabase.LoadAssetAtPath<Material>(mp); }
            AssetDatabase.SaveAssets();
            return true;
        }

        [MenuItem("GDS/Build Village (art/blueprints/village*.json)")]
        static void Menu()
        {
            var path = EditorUtility.OpenFilePanel("Village JSON", System.IO.Path.Combine(Common.ProjectDir, "art/blueprints"), "json");
            if (!string.IsNullOrEmpty(path)) Debug.Log(BuildFromJson(System.IO.File.ReadAllText(path)));
        }
    }
}
