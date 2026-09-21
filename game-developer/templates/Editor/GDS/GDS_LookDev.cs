// GDS LookDev — one call turns a flat kit scene into a lit, graded, stylized scene.
// Sun + ambient + fog + procedural/HDRI skybox + URP Volume (ACES, bloom, color, vignette) + camera post + URP asset quality + SSAO.
// Usage (execute_code):
//   return GDS.LookDev.Apply("stylized-day");                // presets: stylized-day | stylized-sunset | dungeon-torch | night-moon | pastel-bright | scifi-cold
//   return GDS.LookDev.Apply("stylized-day", hdriPath:"Assets/_Game/Art/HDRI/kloofendal_48d_partly_cloudy_2k.hdr");
//   return GDS.LookDev.ApplyPalette(new[]{"#8C5A3C","#B8B0A0","#5A6B4A","#C9A227"});
//   return GDS.LookDev.ConvertMaterials("Universal Render Pipeline/Lit", "Toon Shader");   // if a toon shader package is installed
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
#if GDS_URP
using UnityEngine.Rendering.Universal;
#endif

namespace GDS
{
    public static class LookDev
    {
        public class Preset
        {
            public string name;
            public Vector2 sunAngles; public string sunColor; public float sunIntensity; public float shadowStrength = 0.85f;
            public string ambSky, ambEquator, ambGround;
            public string fogColor; public float fogDensity;
            public string skyTint, skyGround; public float skyExposure = 1.2f, skyAtmosphere = 0.9f;
            public float bloom = 0.35f, bloomThreshold = 1.0f, bloomScatter = 0.6f;
            public float postExposure = 0.2f, contrast = 10f, saturation = 15f, temperature = 5f, vignette = 0.22f;
            public bool ssao = true;
        }

        public static readonly Dictionary<string, Preset> Presets = new Dictionary<string, Preset>(StringComparer.OrdinalIgnoreCase)
        {
            ["stylized-day"]    = new Preset { name = "stylized-day", sunAngles = new Vector2(50, -30), sunColor = "#FFF4E0", sunIntensity = 1.6f, ambSky = "#BFD8FF", ambEquator = "#C9D6DE", ambGround = "#6E6A5F", fogColor = "#C7D9EE", fogDensity = 0.006f, skyTint = "#7FB5FF", skyGround = "#4C5A66", skyExposure = 1.2f, bloom = 0.35f, saturation = 8, contrast = 8, vignette = 0.22f, temperature = 5 },
            ["stylized-sunset"] = new Preset { name = "stylized-sunset", sunAngles = new Vector2(18, -60), sunColor = "#FFB27A", sunIntensity = 1.3f, ambSky = "#6A5A8C", ambEquator = "#C57A7A", ambGround = "#3A2E33", fogColor = "#E8A27A", fogDensity = 0.012f, skyTint = "#E88C6A", skyGround = "#2E2836", skyExposure = 1.1f, skyAtmosphere = 1.2f, bloom = 0.6f, saturation = 20, contrast = 12, vignette = 0.3f, temperature = 15 },
            ["dungeon-torch"]   = new Preset { name = "dungeon-torch", sunAngles = new Vector2(60, 0), sunColor = "#3A4B7A", sunIntensity = 0.12f, shadowStrength = 0.6f, ambSky = "#1B2033", ambEquator = "#262231", ambGround = "#0E0C10", fogColor = "#0A0C14", fogDensity = 0.06f, skyTint = "#0A0C14", skyGround = "#050508", skyExposure = 0.2f, bloom = 0.9f, bloomThreshold = 0.8f, postExposure = 0.1f, contrast = 20, saturation = -5, vignette = 0.42f, temperature = -10 },
            ["night-moon"]      = new Preset { name = "night-moon", sunAngles = new Vector2(35, 20), sunColor = "#8FA8FF", sunIntensity = 0.45f, ambSky = "#223055", ambEquator = "#1A2036", ambGround = "#0A0C12", fogColor = "#101828", fogDensity = 0.02f, skyTint = "#1A2B55", skyGround = "#0A0C12", skyExposure = 0.4f, bloom = 0.7f, saturation = -10, contrast = 15, vignette = 0.35f, temperature = -20 },
            ["pastel-bright"]   = new Preset { name = "pastel-bright", sunAngles = new Vector2(55, -20), sunColor = "#FFFFFF", sunIntensity = 1.4f, shadowStrength = 0.6f, ambSky = "#E8F3FF", ambEquator = "#F3E8FF", ambGround = "#D0C8C0", fogColor = "#F0E6F5", fogDensity = 0.004f, skyTint = "#A6D8FF", skyGround = "#C9B7D8", skyExposure = 1.35f, bloom = 0.25f, contrast = -5, saturation = 25, vignette = 0.15f, temperature = 5 },
            ["scifi-cold"]      = new Preset { name = "scifi-cold", sunAngles = new Vector2(45, -90), sunColor = "#CFE8FF", sunIntensity = 1.3f, ambSky = "#4A6A8C", ambEquator = "#3A4C60", ambGround = "#202830", fogColor = "#7FA7C9", fogDensity = 0.01f, skyTint = "#3A6A9C", skyGround = "#1A2230", skyExposure = 0.9f, bloom = 0.5f, bloomThreshold = 0.9f, contrast = 15, saturation = 5, vignette = 0.3f, temperature = -15 },
        };

