# Roadmap

Idee valide non ancora implementate (dalle vecchie bozze in `docs/ideas/`, rimosse il 2026-09-25, e dall'audit). In ordine di impatto.

| # | Idea | Perché | Note |
|---|---|---|---|
| 1 | Test end-to-end Unreal 5.8 di `gds_ue.py` | il ramo realistico è scritto ma non eseguito (qui c'è solo UE 5.4) | serve installare UE 5.8 |
| 2 | `GDS.SceneLint`: compenetrazioni prop-prop e raggiungibilità NavMesh | due classi di bug ancora viste solo in Play Mode | OverlapBox tra bounds + `NavMesh.CalculatePath` spawn → goal |
| 3 | Biomi in `GDS.World` (più layer/scatter set per regione, transizioni) | mondi grandi più vari | maschera di rumore a bassa frequenza → set di layer e scatter |
| 4 | Strade/fiumi su terrain (spline che scava e appiattisce) | collega villaggi e landmark | Splines package + carve dell'heightmap |
| 5 | Meteo e ciclo giorno/notte runtime | mood e gameplay (survival, horror) | componente runtime che interpola i preset LookDev |
| 6 | Behaviour tree / State Tree template per NPC | nemici oltre chase/attack | Unity Behavior package; UE State Tree |
| 7 | Varietà villaggi (layout per cultura: medievale, nordico, desertico, asiatico) | villaggi meno ripetitivi | preset di spec `village_*.json` + palette |
| 8 | Template di gioco completi (`/game-template fps` ecc.) | partenza più veloce | GDD + world spec + systems già decisi per riga di `genres.md` |
| 9 | Salvataggio dei chunk voxel modificati | sandbox persistente | diff per chunk su disco |
| 10 | Godot come terzo motore | solo se richiesto | non prioritario |
