# Troubleshooting (sintomo -> causa -> fix)

## Blender / export
| Sintomo | Causa | Fix |
|---|---|---|
| "Sollumz non e' abilitato" | addon non installato/abilitato | [setup.md](setup.md) |
| "No Sollumz objects selected for export" | oggetti senza sollum_type o non selezionati | `sz.make_drawable(...)`; `export(objects=[...])` |
| "model has no Sollumz materials" | materiale Principled o slot vuoto | `sz.material` / `convert_existing_materials` |
| `KeyError 'Principled BSDF'` in conversione | materiale con altro shader | ricrea il materiale o usa `sz.material` |
| export solo `.xml` | PyMateria assente (Linux/macOS) | normale: `make_resource` converte con CwXmlToBin |
| texture non embedded "not in DDS format" | png/jpg | `dds_convert.py` (la build lo fa) |
| vertici "raddoppiati" dopo l'export | per GTA un vertice = posizione + attributi (face corner) | normale: valuta i triangoli |
| invisibile in CodeWalker | UV/Color attribute con nomi sbagliati | `UVMap 0`, `Color 1` (`ensure_uv_names`) |
| collisione spostata rispetto al modello | scala non applicata / matrici stale | `prepare_mesh`, ricostruisci con la spec |

## In gioco: il modello
| Sintomo | Causa | Fix |
|---|---|---|
| `IsModelInCdimage` false / CreateObject non crea nulla | file non in `stream/`, nome diverso dall'archetipo, ytyp non caricato | nome file = archetipo; `data_file DLC_ITYP_REQUEST`; restart + riconnessione |
| invisibile ma ha collisione | texture/shader rotti, lodDist 0, `shadow_only` | controlla flag e `--info` |
| texture viola/rosa a scacchi | texture mancante (ytd non trovato o nome diverso) | `textureDictionary` dell'archetipo = nome ytd; nomi texture |
| nero di giorno / rosa-luminoso di notte | vertex color mancante o sbagliato | `Color 1` rosso (esterni) / verde (interni) |
| rilievi invertiti | normal map OpenGL non convertita | `normal_format` ([materials-textures.md](materials-textures.md)) |
| si vede attraverso / trasparenze sbagliate | shader alpha su tutta la mesh | materiale alpha solo dove serve; `cutout`; `draw_last` |
| sparisce troppo presto | `lodDist` basso | alza `lod_dist` |
| scatti LOD o LOD mai usati | distanze 9998 o LOD brutti | `set_lod_distances` |
| ci passo attraverso | nessuna collisione / bound senza flag / materiale collisione mancante | `add_embedded_collision`, audit |
| non si muove quando lo spingo | flag `static` o freeze | flag `dynamic`, `FreezeEntityPosition(false)` |
| vola via / trema appena spawnato | collisioni compenetrate, massa enorme o 0 | hull/box separati, materiali HOLLOW |
| warning "Oversized asset" | texture troppo grandi | 1024/2048 max, ytd condivisi |
| crash `ERR_GFX_STATE` su Enhanced | texture `script_rt_*` non A8R8G8B8 | RGBA senza mip |
| crash su Enhanced con molti materiali | > 128 materiali/geometrie | riduci materiali |

## In gioco: animazioni
| Sintomo | Causa | Fix |
|---|---|---|
| `HasAnimDictLoaded` non diventa mai true | `.ycd` mancante (rimasto `.ycd.xml`) o nome diverso | converti il ycd; nome = `clip_dictionary` |
| `PlayEntityAnim` non fa niente | parametri invertiti (clip, dict!) o prop senza scheletro | `PlayEntityAnim(ent, CLIP, DICT, ...)`; prop da `make_animated_drawable` |
| si muove la parte sbagliata / niente | tag ossi diversi tra ydr e ycd (osso rinominato dopo) | riesporta ydr+ycd insieme; `--info` confronta i tag |
| la parte ruota attorno al punto sbagliato | pivot errato | `pivot` = asse/cardine in coordinate mondo |
| rotazione "a scatti" o al contrario | rotazioni >180 gradi tra due chiavi | chiavi intermedie (<= 120 gradi) |
| torna chiuso a fine animazione | `hold` false | `PlayEntityAnim(..., loop=false, hold=true, ...)` |
| solo io vedo l'animazione | `PlayEntityAnim` e' locale | state bag / evento a tutti ([recipe-animated.md](recipe-animated.md)) |
| auto start non parte | flag mancanti o nome clip | `has_anim` + `auto_start_anim`, clip name = nome modello |
| UV anim ferma | shader senza UV anim (es. `normal_spec`) o flag | shader compatibile; `has_uv_anim` + `auto_start_anim`; hash clip ricalcolato |

## DUI
| Sintomo | Causa | Fix |
|---|---|---|
| schermo mostra ancora il placeholder | `origTxd/origTxn` sbagliati, texture embedded invece che in ytd, archetipo senza `textureDictionary` | [recipe-dui.md](recipe-dui.md) |
| immagine ruotata/specchiata/tagliata | UV dello schermo | UV 0..1 dritte, rapporto corretto |
| pagina bianca | URL errato / `files{}` mancante nel manifest | `nui://<risorsa>/html/screen.html` |
| FPS bassi | troppe DUI attive | crea/distruggi in base alla distanza |

## Porte
Vedi [recipe-doors.md](recipe-doors.md#problemi-tipici).
