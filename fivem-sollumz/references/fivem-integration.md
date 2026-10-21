# Integrazione FiveM

## Struttura risorsa (generata da `make_resource.py`)
```
myrp_props/
  fxmanifest.lua
  stream/             binari Gen8 (FiveM classico)
  stream_enhanced/    binari Gen9 (FiveM for GTAV Enhanced) - opzionale
  client/sz_lib.lua  client/main.lua
  server/sz_lib.lua  server/main.lua
  html/screen.html    (DUI)
```
- Tutto cio' che sta in `stream/` viene streammato automaticamente (anche in sottocartelle). I nomi file sono
  **globali** sul server: due risorse con `myrp_crate.ydr` si sovrascrivono (vince l'ultima caricata).
- `stream_enhanced/`: su FiveM Enhanced, se esiste, sostituisce `stream/`; il FiveM classico la ignora.

## fxmanifest.lua
```lua
fx_version 'cerulean'
game 'gta5'
lua54 'yes'

client_scripts { 'client/sz_lib.lua', 'client/main.lua' }
server_scripts { 'server/sz_lib.lua', 'server/main.lua' }
files { 'html/screen.html' }                       -- solo se DUI

data_file 'DLC_ITYP_REQUEST' 'stream/myrp_props.ytyp'   -- archetipi (forma esplicita classica)
this_is_a_map 'yes'                                -- solo se ci sono .ymap
```
- `.ytyp` e `.ymap` possono anche restare XML (CodeWalker/Sollumz) purche' il file si chiami `x.ytyp` / `x.ymap`
  senza `.xml` (supporto ufficiale Cfx; parsati dal parser del gioco).
- Avvio: `ensure myrp_props` nel `server.cfg`. Durante lo sviluppo: `restart myrp_props` + riconnessione se cambi
  ytyp/modelli gia' caricati (lo streaming in cache a volte resta: `clear cache` lato client se vedi la versione vecchia).

## Limiti di streaming <a id="limiti"></a>
- FiveM avvisa "Oversized assets can and WILL lead to streaming issues" per file con memoria fisica oltre ~16 MiB:
  riduci texture (2048 -> 1024), usa YTD condivisi, LOD.
- Textures > 2048 solo come HD (`+hi`). Enhanced: max 128 materiali/geometrie per asset.
- Molti prop spawnati da script = molte entita' networked: preferisci ymap per arredi fissi.

## Native di riferimento (Lua)
| Scopo | Native |
|---|---|
| hash | `GetHashKey('myrp_crate')` (o `joaat`), backtick `` `myrp_crate` `` in Lua CfX |
| esiste il modello? | `IsModelInCdimage(hash)`, `IsModelValid(hash)` |
| caricare | `RequestModel(hash)` + `HasModelLoaded(hash)`; poi `SetModelAsNoLongerNeeded(hash)` |
| creare | `CreateObjectNoOffset(hash, x, y, z, isNetwork, netMissionEntity, doorFlag)` (client o server OneSync) |
| posizionare | `SetEntityHeading`, `PlaceObjectOnGroundProperly`, `FreezeEntityPosition` |
| trovare prop (anche ymap) | `GetClosestObjectOfType(x, y, z, radius, hash, false, false, false)` |
| animare | `RequestAnimDict`/`HasAnimDictLoaded`, `PlayEntityAnim(ent, clip, dict, blend, loop, hold, false, phase, 0)`, `StopEntityAnim(ent, clip, dict, blend)`, `IsEntityPlayingAnim(ent, dict, clip, 3)`, `SetEntityAnimCurrentTime(ent, dict, clip, t)`, `SetEntityAnimSpeed(ent, dict, clip, s)` |
| tint | `SetObjectTextureVariation(obj, index)` |
| attaccare al ped | `AttachEntityToEntity(obj, ped, GetPedBoneIndex(ped, 57005), x, y, z, rx, ry, rz, true, true, false, true, 1, true)` |
| DUI | `CreateRuntimeTxd`, `CreateDui`, `IsDuiAvailable`, `GetDuiHandle`, `CreateRuntimeTextureFromDuiHandle`, `AddReplaceTexture`, `RemoveReplaceTexture`, `SetDuiUrl`, `SendDuiMessage`, `DestroyDui` |
| texture da immagine | `CreateRuntimeTextureFromImage(txd, name, 'img.png')` (file in `files{}`) |
| render target | `RegisterNamedRendertarget`, `LinkNamedRendertarget(modelHash)`, `GetNamedRendertargetRenderId`, `SetTextRenderId` |
| porte | `AddDoorToSystem`, `DoorSystemSetDoorState`, `DoorSystemSetOpenRatio`, `DoorSystemGetDoorState` |
| nascondere vanilla | `CreateModelHide(x, y, z, r, hash, true)` |
| fisica | `ActivatePhysics(obj)`, `SetEntityDynamic(obj, true)` |
| sync | state bag: `Entity(obj).state:set(k, v, true)` + `AddStateBagChangeHandler(k, nil, fn)` + `GetEntityFromStateBagName` |

Tutte esposte come `exports['<risorsa>']:<Funzione>(...)` da `client/sz_lib.lua` (SpawnProp, PlayPropAnim,
StopPropAnim, SetPropAnimPhase, GetClosestProp, SetTint, AttachToHand, CreateScreen, ScreenSend, ScreenSetUrl,
DestroyScreen, RegisterDoor, SetDoorLocked, LoadModel, LoadAnimDict) e `server/sz_lib.lua`
(SpawnNetworkedProp, PlayPropAnimForAll).

## Integrazione con framework
- **ox_target / qb-target**: `exports.ox_target:addModel('myrp_chest', { { label = 'Apri', onSelect = function(data)
  SZ.PlayPropAnim(data.entity, 'myrp_chest_anims', 'open', false, true) end } })`.
- **ox_inventory / qb-inventory** (oggetti usabili): all'uso, `SZ.SpawnProp` + `SZ.AttachToHand` + anim ped.
- **ox_doorlock**: registra la porta col modello `myrp_door_01` (hash) e le coordinate dell'entita'.

## Test in gioco (comandi generati)
`/sz_<asset>` spawna davanti al player; `/sz_<asset>_<clip>` anima il piu' vicino; `/sz_<porta>_lock`.
Disattiva `Config.DevCommands` in produzione. Console F8: errori di streaming/manifest. Comandi utili:
`resmon 1` (consumo risorse); su Enhanced `con_archetypeMonitor true` (strumento archetipi).
