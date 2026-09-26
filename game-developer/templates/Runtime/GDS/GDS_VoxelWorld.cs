// GDS VoxelWorld — chunked, seeded, editable block world (Minecraft-like) with greedy meshing.
// Editor: GDS.World.BuildFromFile("art/world/<name>.json") with "mode":"voxel" creates and previews it.
// Runtime: streams chunks around `target`, SetBlock/RaycastBlock for dig & place (see VoxelInteractor).
// One opaque mesh + collider per chunk, one water mesh (no collider). Colors come from a palette texture
// (16x4 texture: one column per block id, rows bottom / side / top shading), so URP/Lit works without a custom shader.
using System.Collections.Generic;
using UnityEngine;

namespace GDS
{
    public enum Block : byte { Air = 0, Grass, Dirt, Stone, Sand, Water, Wood, Leaves, Snow, Gravel, Planks, Brick }

    [DisallowMultipleComponent]
    public class VoxelWorld : MonoBehaviour
    {
        [Header("Shape")]
        public int seed = 1;
        public int chunkSize = 16;
        public int height = 64;
        public int baseHeight = 20;
        public float heightAmp = 22f;
        public float scale = 0.018f;
        public int octaves = 4;
        public float mountains = 0.5f;          // 0 = rolling hills, 1 = sharp ridges
        public int seaLevel = 17;
        public int snowLine = 44;
        public bool caves = true;
        [Range(0.5f, 0.8f)] public float caveThreshold = 0.64f;
        [Range(0f, 0.05f)] public float treeChance = 0.012f;

        [Header("Streaming")]
        public Transform target;                // player; null = static world around the origin
        public int viewRadiusChunks = 5;
        public int buildsPerFrame = 2;
        public int editorRadiusChunks = 3;

        [Header("Look")]
        public Material material;               // URP/Lit with the palette texture (GDS.World creates it)
        public Material waterMaterial;
        public Color[] palette =
        {
            new Color(0,0,0,0), new Color32(106,170,74,255), new Color32(134,96,67,255), new Color32(128,128,132,255),
            new Color32(219,203,145,255), new Color32(64,120,200,180), new Color32(102,76,50,255), new Color32(58,120,50,255),
            new Color32(240,244,250,255), new Color32(136,126,120,255), new Color32(176,138,90,255), new Color32(160,70,60,255),
        };

        class Chunk { public Vector2Int key; public byte[] data; public GameObject go; public MeshFilter mf; public MeshCollider mc; public MeshFilter waterMf; public bool dirty; }
        readonly Dictionary<Vector2Int, Chunk> chunks = new Dictionary<Vector2Int, Chunk>();
        Vector2 offHeight, offRidge, offCave;

        int Idx(int x, int y, int z) => (y * chunkSize + z) * chunkSize + x;

        void Init()
        {
            offHeight = Noise.Offset(seed, 1); offRidge = Noise.Offset(seed, 2); offCave = Noise.Offset(seed, 3);
            EnsureMaterials();
        }

        // ---------------------------------------------------------------- generation
        public int SurfaceHeight(int wx, int wz)
        {
            float h = Noise.Fbm(wx * scale, wz * scale, offHeight, octaves);
            float r = Noise.Ridged(wx * scale * 0.6f, wz * scale * 0.6f, offRidge, 4);
            float mask = Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(0.45f, 0.75f, Noise.Fbm(wx * scale * 0.25f, wz * scale * 0.25f, offRidge, 2)));
            float v = baseHeight + (h - 0.5f) * 2f * heightAmp + r * heightAmp * 1.6f * mountains * mask;
            return Mathf.Clamp(Mathf.RoundToInt(v), 2, height - 8);
        }

