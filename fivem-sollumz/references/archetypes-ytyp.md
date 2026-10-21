# Archetipi (.ytyp)

Ogni modello che il gioco deve conoscere ha un **archetipo** (CBaseArchetypeDef) in un `.ytyp` streammato. Senza
archetipo: `IsModelInCdimage` falso, `CreateObject` fallisce, entity del ymap invisibili.

```python
y = sz.get_or_make_ytyp("myrp_pack")                     # un ytyp per risorsa
sz.add_archetype(y, drawable, flags=("static",), lod_dist=100,
                 texture_dictionary=None,                 # None = automatico; "<ytd>" se texture esterne
                 clip_dictionary="",                      # "<ycd>" per prop animati / UV
                 special="none")
```
Campi esportati: `name`, `assetName` (= nome file), `assetType` (DRAWABLE / FRAGMENT / DRAWABLE_DICTIONARY /
ASSETLESS), `lodDist`, `hdTextureDist`, `flags`, `specialAttribute`, `textureDictionary`, `clipDictionary`,
`drawableDictionary` (se dentro un .ydd), `physicsDictionary` (automatico se c'e' collisione embedded), bbox/sfera
(calcolati all'export dall'asset).

## Flag (valori bit, da Sollumz `ytyp/properties/flags.py`)
| Nome in `sz` | Bit | Valore | Significato |
|---|---|---|---|
| `wet_road_reflection` | 0 | 1 | riflesso su strada bagnata |
| `dont_fade` | 1 | 2 | pop invece di fade |
| `draw_last` | 2 | 4 | disegnato per ultimo (trasparenze) |
| `climbable_by_ai` | 3 | 8 | i ped possono scavalcarlo |
| `suppress_hd_txds` | 4 | 16 | mai texture HD |
| `static` | 5 | 32 | **statico**, niente fisica (default per arredi) |
| `disable_alpha_sorting` | 6 | 64 | ordinamento alpha diverso |
| `tough_for_bullets` | 7 | 128 | proiettili non lo attraversano/segnano |
| `is_generic` | 8 | 256 | oggetti procedurali |
| `has_anim` | 9 | 512 | **ha clip dictionary (YCD) di ossa** |
| `has_uv_anim` | 10 | 1024 | **ha UV animation (YCD)** |
| `shadow_only` | 11 | 2048 | invisibile, solo ombra |
| `damage_model` | 12 | 4096 | ha stato danneggiato |
| `dont_cast_shadows` | 13 | 8192 | niente ombre |
| `cast_texture_shadows` | 14 | 16384 | ombre con alpha (effetto poco chiaro) |
| `dont_collide_with_flyer` | 15 | 32768 | gli aerei passano |
| `double_sided` | 16 | 65536 | backface visibili (vegetazione) |
| `dynamic` | 17 | 131072 | **fisica attiva** (si spinge/cade) |
| `override_physics_bounds` | 18 | 262144 | usa bounds dell'archetipo |
| `auto_start_anim` | 19 | 524288 | **l'animazione parte da sola** |
| `has_pre_reflected_water_proxy` | 20 | 1048576 | |
| `has_drawable_proxy_for_water_reflections` | 21 | 2097152 | |
| `no_ai_cover` | 22 | 4194304 | i ped non ci si coprono |
| `no_player_cover` | 23 | 8388608 | il player non ci si copre |
| `is_ladder_deprecated` | 24 | 16777216 | (usa extension ladder) |
| `has_cloth` | 25 | 33554432 | contiene cloth |
| `enable_door_physics` | 26 | 67108864 | **fisica porta** (serve special attribute porta) |
| `is_fixed_for_navigation` | 27 | 134217728 | gia' nella navmesh |
| `dont_avoid_by_peds` | 28 | 268435456 | |
| `use_ambient_scale` | 29 | 536870912 | |
| `is_debug` | 30 | 1073741824 | |
| `has_alpha_shadow` | 31 | 2147483648 | ombre con alpha |

Combinazioni tipiche:
| Prop | flags |
|---|---|
| arredo statico | `static` (32) |
| prop fisico / fragment | `dynamic` (131072) |
| animato da script | `has_anim` (512) (+ `static` se non deve muoversi fisicamente: 544) |
| animato in loop automatico | `has_anim`, `auto_start_anim` (+ `static`) |
| UV anim | `has_uv_anim`, `auto_start_anim` (+ `static`) = 525344 |
| porta | `dynamic`, `enable_door_physics` = 67239936 |
| vegetazione | `double_sided` (+ shader cutout) |

## Special attribute
`none` 0, `traffic_light` 3, `garage_door` 5, `door` 7 (IS_NORMAL_DOOR), `sliding_door` 8, `barrier_door` 9,
`sliding_door_vertical` 10, `bush` 11 (NOISY_BUSH), `rail_crossing_door` 12, `single_axis_rotation` 14
(rotazione procedurale su un asse), `clock` 30 (lancette animate), `street_light` 32.

## Archetype extensions (avanzato)
Sollumz supporta le extension (particelle, ladder, spawn point/scenari, light shaft, door, audio emitter...):
`ytyp/properties/extensions.py`. Esempio: `arch.extensions.add()` poi `extension_type` e proprieta'. Usale per
effetti (fumo da un camino, scenario "sedersi" su una panchina custom).

## Piu' ytyp / time archetype
- Un ytyp per risorsa e' sufficiente (anche centinaia di archetipi).
- **Time archetype** (`ArchetypeType.TIME`): visibile solo in certe ore (`time_flags`), es. insegne accese di notte.
