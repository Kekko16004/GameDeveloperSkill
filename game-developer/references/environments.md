# Environments — which world to build

`village` is ONE environment, not the default. The world phase is chosen from the GDD setting, never assumed. If the GDD says cave, dungeon, interior, city, space or open nature, do NOT run `PHASE village`.

| GDD setting | World phase | Kit genre (`fetch-cc0-kits.ps1 -Genre`) | LookDev preset | Notes |
|---|---|---|---|---|
| Hamlet, town, settlement | `village` | medieval + nature | stylized-day / stylized-sunset | `GDS.Village` — the only case for it |
| Cave, grotto, mine | `level-build` (`mode: probuilder`) | nature (rocks) | dungeon-torch | No modular cave kit exists CC0 — see below |
| Dungeon, crypt, ruins interior | `level-build` (`mode: kit`) | dungeon | dungeon-torch | Kenney modular dungeon / KayKit dungeon / Quaternius modular dungeon |
| House / castle interior | `level-build` (`mode: kit` or `probuilder`) | interior | dungeon-torch or stylized-day | `terrain.enabled` false; no village |
| City, streets | `level-build` per block | city | stylized-day | Quaternius Downtown City |
| Space station, sci-fi base | `level-build` (`mode: kit`) | scifi | scifi-cold | Kenney space kit / KayKit space base |
| Forest, open nature, no buildings | scatter only (blueprint `scatter`) | nature | stylized-day | No buildings required; slice gate adapts (gates.md) |

## Caves — the gap and the recipe

There is no free modular cave kit that matches the low-poly families. Do not invent one and do not hand-model in Blender. Build it in this order:

1. **Shell** — one blueprint, `mode: probuilder`, palette stone material. A cave is a volume with an irregular plan: 2–4 `volumes` overlapping, `floors: 1`, `roof: none`, a few `openings` (entrance, side passage), `wallHeight` 4–6. `GDS.PB` builds the shell; `GDS.SceneLint` must still return `issues: 0`.
2. **Dressing** — `props` and `scatter` from the nature kit: rocks, stalagmites (scaled rocks), rubble. `avoidRadius` around the walkable path so the player can cross.
3. **Hero props** — anything the kit lacks (crystal cluster, underground lake shrine, unique stalactite) goes through `PHASE hero-asset`: search order Poly Pizza → Poly Haven models → Sketchfab CC0 → gen3d tier from the GDD. Query terms: `cave rock`, `stalactite`, `crystal`, `mine cart`. One prop per search, sanitize, export, ledger row.
4. **Light** — `dungeon-torch` preset + `GDS.VFX.AttachTorches`. A cave with flat ambient light is a FAIL at the lookdev gate.

## Dungeons

Kit first, always. `mode: kit` with the dungeon family from `cc0-sources.md` (Kenney modular dungeon, KayKit dungeon remastered, Quaternius modular dungeon — one family per slice). Corridors and rooms are blueprints (`cellsX`/`cellsZ`, `openings` for doors), one blueprint per room or corridor segment, chained by `level-build` workers. Torches, chests, traps are `props` from the same kit; unique props (boss altar, named relic) are `hero-asset`.

## Search discipline (hero props, any environment)

- Search the real catalogs through their tools: `search_polypizza_models`, `search_polyhaven_assets(asset_type="models")`, `search_sketchfab_models(downloadable=True)` filtered to CC0. Never describe an asset from memory and model it.
- FabCLI (`fab.enabled: true` in config.json) covers the user's OWN Fab/MegaScan library only: `fabcli search` / `fabcli download`. It is not a general asset source and it is off unless the user enabled it.
- One family per slice still applies: a stylized cave keeps stylized hero props (decimate + flatten materials), not raw photogrammetry.
