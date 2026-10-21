---
name: fivem-sollumz
description: Pipeline completa e 100% Python per creare modelli GTA V / FiveM in Blender con Sollumz 2.9 e consegnare una risorsa FiveM pronta. Copre prop statici, dinamici/fisici, rompibili (YFT), animati con scheletro (YCD) e come triggerarli da Lua, UV animation (nastri, insegne), schermi DUI (materiale sostituito a runtime da una pagina web), porte (door system), luci embedded, varianti tint, LOD, collisioni, texture DDS/YTD, YTYP/archetipi, YMAP, export Gen8 (FiveM) e Gen9 (FiveM Enhanced), conversione XML->binario, verifica dei binari. Usabile da agenti che pilotano Blender via Python (Blender MCP, `blender -b -P`, modulo bpy) o da vision model. Trigger: FiveM, GTA V, GTA 5, Sollumz, CodeWalker, prop, ydr, yft, ydd, ytd, ytyp, ymap, ycd, ybn, DUI, stream, fxmanifest, PlayEntityAnim, modello per server RP.
---

# FiveM + Blender + Sollumz: dal modello alla risorsa pronta

Questa cartella e' la skill, NON il progetto dell'utente. Percorsi relativi a questa cartella (`<skill>`).
Tutto e' scriptabile in Python: **non serve mai cliccare nella UI** (la UI resta opzionale per controllo visivo).

## Cosa produci (Definition of Done)

Una cartella risorsa FiveM funzionante:

```
<risorsa>/
  fxmanifest.lua            data_file DLC_ITYP_REQUEST, script, files
  stream/                   Gen8 (FiveM "classico" = quello usato di base)  .ydr .yft .ytd .ytyp .ycd ...
  stream_enhanced/          Gen9 (FiveM for GTAV Enhanced) - ignorata dal FiveM classico
  client/sz_lib.lua         libreria: spawn, animazioni, DUI, porte, tint, attach + exports
  client/main.lua           codice/comandi di test per gli asset
  server/*.lua              spawn networked + animazioni sincronizzate (state bag)
  html/screen.html          (se DUI)
  README.md                 cosa contiene + eventuali azioni manuali residue
```

+ il `.blend` sorgente + `build_report.json` (audit, file scritti) + **istruzioni d'uso** per l'utente
(nome modello, come spawnarlo, come triggerare ogni animazione, eventuali limiti).

Non dichiarare "fatto" se: `sz.audit()` ha errori, mancano binari in `stream/` (o restano XML da convertire
senza dirlo chiaramente), o non hai verificato i binari (`CwXmlToBin --info`) quando il tool e' disponibile.

## Regole d'oro (violarle = asset che non funziona in gioco)

1. **Nomi**: minuscolo `[a-z0-9_]`, <= 63 caratteri, prefisso proprio (`myrp_...`), mai nomi vanilla
   (`prop_`, `v_`, `p_`...). Nome file .ydr = nome archetipo = nome usato negli script.
2. **Scala/assi**: 1 unita' = 1 m, Z in alto, fronte verso -Y. Rotazione/scala applicate. **Origine = pivot in gioco**
   (base a terra per prop normali, cardine per porte, perno per parti mobili).
3. **UV** chiamate `UVMap 0`, `UVMap 1`...; **vertex color** `Color 1` (Face Corner, Byte Color) sempre dipinto:
   esterni rosso (1,0,0,1), interni MLO verde (0,1,0,1). Senza: prop nero/rosa di notte.
4. **Materiali** solo shader Sollumz (`sz.material` / `sz.convert_existing_materials`). Texture **.dds**, lati potenza
   di 2, mipmap, <= 2048. Il **nome file** della texture e' il nome in gioco.
5. **Collisione** per ogni prop toccabile, con **flag preset** e **materiale di collisione**. Primitive > mesh.
6. **Animazioni**: solo ossi con keyframe in **quaternion** (location/rotation_quaternion/scale), 30 fps, un solo osso
   radice. Clip name = quello che passi a `PlayEntityAnim`.
7. **YCD esce solo in XML** da Sollumz: va SEMPRE convertito (CwXmlToBin o CodeWalker). Idem tutti i file se
   l'export NATIVE non e' disponibile (PyMateria = solo Windows).
8. Ogni passo si **verifica**: `sz.audit()` prima dell'export, `CwXmlToBin --info` dopo la conversione,
   comandi `/sz_*` in gioco.

## Intervista iniziale (chiedi SOLO cio' che non e' gia' chiaro)

Fai le domande in un unico messaggio, con default proposti. Se l'utente dice "decidi tu", usa i default.