        public static string Apply(string presetName = "stylized-day", string hdriPath = null, bool ssao = true, bool touchUrpAsset = true)
        {
            if (!Presets.TryGetValue(presetName, out var p)) return "{\"status\":\"FAIL\",\"error\":\"unknown preset\",\"presets\":\"" + string.Join(",", Presets.Keys) + "\"}";
            var log = new List<string>();
            Common.EnsureFolder(Common.SettingsRoot);

            // --- sun
            var sun = UnityEngine.Object.FindObjectsByType<Light>(FindObjectsSortMode.None).FirstOrDefault(l => l.type == LightType.Directional);
            if (sun == null) { var go = new GameObject("Directional Light"); Undo.RegisterCreatedObjectUndo(go, "GDS Sun"); sun = go.AddComponent<Light>(); sun.type = LightType.Directional; }
            Undo.RecordObject(sun, "GDS LookDev");
            sun.transform.rotation = Quaternion.Euler(p.sunAngles.x, p.sunAngles.y, 0);
            sun.color = Common.Hex(p.sunColor, Color.white); sun.intensity = p.sunIntensity;
            sun.shadows = LightShadows.Soft; sun.shadowStrength = p.shadowStrength; sun.shadowBias = 0.02f; sun.shadowNormalBias = 0.4f;
            RenderSettings.sun = sun; log.Add("sun");

            // --- ambient + fog
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = Common.Hex(p.ambSky, Color.gray);
            RenderSettings.ambientEquatorColor = Common.Hex(p.ambEquator, Color.gray);
            RenderSettings.ambientGroundColor = Common.Hex(p.ambGround, Color.black);
            RenderSettings.fog = true; RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fogColor = Common.Hex(p.fogColor, Color.gray); RenderSettings.fogDensity = p.fogDensity;
            log.Add("ambient+fog");

            // --- skybox
            Material sky;
            if (!string.IsNullOrEmpty(hdriPath) && AssetDatabase.LoadAssetAtPath<Texture>(hdriPath) is Texture hdri)
            {
                sky = new Material(Shader.Find("Skybox/Panoramic"));
                sky.SetTexture("_MainTex", hdri); sky.SetFloat("_Exposure", p.skyExposure);
                RenderSettings.ambientMode = AmbientMode.Skybox; log.Add("skybox:hdri");
            }
            else
            {
                sky = new Material(Shader.Find("Skybox/Procedural"));
                sky.SetColor("_SkyTint", Common.Hex(p.skyTint, Color.cyan)); sky.SetColor("_GroundColor", Common.Hex(p.skyGround, Color.gray));
                sky.SetFloat("_Exposure", p.skyExposure); sky.SetFloat("_AtmosphereThickness", p.skyAtmosphere); sky.SetFloat("_SunSize", 0.04f);
                log.Add("skybox:procedural");
            }
            var skyPath = $"{Common.SettingsRoot}/Sky_{p.name}.mat";
            AssetDatabase.CreateAsset(sky, skyPath); RenderSettings.skybox = AssetDatabase.LoadAssetAtPath<Material>(skyPath);

#if GDS_URP
            // --- volume
            var volGo = GameObject.Find("Global_Volume"); if (volGo == null) volGo = new GameObject("Global_Volume");
            var vol = volGo.GetComponent<Volume>(); if (vol == null) vol = volGo.AddComponent<Volume>();
            vol.isGlobal = true; vol.priority = 0; vol.weight = 1;
            var profPath = $"{Common.SettingsRoot}/LookDev_{p.name}.asset";
            var prof = ScriptableObject.CreateInstance<VolumeProfile>();
            AssetDatabase.CreateAsset(prof, profPath);
            var bloom = prof.Add<Bloom>(true); bloom.intensity.Override(p.bloom); bloom.threshold.Override(p.bloomThreshold); bloom.scatter.Override(p.bloomScatter);
            var tone = prof.Add<Tonemapping>(true); tone.mode.Override(TonemappingMode.ACES);
            var ca = prof.Add<ColorAdjustments>(true); ca.postExposure.Override(p.postExposure); ca.contrast.Override(p.contrast); ca.saturation.Override(p.saturation);
            var wb = prof.Add<WhiteBalance>(true); wb.temperature.Override(p.temperature);
            var vig = prof.Add<Vignette>(true); vig.intensity.Override(p.vignette); vig.smoothness.Override(0.4f);
            EditorUtility.SetDirty(prof);
            vol.sharedProfile = AssetDatabase.LoadAssetAtPath<VolumeProfile>(profPath);
            log.Add("volume");

            // --- cameras: post-processing + AA
            foreach (var cam in UnityEngine.Object.FindObjectsByType<Camera>(FindObjectsSortMode.None))
            {
                var data = cam.GetUniversalAdditionalCameraData();
                if (data == null) continue;
                data.renderPostProcessing = true; data.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing; data.renderShadows = true;
                cam.allowHDR = true;
            }
            log.Add("camera-post");

            // --- URP asset quality
            if (touchUrpAsset && GraphicsSettings.currentRenderPipeline is UniversalRenderPipelineAsset urp)
            {
                urp.supportsHDR = true; urp.msaaSampleCount = 4; urp.shadowDistance = 80f; urp.shadowCascadeCount = 4;
                urp.supportsCameraDepthTexture = true; urp.supportsCameraOpaqueTexture = true; urp.colorGradingMode = ColorGradingMode.HighDynamicRange;
                EditorUtility.SetDirty(urp); log.Add("urp-asset");
                if (ssao && p.ssao) log.Add(TryAddRendererFeature(urp, "UnityEngine.Rendering.Universal.ScreenSpaceAmbientOcclusion") ? "ssao" : "ssao:skipped(use manage_graphics feature_add ScreenSpaceAmbientOcclusion)");
            }
#else
            log.Add("no-URP: volume/camera/ssao skipped");
#endif
            AssetDatabase.SaveAssets();
            EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
            return "{\"status\":\"PASS\",\"preset\":\"" + p.name + "\",\"applied\":[\"" + string.Join("\",\"", log) + "\"]}";
        }

#if GDS_URP
        // GetInstanceID is obsolete-as-error on Unity 6.5+ (EntityId); invoke via reflection so one source compiles on 6000.0 → 6000.5+.
        static long InstanceId(UnityEngine.Object o)
        {
            var m = typeof(UnityEngine.Object).GetMethod("GetInstanceID", Type.EmptyTypes);
            return m != null ? Convert.ToInt64(m.Invoke(o, null)) : 0L;
        }

