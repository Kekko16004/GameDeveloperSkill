// GDS CLI commands — the GDS layer as first-class Unity CLI commands (com.unity.pipeline).
// Compiles only when the Pipeline package is in the project (asmdef define constraint GDS_PIPELINE).
//   unity command gds_world --spec art/world/overworld.json
//   unity command gds_lint --autofix true
//   unity run <project> --command gds_lint --format ndjson          (one-shot, batchmode)
// Every command returns the same JSON as the GDS.* method it wraps, and writes it under docs/lint/ when the method does.
// Without the package, the same calls work through `unity command eval "return GDS.SceneLint.RunJson();"` or CoplayDev execute_code.
using Unity.Pipeline.Commands;

namespace GDS
{
    public static class CliCommands
    {
        static bool B(string s) => s == "1" || string.Equals(s, "true", System.StringComparison.OrdinalIgnoreCase) || string.Equals(s, "yes", System.StringComparison.OrdinalIgnoreCase);

        [CliCommand("gds_ping", "GDS layer version and which optional modules compiled (ProBuilder, URP, Pipeline)")]
        public static string Ping()
        {
            bool pb = System.Type.GetType("GDS.PB, GDS.Editor.ProBuilder") != null;
            bool urp = UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline != null;
            return $"{{\"gds\":\"2026.09\",\"probuilder\":{(pb ? "true" : "false")},\"urp\":{(urp ? "true" : "false")},\"pipeline\":true,\"unity\":\"{UnityEngine.Application.unityVersion}\"}}";
        }

        [CliCommand("gds_build", "Build one blueprint JSON (art/blueprints/<name>.json) with GDS.LevelBuilder")]
        public static string Build([CliArg("blueprint", "project-relative blueprint path")] string blueprint)
            => LevelBuilder.BuildFromFile(blueprint);

        [CliCommand("gds_village", "Build a settlement from a village spec with GDS.Village")]
        public static string Village([CliArg("spec", "project-relative village JSON")] string spec)
            => GDS.Village.BuildFromFile(spec);

        [CliCommand("gds_world", "Procedural world (terrain | island | dungeon | cave | voxel) from art/world/<name>.json")]
        public static string World([CliArg("spec", "project-relative world JSON")] string spec)
            => GDS.World.BuildFromFile(spec);

        [CliCommand("gds_lint", "Scene lint: buried/floating props, colliders, pink/non-URP materials. Gate = issues 0")]
        public static string Lint([CliArg("autofix", "true to snap + add colliders + convert materials")] string autofix = "false")
            => SceneLint.RunJson(autoFix: B(autofix));

        [CliCommand("gds_lookdev", "Sun, fog, sky, URP Volume, camera post from a preset")]
        public static string Look([CliArg("preset", "stylized-day | stylized-sunset | dungeon-torch | night-moon | pastel-bright | scifi-cold | toon-bright | realistic-overcast")] string preset = "stylized-day",
                                  [CliArg("hdri", "optional .hdr asset path used as skybox")] string hdri = "")
            => LookDev.Apply(preset, string.IsNullOrEmpty(hdri) ? null : hdri);

        [CliCommand("gds_palette", "Create Mat_Palette_N materials from comma-separated hex colors")]
        public static string Palette([CliArg("colors", "#8C5A3C,#B8B0A0,...")] string colors)
            => LookDev.ApplyPalette(colors.Split(','));

        [CliCommand("gds_catalog", "Catalog a kit folder into art/kit-catalog.json (roles, sizes, suggested module)")]
        public static string Catalog([CliArg("folder", "Assets/_Game/Art/Kits/<family>/<pack>")] string folder)
            => KitCatalog.BuildJson(folder);

        [CliCommand("gds_kit_scale", "Set ONE import scale for a whole kit folder (catalog suggestedScale), batched reimport")]
        public static string KitScale([CliArg("folder", "Assets/_Game/Art/Kits/<family>/<pack>")] string folder,
                                      [CliArg("scale", "factor, e.g. 3.19")] string scale)
            => KitCatalog.SetImportScale(folder, float.Parse(scale, System.Globalization.CultureInfo.InvariantCulture));

        [CliCommand("gds_recolor", "Remap one kit material (e.g. leafsGreen) to a palette colour for every model in a folder")]
        public static string Recolor([CliArg("folder", "Assets/_Game/Art/Kits/<family>/<pack>")] string folder,
                                     [CliArg("material", "embedded material name, see get_material_properties / catalog")] string material,
                                     [CliArg("hex", "#RRGGBB (not --color: that is a global CLI flag)")] string hex)
            => LookDev.Recolor(folder, material, hex);

        [CliCommand("gds_vfx", "Create the base VFX prefabs (dust, hit, pickup, torch, smoke, sparkle)")]
        public static string Vfx() => VFX.CreateAll();

        [CliCommand("gds_shot", "Render a camera to PNG (game | aerial | hero | orbit0..7)")]
        public static string Shot([CliArg("out", "project-relative PNG path")] string output,
                                  [CliArg("view", "game | aerial | hero | orbitN")] string view = "game",
                                  [CliArg("width", "pixels")] string width = "1600",
                                  [CliArg("height", "pixels")] string height = "900")
            => Shots.Capture(output, int.TryParse(width, out var w) ? w : 1600, int.TryParse(height, out var h) ? h : 900, view);

        [CliCommand("gds_sheet", "Review sheet for the art director: game + aerial + orbits + hero")]
        public static string Sheet([CliArg("prefix", "screenshots/review/<phase>")] string prefix = "screenshots/review/shot")
            => Shots.Sheet(prefix);
    }
}