| # | Domanda | Default |
|---|---|---|
| 1 | Cos'e' l'oggetto e come si usa in gioco? (arredo, oggetto in mano, porta, insegna, schermo, distributore...) | - |
| 2 | Sorgente: modello esistente (.glb/.fbx/.obj/.blend, texture) o da modellare? Se generato da AI/scaricato: licenza ok? | file fornito |
| 3 | Statico, si muove con la fisica, si rompe, o ha parti animate? Le animazioni partono da sole (loop) o da script (evento/comando/target)? | statico |
| 4 | Materiali speciali: emissivo, vetro/trasparenze, schermo da sostituire con DUI (URL/pagina?), varianti colore? | no |
| 5 | Dove vive: spawnato da script, piazzato fisso sulla mappa (coordinate/ymap), dentro un MLO (interno)? | spawnato da script, esterno |
| 6 | Collisione: forma/materiale (legno, metallo, plastica, vetro...)? Il player ci deve salire sopra? | box + materiale dedotto |
| 7 | Budget: triangoli/qualita' (prop piccolo < 3k tri, medio < 10k, hero < 30k), LOD necessari (visibile da lontano?) | auto |
| 8 | Nome risorsa e prefisso nomi; FiveM classico (Gen8) e/o Enhanced (Gen9)? | `myrp_`, entrambe |
| 9 | Ambiente: Windows con Blender+Sollumz+PyMateria? Blender MCP attivo? CodeWalker/CwXmlToBin installati? | rileva con `env_report()` |

## Albero decisionale