        /// <summary>Add a URP renderer feature by type name via SerializedObject (works for internal URP features such as SSAO).</summary>
        public static bool TryAddRendererFeature(UniversalRenderPipelineAsset urp, string typeName)
        {
            try
            {
                var so = new SerializedObject(urp);
                var list = so.FindProperty("m_RendererDataList");
                if (list == null || list.arraySize == 0) return false;
                var rd = list.GetArrayElementAtIndex(0).objectReferenceValue as ScriptableRendererData;
                if (rd == null) return false;
                if (rd.rendererFeatures.Any(f => f != null && f.GetType().FullName == typeName)) return true;
                var type = AppDomain.CurrentDomain.GetAssemblies().Select(a => a.GetType(typeName)).FirstOrDefault(t => t != null);
                if (type == null) return false;
                var feature = (ScriptableRendererFeature)ScriptableObject.CreateInstance(type);
                feature.name = type.Name;
                AssetDatabase.AddObjectToAsset(feature, rd);
                var rso = new SerializedObject(rd);
                var feats = rso.FindProperty("m_RendererFeatures"); var map = rso.FindProperty("m_RendererFeatureMap");
                feats.arraySize++; feats.GetArrayElementAtIndex(feats.arraySize - 1).objectReferenceValue = feature;
                map.arraySize++; map.GetArrayElementAtIndex(map.arraySize - 1).longValue = InstanceId(feature);
                rso.ApplyModifiedProperties();
                EditorUtility.SetDirty(rd); AssetDatabase.SaveAssets();
                return true;
            }
            catch (Exception e) { Debug.LogWarning("[GDS LookDev] renderer feature: " + e.Message); return false; }
        }
#endif

