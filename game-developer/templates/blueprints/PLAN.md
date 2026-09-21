# Blueprint plan — <game>

Grid: 4 m module. Origin = building corner (min X, min Z). One row = one level-build worker. Names are stable: greybox builds them as `probuilder`/`primitives`, level-build rebuilds them as `kit` in place.

| blueprint | origin (x,y,z) | rotY | cells (X×Z) | floors | mode (greybox → final) | openings | props | scatter | status |
|---|---|---|---|---|---|---|---|---|---|
| BP-house_a | (0,0,12) | 0 | 3×2 | 1 | probuilder → kit | S1 door, N0 window | table, 2 chair, chest | — | [ ] |
| BP-keep | (20,0,0) | 90 | 3×2 | 2 | probuilder → probuilder (gable, Mat_Palette_2) | S1 door, E0 f1 window | torch ×4 | — | [ ] |
| BP-courtyard | (0,0,0) | 0 | — | — | scatter only | — | — | 20 trees, 8 rocks, avoidRadius 14 | [ ] |