        byte Generate(int wx, int y, int wz, int surface)
        {
            if (y == 0) return (byte)Block.Stone;
            if (y > surface) return y <= seaLevel ? (byte)Block.Water : (byte)Block.Air;
            if (caves && y > 3 && y < surface - 3 && Noise.Perlin3(wx * 0.07f, y * 0.1f, wz * 0.07f, offCave) > caveThreshold) return (byte)Block.Air;
            if (y == surface)
            {
                if (surface <= seaLevel + 1) return (byte)Block.Sand;
                if (surface >= snowLine) return (byte)Block.Snow;
                if (surface >= snowLine - 6) return (byte)Block.Stone;
                return (byte)Block.Grass;
            }
            if (y > surface - 4) return surface <= seaLevel + 1 ? (byte)Block.Sand : (byte)Block.Dirt;
            return (byte)Block.Stone;
        }

        Chunk CreateChunk(Vector2Int key)
        {
            var c = new Chunk { key = key, data = new byte[chunkSize * height * chunkSize] };
            int ox = key.x * chunkSize, oz = key.y * chunkSize;
            var surf = new int[chunkSize, chunkSize];
            for (int z = 0; z < chunkSize; z++)
                for (int x = 0; x < chunkSize; x++)
                {
                    int s = SurfaceHeight(ox + x, oz + z); surf[x, z] = s;
                    for (int y = 0; y < height; y++) c.data[Idx(x, y, z)] = Generate(ox + x, y, oz + z, s);
                }
            // trees stay inside the chunk (margin 2) so neighbours never need to know about them
            for (int z = 2; z < chunkSize - 2; z++)
                for (int x = 2; x < chunkSize - 2; x++)
                {
                    int s = surf[x, z];
                    if (c.data[Idx(x, s, z)] != (byte)Block.Grass || s + 7 >= height) continue;
                    if (Noise.Hash01(ox + x, s, oz + z, seed) >= treeChance) continue;
                    int trunk = 4 + (int)(Noise.Hash01(ox + x, 1, oz + z, seed) * 2f);
                    for (int t = 1; t <= trunk; t++) c.data[Idx(x, s + t, z)] = (byte)Block.Wood;
                    int top = s + trunk;
                    for (int dy = -1; dy <= 2; dy++)
                        for (int dz = -2; dz <= 2; dz++)
                            for (int dx = -2; dx <= 2; dx++)
                            {
                                int rad = dy >= 1 ? 1 : 2;
                                if (Mathf.Abs(dx) > rad || Mathf.Abs(dz) > rad || (Mathf.Abs(dx) == 2 && Mathf.Abs(dz) == 2)) continue;
                                int i = Idx(x + dx, top + dy, z + dz);
                                if (c.data[i] == (byte)Block.Air) c.data[i] = (byte)Block.Leaves;
                            }
                }
            return c;
        }

        // ---------------------------------------------------------------- block access
        public byte GetBlock(int wx, int y, int wz)
        {
            if (y < 0) return (byte)Block.Stone;
            if (y >= height) return (byte)Block.Air;
            var key = new Vector2Int(Mathf.FloorToInt(wx / (float)chunkSize), Mathf.FloorToInt(wz / (float)chunkSize));
            if (chunks.TryGetValue(key, out var c) && c.data != null)
                return c.data[Idx(wx - key.x * chunkSize, y, wz - key.y * chunkSize)];
            return Generate(wx, y, wz, SurfaceHeight(wx, wz));   // unloaded neighbour: same deterministic answer (trees excluded)
        }

        public byte GetBlock(Vector3Int p) => GetBlock(p.x, p.y, p.z);

        /// <summary>Set a block in world block coordinates and rebuild the touched chunk(s).</summary>
        public bool SetBlock(Vector3Int p, Block b)
        {
            if (p.y < 1 || p.y >= height) return false;
            var key = new Vector2Int(Mathf.FloorToInt(p.x / (float)chunkSize), Mathf.FloorToInt(p.z / (float)chunkSize));
            if (!chunks.TryGetValue(key, out var c)) return false;
            int lx = p.x - key.x * chunkSize, lz = p.z - key.y * chunkSize;
            c.data[Idx(lx, p.y, lz)] = (byte)b;
            Rebuild(c);
            if (lx == 0) RebuildKey(key + Vector2Int.left);
            if (lx == chunkSize - 1) RebuildKey(key + Vector2Int.right);
            if (lz == 0) RebuildKey(key + Vector2Int.down);
            if (lz == chunkSize - 1) RebuildKey(key + Vector2Int.up);
            return true;
        }

