# CC0 kits — the real free path for a whole game

Only sources that are **$0, unlimited copies, commercial OK**. No daily caps. No personal-use-only licenses.

**Banned as default:** Sloyd Guest, Meshy, Tripo, Rodin, Hunyuan, TRELLIS, Quaternius Pro/Source paid zips.

Kenney **All-in-1** is $19.95 (itch). Use it **only** if already on disk (`config.paths.kenneyAllInOne`). Do not buy it in the pipeline. Per-pack zips on kenney.nl stay $0.

Attribution is nice, never required for CC0.

## 1. Kenney.nl (primary) — 40k+ pieces, same palette, pivot Y=0

Direct zip (skip the donate interstitial). `cc0-fetch.ps1` or `fetch-cc0-kits.ps1`.

| Genre | Pack | Zip (verified) |
|---|---|---|
| Dungeon / interior modular | [Modular Dungeon Kit](https://kenney.nl/assets/modular-dungeon-kit) | https://kenney.nl/media/pages/assets/modular-dungeon-kit/7bed87605b-1771926065/kenney_modular-dungeon-kit_1.0.zip |
| Medieval castle | [Castle Kit](https://kenney.nl/assets/castle-kit) | https://kenney.nl/media/pages/assets/castle-kit/a395102d20-1711543616/kenney_castle-kit.zip |
| Furniture / interiors | [Furniture Kit](https://kenney.nl/assets/furniture-kit) | https://kenney.nl/media/pages/assets/furniture-kit/440e0608a4-1677580847/kenney_furniture-kit.zip |
| Sci-fi / station | [Modular Space Kit](https://kenney.nl/assets/modular-space-kit) | https://kenney.nl/media/pages/assets/modular-space-kit/8261428a47-1771146076/kenney_modular-space-kit_1.0.zip |
| Pirate / island | [Pirate Kit](https://kenney.nl/assets/pirate-kit) | https://kenney.nl/media/pages/assets/pirate-kit/e6d4bb1525-1771333093/kenney_pirate-kit.zip |
| City / suburban | [City Kit Suburban](https://kenney.nl/assets/city-kit-suburban) | https://kenney.nl/media/pages/assets/city-kit-suburban/2c871b7af2-1745479373/kenney_city-kit-suburban_20.zip |

If a hash in the URL 404s, open the pack page and take the `Continue without donating` href. Formats: glTF / FBX / OBJ. Unity, Godot, Unreal.

Also: Kenney Audio packs (RPGAudio, ImpactSounds, InterfaceSounds) — same CC0.

**Offline All-in-1 (optional, paid once):** if `paths.kenneyAllInOne` points at the extracted launcher library, `fetch-cc0-kits.ps1` copies matching 3D folders and skips the HTTP zips. Same CC0 content as the free packs, just local.

## 2. KayKit (GitHub, standard packs) — stylized atlas, modular

Clone `--depth 1`. Standard files are CC0. Ignore EXTRA/SOURCE folders if present.

| Pack | Repo |
|---|---|
| Dungeon (walls, stairs, chests, traps) | https://github.com/KayKit-Game-Assets/KayKit-Dungeon-Remastered-1.0 |
| Medieval hex village / RTS | https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0 |
| Furniture interiors | https://github.com/KayKit-Game-Assets/KayKit-Furniture-Bits-1.0 |
| Space base modules | https://github.com/KayKit-Game-Assets/KayKit-Space-Base-Bits-1.0 |
| City builder bits | https://github.com/KayKit-Game-Assets/KayKit-City-Builder-Bits-1.0 |
| Prototype greybox bits | https://github.com/KayKit-Game-Assets/KayKit-Prototype-Bits-1.0 |
| Adventurers (4 characters) | https://github.com/KayKit-Game-Assets/KayKit-Character-Pack-Adventures-1.0 |
| Skeletons (enemies) | https://github.com/KayKit-Game-Assets/KayKit-Character-Pack-Skeletons-1.0 |
| Restaurant / cooking | https://github.com/KayKit-Game-Assets/KayKit-Restaurant-Bits-1.0 |
| Halloween / cemetery | https://github.com/KayKit-Game-Assets/KayKit-Halloween-Bits-1.0 |

Itch free Standard (same license, more packs than GitHub): https://kaylousberg.itch.io/ — take the **FREE** zip, never EXTRA/SOURCE unless the user paid.

## 3. Quaternius MegaKit **Standard** only (itch $0)

CC0, commercial. Take the `[Standard].zip`. **Never** Pro/Source.

| MegaKit | Itch (Standard = free) |
|---|---|
| Medieval Village | https://quaternius.itch.io/medieval-village-megakit |
| Modular Sci-Fi | https://quaternius.itch.io/modular-sci-fi-megakit |
| Downtown City | https://quaternius.itch.io/downtown-city-megakit |
| Fantasy Props | https://quaternius.itch.io/fantasy-props-megakit |
| Stylized Nature | https://quaternius.itch.io/stylized-nature-megakit |

Older full-free packs (no Standard/Pro split): https://quaternius.com/packs/medievalvillage.html , https://quaternius.com/packs/modulardungeon.html , https://quaternius.itch.io/lowpoly-modular-dungeon-pack

Itch $0 still needs the Download button (browser / logged-in itch). Worker kit-fetch may use TerminalMCP browser; if blocked, skip MegaKit and use Kenney + Poly Pizza.

## 4. Poly Pizza (Blender MCP)

https://poly.pizza — 10k+ GLB, CC0/CC-BY. Not a modular kit. Props only. See [polypizza.md](polypizza.md).

## 5. Coherence filter (before import)

1. **One family per slice.** Kenney dungeon + Kenney furniture = OK. Kenney + KayKit hex = FAIL.
2. Poly density: kit pieces are hundreds of tris. Do not drop a 50k scan next to them.
3. Shader: URP Lit or Simple Lit for the whole scene. Reassign `Mat_Wood` / `Mat_Stone` / `Mat_Metal` if the GDD palette disagrees with the kit colors.
4. Scale: verify a door is ~2.2m. If a pack is in cm, set import scale once for the folder.

## 6. Audio CC0

Kenney Audio (RPG, Impact, SciFi, Interface), Freesound CC0. Same fetch script with `-Url`.
