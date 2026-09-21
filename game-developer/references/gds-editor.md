# GDS Editor scripts — the deterministic layer (install once per project)

The LLM does not place pieces one by one and does not "look at a PNG" to judge 10 cm. C# does it.
Source: `SKILL/templates/Editor/GDS/` → copy to `PROJECT/Assets/_Game/Editor/GDS/` (worker **project** does it, or run
`powershell -File SKILL/scripts/install-gds-editor.ps1 -ProjectPath PROJECT`).

Requires `com.unity.probuilder` (for the ProBuilder shell; the rest compiles without it) and URP.

| Class | Call (CoplayDev `execute_code`) | Result |
|---|---|---|
| `GDS.KitCatalog` | `return GDS.KitCatalog.BuildJson("Assets/_Game/Art/Kits/kenney/kenney_castle-kit");` | `art/kit-catalog.json`: every piece with size, pivot offset, role guess, suggested module, scale warning |
| | `GDS.KitCatalog.SetImportScale(folder, 0.01f)` | one import scale for the whole kit (never per piece) |
| `GDS.LevelBuilder` | `return GDS.LevelBuilder.BuildFromFile("art/blueprints/house_a.json");` | whole building + props + scatter in one call → `docs/lint/build-<name>.json` |
| `GDS.PB` (ProBuilder) | `return GDS.PB.Room(new Vector3(0,0,0), 8, 3, 8, "S:1,N:0:window", "Assets/_Game/Art/Materials/Mat_Palette_2.mat");` | real ProBuilder room with door/window gaps, colliders, static flags |
| | `GDS.PB.Tower(center, 3f, 9f, 8)`, `GDS.PB.Stairs(pos, 2f, 3f, 4f, 10, 90)`, `GDS.PB.Arch(...)` | towers / stairs / arches |
| `GDS.Village` | `return GDS.Village.BuildFromFile("art/blueprints/village_a.json");` | terrain + roads + plaza + lots with buildings facing the street + fences + street props + forest ring → `docs/lint/village-<name>.json` |
| Blender generator | `powershell -File SKILL/scripts/gds-building.ps1 -Spec art/specs/inn.json -ProjectPath PROJECT` | real low-poly house (frames, trims, roofs, beams, balconies, interior) → `Assets/_Game/Art/Exports/building_<name>.fbx` + preview PNG ([blender-building.md](blender-building.md)) |
| `GDS.SceneLint` | `return GDS.SceneLint.RunJson();` | `docs/lint/scene-lint.json`: buried / floating / noCollider / pink / nonUrp / outOfBounds |
| | `return GDS.SceneLint.RunJson(autoFix:true);` | snaps to ground, adds box colliders, converts non-URP materials (reimport / shader swap), then report |
| `GDS.LookDev` | `return GDS.LookDev.Apply("stylized-day");` | sun, ambient, fog, skybox, Volume (ACES/bloom/color/vignette), camera post, URP quality, SSAO |
| | `GDS.LookDev.ApplyPalette(new[]{"#8C5A3C","#B8B0A0"})` / `ConvertMaterials("Universal Render Pipeline/Lit","Toon")` | palette materials / toon swap |
| `GDS.VFX` | `return GDS.VFX.CreateAll();` / `AttachTorches("torch")` | dust, hit, pickup, torch(+light), smoke, sparkle prefabs |
| `GDS.Characters` | `SetHumanoid(fbx)`, `BuildController("Player","Idle","Walk","Run","Jump","Attack")`, `MakePrefab(...)` | Humanoid rig + Animator + CharacterController prefab |

Every method returns JSON. Gate files quote that JSON, not prose.

Menu equivalents exist under `GDS/*` (`execute_menu_item`) and all methods are static → `unity -executeMethod GDS.SceneLint.MenuReport` also works headless.

## execute_code notes

- Tool group `scripting_ext` must be enabled in MCP for Unity (`manage_tools` if hidden).
- The body is a C# method body: always `return GDS.X.Y(...);` so the JSON comes back to the agent.
- After `create_script`/copying the GDS folder: wait for compile, `read_console`, then call.
- If `execute_code` is missing on the host (old MCP), use `execute_menu_item` on `GDS/...` and read the JSON in `docs/lint/`.
