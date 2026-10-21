# Casi speciali: veicoli, vestiti, armi, MLO

La skill automatizza i **prop**. Per gli altri tipi Sollumz funziona, ma servono dati e metadati extra: qui cosa
cambia e da dove partire. Regola: **parti sempre da un asset vanilla importato** e sostituisci la geometria.

## Veicoli (.yft + _hi.yft + meta)
- Base: importa un veicolo vanilla simile (CodeWalker export XML del `.yft` e `_hi.yft` + texture nella cartella
  omonima; Sollumz import con *Import with _hi*). Lo scheletro/ossi (`chassis`, `wheel_lf`, `door_dside_f`, `bonnet`,
  `boot`, `seat_*`, `extra_1`...) e i loro tag sono hardcoded nel gioco: non rinominarli.
- Mesh skinnate per vertex group col nome dell'osso (Split by Group all'import), modificatore Armature.
- Shader veicolo: `vehicle_paint1..9` (paint layer Primary/Secondary... in `Material > Sollumz > Vehicle Paint`),
  `vehicle_vehglass(_inner)`, `vehicle_lightsemissive` + **Light ID** sulle facce (headlight_l, brakelight...).
- Vetri rompibili: collisione `CAR_GLASS_*`, shattermap Auto (richiede PyMateria).
- Ruote: `wheel_lf` unica (istanziata), `Is Wheel Mesh`.
- Vertex color: R = AO, G = deformazione, B = bruciatura.
- `VeryHigh` LOD = `_hi.yft`. Enhanced: max 128 materiali/geometrie.
- Metadati: `vehicles.meta`, `carvariations.meta`, `carcols.meta`, `handling.meta` + `data_file` nel manifest
  (`VEHICLE_METADATA_FILE`, `HANDLING_FILE`, `CARCOLS_FILE`, `VEHICLE_VARIATION_FILE`). Wiki Sollumz: Creating Vehicles.

## Vestiti (EUP / addon clothes, .ydd + .ytd)
- Componenti freemode in `.ydd` (es. `jbib_007_u.ydd`), texture diffuse in `.ytd` separati (`jbib_diff_007_a_uni.ytd`,
  fino a 26 varianti a..z), normal/spec embedded.
- Import con **External Skeleton** (`mp_m_freemode_01.yft` / `mp_f_freemode_01.yft` nella stessa cartella).
- Rig: vertex group sugli ossi SKEL_*, 3 LOD. Shader `ped`/`ped_default`... Vertex color `Color 1` #FF8000,
  `Color 2` nero alpha 0. Export con *Exclude Skeleton* (componenti mp).
- Distribuzione FiveM: stream addon con nomi da creature metadata (`mp_m_freemode_01_<pack>^jbib_000_u.ydd`) +
  `.ymt`/`.meta` di pacchetto: usa strumenti dedicati (es. grzyClothTool / Durty Cloth Tool) per generarli.

## Armi (.ydr + meta)
- Modello `w_xx_nome.ydr` (+ `_hi.ydr`) con scheletro arma (gun_root, gun_muzzle, gun_gripr...), parti come
  componenti (`w_xx_nome_mag1.ydr`). Parti da un'arma vanilla (Sollumz: weapons = TODO nella wiki).
- Shader `weapon_normal_spec*`. Metadati: `weapons.meta`, `weaponcomponents.meta`, `weaponanimations.meta`,
  `pedpersonality.meta` + `data_file 'WEAPONINFO_FILE'`... Animazioni ped e audio sono il grosso del lavoro.
- Solo "arma finta" in mano per RP: e' un prop normale attaccato alla mano ([recipe-static.md](recipe-static.md#oggetti-in-mano)).

## MLO (interni)
- Shell modellata in Blender (pareti, pavimenti), vertex color verdi, collisioni `.ybn` per stanza con Room ID
  corretti, archetipo **MLO** con stanze/portali/entity set (Sollumz Archetype Definition supporta rooms/portals
  "from selection"), ymap con istanza MLO, `_manifest.ymf` con `Interiors`. Wiki Sollumz: Creating Interiors (9 pagine).
- I prop di questa skill si usano dentro gli MLO come entity dell'archetipo MLO (vertex color verde).
