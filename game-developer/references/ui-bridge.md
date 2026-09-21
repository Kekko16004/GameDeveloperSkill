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

## 2. Flusso DesignerSkill (NON OPZIONALE — SCELTA UTENTE PER OGNI SCHERMATA)

Saltare `real-world-design` = FAIL della macrotask UI. UXML scritto a mano come primo passo = FAIL.

### REGOLA TASSATIVA: VARIANT STUDIO E SCELTA UTENTE PER OGNI SCHERMATA
**È VIETATO auto-scegliere o generare direttamente HUD, Pausa o GameOver basandosi sul Main Menu senza presentare le opzioni all'utente.**
L'utente DEVE SEMPRE avere la scelta tra 3-4 varianti per CIASCUNA schermata (Main Menu, HUD, PauseMenu, GameOver/Victory):

1. **Coerenza Stilistica nei Token**: Tutte le schermate successive riutilizzano i token estetici consolidati nel Main Menu (`ui/tokens.css`, palette colori, font, bordi, vibe).
2. **3-4 Varianti Strutturali di Layout**: Per ogni schermata, genera 3-4 interpretazioni di layout distinte in Variant Studio (o mock HTML in `ui/mocks/`):
   - **HUD**: es. Var 1 = Diegetico integrato; Var 2 = Split angoli (survival); Var 3 = Bottom bar compatta; Var 4 = Minimalista immersivo.
   - **Pausa**: es. Var 1 = Sidebar laterale; Var 2 = Modale centrale semitrasparente; Var 3 = Registro/libro diegetico; Var 4 = Minimal scuro.
   - **GameOver / Victory**: es. Var 1 = Certificato/pergamena con ceralacca; Var 2 = Epitaffio/banner oscuro; Var 3 = Statistiche dettagliate giorno; Var 4 = Cinematico sobrio.
3. **Screenshot Gallery Playwright**: Cattura lo screenshot 1440x900 della gallery delle varianti (`screenshots/04X-ui-<screen>-variants.png`).
4. **STOP e Scelta Esplicita dell'Utente**: Mostra la preview all'utente e ATTENDI la sua scelta. Procedere senza il consenso dell'utente è un bug.
5. **Transpilazione**: Solo DOPO che l'utente ha scelto la variante (es. "Scelgo la 2"), procedi con il transpiler a generare UXML e USS.

---

## 3. Transpilazione e Setup Unity
1. Converti la variante scelta con lo script:
   ```bash
   node scripts/ui-transpiler.mjs <mock.html> <mock.css> "<project>/Assets/_Game/UI" <ScreenName>
   ```
2. **Setup PanelSettings Obbligatorio**:
   - Verificare che il GameObject contenente `UIDocument` abbia assegnato un `PanelSettings` valido (Match 1920x1080 o Reference Resolution attiva). Senza `PanelSettings`, Unity non disegna nulla a schermo!
   - Assegnare il controller C# generato per gestire il binding di click ed eventi di gioco.