        void RebuildKey(Vector2Int k) { if (chunks.TryGetValue(k, out var n)) Rebuild(n); }

        /// <summary>Voxel DDA raycast. hit = solid block, before = the empty cell in front of it (for placing).</summary>
        public bool RaycastBlock(Ray ray, float maxDist, out Vector3Int hit, out Vector3Int before)
        {
            var o = transform.InverseTransformPoint(ray.origin); var d = transform.InverseTransformDirection(ray.direction).normalized;
            var cell = Vector3Int.FloorToInt(o); before = cell; hit = cell;
            var step = new Vector3Int(d.x > 0 ? 1 : -1, d.y > 0 ? 1 : -1, d.z > 0 ? 1 : -1);
            var tDelta = new Vector3(d.x == 0 ? float.MaxValue : Mathf.Abs(1f / d.x), d.y == 0 ? float.MaxValue : Mathf.Abs(1f / d.y), d.z == 0 ? float.MaxValue : Mathf.Abs(1f / d.z));
            var tMax = new Vector3(
                d.x == 0 ? float.MaxValue : ((d.x > 0 ? cell.x + 1 - o.x : o.x - cell.x) * tDelta.x),
                d.y == 0 ? float.MaxValue : ((d.y > 0 ? cell.y + 1 - o.y : o.y - cell.y) * tDelta.y),
                d.z == 0 ? float.MaxValue : ((d.z > 0 ? cell.z + 1 - o.z : o.z - cell.z) * tDelta.z));
            float t = 0f;
            while (t <= maxDist)
            {
                var b = GetBlock(cell);
                if (b != (byte)Block.Air && b != (byte)Block.Water) { hit = cell; return true; }
                before = cell;
                if (tMax.x < tMax.y && tMax.x < tMax.z) { cell.x += step.x; t = tMax.x; tMax.x += tDelta.x; }
                else if (tMax.y < tMax.z) { cell.y += step.y; t = tMax.y; tMax.y += tDelta.y; }
                else { cell.z += step.z; t = tMax.z; tMax.z += tDelta.z; }
            }
            return false;
        }

        /// <summary>World position standing on top of the column (for player spawn).</summary>
        public Vector3 SpawnPoint(int wx = 0, int wz = 0)
        {
            if (offHeight == Vector2.zero) Init();
            for (int r = 0; r < 64; r++)
                for (int a = 0; a < 8; a++)
                {
                    int x = wx + Mathf.RoundToInt(Mathf.Cos(a * Mathf.PI / 4) * r), z = wz + Mathf.RoundToInt(Mathf.Sin(a * Mathf.PI / 4) * r);
                    int s = SurfaceHeight(x, z);
                    if (s > seaLevel) return transform.TransformPoint(new Vector3(x + 0.5f, s + 1.05f, z + 0.5f));
                }
            return transform.TransformPoint(new Vector3(wx + 0.5f, SurfaceHeight(wx, wz) + 1.05f, wz + 0.5f));
        }

        // ---------------------------------------------------------------- lifecycle
        /// <summary>Clear and build a square of chunks around the origin (editor preview / static worlds).</summary>
        public int Generate(int radiusChunks = -1)
        {
            if (radiusChunks < 0) radiusChunks = editorRadiusChunks;
            Clear(); Init();
            for (int z = -radiusChunks; z < radiusChunks; z++)
                for (int x = -radiusChunks; x < radiusChunks; x++)
                    Load(new Vector2Int(x, z));
            return chunks.Count;
        }

