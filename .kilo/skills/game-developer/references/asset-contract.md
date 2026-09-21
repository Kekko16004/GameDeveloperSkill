# Asset contract

All 3D assets, CC0 or authored:

| Rule | Value |
|---|---|
| Scale | 1 unit = 1 meter |
| Origin | on the ground plane, centered XZ |
| Forward | glTF default; Unity import: scale 1, bake axis |
| File | one asset = one `art/exports/<id>.glb` |
| Collision | box or low-poly convex, not the render mesh if dense |
| Lights | **none** in the file |
| Cameras | **none** |
| Naming | `role_name` — `prop_crate`, `char_player`, `env_wall_a` |
| Ledger | every file in `ASSET-LEDGER.md` |

Ledger row:

```
| id | role | source | license | path | scale | collision | notes |
```

Strip imported lights/cameras in Unity if a tool added them anyway.
