// GDS Noise — deterministic value fields shared by GDS.World (editor) and VoxelWorld (runtime).
// Everything is seeded: same seed + same spec = same world, so a worker can rebuild instead of patching.
using UnityEngine;

namespace GDS
{
    public static class Noise
    {
        /// <summary>Per-seed offsets so different seeds sample different regions of Perlin space.</summary>
        public static Vector2 Offset(int seed, int salt = 0)
        {
            var r = new System.Random(seed * 7919 + salt * 104729);
            return new Vector2((float)r.NextDouble() * 10000f, (float)r.NextDouble() * 10000f);
        }

        /// <summary>Fractal Brownian motion in [0,1].</summary>
        public static float Fbm(float x, float z, Vector2 off, int octaves = 5, float lacunarity = 2f, float gain = 0.5f)
        {
            float sum = 0f, amp = 1f, freq = 1f, norm = 0f;
            for (int i = 0; i < octaves; i++)
            {
                sum += amp * Mathf.PerlinNoise(off.x + x * freq + i * 31.7f, off.y + z * freq + i * 17.3f);
                norm += amp; amp *= gain; freq *= lacunarity;
            }
            return sum / norm;
        }

        /// <summary>Ridged multifractal in [0,1]: sharp crests, good for mountains.</summary>
        public static float Ridged(float x, float z, Vector2 off, int octaves = 5, float lacunarity = 2f, float gain = 0.5f)
        {
            float sum = 0f, amp = 1f, freq = 1f, norm = 0f;
            for (int i = 0; i < octaves; i++)
            {
                float n = 1f - Mathf.Abs(Mathf.PerlinNoise(off.x + x * freq + i * 13.1f, off.y + z * freq + i * 7.9f) * 2f - 1f);
                sum += amp * n * n; norm += amp; amp *= gain; freq *= lacunarity;
            }
            return sum / norm;
        }

        /// <summary>Domain-warped fBm: organic coastlines and valleys instead of blobby Perlin.</summary>
        public static float Warped(float x, float z, Vector2 off, float warp, int octaves = 5)
        {
            if (warp <= 0f) return Fbm(x, z, off, octaves);
            float wx = Fbm(x + 5.2f, z + 1.3f, off, 3) - 0.5f;
            float wz = Fbm(x + 9.7f, z + 2.8f, off, 3) - 0.5f;
            return Fbm(x + wx * warp, z + wz * warp, off, octaves);
        }

        /// <summary>Cheap 3D noise in [0,1] (average of three axis planes). Good enough for caves.</summary>
        public static float Perlin3(float x, float y, float z, Vector2 off)
        {
            float xy = Mathf.PerlinNoise(off.x + x, off.y + y);
            float yz = Mathf.PerlinNoise(off.x + y + 37.1f, off.y + z + 11.9f);
            float xz = Mathf.PerlinNoise(off.x + x + 71.3f, off.y + z + 53.7f);
            return (xy + yz + xz) / 3f;
        }

        /// <summary>Stable hash in [0,1) for integer coordinates (tree placement, variants).</summary>
        public static float Hash01(int x, int y, int z, int seed)
        {
            unchecked
            {
                uint h = (uint)seed * 374761393u + (uint)x * 668265263u + (uint)y * 2246822519u + (uint)z * 3266489917u;
                h = (h ^ (h >> 13)) * 1274126177u;
                h ^= h >> 16;
                return (h & 0xFFFFFF) / 16777216f;
            }
        }
    }
}