        public void Clear()
        {
            chunks.Clear();
            for (int i = transform.childCount - 1; i >= 0; i--)
            {
                var ch = transform.GetChild(i).gameObject;
                if (!ch.name.StartsWith("chunk_")) continue;
                if (Application.isPlaying) Destroy(ch); else DestroyImmediate(ch);
            }
        }

        void Start()
        {
            if (!Application.isPlaying) return;
            // editor-baked chunks are kept for static worlds; streaming rebuilds around the target deterministically
            if (target != null) { Clear(); Init(); StreamAround(true); }
            else if (chunks.Count == 0) Generate(viewRadiusChunks);
        }

        void Update()
        {
            if (Application.isPlaying && target != null) StreamAround(false);
        }

        void StreamAround(bool immediateNear)
        {
            var lp = transform.InverseTransformPoint(target.position);
            var center = new Vector2Int(Mathf.FloorToInt(lp.x / chunkSize), Mathf.FloorToInt(lp.z / chunkSize));
            int built = 0; bool budgetLeft = true;
            for (int r = 0; r <= viewRadiusChunks && budgetLeft; r++)
                for (int z = -r; z <= r && budgetLeft; z++)
                    for (int x = -r; x <= r && budgetLeft; x++)
                    {
                        if (Mathf.Max(Mathf.Abs(x), Mathf.Abs(z)) != r) continue;
                        var k = center + new Vector2Int(x, z);
                        if (chunks.ContainsKey(k)) continue;
                        if (!(immediateNear && r <= 1) && built >= buildsPerFrame) { budgetLeft = false; break; }
                        Load(k); built++;
                    }
            var drop = new List<Vector2Int>();
            foreach (var kv in chunks)
                if (Mathf.Max(Mathf.Abs(kv.Key.x - center.x), Mathf.Abs(kv.Key.y - center.y)) > viewRadiusChunks + 2) drop.Add(kv.Key);
            foreach (var k in drop) { Destroy(chunks[k].go); chunks.Remove(k); }
        }

        void Load(Vector2Int key)
        {
            var c = CreateChunk(key);
            c.go = new GameObject($"chunk_{key.x}_{key.y}");
            c.go.transform.SetParent(transform, false);
            c.go.transform.localPosition = new Vector3(key.x * chunkSize, 0, key.y * chunkSize);
            c.go.isStatic = !Application.isPlaying;
            c.mf = c.go.AddComponent<MeshFilter>();
            c.go.AddComponent<MeshRenderer>().sharedMaterial = material;
            c.mc = c.go.AddComponent<MeshCollider>();
            var w = new GameObject("water"); w.transform.SetParent(c.go.transform, false);
            c.waterMf = w.AddComponent<MeshFilter>();
            var wr = w.AddComponent<MeshRenderer>(); wr.sharedMaterial = waterMaterial; wr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            var trig = w.AddComponent<BoxCollider>(); trig.isTrigger = true;
            trig.center = new Vector3(chunkSize / 2f, seaLevel / 2f + 0.5f, chunkSize / 2f); trig.size = new Vector3(chunkSize, seaLevel + 0.8f, chunkSize);
            chunks[key] = c;
            Rebuild(c);
        }

        // ---------------------------------------------------------------- meshing
        static bool Opaque(byte b) => b != (byte)Block.Air && b != (byte)Block.Water;

        byte At(Chunk c, int x, int y, int z)
        {
            if (y < 0) return (byte)Block.Stone;
            if (y >= height) return (byte)Block.Air;
            if (x >= 0 && x < chunkSize && z >= 0 && z < chunkSize) return c.data[Idx(x, y, z)];
            return GetBlock(c.key.x * chunkSize + x, y, c.key.y * chunkSize + z);
        }

