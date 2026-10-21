# Ricetta: prop animati (scheletro + YCD) e UV animation

Due tipi di animazione per prop, entrambi in un **Clip Dictionary (.ycd)**:

| Tipo | Cosa si muove | Esempi | Requisiti modello |
|---|---|---|---|
| **Scheletrica** | parti rigide (o skinnate) su ossi | coperchi, sportelli, leve, ventole, bracci, slot machine, sbarre | Drawable = **armatura** con 1 osso radice + 1 osso per parte |
| **UV** | le coordinate texture di un materiale | nastri trasportatori, cascate, insegne scorrevoli, schermi finti | shader con supporto UV anim (NON `normal_spec`) |

## 1. Prop con parti animate

### Modellazione
- Una mesh per parte mobile, posizionata nella posa di riposo (chiuso). La mesh "corpo" e' la parte `root`.
- Per ogni parte decidi il **pivot** (cardine/asse) in coordinate mondo: diventa la testa dell'osso.
- Gli ossi vengono creati lungo +Y senza roll => assi dell'osso = assi del mondo: `rot: [-100, 0, 0]` ruota attorno a X.

### Spec
```json
{ "type": "animated", "name": "myrp_chest",
  "parts": {
    "root": { "source": { "file": "models/chest.glb", "objects": ["Base"] }, "material": {...} },
    "lid":  { "source": { "file": "models/chest.glb", "objects": ["Lid"] },  "material": {...},
              "pivot": [0, 0.3, 0.5] } },
  "clip_dictionary": "myrp_chest_anims",
  "clips": [
    { "name": "open",  "keys": { "lid": [[0, {"rot": [0,0,0]}], [30, {"rot": [-100,0,0]}]] } },
    { "name": "close", "keys": { "lid": [[0, {"rot": [-100,0,0]}], [30, {"rot": [0,0,0]}]] } },
    { "name": "idle_open", "loop": true, "keys": { "lid": [[0, {"rot": [-100,0,0]}], [60, {"rot": [-95,0,0]}], [120, {"rot": [-100,0,0]}]] } } ],
  "collision": { "mode": "hull", "material": "WOOD_SOLID_MEDIUM" },
  "auto_start": false }
```
Per animazioni complesse (curve, molte chiavi, ease) crea le Action in Blender con keyframe sui pose bone
(rotation_mode **QUATERNION**) e poi `sz.add_clip(cd, "nome", action, arm.data)`:
```python
arm = sz.make_animated_drawable("myrp_fan", {"root": {"mesh": base}, "blades": {"mesh": blades, "pivot": (0, 0, 1.2)}})
def keys():
    for f, ang in ((0, 0), (30, 120), (60, 240), (90, 360)):
        sz.keyframe_bone(arm, "blades", f, rot_euler_deg=(0, 0, ang))
act = sz.record_action(arm, "myrp_fan_spin", keys)       # interpolazione LINEAR (loop senza scatti)
cd = sz.make_clip_dictionary("myrp_fan_anims")
sz.add_clip(cd, "spin", act, arm.data)
```
Rotazioni >= 180 gradi: metti chiavi intermedie (max 120 gradi tra due chiavi) - i quaternion prendono la strada
piu' corta. Per un loop perfetto l'ultimo frame = primo (0 e 360) ed export interpola linearmente.

### Cosa esce (verificato)
- `myrp_chest.ydr`: scheletro `root#0`, `lid#<tag>` (tag = hash del nome osso calcolato da Sollumz), modelli legati
  agli ossi. **Rinominare un osso cambia il suo tag**: rifai l'export di ydr E ycd insieme.
- `myrp_chest_anims.ycd(.xml)`: clip `open`, `close`... (hash = nome, `pack:/open.clip`), 30 fps, durata = frame/30.
- Archetipo: `clipDictionary = myrp_chest_anims`, flag `has_anim` (512).

