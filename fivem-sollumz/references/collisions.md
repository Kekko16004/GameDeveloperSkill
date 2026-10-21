# Collisioni

## Embedded (prop) vs YBN (mappa)
- **Embedded** nel `.ydr`/`.yft`: segue il prop ovunque venga spawnato/piazzato. E' quella giusta per i prop.
  Gerarchia: `Drawable > Bound Composite > (Bound Box | Bound GeometryBVH > Bound Poly ...)`.
  `sz.add_embedded_collision(drawable, mode, material)`.
- **YBN separato** (`sz.make_static_collision`): geometria in **coordinate mondo**, per terreni/edifici piazzati con
  ymap. Non usarlo per prop spawnati da script. Le drawable dictionary (`.ydd`) NON supportano collisioni embedded.

## Modalita' di `add_embedded_collision`
| mode | Quando | Costo |
|---|---|---|
| `box` | cassa, mobile, elettrodomestico, cartello squadrato | minimo (primitiva) |
| `boxes` | forme a L, tavoli (piano + gambe), scaffali: lista di (min,max) nello spazio del drawable | basso |
| `hull` | forme organiche/arrotondate, prop animati (copre tutte le parti in posa di riposo) | medio |
| `mesh` | geometria dedicata low-poly (<= ~300-500 tri, chiusa, senza buchi) | medio/alto |
Regola Sollumz/R*: **primitive dove possibile**, mesh solo se indispensabile. Mai la mesh visiva da 20k tri.

## Flag e materiali (obbligatori)
- Ogni bound deve avere i **flag** del preset (`General (Default)` lo applica `sz_fivem`). Senza flag la
  collisione non funziona (errore n.1 secondo la wiki Sollumz). Altri preset: `General 2`, `Water surface`,
  `Leaves - Bush`... (`ybn/gta5/presets/flag_presets.json` in Sollumz).
- Ogni bound mesh/primitiva deve avere un **materiale di collisione** (suono passi, decal proiettili, attrito,
  densita' per massa). Indici completi in Sollumz `ybn/collision_materials.py`; i piu' usati:

| Materiale | Per |
|---|---|
| `CONCRETE`, `BRICK`, `STONE`, `TARMAC` | pietra/cemento |
| `METAL_SOLID_SMALL/MEDIUM/LARGE`, `METAL_HOLLOW_SMALL/MEDIUM/LARGE`, `METAL_CHAINLINK_SMALL`, `METAL_GRILLE`, `METAL_RAILING` | metalli |
| `WOOD_SOLID_SMALL/MEDIUM/LARGE`, `WOOD_HOLLOW_*`, `WOOD_SOLID_POLISHED`, `WOOD_CHIPBOARD` | legno |
| `PLASTIC`, `PLASTIC_HOLLOW`, `PLASTIC_HIGH_DENSITY`, `PLASTIC_CLEAR` | plastica |
| `GLASS_SHOOT_THROUGH`, `GLASS_BULLETPROOF`, `GLASS_OPAQUE`, `PERSPEX`, `TVSCREEN` | vetri/schermi |
| `CARDBOARD_BOX`, `PAPER`, `CLOTH`, `CARPET_SOLID`, `LEATHER`, `RUBBER`, `FOAM` | morbidi |
| `CERAMIC`, `MARBLE`, `LINOLEUM`, `LAMINATE`, `PLASTER_SOLID` | interni |
| `PHYS_NO_FRICTION`, `PHYS_POOLTABLE_*`, `PHYS_ELECTRIC_FENCE` | speciali |

## Prop dinamici (cadono/si spingono)
- Flag archetipo `dynamic` (NON `static`). La massa viene calcolata da volume x densita' del materiale: un prop di
  metallo pieno grande pesa tonnellate -> usa `METAL_HOLLOW_*`, `PLASTIC_HOLLOW`, `WOOD_HOLLOW_*` per oggetti cavi.
- Lato script: `FreezeEntityPosition(obj, false)`; per farlo "svegliare" `ActivatePhysics(obj)`.

## Parti animate e collisione
La collisione embedded di un `.ydr` animato e' legata al root: non segue gli ossi animati (coperchio aperto =
collisione chiusa). Per prop dove conta (porte, sbarre) usa la ricetta porte (door system muove l'intero oggetto) o
un `.yft` con collisione per osso ([recipe-dynamic-fragment.md](recipe-dynamic-fragment.md)).

## Verifica
- In Blender: gli oggetti `*.col` / `Bound *` sono la collisione: confrontali visivamente col modello.
- Reimport: `bpy.ops.sollumz.import_assets(directory=..., files=[{"name": "x.ydr.xml"}])` e controlla bbox.
- In gioco: camminaci contro, sparaci (decal giusto?), con `dynamic` spingilo con un veicolo.