| Caso | Formato | Ricetta |
|---|---|---|
| Arredo, oggetto fermo, decorazione | `.ydr` + collisione embedded, flag `static` | [recipe-static.md](references/recipe-static.md) |
| Cade/si spinge (sedie, coni, barili) | `.ydr` + collisione embedded, flag `dynamic` | [recipe-dynamic-fragment.md](references/recipe-dynamic-fragment.md) |
| Si rompe in pezzi / parti che si staccano (lampioni, cartelli, barriere) | `.yft` (fragment) | [recipe-dynamic-fragment.md](references/recipe-dynamic-fragment.md) |
| Parti che si muovono (coperchi, sportelli, leve, ventole, bracci) | `.ydr` con scheletro + `.ycd` | [recipe-animated.md](references/recipe-animated.md) |
| Texture che scorre (nastri, cascate, insegne LED, schermi finti) | `.ydr` + `.ycd` UV | [recipe-animated.md](references/recipe-animated.md#uv-animation) |
| Schermo/monitor/cartellone con contenuto web live | `.ydr` + `.ytd` esterno + DUI | [recipe-dui.md](references/recipe-dui.md) |
| Porta/cancello/garage/sbarra | `.ydr` 1 osso + special attribute | [recipe-doors.md](references/recipe-doors.md) |
| Lampade, neon, luci che lampeggiano | luci embedded + shader emissive | [recipe-lights-emissive.md](references/recipe-lights-emissive.md) |
| Stesso modello in piu' colori | shader `*_tnt` + palette | [materials-textures.md](references/materials-textures.md#tint) |
| Oggetto in mano al ped | `.ydr` piccolo + `AttachEntityToEntity` | [recipe-static.md](references/recipe-static.md#oggetti-in-mano) |
| Piazzare fisso sulla mappa | `.ymap` (+ `_manifest.ymf` per LOD/HD txd) | [recipe-map-placement.md](references/recipe-map-placement.md) |
| Veicoli, vestiti, armi, MLO | casi speciali | [recipe-vehicles-clothes-weapons.md](references/recipe-vehicles-clothes-weapons.md) |

## Pipeline (in ordine, ogni passo verificato)

0. **Ambiente** - [setup.md](references/setup.md). In Blender: `import sz_fivem as sz; sz.env_report()`.
   Annota se `native_gen8` e' true (Windows+PyMateria) e se CwXmlToBin e' compilato.
1. **Spec** - scrivi la spec JSON della richiesta ([python-pipeline.md](references/python-pipeline.md),
   esempio completo `templates/spec_examples/all_types.json`). La spec e' la "verita'": per correggere, si corregge
   la spec e si ricostruisce, non si ritocca a mano la scena.
2. **Texture** - PNG/TGA -> DDS automatico (`scripts/dds_convert.py`, texconv se presente). Regole in
   [materials-textures.md](references/materials-textures.md).
3. **Build** - `blender -b -P <skill>/scripts/build_from_spec.py -- spec.json` oppure, da MCP/console,
   `import build_from_spec as b; b.build("spec.json")`. Per casi fuori dalla spec usa direttamente le funzioni
   di `sz_fivem` ([python-pipeline.md](references/python-pipeline.md#api)).
4. **Controllo visivo** (se hai viewport/MCP/vision): screenshot del modello, del pivot, della collisione
   (`sz` crea oggetti `*.col`), di ogni posa animata. Correggi la spec se qualcosa e' fuori posto.
5. **Audit** - automatico nella build; zero errori. I warning vanno letti e giustificati.
6. **Export** - automatico: NATIVE (se disponibile) + CW XML, Gen8 + Gen9.
7. **Conversione/verifica** - `make_resource` usa `tools/CwXmlToBin` se compilato: XML -> Gen8, YCD, Gen8 -> Gen9,
   poi `CwXmlToBin --info stream/*` per verificare texture/ossi/clip. Senza tool: istruzioni CodeWalker nel README
   ([codewalker-conversion.md](references/codewalker-conversion.md)).
8. **Risorsa** - generata in `resource.path`. Integrazione e codice Lua: [fivem-integration.md](references/fivem-integration.md).
9. **Consegna** - riepilogo all'utente: file, nomi modello/ytd/ycd/clip, comandi di test (`/sz_<nome>`,
   `/sz_<nome>_<clip>`), snippet Lua per l'uso reale, limiti noti, passi manuali residui (se ce ne sono).

Se qualcosa non va in gioco: [troubleshooting.md](references/troubleshooting.md).

## Riferimenti

| File | Contenuto |
|---|---|
| [setup.md](references/setup.md) | installazione Blender/Sollumz/PyMateria/CodeWalker/CwXmlToBin/texconv, modi di eseguire Python |
| [python-pipeline.md](references/python-pipeline.md) | formato spec JSON, API `sz_fivem`, esempi di script |
| [asset-formats.md](references/asset-formats.md) | ydr/ydd/yft/ybn/ytd/ytyp/ymap/ycd, gerarchie Sollumz, Gen8 vs Gen9 |
| [modeling-rules.md](references/modeling-rules.md) | scala, pivot, topologia, budget, UV, vertex color, normali, nomi |
| [materials-textures.md](references/materials-textures.md) | shader, DDS, embedded vs YTD, specular, alpha, emissive, tint, HD txd |
| [shaders-catalog.md](references/shaders-catalog.md) | tutti i 296 preset con sampler e parametri |
| [collisions.md](references/collisions.md) | embedded vs ybn, primitive, flag, materiali, collisioni per parti animate |
| [lods.md](references/lods.md) | LOD del drawable, distanze, lodDist archetipo, HD/LOD in ymap |
| [archetypes-ytyp.md](references/archetypes-ytyp.md) | flag archetipo (valori bit), special attribute, campi, esempi |
| [recipe-static.md](references/recipe-static.md) | prop statico, oggetto in mano |
| [recipe-dynamic-fragment.md](references/recipe-dynamic-fragment.md) | prop fisici e rompibili (YFT) |
| [recipe-animated.md](references/recipe-animated.md) | scheletro, YCD, UV anim, auto start, trigger da Lua, sync multiplayer |
| [recipe-dui.md](references/recipe-dui.md) | materiale sostituito da DUI, render target, interazione |
| [recipe-doors.md](references/recipe-doors.md) | porte/cancelli/garage, door system |
| [recipe-lights-emissive.md](references/recipe-lights-emissive.md) | luci embedded, flashiness, emissive, neon |
| [recipe-map-placement.md](references/recipe-map-placement.md) | ymap, CodeWalker, _manifest.ymf |
| [recipe-vehicles-clothes-weapons.md](references/recipe-vehicles-clothes-weapons.md) | cosa cambia per veicoli, vestiti, armi, MLO |
| [fivem-integration.md](references/fivem-integration.md) | fxmanifest, stream/stream_enhanced, natives, limiti streaming, Lua |
| [codewalker-conversion.md](references/codewalker-conversion.md) | CwXmlToBin, CodeWalker manuale, Alchemist |
| [sollumz-internals.md](references/sollumz-internals.md) | sollum_type, operatori `bpy.ops.sollumz.*`, proprieta' (per casi custom) |
| [troubleshooting.md](references/troubleshooting.md) | sintomo -> causa -> fix |

## File della skill

- `scripts/sz_fivem.py` - libreria Blender/Sollumz (deterministica, testata su Blender 5.2.2 + Sollumz 2.9.0).
- `scripts/build_from_spec.py` - spec JSON -> scena -> audit -> export -> risorsa.
- `scripts/dds_convert.py` - immagini -> DDS (BC1/BC3/RGBA, mipmap) senza dipendenze da Blender.
- `scripts/make_resource.py` - export -> risorsa FiveM (+ conversione/verifica con CwXmlToBin).
- `tools/CwXmlToBin/` - convertitore C# su CodeWalker.Core: XML->binario, Gen8->Gen9, `--info` per verifica.
- `templates/resource/` - Lua (client/server lib), pagina DUI. `templates/spec_examples/` - spec d'esempio.
