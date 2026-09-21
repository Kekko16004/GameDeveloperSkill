// GDS VFX — stylized particle prefabs from code (no Asset Store needed; Cartoon FX Free / Kenney sprites are optional upgrades).
// Usage (execute_code):
//   return GDS.VFX.CreateAll();                               // dust, hit, pickup, torch, smoke → Assets/_Game/Prefabs/VFX/
//   return GDS.VFX.Create("torch", "#FFB050");
//   return GDS.VFX.AttachTorches("torch_", 1.2f);              // put a torch flame on every object whose name starts with torch_
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace GDS
{
    public static class VFX
    {
        public const string Root = "Assets/_Game/Prefabs/VFX";

        public static string CreateAll()
        {
            var made = new[] { "dust", "hit", "pickup", "torch", "smoke", "sparkle" }.Select(k => Create(k)).ToList();
            return "[" + string.Join(",", made) + "]";
        }

        public static string Create(string kind, string colorHex = null)
        {
            Common.EnsureFolder(Root);
            var go = new GameObject("VFX_" + kind);
            var ps = go.AddComponent<ParticleSystem>();
            var main = ps.main; var em = ps.emission; var sh = ps.shape; var col = ps.colorOverLifetime; var sz = ps.sizeOverLifetime; var vel = ps.velocityOverLifetime;
            var r = go.GetComponent<ParticleSystemRenderer>();
            r.sharedMaterial = ParticleMaterial();
            main.playOnAwake = true; main.loop = false; main.simulationSpace = ParticleSystemSimulationSpace.World;
            Color c = Common.Hex(colorHex, Color.white);
            switch (kind)
            {
                case "dust":
                    c = colorHex == null ? new Color(0.75f, 0.68f, 0.55f) : c;
                    main.duration = 0.3f; main.startLifetime = 0.6f; main.startSpeed = 1.5f; main.startSize = new ParticleSystem.MinMaxCurve(0.15f, 0.35f); main.gravityModifier = -0.05f;
                    em.rateOverTime = 0; em.SetBursts(new[] { new ParticleSystem.Burst(0f, 12) });
                    sh.shapeType = ParticleSystemShapeType.Hemisphere; sh.radius = 0.2f;
                    Fade(col, c); Shrink(sz);
                    break;
                case "hit":
                    c = colorHex == null ? new Color(1f, 0.85f, 0.4f) : c;
                    main.duration = 0.2f; main.startLifetime = 0.35f; main.startSpeed = new ParticleSystem.MinMaxCurve(3f, 6f); main.startSize = new ParticleSystem.MinMaxCurve(0.05f, 0.15f); main.gravityModifier = 0.6f;
                    em.rateOverTime = 0; em.SetBursts(new[] { new ParticleSystem.Burst(0f, 18) });
                    sh.shapeType = ParticleSystemShapeType.Sphere; sh.radius = 0.05f;
                    r.renderMode = ParticleSystemRenderMode.Stretch; r.lengthScale = 3f; Fade(col, c);
                    break;
                case "pickup":
                case "sparkle":
                    c = colorHex == null ? new Color(0.6f, 0.9f, 1f) : c;
                    main.duration = 0.4f; main.startLifetime = 0.8f; main.startSpeed = 1.2f; main.startSize = new ParticleSystem.MinMaxCurve(0.06f, 0.14f); main.gravityModifier = -0.3f;
                    em.rateOverTime = 0; em.SetBursts(new[] { new ParticleSystem.Burst(0f, 20) });
                    sh.shapeType = ParticleSystemShapeType.Sphere; sh.radius = 0.3f;
                    Fade(col, c); Shrink(sz);
                    break;
                case "torch":
                    c = colorHex == null ? new Color(1f, 0.6f, 0.2f) : c;
                    main.loop = true; main.startLifetime = 0.6f; main.startSpeed = 0.8f; main.startSize = new ParticleSystem.MinMaxCurve(0.12f, 0.25f); main.gravityModifier = -0.4f;
                    em.rateOverTime = 24; sh.shapeType = ParticleSystemShapeType.Cone; sh.angle = 8f; sh.radius = 0.05f;
                    Fade(col, c, new Color(1f, 0.2f, 0.05f, 0f)); Shrink(sz);
                    var light = go.AddComponent<Light>(); light.type = LightType.Point; light.color = new Color(1f, 0.62f, 0.3f); light.intensity = 2.5f; light.range = 7f; light.shadows = LightShadows.None;
                    var lights = ps.lights; lights.enabled = false;
                    break;
                case "smoke":
                    c = colorHex == null ? new Color(0.35f, 0.35f, 0.38f) : c;
                    main.loop = true; main.startLifetime = 2.5f; main.startSpeed = 0.6f; main.startSize = new ParticleSystem.MinMaxCurve(0.3f, 0.6f); main.gravityModifier = -0.08f;
                    em.rateOverTime = 6; sh.shapeType = ParticleSystemShapeType.Cone; sh.angle = 12f; sh.radius = 0.1f;
                    Fade(col, c); var grow = ps.sizeOverLifetime; grow.enabled = true; grow.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.Linear(0, 0.4f, 1, 1f));
                    break;
                default: UnityEngine.Object.DestroyImmediate(go); return "{\"status\":\"FAIL\",\"error\":\"unknown kind " + Common.Esc(kind) + "\"}";
            }
            var path = $"{Root}/VFX_{kind}.prefab";
            PrefabUtility.SaveAsPrefabAsset(go, path);
            UnityEngine.Object.DestroyImmediate(go);
            return "{\"kind\":\"" + kind + "\",\"prefab\":\"" + path + "\"}";
        }

        public static string AttachTorches(string namePrefix = "torch", float heightOffset = 1.0f)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>($"{Root}/VFX_torch.prefab");
            if (prefab == null) { Create("torch"); prefab = AssetDatabase.LoadAssetAtPath<GameObject>($"{Root}/VFX_torch.prefab"); }
            int n = 0;
            foreach (var go in UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsSortMode.None).Where(t => t.name.StartsWith(namePrefix, StringComparison.OrdinalIgnoreCase)))
            {
                if (go.Find("VFX_torch") != null) continue;
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab, go);
                if (Common.TryGetBounds(go.gameObject, out var b)) inst.transform.position = new Vector3(b.center.x, b.max.y, b.center.z);
                else inst.transform.localPosition = Vector3.up * heightOffset;
                Undo.RegisterCreatedObjectUndo(inst, "GDS torch"); n++;
            }
            return "{\"attached\":" + n + "}";
        }

        static Material ParticleMaterial()
        {
            const string path = Root + "/Mat_ParticleAdditive.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m != null) return m;
            var sh = Shader.Find("Universal Render Pipeline/Particles/Unlit"); if (sh == null) sh = Shader.Find("Particles/Standard Unlit"); if (sh == null) sh = Shader.Find("Sprites/Default");
            m = new Material(sh);
            if (m.HasProperty("_Surface")) { m.SetFloat("_Surface", 1); m.SetFloat("_Blend", 1); m.SetOverrideTag("RenderType", "Transparent"); m.renderQueue = 3000; m.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha); m.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.One); m.SetFloat("_ZWrite", 0); m.EnableKeyword("_ALPHAPREMULTIPLY_ON"); }
            var tex = AssetDatabase.GetBuiltinExtraResource<Texture2D>("Default-Particle.psd");
            if (tex != null) { if (m.HasProperty("_BaseMap")) m.SetTexture("_BaseMap", tex); else m.mainTexture = tex; }
            AssetDatabase.CreateAsset(m, path);
            return m;
        }

        static void Fade(ParticleSystem.ColorOverLifetimeModule col, Color c, Color? end = null)
        {
            col.enabled = true;
            var g = new Gradient();
            var e = end ?? new Color(c.r, c.g, c.b, 0f);
            g.SetKeys(new[] { new GradientColorKey(c, 0f), new GradientColorKey(e, 1f) }, new[] { new GradientAlphaKey(1f, 0f), new GradientAlphaKey(0.8f, 0.5f), new GradientAlphaKey(0f, 1f) });
            col.color = g;
        }

        static void Shrink(ParticleSystem.SizeOverLifetimeModule sz) { sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.Linear(0, 1f, 1, 0f)); }

        [MenuItem("GDS/VFX/Create all stylized particle prefabs")] static void Menu() => Debug.Log(CreateAll());
    }
}
