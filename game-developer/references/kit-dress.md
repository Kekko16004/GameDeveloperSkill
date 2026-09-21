# Kit-dress — place CC0 modular pieces

One worker dresses **one ledger row** (one mesh / one prefab / one placement). Do not "fill the house".

## Before you start

1. Read `GDD.md` style + `ASSET-LEDGER.md` row `$ASSET_ID`.
2. Confirm a kit was fetched into `art/cc0/<family>/`. If empty, run:

```
powershell -File SKILL/scripts/fetch-cc0-kits.ps1 -ProjectPath PROJECT -Genre <medieval|scifi|city|pirate|interior|prototype>
```

3. Pick the **closest existing file** (gltf/glb/fbx). Do not download a second family.

## Copy + import

1. Copy the chosen file to `art/exports/$ASSET_ID.glb` (or keep gltf+bin together). If the kit is FBX-only, copy FBX and set ledger `format: fbx`.
2. Unity: `Assets/_Game/Art/Kits/<family>/`. Scale **1**. Strip lights/cameras.
3. Prefab `Assets/_Game/Prefabs/$ASSET_ID.prefab`.
4. Collider: Box or Capsule matching Geometra bounds. Convex MeshCollider only if the kit shipped one.
5. Pivot: if the mesh floats, fix Transform so the bottom sits on `Y=0`. Do not open Blender unless the pivot is >5cm off — then sanitize-only (`blender-game-assets.md`). No bpy modelling.

## Place

Coordinates come from `GAME_TASKS.md`. Snap XZ to `0.5m` or `1m`. Rotation Y in 90° steps for modular walls.

Screenshot `screenshots/030-import-$ASSET_ID.png` of the instance in Game or Scene view.

## Gate

`docs/gates/07-kit-$ASSET_ID.md`:

```
phase: kit-dress
status: PASS
id: $ASSET_ID
source: kenney|kaykit|quaternius-standard
kit_file: art/cc0/...
export: art/exports/$ASSET_ID.glb
prefab: Assets/_Game/Prefabs/$ASSET_ID.prefab
evidence:
  - screenshots/030-import-$ASSET_ID.png
```

FAIL if: paid MegaKit Source used, second style family mixed in, no collider, player clips through, screenshot missing.

## Anti-slop

- One Kenney **or** one KayKit pack per slice. Mixing Kenney dungeon with KayKit hex village = Frankenstein = FAIL.
- Do not rescale each piece ad-hoc. One import scale for the whole pack.
- Do not generate a "better" crate in Blender when Kenney already has `crate.glb`.