        /// <summary>Create flat URP/Lit palette materials from GDD hex colors → Assets/_Game/Art/Materials/Mat_Palette_N.mat</summary>
        public static string ApplyPalette(string[] hex, float smoothness = 0.25f, string shaderName = "Universal Render Pipeline/Lit")
        {
            Common.EnsureFolder(Common.MaterialsRoot);
            var shader = Shader.Find(shaderName); if (shader == null) return "{\"status\":\"FAIL\",\"error\":\"shader not found\"}";
            var made = new List<string>();
            for (int i = 0; i < hex.Length; i++)
            {
                var m = new Material(shader); var c = Common.Hex(hex[i], Color.magenta);
                if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", c); else m.color = c;
                if (m.HasProperty("_Smoothness")) m.SetFloat("_Smoothness", smoothness);
                var path = $"{Common.MaterialsRoot}/Mat_Palette_{i + 1}.mat";
                AssetDatabase.CreateAsset(m, path); made.Add(path);
            }
            AssetDatabase.SaveAssets();
            return "{\"status\":\"PASS\",\"materials\":[\"" + string.Join("\",\"", made) + "\"]}";
        }

        /// <summary>Swap every material under Assets/_Game/Art that uses fromShader to toShader (e.g. an installed toon shader), keeping base color/map.</summary>
        public static string ConvertMaterials(string fromShader, string toShaderContains, string folder = Common.ArtRoot)
        {
            var target = Resources.FindObjectsOfTypeAll<Shader>().FirstOrDefault(s => s.name.IndexOf(toShaderContains, StringComparison.OrdinalIgnoreCase) >= 0 && !s.name.StartsWith("Hidden/"));
            if (target == null)
            {
                foreach (var g in AssetDatabase.FindAssets("t:Shader")) { var s = AssetDatabase.LoadAssetAtPath<Shader>(AssetDatabase.GUIDToAssetPath(g)); if (s != null && s.name.IndexOf(toShaderContains, StringComparison.OrdinalIgnoreCase) >= 0) { target = s; break; } }
            }
            if (target == null) return "{\"status\":\"FAIL\",\"error\":\"no shader containing '" + Common.Esc(toShaderContains) + "' — install one (see references/lookdev.md)\"}";
            int n = 0;
            foreach (var g in AssetDatabase.FindAssets("t:Material", new[] { folder }))
            {
                var m = AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(g));
                if (m == null || m.shader == null || m.shader.name != fromShader) continue;
                var col = m.HasProperty("_BaseColor") ? m.GetColor("_BaseColor") : m.color; var tex = m.HasProperty("_BaseMap") ? m.GetTexture("_BaseMap") : m.mainTexture;
                m.shader = target;
                if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", col); else if (m.HasProperty("_Color")) m.SetColor("_Color", col);
                if (tex != null) { if (m.HasProperty("_BaseMap")) m.SetTexture("_BaseMap", tex); else if (m.HasProperty("_MainTex")) m.SetTexture("_MainTex", tex); }
                EditorUtility.SetDirty(m); n++;
            }
            AssetDatabase.SaveAssets();
            return "{\"status\":\"PASS\",\"shader\":\"" + Common.Esc(target.name) + "\",\"converted\":" + n + "}";
        }

        [MenuItem("GDS/LookDev/stylized-day")] static void M1() => Debug.Log(Apply("stylized-day"));
        [MenuItem("GDS/LookDev/stylized-sunset")] static void M2() => Debug.Log(Apply("stylized-sunset"));
        [MenuItem("GDS/LookDev/dungeon-torch")] static void M3() => Debug.Log(Apply("dungeon-torch"));
        [MenuItem("GDS/LookDev/night-moon")] static void M4() => Debug.Log(Apply("night-moon"));
        [MenuItem("GDS/LookDev/pastel-bright")] static void M5() => Debug.Log(Apply("pastel-bright"));
        [MenuItem("GDS/LookDev/scifi-cold")] static void M6() => Debug.Log(Apply("scifi-cold"));
    }
}