### Triggerare l'animazione in FiveM
```lua
-- 1) trova/crea l'oggetto
local obj = SZ.GetClosestProp('myrp_chest', GetEntityCoords(PlayerPedId()), 3.0)   -- anche se piazzato da ymap
-- 2) riproduci (wrapper: RequestAnimDict + PlayEntityAnim + ForceEntityAiAndAnimationUpdate)
SZ.PlayPropAnim(obj, 'myrp_chest_anims', 'open', false, true)   -- loop=false, hold ultimo frame=true
```
Native sotto (attenzione all'**ordine dei parametri**, diverso tra le native!):
```lua
RequestAnimDict('myrp_chest_anims'); while not HasAnimDictLoaded('myrp_chest_anims') do Wait(0) end
PlayEntityAnim(obj, 'open', 'myrp_chest_anims', 8.0, false, true, false, 0.0, 0)
--             entity, CLIP, DIZIONARIO, blendDelta, loop, holdLastFrame, driveToPose, startPhase, flags
IsEntityPlayingAnim(obj, 'myrp_chest_anims', 'open', 3)        -- qui DIZIONARIO, CLIP
StopEntityAnim(obj, 'open', 'myrp_chest_anims', 8.0)            -- qui CLIP, DIZIONARIO
SetEntityAnimCurrentTime(obj, 'myrp_chest_anims', 'open', 0.5)  -- DIZIONARIO, CLIP, fase 0-1
SetEntityAnimSpeed(obj, 'myrp_chest_anims', 'open', 0.0)         -- 0 = pausa
GetEntityAnimCurrentTime(obj, 'myrp_chest_anims', 'open')
HasEntityAnimFinished(obj, 'myrp_chest_anims', 'open', 3)
```
- "Chiudere": fai un clip `close` dedicato (non esiste reverse affidabile). Posa intermedia:
  `SZ.SetPropAnimPhase(obj, dict, clip, 0.5)`.
- Loop continuo: `PlayEntityAnim(..., loop=true, ...)` oppure `auto_start` (sotto).
- Trigger tipici: comando, `ox_target`/`qb-target` sull'entita', zona (PolyZone/lib.zones), evento server, distanza.

### Avvio automatico (senza script)
`"auto_start": true` -> flag `auto_start_anim` (524288). Il gioco avvia da solo il clip il cui **nome e' uguale al nome
del modello/archetipo** (convenzione della guida ufficiale Cfx "Map Animation Creation"): nella spec metti un clip con
`"name": "<nome asset>"`. In loop continuo: insegne rotanti, ventole, giostre, mulini.

### Multiplayer: tutti vedono la stessa animazione
`PlayEntityAnim` e' **locale**. Opzioni:
1. **State bag** (incluso): l'oggetto networked ha `Entity(obj).state.szAnim = {dict, clip, loop, hold}`; ogni client
   lo applica (handler in `client/sz_lib.lua`).
   ```lua
   -- server (OneSync)
   local obj = SZS.SpawnNetworkedProp('myrp_chest', coords, heading)
   SZS.PlayPropAnimForAll(obj, 'myrp_chest_anims', 'open', false, true)
   -- client proprietario: Entity(obj).state:set('szAnim', {dict='myrp_chest_anims', clip='open', hold=true}, true)
   ```
2. Prop della **mappa** (ymap, non networked): evento server -> `TriggerClientEvent` a tutti -> ognuno trova il prop
   con `GetClosestObjectOfType` alle coordinate note e lo anima. Salva lo stato lato server: quando un client entra
   nel raggio di streaming il prop viene ricreato in posa di riposo -> riapplica lo stato (es. clip `open` con
   `startPhase = 1.0` e hold).

### Prop animato + ped (scene sincronizzate)
Per un ped che apre il baule con il coperchio sincronizzato servono un clip per il ped (scheletro ped) e uno per il
prop nello stesso dizionario, riprodotti con `CreateSynchronizedScene` + `TaskSynchronizedScene(ped, ...)` +
`PlaySynchronizedEntityAnim(obj, scene, clip, dict, 1000.0, -1000.0, 0, 1000.0)`. Le animazioni ped si fanno con un
rig del ped (import `mp_m_freemode_01.yft` in Sollumz): fuori dallo scopo dei prop semplici; in alternativa usa
un'animazione ped vanilla e cronometra l'apertura del prop.

## 2. UV animation <a id="uv-animation"></a>

```json
{ "type": "uv_scroll", "name": "myrp_conveyor",
  "source": {...},
  "material": { "shader": "normal", "textures": { "diffuse": "textures/myrp_belt_d.png", "normal": "textures/myrp_belt_n.png" } },
  "uv": { "frames": 60, "du": 0.0, "dv": 1.0 } }
```
- Shader compatibili: `default, normal, spec, emissive, emissivestrong, alpha, cutout, normal_cutout, normal_alpha,
  spec_alpha, normal_decal, glass_emissive...` (lista in [shaders-catalog.md](shaders-catalog.md)). **Non** `normal_spec`.
- La texture deve essere **tileable** nella direzione dello scorrimento. `du/dv` = quante ripetizioni in `frames`
  (1.0 = una texture intera in frames/30 secondi). Valori negativi = verso opposto.
- Hash del clip UV = `joaat(nome_modello) + indice_materiale + 1` (calcolato da Sollumz `update_uv_clip_hash`): per
  questo l'asset deve essere gia' un Drawable quando crei il clip (la build lo fa nell'ordine giusto).
- Archetipo: `has_uv_anim` + `auto_start_anim` (+ `static`), `clipDictionary` = `<nome>_uv`. Nessun codice Lua.
- Sprite sheet (fotogrammi in griglia: fuoco, schermi animati a scatti): Sollumz ha `sollumz.uv_sprite_sheet_anim`;
  in alternativa keyframe "costanti" su `animation_tracks.uv0/uv1` del materiale (interpolazione CONSTANT).
- Rotazione/scala UV: aggiungi `uv_transforms` al materiale (`mat.animation_tracks.uv_transforms.add()` con
  `mode = 'ROTATE'|'SCALE'...`) e keyframe su `animation_tracks.uv_transforms[i].rotation` ecc.

## Checklist animazioni
- [ ] Un solo osso radice; pivot corretti; keyframe in quaternion; 30 fps.
- [ ] Nomi clip = quelli usati nel Lua; ycd e archetipo con lo stesso nome dizionario.
- [ ] Flag `has_anim` / `has_uv_anim` (+ `auto_start_anim` se deve partire da solo).
- [ ] `.ycd` convertito in binario e presente in `stream/` (e `stream_enhanced/`).
- [ ] `CwXmlToBin --info` mostra i clip e gli ossi attesi; test `/sz_<nome>_<clip>` in gioco.
