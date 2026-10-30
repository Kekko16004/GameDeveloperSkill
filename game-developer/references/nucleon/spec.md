# Nucleon deterministic layer: specs, kit catalog, worlds and look (level-build, world-gen, greybox, village, lookdev)

## 4. Deterministic layer for Nucleon

**Spec, not clicks.** A worker writes JSON, ncli builds it; the scene is never edited entity by entity.

`art/blueprints/<name>.json` (Nucleon flavour, example `templates/nucleon/specs/house_example.json`):

```json
{"name":"house_a","origin":[10,0,0],"yaw":0,"seed":7,
 "defaults":{"h":3,"wall":0.2,"wallColor":[0.8,0.78,0.72],"floorColor":[0.45,0.4,0.35]},
 "rooms":[{"name":"main","x":0,"y":0,"w":8,"d":6,"h":3,
           "doors":[{"side":"S","at":0.5,"width":1.2,"height":2.2}],
           "windows":[{"side":"E","at":0.5,"width":1.5,"sill":0.9,"height":2.0}],
           "ceiling":false,"omit":[]}],
 "pieces":[{"asset":"Content/Models/Crate.glb","position":[2,2,0],"rotation":[0,0,45],"scale":[1,1,1]}],
 "scatter":[{"name":"trees","assets":["Content/Models/Tree1.glb","Content/Models/Tree2.glb"],"count":30,
             "area":[-40,-40,40,40],"minDist":4,"scale":[0.8,1.3],"avoid":[[-2,-2,10,8]],"z":0}],
 "shapes":[{"name":"ramp","position":[0,-4,0.5],"shape":{"kind":"stairs","width":2,"depth":3,"height":1,"steps":6}}],
 "lights":[{"type":"point","position":[4,3,2.5],"intensity":60,"unit":"cd","range":8}],
 "cameras":[{"name":"Hero","position":[0,-12,6],"target":[4,3,1],"focalLength":35,"depthOfField":true,"fStop":2.8,"focusDistance":14}],
 "playerStart":{"position":[4,-3,0],"yaw":0}}
```

