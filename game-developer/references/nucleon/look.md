# Nucleon look and materials (lookdev, art review)

## 8. Look

- Project lighting `graphics.lighting = "modern"` (Lumen-like GI, reflections, volumetric fog) for stylized/realistic; `classic` for very low-end targets.
- Post process and sky: the Post Process panel / `lighting` table of the level or `project.ncproject`; sun = the Directional Light flagged `atmosphere_sun`.
- Lookdev preset = a `lighting`+`environment` table written by the lookdev worker into the level (`call entity_modify` on the sun + Project Settings) and a `shot` per preset view; art review as for Unity ([art-direction.md](art-direction.md)).
- Software rendering (CI, Xvfb/llvmpipe) washes colours out: art review only on screenshots from the owner's GPU.


## 8a. Materials: `scripts/nc_mat.py` (the material system of 21 October 2026)
Nucleon has Unreal's shading models as presets of one Substrate-style slab (engine docs `docs/rendering/MATERIAL_SYSTEM.md`,
`MATERIALS.md`): Default Lit, Unlit, Subsurface, Preintegrated Skin, Clear Coat, Subsurface Profile (`.ncsss`), Two Sided Foliage,
Hair, Cloth, Eye, Single Layer Water, Thin Translucent, Glass/Acrylic, Car Paint, Thin Film; plus layers (`layers`, `layerStack`
of `.ncmatfunc` layer functions), World Position Offset / material wind, parallax, triplanar, detail normals, material domains
(post process, sky, fog, decal, light function, volume, UI) and parameter collections (`.ncmpc`). A kit left on its glTF material is
Default Lit everywhere: the lookdev worker gives every surface its model.
- `nc_mat.py auto --project P --catalog art/kit-catalog.json --style <GDD style> --name <kit>`: every glTF/GLB slot gets a role
  (material and texture names; on an **atlas** texture only the catalog role, never water/glass/emissive guessed from an asset
  name), shared `.ncmat` in `Content/Materials/Auto/<kit>/` (one per role and texture set: the renderer batches **per material**,
  so few materials = few draws), separate PBR maps packed into ORM (`realistic`), GLB images extracted, and the vegetation wind of
  the plants (`wind = {type = "tree"|"bush"|"grass"}`: weighted by height, the trunk base stays; never on hills, buildings, stumps).
- `nc_mat.py assign --project P --map art/materials/<kit>.map.json` (editor CLOSED, `session-stop` first): `materials` and `wind` on the
  level's model entities. Run it after every `build --save` that placed kit pieces (the MCP `entity_add` has no materials field).
- `nc_mat.py make <role> OUT.ncmat [--texture T] [--set k=v]` for one surface: `glass`, `frosted`, `ice`, `crystal`, `stained`,
  `water`/`ocean`/`pool`/`swamp` (Single Layer Water, the engine's Ocean/Lake/Pool/Swamp numbers), `carPaint`, `lacquer`, `painted`,
  `cloth`, `velvet`, `skin`, `wax`, `jade`, `marble`, `hair`, `eye`, `neon`, `screen`, `holo`, `film`, `foliage`, `grass`... (`presets`
  lists them with their keys). Big water surfaces stay the Water entity (its own pass); the material is for ponds, pools, troughs.
- `nc_mat.py check --project P --editor NucleonEditor <files>`: every NEW shading model is "written and built, never run" in the engine:
  the check renders the Material document with models on and with `NC_MATERIAL_MODELS=0` (on the hidden desktop), and fails a black, flat or unchanged preview. The D3D12 editor draws the big preview blank in a window shot (engine notes D3): the check then measures the strip of model spheres under it, so a pass means "the models render", not "this material looks right": look at the PNG.
  A failing model goes to the engine notes (`docs/NUCLEON-ENGINE-NOTES.md`) and the material falls back to `defaultLit` with the
  same textures: never ship a surface nobody saw.
- A material replaces the slot completely (textures too): `auto` copies the glTF's maps; a hand-made `.ncmat` must name its maps.
- Triplanar / parallax replace or displace the mesh UVs: only on tileable sets, never on a kit atlas.

Material graph nodes added on 2026-10-29 (engine docs `MATERIAL_GRAPH.md`): Two Sided Sign, Shadow Pass Switch, Per Instance Random (variation per instance of an `instances` entity without a texture), Scene Color, Distance To Nearest Surface. Post Process materials (domain `postProcess`) are applied by a Post Process Volume `blendables` list or by the level's Post Process panel.
