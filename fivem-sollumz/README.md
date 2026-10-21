# fivem-sollumz

Skill per agenti (Claude Code, Kilo, Codex, Cursor, GPT/vision agent con Python) che porta un modello 3D in
Blender a una **risorsa FiveM pronta**, con Sollumz 2.9: prop statici, fisici, rompibili, animati (YCD) con
trigger Lua, UV animation, schermi DUI, porte, luci, tint, LOD, collisioni, YTD/YTYP/YMAP, Gen8 + Gen9.
Tutto pilotabile da Python (spec JSON -> build -> export -> risorsa), senza UI.

Punto d'ingresso: [SKILL.md](SKILL.md).

## Installazione della skill
- Claude Code: copia (o collega) la cartella in `%USERPROFILE%\.claude\skills\fivem-sollumz` (o `.agents/skills`).
- Altri agenti: dai come contesto `SKILL.md` + i reference necessari, e l'accesso alla cartella `scripts/`.
- Requisiti macchina: [references/setup.md](references/setup.md) (Blender 4.2+, Sollumz 2.9+, consigliati PyMateria,
  .NET 8 per `tools/CwXmlToBin`).

## Prova rapida
```bash
blender -b -P fivem-sollumz/scripts/selftest.py -- C:/tmp/sz_selftest
```
Costruisce 8 asset d'esempio (statico con LOD, dinamico, animato con 2 clip, UV scroll, schermo DUI, lampada con
luce, porta, fragment rompibile), crea la risorsa e, se CwXmlToBin e' compilato, verifica i binari.
Testato su Blender 5.2.2 LTS + Sollumz 2.9.0 (headless) e CodeWalker.Core (GitHub, aprile 2025).