        void Rebuild(Chunk c)
        {
            var verts = new List<Vector3>(); var norms = new List<Vector3>(); var uvs = new List<Vector2>(); var tris = new List<int>();
            int[] dims = { chunkSize, height, chunkSize };
            for (int d = 0; d < 3; d++)
            {
                int u = (d + 1) % 3, v = (d + 2) % 3;
                var x = new int[3]; var q = new int[3]; q[d] = 1;
                var mask = new int[dims[u] * dims[v]];
                for (x[d] = -1; x[d] < dims[d];)
                {
                    int n = 0;
                    for (x[v] = 0; x[v] < dims[v]; x[v]++)
                        for (x[u] = 0; x[u] < dims[u]; x[u]++, n++)
                        {
                            byte a = At(c, x[0], x[1], x[2]);
                            byte b = At(c, x[0] + q[0], x[1] + q[1], x[2] + q[2]);
                            bool aIn = x[d] >= 0, bIn = x[d] < dims[d] - 1;
                            if (Opaque(a) && !Opaque(b) && aIn) mask[n] = a;
                            else if (Opaque(b) && !Opaque(a) && bIn) mask[n] = -b;
                            else mask[n] = 0;
                        }
                    x[d]++;
                    n = 0;
                    for (int j = 0; j < dims[v]; j++)
                        for (int i = 0; i < dims[u];)
                        {
                            int m = mask[n];
                            if (m == 0) { i++; n++; continue; }
                            int w = 1; while (i + w < dims[u] && mask[n + w] == m) w++;
                            int h = 1; bool done = false;
                            for (; j + h < dims[v]; h++)
                            {
                                for (int k = 0; k < w; k++) if (mask[n + k + h * dims[u]] != m) { done = true; break; }
                                if (done) break;
                            }
                            x[u] = i; x[v] = j;
                            var du = new int[3]; du[u] = w; var dv = new int[3]; dv[v] = h;
                            var p0 = new Vector3(x[0], x[1], x[2]);
                            var p1 = p0 + new Vector3(du[0], du[1], du[2]);
                            var p3 = p0 + new Vector3(dv[0], dv[1], dv[2]);
                            var p2 = p1 + (p3 - p0);
                            var nrm = Vector3.zero; nrm[d] = m > 0 ? 1 : -1;
                            int id = Mathf.Abs(m);
                            AddQuad(verts, norms, uvs, tris, p0, p1, p2, p3, nrm, PaletteUv(id, d == 1 ? (m > 0 ? 2 : 0) : 1));
                            for (int l = 0; l < h; l++) for (int k = 0; k < w; k++) mask[n + k + l * dims[u]] = 0;
                            i += w; n += w;
                        }
                }
            }
            var mesh = c.mf.sharedMesh != null ? c.mf.sharedMesh : new Mesh { name = c.go.name };
            mesh.Clear();
            mesh.indexFormat = verts.Count > 65000 ? UnityEngine.Rendering.IndexFormat.UInt32 : UnityEngine.Rendering.IndexFormat.UInt16;
            mesh.SetVertices(verts); mesh.SetNormals(norms); mesh.SetUVs(0, uvs); mesh.SetTriangles(tris, 0);
            mesh.RecalculateBounds();
            c.mf.sharedMesh = mesh;
            c.mc.sharedMesh = null; c.mc.sharedMesh = verts.Count > 0 ? mesh : null;

            // water: top faces only, where air sits above
            var wv = new List<Vector3>(); var wn = new List<Vector3>(); var wu = new List<Vector2>(); var wt = new List<int>();
            var wuv = PaletteUv((int)Block.Water, 2);
            for (int z = 0; z < chunkSize; z++)
                for (int xx = 0; xx < chunkSize; xx++)
                {
                    int y = seaLevel;
                    if (c.data[Idx(xx, y, z)] != (byte)Block.Water || At(c, xx, y + 1, z) != (byte)Block.Air) continue;
                    float top = y + 0.88f;
                    AddQuad(wv, wn, wu, wt, new Vector3(xx, top, z), new Vector3(xx + 1, top, z), new Vector3(xx + 1, top, z + 1), new Vector3(xx, top, z + 1), Vector3.up, wuv);
                }
            var wm = c.waterMf.sharedMesh != null ? c.waterMf.sharedMesh : new Mesh { name = c.go.name + "_water" };
            wm.Clear(); wm.SetVertices(wv); wm.SetNormals(wn); wm.SetUVs(0, wu); wm.SetTriangles(wt, 0); wm.RecalculateBounds();
            c.waterMf.sharedMesh = wm;
        }

