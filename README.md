# GameDeveloperSkill

Orchestratore universale autonomo per lo sviluppo rapido di vertical slice **beta-ready** (livelli da blueprint, lint scena, lighting/post-processing, personaggi animati, VFX, UI Toolkit) da un'idea grezza fino al playtest verificato.

Compatibile con **Kilo**, **Claude Code**, **Codex** e **Antigravity**.

---

## Documentazione e Guide
- 👉 [Guida Rapida Passo-Passo](GUIDA_RAPIDA.md): Guida in 7 passaggi numerati per installare e avviare subito.
- 📐 [Il Geometra](game-developer/references/geometra.md): Standard di dimensionamento e snap per ambienti e arredi.
- 🎨 [Ponte UI DesignerSkill](game-developer/references/ui-bridge.md): Conversione da HTML/CSS a Unity UI Toolkit UXML/USS.
- 🖥️ [TerminalMCP](game-developer/references/terminalmcp.md): Controllo operativo del sistema, finestre, screenshot e input reale.
- 🧱 [Art pipeline](game-developer/references/art-pipeline.md): blueprint JSON → `GDS.LevelBuilder` / ProBuilder, una famiglia kit, hero prop CC0 o tier generativo.
- 🏠 [Blender building generator](game-developer/references/blender-building.md) · [Village](game-developer/references/village.md): case vere (infissi, tetti, travi, balconi, interni) da una spec JSON, headless; villaggi con terreno, strade, lotti. Esempi in `docs/samples/`.
- 🏗️ [Level builder](game-developer/references/level-builder.md) · [Scene lint](game-developer/references/scene-lint.md) · [LookDev](game-developer/references/lookdev.md) · [Characters](game-developer/references/characters.md) · [VFX](game-developer/references/vfx.md) · [Gen3D tiers](game-developer/references/gen3d.md): il layer deterministico (`templates/Editor/GDS/*.cs`, compilato su Unity 6 URP + ProBuilder 6.1.2).
- 📦 [Catalogo CC0 + Asset Store free](game-developer/references/cc0-sources.md): Kenney (incl. personaggi animati, nature, particle), KayKit, Quaternius UAL, Synty Starter, Poly Haven, Sketchfab CC0, shader URP MIT.
- 🧹 [Blender](game-developer/references/blender-game-assets.md): solo sanitize / hero prop.

## Installazione Rapida
Fai doppio click su `install.bat` oppure esegui:
```powershell
powershell ./game-developer/install.ps1 -All
```

## Avvio
Nel tuo coding agent preferito:
```
/game <la tua idea di gioco>
```
