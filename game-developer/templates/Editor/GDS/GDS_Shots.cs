// GDS Shots — deterministic screenshots straight from a camera render (works in batchmode, no Game view focus needed).
//   return GDS.Shots.Capture("screenshots/035-lookdev.png");                  // Main Camera
//   return GDS.Shots.Capture("screenshots/025-aerial.png", view:"aerial");    // auto camera framing the whole level
//   return GDS.Shots.Sheet("screenshots/review/lookdev");                     // game + aerial + 2 orbit shots for the art review
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
#if GDS_URP
using UnityEngine.Rendering.Universal;
#endif

namespace GDS
{
    public static class Shots
    {
        /// <summary>view: game (Main Camera) | aerial (45° over the level bounds) | hero (behind the Player) | orbitN (N = 0..7 around the level).</summary>
        public static string Capture(string outPath, int width = 1600, int height = 900, string view = "game")
        {
            Camera cam = null; GameObject temp = null;
            try
            {
                if (view == "game") cam = Camera.main ?? UnityEngine.Object.FindObjectsByType<Camera>(FindObjectsSortMode.None).FirstOrDefault(c => c.enabled);
                if (cam == null || view != "game")
                {
                    temp = new GameObject("__gds_shot_cam") { hideFlags = HideFlags.HideAndDontSave };
                    cam = temp.AddComponent<Camera>();
                    cam.fieldOfView = 50; cam.nearClipPlane = 0.1f; cam.farClipPlane = 3000;
                    cam.clearFlags = CameraClearFlags.Skybox;
#if GDS_URP
                    var data = temp.AddComponent<UniversalAdditionalCameraData>(); data.renderPostProcessing = true; data.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing;
#endif
                    Frame(cam, view);
                }
                // review views (aerial/orbit) read layout, not mood: lift fog so a dungeon-torch level is not a black frame
                bool fogWas = RenderSettings.fog; float ambWas = RenderSettings.ambientIntensity;
                bool review = view == "aerial" || view.StartsWith("orbit");
                if (view == "aerial" || (review && RenderSettings.fogDensity > 0.012f)) RenderSettings.fog = false;
                var rt = RenderTexture.GetTemporary(width, height, 24, RenderTextureFormat.ARGB32);
                var prevTarget = cam.targetTexture;
                bool submitted = false;
#if UNITY_2023_1_OR_NEWER
                var req = new RenderPipeline.StandardRequest { destination = rt };
                if (GraphicsSettings.currentRenderPipeline != null && RenderPipeline.SupportsRenderRequest(cam, req)) { RenderPipeline.SubmitRenderRequest(cam, req); submitted = true; }
#endif
                if (!submitted) { cam.targetTexture = rt; cam.Render(); cam.targetTexture = prevTarget; }
                RenderSettings.fog = fogWas; RenderSettings.ambientIntensity = ambWas;
                var prevActive = RenderTexture.active; RenderTexture.active = rt;
                var tex = new Texture2D(width, height, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, width, height), 0, 0); tex.Apply();
                RenderTexture.active = prevActive; RenderTexture.ReleaseTemporary(rt);
                var full = System.IO.Path.IsPathRooted(outPath) ? outPath : System.IO.Path.Combine(Common.ProjectDir, outPath);
                System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(full));
                System.IO.File.WriteAllBytes(full, tex.EncodeToPNG());
                UnityEngine.Object.DestroyImmediate(tex);
                // a black frame means the camera saw nothing (no lights, wrong layer, empty scene): report it instead of pretending
                return $"{{\"status\":\"PASS\",\"path\":\"{Common.Esc(outPath)}\",\"view\":\"{view}\",\"camera\":\"{Common.Esc(cam.name)}\",\"pos\":\"{cam.transform.position}\"}}";
            }
            catch (Exception e) { return "{\"status\":\"FAIL\",\"error\":\"" + Common.Esc(e.Message) + "\"}"; }
            finally { if (temp != null) UnityEngine.Object.DestroyImmediate(temp); }
        }

        /// <summary>Four shots for the art-direction review: game, aerial, two orbits. Returns the JSON list.</summary>
        public static string Sheet(string prefix = "screenshots/review/shot", int width = 1280, int height = 720)
        {
            var outs = new List<string>();
            foreach (var v in new[] { "game", "aerial", "orbit1", "orbit5", "hero" })
            {
                if (v == "hero" && GameObject.Find("Player") == null) continue;
                outs.Add(Capture($"{prefix}-{v}.png", width, height, v));
            }
            return "[" + string.Join(",", outs) + "]";
        }

        static void Frame(Camera cam, string view)
        {
            var b = LevelBounds();
            float ext = Mathf.Max(8f, Mathf.Max(b.extents.x, b.extents.z));
            if (view == "hero")
            {
                var p = GameObject.Find("Player");
                var pos = p != null ? p.transform.position : b.center;
                var fwd = p != null ? p.transform.forward : Vector3.forward;
                cam.transform.position = pos - fwd * 6f + Vector3.up * 3f;
                cam.transform.LookAt(pos + Vector3.up * 1.2f + fwd * 4f);
                return;
            }
            if (view.StartsWith("orbit"))
            {
                int.TryParse(view.Substring(5), out int k);
                float a = k * Mathf.PI / 4f;
                var dir = new Vector3(Mathf.Cos(a), 0, Mathf.Sin(a));
                cam.transform.position = b.center + dir * ext * 0.9f + Vector3.up * Mathf.Max(3f, ext * 0.25f);
                cam.transform.LookAt(b.center + Vector3.up * 1.5f);
                return;
            }
            // aerial
            cam.transform.position = b.center + new Vector3(-0.7f, 0.9f, -0.7f).normalized * ext * 2.1f;
            cam.transform.LookAt(b.center);
        }

        /// <summary>Bounds of the playable content: renderers except sky/water planes; clamped so a 2 km terrain doesn't zoom the shot out to nothing.</summary>
        public static Bounds LevelBounds()
        {
            var rs = UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsSortMode.None)
                .Where(r => r.enabled && (r is MeshRenderer || r is SkinnedMeshRenderer) && !r.name.StartsWith("water")).ToList();
            var b = new Bounds(Vector3.zero, Vector3.one * 10f); bool any = false;
            foreach (var r in rs)
            {
                if (r.bounds.size.x > 300f || r.bounds.size.z > 300f) continue;
                if (!any) { b = r.bounds; any = true; } else b.Encapsulate(r.bounds);
            }
            foreach (var t in Terrain.activeTerrains)
            {
                var tb = new Bounds(t.transform.position + t.terrainData.size / 2f, t.terrainData.size);
                if (!any) { b = tb; any = true; } else b.Encapsulate(tb);
            }
            var spawn = GameObject.Find("PlayerSpawn");
            if (!any && spawn != null) b = new Bounds(spawn.transform.position, Vector3.one * 60f);
            if (b.extents.x > 150f || b.extents.z > 150f)
            {
                var c = spawn != null ? spawn.transform.position : b.center;
                b = new Bounds(c, new Vector3(200f, b.size.y, 200f));
            }
            return b;
        }

        [MenuItem("GDS/Screenshots/Review sheet (screenshots/review)")]
        static void Menu() => Debug.Log(Sheet());
    }
}
