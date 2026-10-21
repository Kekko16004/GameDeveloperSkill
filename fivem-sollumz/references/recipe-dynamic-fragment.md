# Ricetta: prop fisici (dynamic) e rompibili (fragment .yft)

## A) Prop dinamico semplice (.ydr)
Si spinge, cade, rotola (coni, barili, sedie, scatole).
```json
{ "type": "dynamic", "name": "myrp_barrel", "source": { "file": "models/barrel.glb" },
  "material": { "convert_existing": true },
  "collision": { "mode": "hull", "material": "METAL_HOLLOW_MEDIUM" },
  "flags": ["dynamic"] }
```
- Flag archetipo **`dynamic`**, MAI `static`.
- Massa = volume collisione x densita' materiale: scegli materiali *HOLLOW* per oggetti cavi, altrimenti pesano
  troppo e non si muovono.
- Collisione convessa (`hull`) o primitive: stabile nella simulazione. Evita mesh concave per oggetti che rotolano.
- Lua: `SZ.SpawnProp(model, pos, h, true, false)` (freeze=false) e se serve `ActivatePhysics(obj)`.

## B) Fragment (.yft): parti che si staccano / pivotano
Lampioni, cartelli stradali, recinzioni, barriere, contenitori con sportelli, vetrine.
```json
{ "type": "fragment", "name": "myrp_sign_break",
  "parts": {
    "root":  { "source": {...}, "collision": "box", "collision_material": "CONCRETE", "mass": 200 },
    "pole":  { "source": {...}, "pivot": [0,0,0.1],  "collision": "box", "collision_material": "METAL_SOLID_SMALL", "mass": 20, "strength": 50 },
    "board": { "source": {...}, "pivot": [0,0,2.05], "parent": "pole", "collision": "box", "mass": 5, "strength": -1 } } }
```
Cosa costruisce `sz.make_fragment` (verificato al round-trip):
- Armatura `Fragment` con **un solo osso radice** (nome = nome prop, tag 0) + un osso per parte (testa = pivot).
- `<nome>.mesh` (Drawable) con ogni modello legato al suo osso (vincolo COPY_TRANSFORMS, geometria in spazio osso).
- `<nome>.col` (Bound Composite) con una collisione **per osso** (box o hull), massa in `child_properties.mass`.
- Ossi con `Use Physics`; `strength`: **-1 = non si stacca** (sportello/insegna che oscilla), valori bassi = si
  stacca facilmente (50-100 per cartelli), alti = robusto (1000+).
- Il root ha sempre fisica (gruppo radice), altrimenti la sua collisione non viene esportata.
- Archetipo `dynamic`.

Regole:
- Ogni parte che si muove/si stacca = un osso + una collisione legata a quell'osso.
- Prima di inventare i parametri fisici importa un prop vanilla simile (`prop_sign_road_01a.yft`,
  `prop_streetlight_01.yft`, `prop_container_05a.yft`) e copia `group_properties` (Sollumz: Bone > Fragment Physics).
- Vetri rompibili di prop: flag gruppo "Breakable Glass" + collisione `GLASS_SHOOT_THROUGH` (avanzato: parti da un
  prop vanilla).
- Gas/esplosioni (`prop_gas_tank`): richiedono drawable "damaged", non supportato da Sollumz.

## Test in gioco
`/sz_myrp_sign_break` poi urtalo con un veicolo / sparagli. Se non si stacca: strength troppo alta o ossi senza
fisica. Se cade a pezzi da solo appena spawnato: collisioni compenetrate o masse a 0.
