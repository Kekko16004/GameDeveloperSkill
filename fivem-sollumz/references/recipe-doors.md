# Ricetta: porte, cancelli, garage, sbarre

Schema delle porte vanilla (e della guida ufficiale Cfx "Door Creation"): `.ydr` con **armatura a un osso** (tag 0),
mesh legata all'osso, **origine sul cardine**, collisione embedded, archetipo con **special attribute** porta e flag
`dynamic` + `enable_door_physics`. La porta poi si muove con la fisica (spinta dal ped) o via door system.

| kind | Special attribute | Origine (pivot) | Template vanilla da confrontare |
|---|---|---|---|
| `swing` | Normal Door (7) | cardine: centro del lato del cardine, a terra | `v_ilev_bl_door_l` |
| `sliding` | Sliding Door (8) | angolo in basso | `prop_facgate_07b` |
| `garage` | Garage Door (5) | centro in basso | `lr_prop_supermod_door_01` |
| `sliding_vertical` | Sliding Vertical Door (10) | centro in basso | - |
| `barrier` | Barrier Door (9) | perno della sbarra | `prop_sec_barier_02a` |

```json
{ "type": "door", "name": "myrp_door_01", "kind": "swing", "hinge": [0, 0, 0],
  "source": { "file": "models/door.glb" }, "material": {...},
  "collision": { "material": "WOOD_SOLID_MEDIUM" } }
```
- Modella la porta **chiusa**, con il pannello che parte dal cardine lungo X (+X o -X). `hinge` = punto del cardine in
  coordinate del file sorgente (a terra).
- Spessore reale (4-6 cm), maniglie incluse nella mesh. Niente telaio nel modello della porta (il telaio sta
  nell'edificio/MLO).

## In gioco
Porte piazzate in un MLO/ymap: registrale nel door system per bloccarle/sbloccarle (lato client, di solito tramite
una risorsa doorlock tipo ox_doorlock che usa queste native):
```lua
local doorHash = SZ.RegisterDoor('myrp_shop_front', 'myrp_door_01', vector3(x, y, z))   -- coordinate dell'entita'
SZ.SetDoorLocked(doorHash, true)                 -- DoorSystemSetDoorState(hash, 1, false, true)
DoorSystemSetOpenRatio(doorHash, 0.0, false, true)
DoorSystemSetAutomaticRate(doorHash, 1.0, false, true)   -- garage/automatiche
```
Comando di test generato: `/sz_myrp_door_01_lock` (blocca/sblocca la porta piu' vicina).
Spawnata da script (non ymap): `CreateObjectNoOffset(..., doorFlag=true)` oppure registra con le coordinate
dell'oggetto creato.

## Problemi tipici
- La porta ruota attorno al centro: origine sbagliata (deve essere sul cardine).
- Non si muove: manca `enable_door_physics`/special attribute, oppure e' `static`.
- Trema/esplode: collisione che compenetra il telaio -> riduci la box di 1-2 cm.
