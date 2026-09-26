// GDS World — procedural world generation from one seeded JSON spec.
//   mode "terrain" : Unity Terrain (warped fBm + ridges + thermal erosion), height/slope layers, water, kit scatter, flat spots (+ optional village)
//   mode "island"  : same, with a radial falloff into the sea
//   mode "dungeon" : grid rooms + corridors (BSP-ish), merged floor/wall meshes or kit tiles, spawn + goal markers
//   mode "cave"    : cellular-automata cave on the same grid, organic jittered walls
//   mode "voxel"   : GDS.VoxelWorld (chunked Minecraft-like, editable at runtime)
// Usage: return GDS.World.BuildFromFile("art/world/overworld.json");   (or: unity command gds_world --spec art/world/overworld.json)
// Schema + examples: references/world-gen.md, templates/world/*.json
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace GDS
{
    public static class World
    {
        [Serializable] public class Flat { public float x, z, r = 25; public string village; }
        [Serializable] public class TerrainSpec
        {
            public float size = 400, height = 60; public int resolution = 513;
            public float scale = 0.006f; public int octaves = 5; public float warp = 1.5f, mountains = 0.4f;
            public int erosion = 20; public float seaLevel; public float islandFalloff = 0.55f;
            public List<Flat> flat = new List<Flat>();
        }
        [Serializable] public class Layer { public string name = "layer", color = "#6B8E4E", texture, normal; public float tile = 8, minHeight = -1, maxHeight = 2, minSlope = -1, maxSlope = 91; }
        [Serializable] public class Scatter
        {
            public string file; public int count = 100; public float minHeight = -1, maxHeight = 2, maxSlope = 30, minDist = 4, scaleMin = 0.85f, scaleMax = 1.25f;
            public float clusters = 0.4f; public string collider = "trunk"; public bool alignToSlope;
        }
        [Serializable] public class GridProp { public string file; public int every = 4; public int perRoom = 1; public string collider = "box"; }
        [Serializable] public class GridSpec
        {
            public float cell = 4, wallHeight = 4; public int width = 24, depth = 24;
            public int rooms = 9, minRoom = 3, maxRoom = 6, corridorWidth = 1;
            public float fill = 0.47f; public int smooth = 5; public float jitter = 0.6f;
            public string floorFile, wallFile, floorMaterial, wallMaterial; public string floorColor = "#5B5550", wallColor = "#6E6862";
            public bool ceiling; public List<GridProp> wallProps = new List<GridProp>(); public List<GridProp> roomProps = new List<GridProp>();
        }
        [Serializable] public class VoxelSpec
        {
            public int chunkSize = 16, height = 64, baseHeight = 20; public float heightAmp = 22, scale = 0.018f; public int octaves = 4; public float mountains = 0.5f;
            public int seaLevel = 17, snowLine = 44; public bool caves = true; public float caveThreshold = 0.64f, treeChance = 0.012f;
            public int viewRadiusChunks = 5, editorRadiusChunks = 3; public bool stream = true, interact = true;
            public List<string> palette = new List<string>();
        }
        [Serializable] public class Spec
        {
            public string name = "World", mode = "terrain", group = "Level/World"; public int seed = 1; public bool spawn = true;
            public TerrainSpec terrain = new TerrainSpec(); public List<Layer> layers = new List<Layer>(); public List<Scatter> scatter = new List<Scatter>();
            public GridSpec grid = new GridSpec(); public VoxelSpec voxel = new VoxelSpec();
        }
        [Serializable] public class Result
        {
            public string name, mode, status = "PASS"; public int seed; public int scattered, rooms, cells, chunks, props; public bool water;
            public LevelBuilder.V3 spawn = new LevelBuilder.V3(), goal = new LevelBuilder.V3();
            public List<string> villages = new List<string>(); public List<string> warnings = new List<string>();
        }

        public static string BuildFromFile(string projectRelJson)
        {
            var json = Common.ReadProjectFile(projectRelJson);
            if (json == null) return "{\"status\":\"FAIL\",\"error\":\"world spec not found: " + Common.Esc(projectRelJson) + "\"}";
            return BuildFromJson(json);
        }

        public static string BuildFromJson(string json)
        {
            Spec sp; try { sp = JsonUtility.FromJson<Spec>(json); } catch (Exception e) { return "{\"status\":\"FAIL\",\"error\":\"bad json: " + Common.Esc(e.Message) + "\"}"; }
            Result res;
            try { res = Build(sp); }
            catch (Exception e) { res = new Result { name = sp.name, mode = sp.mode, status = "FAIL" }; res.warnings.Add(e.GetType().Name + ": " + e.Message); }
            var outJson = JsonUtility.ToJson(res, true);
            Common.WriteProjectFile($"docs/lint/world-{sp.name}.json", outJson);
            return outJson;
        }

        public static Result Build(Spec sp)
        {
            var res = new Result { name = sp.name, mode = sp.mode, seed = sp.seed };
            var group = Common.GetOrCreateGroup(sp.group);
            var existing = group.Find(sp.name); if (existing != null) Undo.DestroyObjectImmediate(existing.gameObject);
            var root = new GameObject(sp.name).transform; root.SetParent(group, false);
            Undo.RegisterCreatedObjectUndo(root.gameObject, "GDS World");
            switch ((sp.mode ?? "terrain").ToLowerInvariant())
            {
                case "terrain": BuildTerrain(sp, root, res, false); break;
                case "island": BuildTerrain(sp, root, res, true); break;
                case "dungeon": BuildGrid(sp, root, res, false); break;
                case "cave": BuildGrid(sp, root, res, true); break;
                case "voxel": BuildVoxel(sp, root, res); break;
                default: res.status = "FAIL"; res.warnings.Add("unknown mode " + sp.mode + " (terrain|island|dungeon|cave|voxel)"); return res;
            }
            if (sp.spawn) PlaceMarkers(root, res);
            EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
            AssetDatabase.SaveAssets();
            return res;
        }

        // ======================================================================================= TERRAIN / ISLAND
        static void BuildTerrain(Spec sp, Transform root, Result res, bool island)
        {
            var t = sp.terrain; int n = Mathf.ClosestPowerOfTwo(Mathf.Clamp(t.resolution - 1, 32, 2048)) + 1;
            var off = Noise.Offset(sp.seed, 11); var offR = Noise.Offset(sp.seed, 12); var offM = Noise.Offset(sp.seed, 13);
            var h = new float[n, n];
            for (int y = 0; y < n; y++)
                for (int x = 0; x < n; x++)
                {
                    float wx = (x / (float)(n - 1) - 0.5f) * t.size, wz = (y / (float)(n - 1) - 0.5f) * t.size;
                    float baseH = Noise.Warped(wx * t.scale, wz * t.scale, off, t.warp, t.octaves);
                    float ridge = Noise.Ridged(wx * t.scale * 0.7f, wz * t.scale * 0.7f, offR, 5);
                    float mask = Mathf.SmoothStep(0, 1, Mathf.InverseLerp(0.4f, 0.75f, Noise.Fbm(wx * t.scale * 0.3f, wz * t.scale * 0.3f, offM, 2)));
                    float v = baseH * 0.65f + ridge * t.mountains * mask * 0.6f;
                    if (island)
                    {
                        float d = new Vector2(x / (float)(n - 1) - 0.5f, y / (float)(n - 1) - 0.5f).magnitude * 2f;
                        d += (Noise.Fbm(wx * t.scale * 2f, wz * t.scale * 2f, offM, 3) - 0.5f) * 0.25f;
                        v = Mathf.Lerp(v, -0.05f, Mathf.SmoothStep(0, 1, Mathf.InverseLerp(t.islandFalloff, 0.98f, d)));
                        if (t.seaLevel <= 0) t.seaLevel = 0.12f;
                    }
                    h[y, x] = v;
                }
            // normalise to [0,1]
            float lo = float.MaxValue, hi = float.MinValue;
            foreach (var v in h) { lo = Mathf.Min(lo, v); hi = Mathf.Max(hi, v); }
            for (int y = 0; y < n; y++) for (int x = 0; x < n; x++) h[y, x] = Mathf.InverseLerp(lo, hi, h[y, x]);
            ThermalErosion(h, t.erosion, 0.6f / n * 40f);
            foreach (var f in t.flat) Flatten(h, n, t.size, f, t.seaLevel);

            var data = new TerrainData { heightmapResolution = n, size = new Vector3(t.size, t.height, t.size) };
            data.alphamapResolution = Mathf.Clamp(Mathf.ClosestPowerOfTwo(n - 1), 64, 1024);
            data.SetHeights(0, 0, h);
            Common.EnsureFolder(Common.SettingsRoot);
            var dataPath = $"{Common.SettingsRoot}/Terrain_{sp.name}.asset";
            AssetDatabase.DeleteAsset(dataPath); AssetDatabase.CreateAsset(data, dataPath);
            ApplyLayers(sp, data, res);

            var go = Terrain.CreateTerrainGameObject(data); go.name = "Terrain_" + sp.name; go.transform.SetParent(root, false);
            go.transform.localPosition = new Vector3(-t.size / 2f, 0, -t.size / 2f);
            go.isStatic = true;
            var terr = go.GetComponent<Terrain>();
            var urpTerrain = UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline != null ? Shader.Find("Universal Render Pipeline/Terrain/Lit") : null;
            if (urpTerrain != null)
            {
                var mp = $"{Common.SettingsRoot}/Mat_Terrain_{sp.name}.mat"; AssetDatabase.DeleteAsset(mp);
                AssetDatabase.CreateAsset(new Material(urpTerrain), mp); terr.materialTemplate = AssetDatabase.LoadAssetAtPath<Material>(mp);
            }
            terr.heightmapPixelError = 3; terr.basemapDistance = 400;

            if (t.seaLevel > 0f)
            {
                var water = GameObject.CreatePrimitive(PrimitiveType.Plane); water.name = "water_" + sp.name;
                water.transform.SetParent(root, false);
                water.transform.localPosition = new Vector3(0, t.seaLevel * t.height, 0);
                water.transform.localScale = new Vector3(t.size * 0.3f, 1, t.size * 0.3f);
                UnityEngine.Object.DestroyImmediate(water.GetComponent<MeshCollider>());
                var trig = water.AddComponent<BoxCollider>(); trig.isTrigger = true; trig.center = new Vector3(0, -2.5f, 0); trig.size = new Vector3(10, 5, 10);
                water.GetComponent<MeshRenderer>().sharedMaterial = WaterMaterial();
                water.GetComponent<MeshRenderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                res.water = true;
            }
            Physics.SyncTransforms();
            ScatterOnTerrain(sp, terr, root, res);

            // spawn: first flat spot, else the lowest-slope land point near the centre
            Vector3 spawn;
            if (t.flat.Count > 0) spawn = new Vector3(t.flat[0].x, 0, t.flat[0].z);
            else spawn = FindLandSpot(terr, t, sp.seed);
            spawn.y = terr.SampleHeight(root.TransformPoint(spawn)) + terr.transform.position.y;
            res.spawn = new LevelBuilder.V3 { x = spawn.x, y = spawn.y, z = spawn.z };

            // villages on flat spots (the village keeps its own roads/lots but uses our terrain)
            foreach (var f in t.flat)
            {
                if (string.IsNullOrEmpty(f.village)) continue;
                var vj = Common.ReadProjectFile(f.village);
                if (vj == null) { res.warnings.Add("village spec missing " + f.village); continue; }
                var vs = JsonUtility.FromJson<Village.Spec>(vj);
                vs.terrain.enabled = false;
                var c = root.TransformPoint(new Vector3(f.x, 0, f.z));
                vs.origin = new LevelBuilder.V3 { x = c.x, y = terr.SampleHeight(c) + terr.transform.position.y, z = c.z };
                var vr = Village.Build(vs);
                res.villages.Add($"{vs.name}: buildings {vr.buildings}, warnings {vr.warnings.Count}");
            }
        }

        static void ThermalErosion(float[,] h, int iterations, float talus)
        {
            int n = h.GetLength(0);
            var d = new[] { new Vector2Int(1, 0), new Vector2Int(-1, 0), new Vector2Int(0, 1), new Vector2Int(0, -1) };
            for (int it = 0; it < iterations; it++)
                for (int y = 1; y < n - 1; y++)
                    for (int x = 1; x < n - 1; x++)
                    {
                        float hv = h[y, x]; float maxDiff = 0; int best = -1;
                        for (int k = 0; k < 4; k++) { float diff = hv - h[y + d[k].y, x + d[k].x]; if (diff > maxDiff) { maxDiff = diff; best = k; } }
                        if (best >= 0 && maxDiff > talus) { float move = (maxDiff - talus) * 0.5f; h[y, x] -= move; h[y + d[best].y, x + d[best].x] += move; }
                    }
        }

        static void Flatten(float[,] h, int n, float size, Flat f, float seaLevel)
        {
            int cx = Mathf.RoundToInt((f.x / size + 0.5f) * (n - 1)), cz = Mathf.RoundToInt((f.z / size + 0.5f) * (n - 1));
            cx = Mathf.Clamp(cx, 0, n - 1); cz = Mathf.Clamp(cz, 0, n - 1);
            float target = Mathf.Max(h[cz, cx], seaLevel + 0.03f);
            float rCells = f.r / size * (n - 1), outer = rCells * 1.8f;
            for (int y = Mathf.Max(0, cz - (int)outer - 1); y <= Mathf.Min(n - 1, cz + (int)outer + 1); y++)
                for (int x = Mathf.Max(0, cx - (int)outer - 1); x <= Mathf.Min(n - 1, cx + (int)outer + 1); x++)
                {
                    float dist = Mathf.Sqrt((x - cx) * (x - cx) + (y - cz) * (y - cz));
                    float k = dist <= rCells ? 1f : 1f - Mathf.SmoothStep(0, 1, Mathf.InverseLerp(rCells, outer, dist));
                    h[y, x] = Mathf.Lerp(h[y, x], target, k);
                }
        }

        static void ApplyLayers(Spec sp, TerrainData data, Result res)
        {
            var specs = sp.layers.Count > 0 ? sp.layers : new List<Layer>
            {
                new Layer { name = "sand", color = "#D6C38E", maxHeight = sp.terrain.seaLevel + 0.03f },
                new Layer { name = "grass", color = "#6B8E4E", maxSlope = 30 },
                new Layer { name = "rock", color = "#7D7872", minSlope = 30 },
                new Layer { name = "snow", color = "#EEF1F4", minHeight = 0.82f },
            };
            var layers = new List<TerrainLayer>();
            for (int i = 0; i < specs.Count; i++)
            {
                var L = specs[i];
                Texture2D diffuse = string.IsNullOrEmpty(L.texture) ? null : AssetDatabase.LoadAssetAtPath<Texture2D>(L.texture);
                if (diffuse == null)
                {
                    if (!string.IsNullOrEmpty(L.texture)) res.warnings.Add("layer texture missing " + L.texture + " (solid color used)");
                    diffuse = SolidNoiseTexture($"{Common.SettingsRoot}/TerrainTex_{sp.name}_{L.name}.png", Common.Hex(L.color, Color.gray), sp.seed + i);
                }
                var tl = new TerrainLayer { diffuseTexture = diffuse, tileSize = new Vector2(L.tile, L.tile) };
                if (!string.IsNullOrEmpty(L.normal)) tl.normalMapTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(L.normal);
                var lp = $"{Common.SettingsRoot}/TerrainLayer_{sp.name}_{L.name}.terrainlayer"; AssetDatabase.DeleteAsset(lp); AssetDatabase.CreateAsset(tl, lp);
                layers.Add(AssetDatabase.LoadAssetAtPath<TerrainLayer>(lp));
            }
            data.terrainLayers = layers.ToArray();
            int ar = data.alphamapResolution; var alpha = new float[ar, ar, layers.Count];
            for (int y = 0; y < ar; y++)
                for (int x = 0; x < ar; x++)
                {
                    float nx = x / (float)(ar - 1), ny = y / (float)(ar - 1);
                    float hh = data.GetInterpolatedHeight(nx, ny) / Mathf.Max(0.01f, data.size.y);
                    float slope = data.GetSteepness(nx, ny);
                    float sum = 0; var w = new float[layers.Count];
                    for (int l = 0; l < specs.Count; l++)
                    {
                        var L = specs[l];
                        float fit = Band(hh, L.minHeight, L.maxHeight, 0.03f) * Band(slope, L.minSlope, L.maxSlope, 4f);
                        // later layers override earlier ones (snow over rock over grass)
                        for (int prev = 0; prev < l; prev++) w[prev] *= 1f - fit;
                        w[l] = fit;
                    }
                    for (int l = 0; l < w.Length; l++) sum += w[l];
                    if (sum <= 0.0001f) { w[0] = 1; sum = 1; }
                    for (int l = 0; l < w.Length; l++) alpha[y, x, l] = w[l] / sum;
                }
            data.SetAlphamaps(0, 0, alpha);
        }

        static float Band(float v, float min, float max, float soft)
        {
            float a = min <= -0.99f ? 1f : Mathf.SmoothStep(0, 1, Mathf.InverseLerp(min - soft, min + soft, v));
            float b = max >= 1.99f || max >= 90.9f ? 1f : 1f - Mathf.SmoothStep(0, 1, Mathf.InverseLerp(max - soft, max + soft, v));
            return a * b;
        }

        static Texture2D SolidNoiseTexture(string path, Color c, int seed)
        {
            const int S = 128; var tex = new Texture2D(S, S, TextureFormat.RGBA32, true); var off = Noise.Offset(seed, 5);
            for (int y = 0; y < S; y++) for (int x = 0; x < S; x++)
                {
                    float v = (Noise.Fbm(x * 0.06f, y * 0.06f, off, 3) - 0.5f) * 0.16f + (Noise.Hash01(x, y, 0, seed) - 0.5f) * 0.05f;
                    tex.SetPixel(x, y, new Color(Mathf.Clamp01(c.r + v), Mathf.Clamp01(c.g + v), Mathf.Clamp01(c.b + v), 1));
                }
            tex.Apply();
            System.IO.File.WriteAllBytes(System.IO.Path.Combine(Common.ProjectDir, path), tex.EncodeToPNG());
            AssetDatabase.ImportAsset(path);
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        static Material WaterMaterial()
        {
            var path = Common.MaterialsRoot + "/Mat_Water.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m != null) return m;
            var sh = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            m = new Material(sh);
            VoxelWorld.MakeTransparent(m, new Color(0.18f, 0.45f, 0.62f, 0.72f));
            Common.EnsureFolder(Common.MaterialsRoot); AssetDatabase.CreateAsset(m, path);
            return m;
        }

        static Vector3 FindLandSpot(Terrain terr, TerrainSpec t, int seed)
        {
            var data = terr.terrainData; Vector3 best = Vector3.zero; float bestScore = float.MaxValue;
            for (int i = 0; i < 400; i++)
            {
                float r = Mathf.Sqrt(Noise.Hash01(i, 1, 0, seed)) * t.size * 0.35f, a = Noise.Hash01(i, 2, 0, seed) * Mathf.PI * 2;
                float x = Mathf.Cos(a) * r, z = Mathf.Sin(a) * r;
                float nx = x / t.size + 0.5f, nz = z / t.size + 0.5f;
                float hh = data.GetInterpolatedHeight(nx, nz) / t.height; if (hh < t.seaLevel + 0.02f) continue;
                float score = data.GetSteepness(nx, nz) + r * 0.05f;
                if (score < bestScore) { bestScore = score; best = new Vector3(x, 0, z); }
            }
            return best;
        }

        static void ScatterOnTerrain(Spec sp, Terrain terr, Transform root, Result res)
        {
            var data = terr.terrainData; var t = sp.terrain;
            var scatterRoot = new GameObject("Scatter").transform; scatterRoot.SetParent(root, false);
            var taken = new List<Vector3>();
            for (int s = 0; s < sp.scatter.Count; s++)
            {
                var S = sp.scatter[s];
                var asset = Common.LoadModel(S.file, Common.ArtRoot);
                if (asset == null) { res.warnings.Add("scatter model missing " + S.file + " (run KitCatalog, check the name)"); continue; }
                var off = Noise.Offset(sp.seed, 100 + s); int placed = 0;
                for (int tries = 0; tries < S.count * 30 && placed < S.count; tries++)
                {
                    float x = (Noise.Hash01(tries, s, 1, sp.seed) - 0.5f) * t.size * 0.96f, z = (Noise.Hash01(tries, s, 2, sp.seed) - 0.5f) * t.size * 0.96f;
                    if (S.clusters > 0 && Noise.Fbm(x * 0.02f, z * 0.02f, off, 2) < S.clusters * 0.6f) continue;
                    float nx = x / t.size + 0.5f, nz = z / t.size + 0.5f;
                    float hh = data.GetInterpolatedHeight(nx, nz) / t.height, slope = data.GetSteepness(nx, nz);
                    if (hh < S.minHeight || hh > S.maxHeight || slope > S.maxSlope) continue;
                    if (t.seaLevel > 0 && hh < t.seaLevel + 0.01f) continue;
                    if (t.flat.Any(f => (new Vector2(f.x - x, f.z - z)).magnitude < f.r * 1.2f)) continue;
                    var p = new Vector3(x, 0, z);
                    if (taken.Any(q => (q - p).sqrMagnitude < S.minDist * S.minDist)) continue;
                    var inst = Common.Spawn(asset, scatterRoot, (S.collider == "none" ? "deco_" : "") + $"{asset.name}_{placed}");
                    float sc = Mathf.Lerp(S.scaleMin, S.scaleMax, Noise.Hash01(tries, s, 3, sp.seed));
                    inst.transform.localScale *= sc;
                    inst.transform.rotation = Quaternion.Euler(0, Noise.Hash01(tries, s, 4, sp.seed) * 360f, 0);
                    var wp = root.TransformPoint(p); wp.y = terr.SampleHeight(wp) + terr.transform.position.y;
                    if (S.alignToSlope) inst.transform.rotation = Quaternion.FromToRotation(Vector3.up, data.GetInterpolatedNormal(nx, nz)) * inst.transform.rotation;
                    Common.AlignBottomCenter(inst, wp);
                    // re-seat on the height under the bounds centre (what SceneLint measures), a hair inside the tolerance
                    if (Common.TryGetBounds(inst, out var ib))
                    {
                        var under = new Vector3(ib.center.x, 0, ib.center.z); under.y = terr.SampleHeight(under) + terr.transform.position.y;
                        inst.transform.position += Vector3.up * (under.y - ib.min.y - 0.01f);
                    }
                    inst.isStatic = true;
                    AddCollider(inst, S.collider);
                    taken.Add(p); placed++;
                }
                res.scattered += placed;
                if (placed < S.count / 2) res.warnings.Add($"scatter {S.file}: only {placed}/{S.count} fit the height/slope rules");
            }
        }

        static void AddCollider(GameObject inst, string kind)
        {
            if (kind == "none" || inst.GetComponentInChildren<Collider>(true) != null) return;
            if (kind == "trunk" && Common.TryGetBounds(inst, out var b))
            {
                var cap = inst.AddComponent<CapsuleCollider>();
                float r = Mathf.Clamp(Mathf.Min(b.size.x, b.size.z) * 0.12f, 0.15f, 0.8f);
                cap.radius = r / Mathf.Max(0.001f, inst.transform.lossyScale.x);
                cap.height = b.size.y * 0.6f / Mathf.Max(0.001f, inst.transform.lossyScale.y);
                cap.center = inst.transform.InverseTransformPoint(new Vector3(b.center.x, b.min.y + b.size.y * 0.3f, b.center.z));
                return;
            }
            Common.EnsureCollider(inst, kind == "convex", kind == "mesh");
        }

        // ======================================================================================= DUNGEON / CAVE (grid)
        class RoomRect { public int x, z, w, d; public Vector2Int Center => new Vector2Int(x + w / 2, z + d / 2); }

        static void BuildGrid(Spec sp, Transform root, Result res, bool cave)
        {
            var g = sp.grid; int W = Mathf.Clamp(g.width, 8, 200), D = Mathf.Clamp(g.depth, 8, 200);
            var open = new bool[W, D]; var rooms = new List<RoomRect>();
            var rnd = new System.Random(sp.seed);
            if (cave) CellularCave(open, W, D, g, rnd);
            else Rooms(open, W, D, g, rnd, rooms);
            res.rooms = rooms.Count;
            for (int x = 0; x < W; x++) for (int z = 0; z < D; z++) if (open[x, z]) res.cells++;
            if (res.cells == 0) { res.status = "FAIL"; res.warnings.Add("no walkable cells"); return; }

            // start / goal: BFS from the first room (or the first open cell), goal = farthest reachable cell
            var start = rooms.Count > 0 ? rooms[0].Center : FirstOpen(open, W, D);
            var dist = Bfs(open, W, D, start);
            var goal = start; int far = 0;
            for (int x = 0; x < W; x++) for (int z = 0; z < D; z++) if (dist[x, z] > far) { far = dist[x, z]; goal = new Vector2Int(x, z); }
            Vector3 CellPos(Vector2Int c) => new Vector3((c.x - W / 2f + 0.5f) * g.cell, 0, (c.y - D / 2f + 0.5f) * g.cell);
            var sPos = CellPos(start); var gPos = CellPos(goal);
            res.spawn = new LevelBuilder.V3 { x = sPos.x, y = 0, z = sPos.z }; res.goal = new LevelBuilder.V3 { x = gPos.x, y = 0, z = gPos.z };

            var floorMat = LoadOrColor(g.floorMaterial, g.floorColor, "DungeonFloor");
            var wallMat = LoadOrColor(g.wallMaterial, g.wallColor, cave ? "CaveWall" : "DungeonWall");
            var floorKit = string.IsNullOrEmpty(g.floorFile) ? null : Common.LoadModel(g.floorFile);
            var wallKit = string.IsNullOrEmpty(g.wallFile) ? null : Common.LoadModel(g.wallFile);
            if (!string.IsNullOrEmpty(g.floorFile) && floorKit == null) res.warnings.Add("floorFile missing " + g.floorFile + " (procedural floor used)");
            if (!string.IsNullOrEmpty(g.wallFile) && wallKit == null) res.warnings.Add("wallFile missing " + g.wallFile + " (procedural walls used)");

            var geo = new GameObject(cave ? "Cave" : "Dungeon").transform; geo.SetParent(root, false);
            var floorQuads = new List<Vector3[]>(); var wallBoxes = new List<(Vector3 c, Vector3 s)>(); var ceilQuads = new List<Vector3[]>();
            var wallRuns = new List<(Vector3 pos, float rotY)>();
            float c2 = g.cell / 2f, thick = cave ? g.cell * 0.5f : Mathf.Min(0.5f, g.cell * 0.15f);
            var dirs = new[] { new Vector2Int(1, 0), new Vector2Int(-1, 0), new Vector2Int(0, 1), new Vector2Int(0, -1) };
            for (int x = 0; x < W; x++)
                for (int z = 0; z < D; z++)
                {
                    if (!open[x, z]) continue;
                    var p = CellPos(new Vector2Int(x, z));
                    if (floorKit != null) { var f = Common.Spawn(floorKit, geo, $"floor_{x}_{z}"); f.transform.position = p; f.isStatic = true; Common.EnsureCollider(f); }
                    else floorQuads.Add(new[] { p + new Vector3(-c2, 0, -c2), p + new Vector3(-c2, 0, c2), p + new Vector3(c2, 0, c2), p + new Vector3(c2, 0, -c2) });
                    if (g.ceiling) ceilQuads.Add(new[] { p + new Vector3(-c2, g.wallHeight, -c2), p + new Vector3(c2, g.wallHeight, -c2), p + new Vector3(c2, g.wallHeight, c2), p + new Vector3(-c2, g.wallHeight, c2) });
                    foreach (var d in dirs)
                    {
                        int nx = x + d.x, nz = z + d.y;
                        if (nx >= 0 && nz >= 0 && nx < W && nz < D && open[nx, nz]) continue;
                        var edge = p + new Vector3(d.x * c2, 0, d.y * c2);
                        float rotY = d.x != 0 ? (d.x > 0 ? 90 : -90) : (d.y > 0 ? 0 : 180);
                        wallRuns.Add((edge, rotY));
                        if (wallKit != null) { var w = Common.Spawn(wallKit, geo, $"wall_{x}_{z}_{rotY}"); w.transform.rotation = Quaternion.Euler(0, rotY + 180f, 0); Common.AlignBottomCenter(w, edge); w.isStatic = true; Common.EnsureCollider(w); }
                        else
                        {
                            var size = d.x != 0 ? new Vector3(thick, g.wallHeight, g.cell + thick) : new Vector3(g.cell + thick, g.wallHeight, thick);
                            wallBoxes.Add((edge + new Vector3(d.x * thick / 2f, g.wallHeight / 2f, d.y * thick / 2f), size));
                        }
                    }
                }
            if (floorQuads.Count > 0) MeshObject("floor_" + sp.name, geo, QuadsMesh(floorQuads, Vector3.up), floorMat);
            if (ceilQuads.Count > 0) MeshObject("ceiling_" + sp.name, geo, QuadsMesh(ceilQuads, Vector3.down), wallMat);
            if (wallBoxes.Count > 0) MeshObject("wall_" + sp.name, geo, BoxesMesh(wallBoxes, cave ? g.jitter : 0f, sp.seed), wallMat);

            // props: wall props every N wall edges (torches), room props at room centres (chests, altars)
            var propsT = new GameObject("Props").transform; propsT.SetParent(root, false);
            foreach (var wp in g.wallProps)
            {
                var a = Common.LoadModel(wp.file, Common.ArtRoot); if (a == null) { res.warnings.Add("wall prop missing " + wp.file); continue; }
                for (int i = 0; i < wallRuns.Count; i += Mathf.Max(1, wp.every))
                {
                    var (pos, rotY) = wallRuns[i];
                    var inst = Common.Spawn(a, propsT, $"{a.name}_{i}");
                    inst.transform.rotation = Quaternion.Euler(0, rotY + 180f, 0);
                    var inward = Quaternion.Euler(0, rotY, 0) * Vector3.forward;
                    Common.AlignBottomCenter(inst, pos - inward * 0.3f + Vector3.up * g.wallHeight * 0.45f);
                    inst.name = "attach_" + inst.name;   // wall-mounted: not a floor prop for the lint
                    res.props++;
                }
            }
            var centres = rooms.Count > 0 ? rooms.Select(r => r.Center).ToList() : SampleOpen(open, W, D, 6, rnd);
            foreach (var rp in g.roomProps)
            {
                var a = Common.LoadModel(rp.file, Common.ArtRoot); if (a == null) { res.warnings.Add("room prop missing " + rp.file); continue; }
                for (int r = 1; r < centres.Count; r++)
                    for (int k = 0; k < rp.perRoom; k++)
                    {
                        var cpos = CellPos(centres[r]) + new Vector3((float)rnd.NextDouble() - 0.5f, 0, (float)rnd.NextDouble() - 0.5f) * g.cell * 0.5f;
                        var inst = Common.Spawn(a, propsT, $"{a.name}_{r}_{k}");
                        inst.transform.rotation = Quaternion.Euler(0, rnd.Next(4) * 90, 0);
                        Common.AlignBottomCenter(inst, cpos); Common.EnsureCollider(inst, rp.collider == "convex", rp.collider == "mesh");
                        res.props++;
                    }
            }
            // layout for gameplay (enemy spawns, loot): rooms, start, goal
            var layout = new System.Text.StringBuilder();
            layout.Append("{\"cell\":").Append(g.cell).Append(",\"width\":").Append(W).Append(",\"depth\":").Append(D).Append(",\"roomCentres\":[");
            layout.Append(string.Join(",", centres.Select(c => { var q = CellPos(c); return $"[{q.x:F1},{q.z:F1}]"; })));
            layout.Append($"],\"spawn\":[{sPos.x:F1},{sPos.z:F1}],\"goal\":[{gPos.x:F1},{gPos.z:F1}]}}");
            Common.WriteProjectFile($"art/world/{sp.name}.layout.json", layout.ToString());
        }

        static void Rooms(bool[,] open, int W, int D, GridSpec g, System.Random rnd, List<RoomRect> rooms)
        {
            for (int tries = 0; tries < g.rooms * 40 && rooms.Count < g.rooms; tries++)
            {
                int w = rnd.Next(g.minRoom, g.maxRoom + 1), d = rnd.Next(g.minRoom, g.maxRoom + 1);
                int x = rnd.Next(1, Math.Max(2, W - w - 1)), z = rnd.Next(1, Math.Max(2, D - d - 1));
                var r = new RoomRect { x = x, z = z, w = w, d = d };
                if (rooms.Any(o => r.x - 1 < o.x + o.w && r.x + r.w + 1 > o.x && r.z - 1 < o.z + o.d && r.z + r.d + 1 > o.z)) continue;
                rooms.Add(r);
                for (int i = x; i < x + w; i++) for (int j = z; j < z + d; j++) open[i, j] = true;
            }
            // connect: each room to its nearest already-connected room (tree), plus one loop for variety
            var connected = new List<RoomRect> { rooms.FirstOrDefault() };
            if (connected[0] == null) return;
            foreach (var r in rooms.Skip(1).OrderBy(r => (r.Center - rooms[0].Center).sqrMagnitude))
            {
                var near = connected.OrderBy(c => (c.Center - r.Center).sqrMagnitude).First();
                Corridor(open, W, D, r.Center, near.Center, g.corridorWidth, rnd.Next(2) == 0);
                connected.Add(r);
            }
            if (rooms.Count > 3) Corridor(open, W, D, rooms[rooms.Count - 1].Center, rooms[1].Center, g.corridorWidth, true);
        }

        static void Corridor(bool[,] open, int W, int D, Vector2Int a, Vector2Int b, int width, bool xFirst)
        {
            var corner = xFirst ? new Vector2Int(b.x, a.y) : new Vector2Int(a.x, b.y);
            Carve(open, W, D, a, corner, width); Carve(open, W, D, corner, b, width);
        }

        static void Carve(bool[,] open, int W, int D, Vector2Int a, Vector2Int b, int width)
        {
            int x0 = Math.Min(a.x, b.x), x1 = Math.Max(a.x, b.x), z0 = Math.Min(a.y, b.y), z1 = Math.Max(a.y, b.y);
            for (int x = x0; x <= x1; x++)
                for (int z = z0; z <= z1; z++)
                    for (int k = 0; k < Math.Max(1, width); k++)
                    {
                        int xx = a.y == b.y ? x : x + k, zz = a.y == b.y ? z + k : z;
                        if (xx > 0 && zz > 0 && xx < W - 1 && zz < D - 1) open[xx, zz] = true;
                    }
        }

        static void CellularCave(bool[,] open, int W, int D, GridSpec g, System.Random rnd)
        {
            for (int x = 0; x < W; x++) for (int z = 0; z < D; z++) open[x, z] = x > 0 && z > 0 && x < W - 1 && z < D - 1 && rnd.NextDouble() > g.fill;
            for (int it = 0; it < g.smooth; it++)
            {
                var next = new bool[W, D];
                for (int x = 1; x < W - 1; x++)
                    for (int z = 1; z < D - 1; z++)
                    {
                        int walls = 0;
                        for (int dx = -1; dx <= 1; dx++) for (int dz = -1; dz <= 1; dz++) if ((dx != 0 || dz != 0) && !open[x + dx, z + dz]) walls++;
                        next[x, z] = walls < 5;
                    }
                Array.Copy(next, open, next.Length);
            }
            // keep the largest connected region only
            var seen = new bool[W, D]; List<Vector2Int> best = null;
            for (int x = 0; x < W; x++)
                for (int z = 0; z < D; z++)
                {
                    if (!open[x, z] || seen[x, z]) continue;
                    var region = new List<Vector2Int>(); var q = new Queue<Vector2Int>(); q.Enqueue(new Vector2Int(x, z)); seen[x, z] = true;
                    while (q.Count > 0)
                    {
                        var c = q.Dequeue(); region.Add(c);
                        foreach (var d in new[] { Vector2Int.right, Vector2Int.left, Vector2Int.up, Vector2Int.down })
                        {
                            var nb = c + d;
                            if (nb.x < 0 || nb.y < 0 || nb.x >= W || nb.y >= D || seen[nb.x, nb.y] || !open[nb.x, nb.y]) continue;
                            seen[nb.x, nb.y] = true; q.Enqueue(nb);
                        }
                    }
                    if (best == null || region.Count > best.Count) best = region;
                }
            Array.Clear(open, 0, open.Length);
            if (best != null) foreach (var c in best) open[c.x, c.y] = true;
        }

        static Vector2Int FirstOpen(bool[,] open, int W, int D)
        {
            for (int x = 0; x < W; x++) for (int z = 0; z < D; z++) if (open[x, z]) return new Vector2Int(x, z);
            return Vector2Int.zero;
        }

        static List<Vector2Int> SampleOpen(bool[,] open, int W, int D, int count, System.Random rnd)
        {
            var all = new List<Vector2Int>();
            for (int x = 0; x < W; x++) for (int z = 0; z < D; z++) if (open[x, z]) all.Add(new Vector2Int(x, z));
            return all.OrderBy(_ => rnd.Next()).Take(count).ToList();
        }

        static int[,] Bfs(bool[,] open, int W, int D, Vector2Int s)
        {
            var dist = new int[W, D]; for (int x = 0; x < W; x++) for (int z = 0; z < D; z++) dist[x, z] = -1;
            var q = new Queue<Vector2Int>(); q.Enqueue(s); dist[s.x, s.y] = 0;
            while (q.Count > 0)
            {
                var c = q.Dequeue();
                foreach (var d in new[] { Vector2Int.right, Vector2Int.left, Vector2Int.up, Vector2Int.down })
                {
                    var n = c + d;
                    if (n.x < 0 || n.y < 0 || n.x >= W || n.y >= D || !open[n.x, n.y] || dist[n.x, n.y] >= 0) continue;
                    dist[n.x, n.y] = dist[c.x, c.y] + 1; q.Enqueue(n);
                }
            }
            return dist;
        }

        static Mesh QuadsMesh(List<Vector3[]> quads, Vector3 normal)
        {
            var v = new List<Vector3>(); var t = new List<int>(); var uv = new List<Vector2>(); var n = new List<Vector3>();
            foreach (var q in quads)
            {
                int b = v.Count; v.AddRange(q);
                foreach (var p in q) { uv.Add(new Vector2(p.x, p.z) * 0.25f); n.Add(normal); }
                if (Vector3.Dot(Vector3.Cross(q[1] - q[0], q[2] - q[0]), normal) > 0) t.AddRange(new[] { b, b + 1, b + 2, b, b + 2, b + 3 });
                else t.AddRange(new[] { b, b + 2, b + 1, b, b + 3, b + 2 });
            }
            var m = new Mesh { indexFormat = v.Count > 65000 ? UnityEngine.Rendering.IndexFormat.UInt32 : UnityEngine.Rendering.IndexFormat.UInt16 };
            m.SetVertices(v); m.SetNormals(n); m.SetUVs(0, uv); m.SetTriangles(t, 0); m.RecalculateBounds(); m.RecalculateTangents();
            return m;
        }

        /// <summary>Merged boxes; jitter > 0 displaces vertices with a position-stable noise (organic cave walls, shared corners stay welded).</summary>
        static Mesh BoxesMesh(List<(Vector3 c, Vector3 s)> boxes, float jitter, int seed)
        {
            var v = new List<Vector3>(); var t = new List<int>(); var uv = new List<Vector2>();
            var off = Noise.Offset(seed, 77);
            Vector3 J(Vector3 p)
            {
                if (jitter <= 0 || p.y <= 0.01f) return p;
                float k = jitter * Mathf.Clamp01(p.y);
                return p + new Vector3(Noise.Fbm(p.x * 0.3f, p.z * 0.3f + p.y * 0.2f, off, 2) - 0.5f, 0, Noise.Fbm(p.z * 0.3f + 9f, p.x * 0.3f + p.y * 0.2f, off, 2) - 0.5f) * 2f * k;
            }
            var faces = new[] { Vector3.right, Vector3.left, Vector3.up, Vector3.down, Vector3.forward, Vector3.back };
            foreach (var (c, s) in boxes)
            {
                var h = s / 2f;
                foreach (var f in faces)
                {
                    var a = f.x != 0 ? Vector3.forward : Vector3.right; var b = f.y != 0 ? Vector3.forward : Vector3.up;
                    if (f.x == 0 && f.y == 0) { a = Vector3.right; b = Vector3.up; }
                    var center = c + Vector3.Scale(f, h); var A = Vector3.Scale(a, h); var B = Vector3.Scale(b, h);
                    var q = new[] { J(center - A - B), J(center + A - B), J(center + A + B), J(center - A + B) };
                    int i = v.Count; v.AddRange(q);
                    foreach (var p in q) uv.Add(f.y != 0 ? new Vector2(p.x, p.z) * 0.25f : new Vector2(p.x + p.z, p.y) * 0.25f);
                    if (Vector3.Dot(Vector3.Cross(q[1] - q[0], q[2] - q[0]), f) > 0) t.AddRange(new[] { i, i + 1, i + 2, i, i + 2, i + 3 });
                    else t.AddRange(new[] { i, i + 2, i + 1, i, i + 3, i + 2 });
                }
            }
            var m = new Mesh { indexFormat = v.Count > 65000 ? UnityEngine.Rendering.IndexFormat.UInt32 : UnityEngine.Rendering.IndexFormat.UInt16 };
            m.SetVertices(v); m.SetUVs(0, uv); m.SetTriangles(t, 0); m.RecalculateNormals(); m.RecalculateBounds(); m.RecalculateTangents();
            return m;
        }

        static GameObject MeshObject(string name, Transform parent, Mesh mesh, Material mat)
        {
            Common.EnsureFolder(Common.ArtRoot + "/Generated");
            var path = $"{Common.ArtRoot}/Generated/{name}.asset";
            AssetDatabase.DeleteAsset(path); mesh.name = name; AssetDatabase.CreateAsset(mesh, path);
            var go = new GameObject(name); go.transform.SetParent(parent, false); go.isStatic = true;
            go.AddComponent<MeshFilter>().sharedMesh = mesh; go.AddComponent<MeshRenderer>().sharedMaterial = mat;
            go.AddComponent<MeshCollider>().sharedMesh = mesh;
            return go;
        }

        static Material LoadOrColor(string matPath, string hex, string tag)
        {
            if (!string.IsNullOrEmpty(matPath)) { var m = AssetDatabase.LoadAssetAtPath<Material>(matPath); if (m != null) return m; }
            return Common.PaletteMaterial(-1, Common.Hex(hex, Color.gray), tag);
        }

        // ======================================================================================= VOXEL
        static void BuildVoxel(Spec sp, Transform root, Result res)
        {
            var v = sp.voxel;
            var go = new GameObject("VoxelWorld"); go.transform.SetParent(root, false);
            var w = go.AddComponent<VoxelWorld>();
            w.seed = sp.seed; w.chunkSize = v.chunkSize; w.height = v.height; w.baseHeight = v.baseHeight; w.heightAmp = v.heightAmp; w.scale = v.scale;
            w.octaves = v.octaves; w.mountains = v.mountains; w.seaLevel = v.seaLevel; w.snowLine = v.snowLine; w.caves = v.caves;
            w.caveThreshold = v.caveThreshold; w.treeChance = v.treeChance; w.viewRadiusChunks = v.viewRadiusChunks; w.editorRadiusChunks = v.editorRadiusChunks;
            for (int i = 0; i < v.palette.Count && i < w.palette.Length; i++) if (!string.IsNullOrEmpty(v.palette[i])) w.palette[i] = Common.Hex(v.palette[i], w.palette[i]);

            // persistent materials so builds keep them
            Common.EnsureFolder(Common.MaterialsRoot);
            var texPath = $"{Common.MaterialsRoot}/VoxelPalette_{sp.name}.png";
            System.IO.File.WriteAllBytes(System.IO.Path.Combine(Common.ProjectDir, texPath), w.BuildPaletteTexture().EncodeToPNG());
            AssetDatabase.ImportAsset(texPath);
            if (AssetImporter.GetAtPath(texPath) is TextureImporter ti) { ti.filterMode = FilterMode.Point; ti.mipmapEnabled = false; ti.npotScale = TextureImporterNPOTScale.None; ti.textureCompression = TextureImporterCompression.Uncompressed; ti.wrapMode = TextureWrapMode.Clamp; ti.SaveAndReimport(); }
            var sh = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            var matPath = $"{Common.MaterialsRoot}/Mat_Voxel_{sp.name}.mat"; AssetDatabase.DeleteAsset(matPath);
            var mat = new Material(sh); var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(texPath);
            if (mat.HasProperty("_BaseMap")) mat.SetTexture("_BaseMap", tex); else mat.mainTexture = tex;
            if (mat.HasProperty("_Smoothness")) mat.SetFloat("_Smoothness", 0.05f);
            AssetDatabase.CreateAsset(mat, matPath); w.material = mat;
            var wmPath = $"{Common.MaterialsRoot}/Mat_VoxelWater_{sp.name}.mat"; AssetDatabase.DeleteAsset(wmPath);
            var wm = new Material(sh); VoxelWorld.MakeTransparent(wm, new Color(0.25f, 0.5f, 0.85f, 0.6f)); AssetDatabase.CreateAsset(wm, wmPath); w.waterMaterial = wm;

            res.chunks = w.Generate(v.editorRadiusChunks);
            var sPos = w.SpawnPoint(0, 0);
            res.spawn = new LevelBuilder.V3 { x = sPos.x, y = sPos.y, z = sPos.z };
            var player = GameObject.Find("Player");
            if (v.stream && player != null) w.target = player.transform;
            else if (v.stream) res.warnings.Add("no 'Player' in scene yet: set VoxelWorld.target after greybox to enable streaming");
            if (v.interact)
            {
                var cam = Camera.main;
                if (cam != null && cam.GetComponent<VoxelInteractor>() == null) cam.gameObject.AddComponent<VoxelInteractor>().world = w;
                else if (cam == null) res.warnings.Add("no Main Camera: add GDS.VoxelInteractor to the player camera for dig/place");
            }
        }

        // ======================================================================================= MARKERS
        static void PlaceMarkers(Transform root, Result res)
        {
            var spawn = GameObject.Find("PlayerSpawn") ?? new GameObject("PlayerSpawn");
            spawn.transform.SetParent(root, true);
            spawn.transform.position = res.spawn.V + Vector3.up * 0.05f;
            if (res.mode == "dungeon" || res.mode == "cave")
            {
                var goal = GameObject.Find("spawn_goal") ?? new GameObject("spawn_goal");
                goal.transform.SetParent(root, true); goal.transform.position = res.goal.V;
            }
            var player = GameObject.Find("Player");
            if (player == null && Camera.main != null)
            {
                // no player yet (world built before greybox): put the camera at eye height on the spawn, looking across the world
                var cam = Camera.main.transform; Undo.RecordObject(cam, "GDS spawn camera");
                cam.position = res.spawn.V + Vector3.up * 1.7f;
                var look = res.mode == "dungeon" || res.mode == "cave" ? res.goal.V : root.position;
                var dir = look - cam.position; dir.y = 0; if (dir.sqrMagnitude < 1f) dir = Vector3.forward;
                cam.rotation = Quaternion.LookRotation(dir.normalized) * Quaternion.Euler(8f, 0, 0);
            }
            if (player != null)
            {
                var cc = player.GetComponent<CharacterController>(); bool was = cc != null && cc.enabled; if (cc != null) cc.enabled = false;
                Undo.RecordObject(player.transform, "GDS spawn"); player.transform.position = res.spawn.V + Vector3.up * 1.1f;
                if (cc != null) cc.enabled = was;
            }
        }

        [MenuItem("GDS/Build World (art/world/*.json)")]
        static void Menu()
        {
            var path = EditorUtility.OpenFilePanel("World JSON", System.IO.Path.Combine(Common.ProjectDir, "art/world"), "json");
            if (!string.IsNullOrEmpty(path)) Debug.Log(BuildFromJson(System.IO.File.ReadAllText(path)));
        }
    }
}
