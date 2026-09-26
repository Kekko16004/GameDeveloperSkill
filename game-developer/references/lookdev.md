# LookDev — why Kenney looks like a prototype, and the fix

A CC0 kit with default lighting, no fog, no tonemapping and no AO **is** a prototype look. The same kit with a sun angle, tri-light ambient, exponential fog, ACES, a little bloom, AO and a vignette reads as a finished stylized game. This phase is mandatory before any UI/playtest screenshot.

## One call

```
unity command gds_lookdev --preset stylized-day        # = eval "return GDS.LookDev.Apply(\"stylized-day\");"
```

| Preset | Use |
|---|---|
| `stylized-day` | default low-poly outdoor / village / city |
| `stylized-sunset` | warm hero moment, pirate, fantasy |
| `dungeon-torch` | interiors, dungeon; pair with `GDS.VFX.AttachTorches("torch")` and point lights |
| `night-moon` | horror / stealth |
| `pastel-bright` | playful, cozy, casual |
| `scifi-cold` | station, lab, space base |
| `toon-bright` | toon style: soft shadows, high saturation, no SSAO (pair with toon + outline packages) |
| `realistic-overcast` | stylized-realistic in Unity, soft diffuse light |
| `realistic-golden` | low warm sun, long shadows, atmospheric |

Optional HDRI sky (Poly Haven, CC0, allowed **for sky and ambient**): `Apply("stylized-day", hdriPath:"Assets/_Game/Art/HDRI/<name>_2k.hdr")`. Fetch via Blender MCP `download_polyhaven_asset(asset_type="hdris")` or `scripts/polyhaven.mjs`. Never put an HDRI *on* a prop material.

What it sets: Directional light (angle, color, soft shadows), `RenderSettings` tri-light ambient + exp² fog, `GDS/SkyGradient` skybox (top = sky tint, horizon = fog colour, sun disc from the light) or Panoramic HDRI, `Global_Volume` (Bloom, ACES Tonemapping, Color Adjustments, White Balance, Vignette) saved in `Assets/_Game/Settings/`, camera post-processing + SMAA, URP asset (HDR, MSAA 4x, 4 cascades, 80 m shadows, depth/opaque textures) and the SSAO renderer feature. Fog density is thinned automatically on terrains larger than 150 m.

Kit colours off-palette (e.g. Kenney nature leaves are teal #29C9AB): `unity command gds_recolor --folder <kit> --material leafsGreen --hex "#5E9E3A"` for each material listed in `art/kit-catalog.json → materials`. Remap at import, source files untouched, every instance updates.

Then, from the GDD palette: `return GDS.LookDev.ApplyPalette(new[]{"#8C5A3C","#B8B0A0","#5A6B4A","#C9A227"});` → `Mat_Palette_1..4` for ProBuilder shells and recolors.

Fine-tune with CoplayDev `manage_graphics` (`volume_set_effect`, `skybox_set_fog`, `feature_add`) — do not hand-edit YAML.

## Optional free packages (git URL in `Packages/manifest.json` or `manage_packages add_package`)

| Look | Package | Then |
|---|---|---|
| Cel / toon shading | `https://github.com/Delt06/urp-toon-shader.git?path=Packages/com.deltation.toon-shader` (MIT) | `GDS.LookDev.ConvertMaterials("Universal Render Pipeline/Lit", "Toon")` |
| Outlines (Unity 6 render graph) | `https://github.com/CristianQiu/Unity-URP-Outline.git` | add its renderer feature via `manage_graphics feature_add`, set rendering layer on props |
| Volumetric light shafts | `https://github.com/CristianQiu/Unity-URP-Volumetric-Light.git` | dungeon-torch / sunset presets |
| Watercolor / painterly post | `https://github.com/keijiro/KinoAqua.git` | one Volume override |
| Toon water | `https://github.com/JiahuanZhang/ToonWaterShader-URP` (copy shader) | lakes, moats |

Verify with `read_console` after each package. If a package breaks compilation, remove it — the six presets already give a beta look without them.

## Lights per genre (after Apply)

- Interiors: one Point light per torch/lamp prop (`GDS.VFX.AttachTorches`) — range 6–8, intensity 2–3, warm; ≤ 8 realtime point lights per scene, rest baked (`manage_graphics bake_start`).
- Outdoor: sun only + fog. Add 1 fill Point light near the objective (cool color) so the goal reads.
- Reflection probe at the level center (`manage_graphics bake_create_reflection_probe`) for metal materials.

## Gate (`docs/gates/08-lookdev.md`)

- `Assets/_Game/Settings/LookDev_<preset>.asset` + `Sky_<preset>.mat` exist
- `Global_Volume` in scene, `screenshots/035-lookdev.png` (Game view, post-processing visible: bloom on the sky/lights, vignette corners)
- `read_console` 0 errors
- SceneLint `issues: 0`
