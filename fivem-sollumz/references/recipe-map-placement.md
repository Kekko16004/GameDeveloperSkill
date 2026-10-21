# Ricetta: piazzare prop fissi sulla mappa (.ymap)

Due modi di avere un prop nel mondo:
1. **Script** (`CreateObject`): dinamico, si puo' animare/rimuovere, costa un'entita' per client. Ottimo per
   oggetti interattivi o pochi pezzi.
2. **YMAP**: piazzamento statico caricato dallo streaming, zero script, ideale per arredare zone (decine/centinaia
   di oggetti). Gli oggetti ymap sono comunque trovabili con `GetClosestObjectOfType` (e animabili).

## YMAP con CodeWalker (visuale)
1. CodeWalker > Project window > File > New > Ymap. Aggiungi il tuo ytyp/ydr al progetto (o mettili in un RPF di test).
2. Ymap > New Entity, imposta Archetype = `myrp_crate`, posiziona/ruota.
3. Seleziona la ymap: **Calculate Extents** e **Calculate All Flags**. Salva `myrp_area.ymap`.
4. Tools > Manifest Generator > Generate -> `_manifest.ymf` (necessario per LOD/HD txd/dipendenze).
5. Copia `.ymap` (+ `_manifest.ymf`) in `stream/`. FiveM legge anche la ymap in XML se rinominata `.ymap`.
6. `fxmanifest.lua`: `this_is_a_map 'yes'` (make_resource lo aggiunge se trova .ymap).

## YMAP da Python (Sollumz "Maps")
Sollumz 2.9 ha un editor mappe (`ymap_next`): gruppi di mappe, entity, occluder, cargen, LOD lights.
Approccio semplice e robusto: crea gli oggetti istanza (o empty) dove vuoi i prop, poi
`bpy.ops.sollumz.map_add_obj_as_entity` / `sollumz.map_auto_assign_unassigned`, e export con
`sz.export(..., ymaps=True)`. Per pochi prop e' piu' semplice CodeWalker; per molti (layout procedurali) conviene
scriverli via Python ispirandosi agli operatori in Sollumz `ymap_next/operators/map.py`.

## Coordinate e rotazioni
- Le entity ymap usano quaternioni con segno invertito rispetto alla rotazione visuale (CodeWalker lo gestisce):
  piazza con CodeWalker o con gli operatori Sollumz, non scrivere a mano i quaternioni.
- Collisione: quella embedded del prop funziona anche da ymap. Per geometria grande (pavimenti, rampe) usa un `.ybn`
  in coordinate mondo (`sz.make_static_collision`).

## HD texture e manifest
Texture HD (`+hi`) e LOD parent/child richiedono `_manifest.ymf`:
```xml
<CPackFileMetaData>
 <MapDataGroups itemType="CMapDataGroup" />
 <HDTxdBindingArray itemType="CHDTxdAssetBinding">
  <Item><assetType>AT_DRB</assetType><targetAsset>myrp_crate</targetAsset><HDTxd>myrp_crate+hidr</HDTxd></Item>
  <Item><assetType>AT_TXD</assetType><targetAsset>myrp_pack_txd</targetAsset><HDTxd>myrp_pack_txd+hi</HDTxd></Item>
 </HDTxdBindingArray>
 <imapDependencies itemType="CImapDependency" />
 <imapDependencies_2 itemType="CImapDependencies" />
 <itypDependencies_2 itemType="CItypDependencies" />
 <Interiors itemType="CInteriorBoundsFiles" />
</CPackFileMetaData>
```
(`AT_DRB` drawable, `AT_FRG` fragment, `AT_TXD` texture dictionary.) Il manifest va generato/convertito con
CodeWalker (Manifest Generator) e messo in `stream/`.

## LOD di mappa (oggetti grandi visibili da lontano)
Modello HD + modello LOD semplificato, due ymap: entity HD con flag "LOD in parent map", `lodLevel HD`, parent = ymap
LOD; entity LOD stessa posizione, `lodLevel LOD`, `childLodDist` = lodDist dell'HD, `numChildren` 1. Rigenera il
manifest. (Guida Cfx "Part 6 - LODs".)

## Rimuovere/sostituire oggetti vanilla
Script: `CreateModelHide(x, y, z, radius, GetHashKey('prop_vanilla'), true)`. Mappa: occluder/entity sets, oppure
ymap modificate (avanzato).
