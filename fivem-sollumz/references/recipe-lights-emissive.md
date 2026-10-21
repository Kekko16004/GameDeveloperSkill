# Ricetta: luci embedded ed emissive

Due cose diverse, di solito insieme:
- **Emissive** (shader): la superficie "brilla" (lampadina, neon, LED) ma NON illumina l'ambiente.
- **Luce embedded** (nel `.ydr`/`.yft`): illumina davvero l'ambiente (point/spot/capsule), con corona, flicker,
  ombre, orari.

## Spec
```json
{ "type": "light", "name": "myrp_lamp", "source": {...},
  "material": { "slots": {
     "Body": { "shader": "normal_spec", "textures": {...} },
     "Bulb": { "shader": "emissive", "textures": { "diffuse": "textures/myrp_bulb_e.png" }, "params": { "emissiveMultiplier": 6 } } } },
  "lights": [ { "kind": "point", "location": [0, 0, 1.55], "color": [1.0, 0.85, 0.6],
                "intensity": 6, "falloff": 8, "falloff_exponent": 8, "flashiness": 0,
                "corona_size": 0.5, "corona_intensity": 1.0, "cast_shadows": false } ] }
```
`sz.add_light(drawable, kind, location, color, intensity, falloff, falloff_exponent, cone_outer_deg,
cone_inner_deg, direction, flashiness, time_flags_all_day, cast_shadows, corona_intensity, corona_size, bone)`:
- `location`: nello spazio del drawable (origine del prop).
- `kind="spot"` + `direction=(0,0,-1)` (verso il basso) + coni in gradi: lampioni, faretti.
- `falloff`: raggio in metri. `intensity`: 1-10 tipico per interni, 10-50 per esterni grandi.
- `time_flags_all_day=True`: accesa 24h (altrimenti imposta `ldata.time_flags` per ore specifiche, es. solo notte).
- `bone`: per luci che si muovono con un osso (prop animati, es. lampeggiante rotante).
- `cast_shadows`: costoso, solo per luci importanti.

## Flashiness (lampeggio)
| valore | effetto |
|---|---|
| 0 CONSTANT | fissa |
| 1 RANDOM | casuale (usa extent) |
| 3 / 4 / 5 | 1 / 2 / 5 lampeggi al secondo |
| 9 ALARM | allarme |
| 10 ON_WHEN_RAINING | quando piove |
| 11-13 CYCLE_1..3 | cicli predefiniti |
| 14 DISCO | disco |
| 15 CANDLE | candela |
| 17 FIRE | fuoco |
| 19 ELECTRIC | neon difettoso |
| 20 STROBE | strobo |
Passa l'intero o il nome (`"flashiness": "CANDLE"`).

## Neon / insegne
- Tubi neon: shader `emissive` o `emissivestrong`, diffuse = colore pieno, `emissiveMultiplier` 4-10.
- Solo di notte: `emissivenight` + archetipo TIME o luce con time flags notturne.
- Lampeggio dell'insegna (non della luce): UV animation su una texture a strisce acceso/spento
  ([recipe-animated.md](recipe-animated.md#uv-animation)) o due archetipi time.

## Limiti
- Molte luci embedded per prop = costo: 1-2 per prop, usa corona+emissive per le altre lampadine.
- Le luci embedded di prop spawnati funzionano; per illuminazione di mappa lontana servono LOD lights (ymap,
  Sollumz `map_bake_lod_lights`).