        static void AddQuad(List<Vector3> v, List<Vector3> n, List<Vector2> uv, List<int> t, Vector3 p0, Vector3 p1, Vector3 p2, Vector3 p3, Vector3 nrm, Vector2 cellUv)
        {
            int b = v.Count;
            v.Add(p0); v.Add(p1); v.Add(p2); v.Add(p3);
            for (int i = 0; i < 4; i++) { n.Add(nrm); uv.Add(cellUv); }
            // Unity: front face = cross(b-a, c-a) along the normal
            if (Vector3.Dot(Vector3.Cross(p1 - p0, p2 - p0), nrm) > 0) { t.Add(b); t.Add(b + 1); t.Add(b + 2); t.Add(b); t.Add(b + 2); t.Add(b + 3); }
            else { t.Add(b); t.Add(b + 2); t.Add(b + 1); t.Add(b); t.Add(b + 3); t.Add(b + 2); }
        }

        // ---------------------------------------------------------------- materials
        // Power-of-two palette so no importer ever rescales it (a rescaled 12x3 put UVs exactly on texel borders = striped faces).
        public const int PaletteW = 16, PaletteH = 4;
        static Vector2 PaletteUv(int id, int row) => new Vector2((Mathf.Clamp(id, 0, PaletteW - 1) + 0.5f) / PaletteW, (row + 0.5f) / PaletteH);

        /// <summary>Palette texture: one column per block id (max 16), rows = bottom / side / top brightness.</summary>
        public Texture2D BuildPaletteTexture()
        {
            var tex = new Texture2D(PaletteW, PaletteH, TextureFormat.RGBA32, false) { filterMode = FilterMode.Point, wrapMode = TextureWrapMode.Clamp, name = "VoxelPalette" };
            float[] shade = { 0.62f, 0.82f, 1f, 1f };
            for (int y = 0; y < PaletteH; y++)
                for (int x = 0; x < PaletteW; x++)
                {
                    var c = x < palette.Length ? palette[x] : Color.magenta;
                    tex.SetPixel(x, y, new Color(c.r * shade[y], c.g * shade[y], c.b * shade[y], c.a));
                }
            tex.Apply();
            return tex;
        }

        void EnsureMaterials()
        {
            if (material != null && waterMaterial != null) return;
            var sh = Shader.Find("Universal Render Pipeline/Lit"); if (sh == null) sh = Shader.Find("Standard");
            var tex = BuildPaletteTexture();
            if (material == null)
            {
                material = new Material(sh) { name = "Voxel_Runtime" };
                if (material.HasProperty("_BaseMap")) material.SetTexture("_BaseMap", tex); else material.mainTexture = tex;
                if (material.HasProperty("_Smoothness")) material.SetFloat("_Smoothness", 0.05f);
            }
            if (waterMaterial == null)
            {
                waterMaterial = new Material(sh) { name = "VoxelWater_Runtime" };
                MakeTransparent(waterMaterial, new Color(0.25f, 0.5f, 0.85f, 0.6f));
            }
        }

        public static void MakeTransparent(Material m, Color c)
        {
            if (m.HasProperty("_Surface")) { m.SetFloat("_Surface", 1); m.SetFloat("_Blend", 0); m.SetOverrideTag("RenderType", "Transparent"); m.renderQueue = 3000; m.SetFloat("_ZWrite", 0); m.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha); m.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha); m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); }
            if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", c); else m.color = c;
            if (m.HasProperty("_Smoothness")) m.SetFloat("_Smoothness", 0.85f);
        }
    }
}