- Rooms: floor + four walls, one box per wall segment, door and window gaps cut by the builder (no CSG). Side `S` = min Y, `N` = max Y, `W` = min X, `E` = max X. Adjacent rooms share a wall: `omit` it on one of them.
- `pieces` / `scatter` take `.glb/.gltf/.fbx/.obj` models or `.ncactor` actors already in the project (`asset_search` / `asset_import` first: `call asset_import '{"sources":["/abs/art/exports/crate.glb"],"folder":"Content/Models/Kit"}'`).
- **Lights are in physical units** (`lightUnits = 2`): point / spot / rect / disc in candela (`"unit":"cd"`, or lumen), directional in lux, sky light a multiplier. 10 cd at 1 m is about a surface value of 1 at 0 EV, so an indoor lamp is 30-100 cd and `intensity: 400` is blown out (the old examples were). Fields: `type`, `position`, `rotation`, `color`, `intensity`, `unit`, `range`, `inner_cone`, `outer_cone`, `cast_shadows`, `atmosphere_sun` (the sun = a Directional Light flagged so).
- **Many repeated props = `instances`** (one entity, up to 100000 transforms, one draw path): `"instances":[{"name":"crate_field","asset":"Content/Models/Box.glb","collision":"none|box|capsule","cast_shadows":true,"cull_distance":0,"wind":"tree","transforms":[{"position":[8,0,0.5],"rotation":[0,0,30],"scale":0.6}]}]`, or `"performance":{"auto_group":true,"min_group":6}` to fold repeated models of `pieces` / `scatter` into groups. `collision` `mesh` is accepted but the runtime uses a box and logs a warning on every Play (engine notes D2): write `box`. Do not use instances for anything with identity (a pickup, a door): keep those as models / actors.
- **Cameras**: `"cameras":[{"name","position","target"|"rotation","fov"|"focalLength","depthOfField","fStop","focusDistance","manualExposure","ev100","defaultView"}]` (docs/engine/CAMERA.md: a plain camera has `fov`; a Cine camera has a physical lens: focal length, sensor, f-stop, focus distance). `defaultView: true` = the game starts through it; natives `SetActiveCamera`, `GetActiveCamera`, `GetCameraEntities`, `GetCameraEntityLens`, `SetCameraEntityLens` (a focus pull = a loop of `SetCameraEntityLens(cam, {focusDistance = d})`).
- **Render flags** on `shapes` / `pieces` (and `entity set` / `add` `render_flags`): `"renderFlags":{"castShadow":false,"receiveShadow":false,"visibleInRayTracing":false,"affectGI":false,"hiddenInGame":true,"lightingChannels":2,"customDepth":3}` (docs/engine/RENDER_FLAGS.md; snake_case names also work). `castShadow` now applies to shapes too (checked at `a58cb429`); `receiveShadow:false` lights the object as if nothing shadowed it (it still casts; it stays in the forward pass: a small cost); `lightingChannels` is a bit mask 0..7 (1 = channel 0, the default of every object AND every light): a light shines only on objects that share a channel, so put a character on channel 1 (`2`) and its rim light `"light":{"lighting_channels":2}` to light only it (fog, GI, ray traced lights and the sky light ignore channels); `customDepth` = the stencil 0..255 for the custom depth pass (outline / x-ray Post Process materials read it, -1 off). `hiddenInGame` = a marker or blocker that must exist in the editor and not in Play. At run time the same flags are natives: `SetEntityCastShadows`, `SetEntityReceivesShadows`, `SetEntityVisibleInRayTracing`, `SetEntityAffectsGlobalIllumination`, `SetEntityLightingChannels`, `SetEntityCustomDepth`, `SetLightLightingChannels`.
- **Post Process Volumes**: `"postVolumes":[{"name":"Night","position":[0,0,0],"size":[40,40,20],"unbound":false,"priority":1,"blendRadius":5,"weight":1,"settings":{"bloom":true,"exposure":-0.5},"blendables":[{"material":"Content/Materials/PP_Outline.ncmat","weight":0.8}]}]` (docs/rendering/POSTPROCESS.md; `settings` are the `Lighting` keys of the Post Process panel, `null` removes one; a blendable is a `.ncmat` whose domain is `postProcess`: `nc_mat.py make` a material, then `ncli material domain PATH --domain postProcess`; an `unbound` volume covers the whole level; a project-wide look is still `nc_world.py look`).
- Greybox = rooms + shapes only; art = same `name` with `pieces` (kit) → rebuild in place.
- **Kit catalog** (`python SKILL/scripts/nc_gds.py catalog Content/Models/<Kit> --project . --out art/kit-catalog.json`): every glTF/GLB/OBJ measured offline (display bounds, pivot, size), a role guessed from the name (`wall`, `wallDoor`, `wallWindow`, `floor`, `corner`, `fence`, `roof`, `stairs`, `building`, `tree`, `rock`, `plant`, `light`, `container`, `furniture`, `prop`), the wall module. Then specs say `{"role": "container"}` or `{"piece": "barrel"}` instead of a path, and rooms say `"kit": {}`: floor tiles, wall modules along each side, door/window modules at the openings, corners; lengths snap to the module.
- **Kit scale**: `"kitScale": 6` in a spec scales a miniature kit (KayKit hex: a 0.9 m house) once, with bounds and placement scaled correctly (or set the asset's `import.scale` in `Config/AssetDatabase.json`).
- **On a generated world**: `"origin": [x, y, "ground"]` takes the height of the flat spot of `art/world/*.layout.json` under the origin (a hard-coded z is wrong as soon as the terrain changes; the lint catches it).


## 4b. Worlds and look: `scripts/nc_world.py`

`python SKILL/scripts/nc_world.py build art/world/<name>.json --project .` — Python generates, the engine writes:

| mode | output | then |
|---|---|---|
| `terrain` / `island` | heightmap (warped fBm + ridged), layers by height/slope (solid-colour PNGs from the palette), grass foliage, flat spots (`flat: [{x, y, r, spawn}]`; `z` is accepted as another spelling of `y`), kit scatter at the **real** height (pivot-aware, `kitScale`), water for islands | `ncli exe run-lua Tools/gds_world_<name>.lua .` → `.land`; `nc_world.py attach . --name <name>` (editor closed: adds terrain + water, removes the template `Ground`); `ncli build art/blueprints/_world_<name>.json` |
| `dungeon` / `cave` | grid of rooms + corridors (MST + loops) or cellular cave; kit floor/wall pieces when the catalog has them, boxes otherwise; room props, torches | `ncli build ...` |
| `village` | plaza, bent roads, lots facing the road, kit houses (or `buildings` / greybox houses), fences, lamps, trees outside lots and roads | `ncli build ...` |

`reference` in the world JSON = numbers the worker measures on `art/reference/BOARD.md` (street width, lot size, relief, density, treeline, rooms...): the world follows the references, not the generator's defaults. Every mode writes `art/world/<name>.layout.json` (spawn, goal, rooms, lots, flats with their z) for the systems workers.

**Look**: `nc_world.py look . art/look/<name>.json` (editor closed) writes the level's `lighting` table (any `Lighting.set` / Post Process key: atmosphere, clouds, volumetric clouds, height fog, volumetric fog, light shafts, GI, bloom, exposure, tonemapper, SSAO, vignette...), the sun (azimuth / elevation / colour / intensity → `environment.sun` and the `Sun` entity) and ambient. Values come from the reference board; lessons from the glade demo: auto exposure + AgX + a strong warm height fog turn a sunny scene brown; for a stylized daytime start from `autoExposure=false, tonemapper="aces"`, sun 20-35°, height fog density ≤ 0.005 with `heightFogStart` 40+ (haze at the horizon only).
- Worlds: landscape (`.land`), foliage, water are authored with a Lua tool script run by `ncli exe run-lua Tools/make_world.lua <project>` (the engine's sample `samples/ThirdPersonDemo/Tools/make_world.lua` is the reference: `LandscapeNew`, `setHeightAt`, paint layers, foliage), seeded from `art/world/<name>.json`. The level then references the `.land` (`type = "terrain"`); after that ncli builds on top.
