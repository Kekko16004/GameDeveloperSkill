# UI Bridge — Da DesignerSkill a Unity UI Toolkit

Ponte per progettare e convertire l'intera suite di schermate di gioco (Main Menu, HUD diegetico, Pausa, Game Over) create con `DesignerSkill` (`C:\Users\FRANCY\Desktop\DesignerSkill`) in UI native Unity UI Toolkit.

---

## 0. Ordine tassativo

`ui-main-menu` PRIMA di HUD. Build settings: MainMenu scena **index 0**. Il player non spawna in FP nel livello. Senza Main Menu il parent marca lo slice FAIL.

Worker isolato per schermata (vedi `workers.md`). Non fare le 4 UI nello stesso Task.

## 1. Le 4 Schermate Fondamentali del Gioco
L'agente deve progettare ciascuna delle 4 schermate attraverso il protocollo `real-world-design`:

1. **Main Menu (`MainMenu`)**:
   - Titolo stilizzato, sfondo d'atmosfera o vista della scena.
   - Pulsanti: `Gioca`, `Impostazioni` (Volume/Sensibilità mouse), `Esci`.
   - Controller C#: gestione caricamento scena o sblocco vista di gioco.

2. **In-Game HUD (`HUD`)**:
   - Indicatori vitali (Salute, Contagion/Infezione, Stamina/Respiro).
   - Orologio a quadrante / Campana del coprifuoco (Giorno vs Notte).
   - Mirino centrale (Reticle) e **Prompt contestuale diegetico** (es. `[E] Apri credenza`, `[Tasto Dx] Inchioda asse`).
   - Overlay venature nere di contagio che avanzano sui bordi dello schermo all'aumentare dell'infezione.

3. **Menu di Pausa (`PauseMenu`)**:
   - Attivato con `Esc`: congela il tempo di gioco (`Time.timeScale = 0`) e mostra il cursore.
   - Pulsanti: `Riprendi`, `Riavvia Livello`, `Opzioni`, `Menu Principale`.

4. **Schermata Morte / Fine Notte (`GameOver` / `Victory`)**:
   - Registro parrocchiale seicentesco con inchiostro e sigilli: certificato di decesso o vittoria della notte.
   - Statistiche del giorno (ore sopravvissute, assi barricate, rimedi distillati) e pulsante `Riprova`.

---

## 2. Flusso DesignerSkill (NON OPZIONALE)

Saltare `real-world-design` = FAIL della macrotask UI. UXML scritto a mano come primo passo = FAIL.

1. Skill tool `real-world-design`, mode `game`.
2. Token in `ui/tokens.css` dalla palette GDD.
3. 3-4 varianti HTML (Variant Studio se Node c'e; altrimenti mock HTML nella cartella `ui/mocks/`).
4. Playwright 1440x900. File in `screenshots/`.
5. Pick. Poi transpiler. Senza mock HTML su disco il parent non accetta il gate.

---

## 3. Transpilazione e Setup Unity
1. Converti la variante scelta con lo script:
   ```bash
   node scripts/ui-transpiler.mjs <mock.html> <mock.css> "<project>/Assets/_Game/UI" <ScreenName>
   ```
2. **Setup PanelSettings Obbligatorio**:
   - Verificare che il GameObject contenente `UIDocument` abbia assegnato un `PanelSettings` valido (Match 1920x1080 o Reference Resolution attiva). Senza `PanelSettings`, Unity non disegna nulla a schermo!
   - Assegnare il controller C# generato per gestire il binding di click ed eventi di gioco.
