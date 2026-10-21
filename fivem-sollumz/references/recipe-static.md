# Ricetta: prop statico

## Spec
```json
{ "type": "static", "name": "myrp_crate",
  "source": { "file": "models/crate.glb" },
  "origin": "BOTTOM_CENTER",
  "material": { "shader": "normal_spec", "textures": { "diffuse": "textures/myrp_crate_d.png",
                "normal": "textures/myrp_crate_n.png", "spec": "textures/myrp_crate_s.png" } },
  "collision": { "mode": "box", "material": "WOOD_SOLID_MEDIUM" },
  "lod_dist": 100, "flags": ["static"] }
```

## Passi (cosa fa la build e cosa controllare)
1. Import + unione mesh, applicazione rot/scala, `UVMap 0`, `Color 1` rosso (esterni).
2. Origine al centro della base (il prop appoggia a terra a z=0 del suo sistema locale).
3. Materiale Sollumz con texture DDS embedded.
4. Drawable `myrp_crate` + Drawable Model; collisione box embedded con flag + materiale.
5. Archetipo `static`, lodDist 100.
6. Audit -> export -> risorsa.

Controllo visivo: il modello poggia sul piano z=0? Il fronte guarda -Y? La box di collisione lo avvolge?

## Uso in FiveM
```lua
-- client
local obj = SZ.SpawnProp('myrp_crate', vector3(x, y, z), heading, true)   -- true = networked
PlaceObjectOnGroundProperly(obj)
-- oppure piazzato fisso: ymap (recipe-map-placement.md)
```
Test: `/sz_myrp_crate` (comando generato in `client/main.lua`).

## Oggetti in mano <a id="oggetti-in-mano"></a>
Oggetti che il ped tiene (telefono, tazza, attrezzo, arma finta):
- Origine = **punto di presa**. Orienta il modello come lo terrebbe la mano destra (prova e correggi l'offset
  in Lua piu' che in Blender).
- Collisione: piccola o assente (`"collision": null`) per non spingere il ped; flag `static` o nessuno.
- Budget basso (< 2k tri), texture 256-512.
```lua
local ped = PlayerPedId()
local obj = SZ.SpawnProp('myrp_mug', GetEntityCoords(ped), 0.0, true, false)
SZ.AttachToHand(obj, ped, 57005, vector3(0.12, 0.0, -0.03), vector3(-80.0, 0.0, 0.0))  -- 57005 SKEL_R_Hand
-- animazione del ped (dizionario vanilla), es. bere:
RequestAnimDict('mp_player_intdrink') while not HasAnimDictLoaded('mp_player_intdrink') do Wait(0) end
TaskPlayAnim(ped, 'mp_player_intdrink', 'loop_bottle', 8.0, -8.0, -1, 49, 0, false, false, false)
```
Ossa ped utili: 57005 mano dx, 18905 mano sx, 31086 testa, 24818 spine3 (zaino), 28422 PH_R_Hand (presa).

## Pack di molti prop
Una spec con N asset, un solo ytyp. Se condividono texture: `"embedded": false` + stesso `"texture_dictionary"`
(es. `myrp_pack_txd`) -> un solo .ytd, file piu' leggeri.
