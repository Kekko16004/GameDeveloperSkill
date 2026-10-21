# Formati asset GTA V e come li rappresenta Sollumz

| Ext | Cos'e' | In Blender (Sollumz) | Export Sollumz 2.9 |
|---|---|---|---|
| `.ydr` | Drawable: mesh + shader + (texture embedded) + (scheletro) + (luci) + (collisione embedded) | `Drawable` (empty, o **armatura** se ha scheletro) > `Drawable Model` (mesh, LOD in `Mesh > Sollumz LODs`) | NATIVE + CWXML |
| `.ydd` | Drawable Dictionary: piu' drawable in un file (ped, LOD, minimappe) | `Drawable Dictionary` > Drawable... | NATIVE + CWXML |
| `.yft` | Fragment: drawable + fisica per osso (parti separabili, veicoli, rompibili) | `Fragment` (armatura) > `Drawable` + `Bound Composite`, ossi con `Use Physics` | NATIVE + CWXML |
| `.ybn` | Collisione statica separata (mappe), coordinate mondo | `Bound Composite` radice > `Bound GeometryBVH` > poly | NATIVE + CWXML |
| `.ytd` | Texture Dictionary (texture condivise, schermi DUI, vestiti) | `Sollumz Tools > Texture Dictionaries` (scena) | NATIVE + CWXML |
| `.ytyp` | Archetipi: definisce ogni modello (lodDist, flag, txd, ycd, tipo) | `Sollumz Tools > Archetype Definition` (scena) | NATIVE + CWXML (FiveM accetta anche l'XML rinominato `.ytyp`) |
| `.ymap` | Mappa: istanze piazzate (entity), LOD, occluder, cargen | `ymap_next` (Maps) | NATIVE + CWXML (FiveM accetta XML rinominato) |
| `.ycd` | Clip Dictionary: animazioni (ossa, UV, camera) | `Clip Dictionary` > `Clips` + `Animations` | **solo CWXML** -> conversione obbligatoria |
| `+hi.ytd`, `+hidr.ytd` | texture HD caricate da vicino | toggle HD sull'immagine | auto se HD |

## Gerarchie che `sz_fivem` crea

```
Prop statico/dinamico (.ydr)
myrp_crate                  sollumz_drawable (empty)
├─ crate.model              sollumz_drawable_model (mesh, materiali Sollumz)
└─ myrp_crate.col           sollumz_bound_composite
   └─ Bound Box             sollumz_bound_box (flag preset + materiale collisione)

Prop animato (.ydr con scheletro)
myrp_chest                  sollumz_drawable (ARMATURA, osso "root" tag 0, osso "lid" tag calcolato)
├─ base.model               vincolo COPY_TRANSFORMS -> osso root
├─ lid.model                vincolo COPY_TRANSFORMS -> osso lid  (mesh in spazio osso)
└─ myrp_chest.col > .bvh > hull (sollumz_bound_poly_triangle)
myrp_chest_anims            sollumz_clip_dictionary
├─ Clips   > open.clip (hash "open", name "open.clip", durata = frame/30)
└─ Animations > open (hash "open", target = armatura, action con pose.bones["lid"].rotation_quaternion)

Fragment (.yft)
myrp_sign_break             sollumz_fragment (armatura; osso radice = nome prop)
├─ myrp_sign_break.mesh     sollumz_drawable (empty) > modelli legati agli ossi
└─ myrp_sign_break.col      sollumz_bound_composite > Bound Box per osso (vincolo all'osso, massa)
```

## Gen8 vs Gen9

- **Gen8** = GTA V Legacy = FiveM "normale" (quello piu' usato). Cartella `stream/`.
- **Gen9** = GTA V Enhanced = "FiveM for GTAV Enhanced" (nuovo client Cfx). Cartella `stream_enhanced/`: se presente,
  su Enhanced viene caricata AL POSTO di `stream/`; il FiveM classico la ignora. Una risorsa puo' supportare entrambi.
- Sollumz esporta entrambe le versioni (cartelle `gen8/` e `gen9/`). `.ytd/.ydr/.ydd/.yft/.ypt` hanno formati
  diversi; `.ytyp/.ymap/.ybn/.ycd` sono uguali.
- Enhanced: max **128 materiali/geometrie** per file; texture `script_rt_*` solo `A8R8G8B8` senza mip.
- Asset Legacy esistenti -> Enhanced: Cfx **Alchemist** (portal.cfx.re), CodeWalker *Asset Converter*,
  `CwXmlToBin --gen9`.

## Quale formato scegliere

- Prop unico: `.ydr`. Piu' prop che condividono texture: `.ydr` con texture NON embedded + un `.ytd` comune
  (archetipi con `textureDictionary` = quel ytd).
- Parti che si staccano o pivotano fisicamente: `.yft`. Parti che si muovono per animazione: `.ydr` + scheletro + `.ycd`.
- Collisione: embedded nel `.ydr`/`.yft` per prop (sempre se spawnati da script); `.ybn` separato solo per geometria
  di mappa piazzata via ymap (pavimenti, edifici).
- Porte: `.ydr` con 1 osso + archetipo con special attribute (non serve ycd).
