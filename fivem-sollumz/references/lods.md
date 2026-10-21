# LOD e distanze

Tre livelli diversi, da non confondere:

1. **LOD del drawable** (dentro il `.ydr`): High / Medium / Low / VeryLow. Ogni Drawable Model ha una mesh per
   livello (`Mesh Properties > Sollumz LODs`). Distanze in `drawable.drawable_properties.lod_dist_high/med/low/vlow`.
   Default Sollumz **9998** = "usa sempre questo livello": se aggiungi LOD Medium/Low devi abbassare le distanze
   (`sz.set_lod_distances(d, 25, 50, 75, 100)`), altrimenti non verranno mai usati.
   `VeryHigh` serve solo ai veicoli (`_hi.yft`).
2. **lodDist dell'archetipo** (`.ytyp`): oltre questa distanza l'entita' non viene disegnata (fade). Prop piccoli
   50-100 m, medi 100-150, grandi/insegne 200-500. Troppo alta = costo inutile; troppo bassa = pop-in.
3. **Gerarchia LOD della mappa** (`.ymap`): un'entita' HD con un genitore LOD/SLOD (modello semplificato per la
   distanza). Serve solo per oggetti grandi visibili da lontano piazzati con ymap
   ([recipe-map-placement.md](recipe-map-placement.md)).

## Generazione
- `sz.auto_lods(model)` / `"lods": "auto"`: Decimate 50%, 25%, 10% dal LOD High. Va bene per forme semplici; per
  modelli importanti fai LOD a mano (rimuovi dettagli piccoli, fondi materiali, texture piu' piccole).
- `sz.add_lod(model, "MEDIUM", mesh_o_oggetto)` per LOD fatti a mano.
- Regola pratica: High = vicino (< 25-30 m), Medium ~50%, Low ~25% + materiali fusi, VeryLow = scatola/billboard.
- Prop sotto ~1500 tri e lodDist <= 100: i LOD non servono.

## Verifica
`CwXmlToBin --info x.ydr` stampa `models H/M/L/VL` e le `lodDist`: controlla che i livelli ci siano e le
distanze non siano 9998 quando hai LOD.
