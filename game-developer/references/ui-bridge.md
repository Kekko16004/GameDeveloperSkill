# UI Bridge — Da DesignerSkill a Unity UI Toolkit

Ponte per progettare e convertire l'intera suite di schermate di gioco (Main Menu, HUD diegetico, Pausa, Game Over) create con `DesignerSkill` (skill `designer`, percorso in `paths.designerSkill` di `config.json`) in UI native Unity UI Toolkit.

## 3b. Nucleon: pagina web (NUI su CEF, come FiveM); RmlUi solo legacy
Dal 2026-10-29 la UI di gioco dell'engine è una pagina Chromium vera (NUI/DUI): il mock HTML scelto dall'utente è già la schermata, **nessuna transpilazione** (flex/grid, animazioni CSS, web font, SVG, JS e `backdrop-filter` sul gioco funzionano). Dettaglio in [nucleon-loop.md](nucleon-loop.md) §7.
1. Il template ha `UI/index.html` (una pagina: `#hud` tuo, `#nc-menu` pausa/titolo/impostazioni). Metti la variante scelta nelle sezioni della pagina (HUD in `#hud`; game over, negozio... come `<section>` mostrate da messaggi), copia il CSS del mock quasi tale e quale; `body` trasparente, `pointer-events: none` sull'HUD; font e librerie dentro `UI/` (niente URL esterni).
2. Lua → pagina `SendNUIMessage({type = "...", ...})`; pagina → Lua `fetch("https://" + GetParentResourceName() + "/nome", {method:"POST", body: JSON.stringify(dati)})` + `RegisterNUICallback("nome", function(dati, risposta) risposta("ok") end)`; `SetNuiFocus(true, true)` solo con un menu aperto. Controller: `Content/Scripts/game.lua` (o `ui_<screen>.lua`); niente regole di gioco nel JS della pagina.
3. Pausa e opzioni: `nc.pause` e `nc.graphics_options.bindWeb()` pilotano già `#nc-menu` (opzioni grafiche cablate): si restyla con le variabili CSS di `nc-menu.css`, non si rifà.
4. Controllo: Play e `ncli play-test --shot` (la pagina si vede nell'immagine del gioco), `ncli call web_ui '{"action":"status"}'` (browser, pagina aperta, focus), `nui_eval` per il JS; guarda sempre il PNG. `IsWebBrowserAvailable()` deve essere true (la build congelata ha CEF).
5. Legacy RmlUi, solo per progetti che hanno già `.rml`: `python scripts/html2rml.py <mock.html> "<project>/UI/<screen>.rml" --model <screen>` (JSON dei cambi; `NC_EDITOR_UI_DOCUMENT=...` per il controllo). Un gioco nuovo non lo usa.

---

## 0. Ordine tassativo

`ui-main-menu` PRIMA di HUD. Build settings: MainMenu scena **index 0**. Il player non spawna in FP nel livello. Senza Main Menu il parent marca lo slice FAIL.

Worker isolato per schermata (vedi `workers.md`). Non fare le 4 UI nello stesso Task.

## 1. Le 4 Schermate Fondamentali del Gioco
L'agente deve progettare ciascuna delle 4 schermate attraverso il protocollo `designer`:

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

Saltare `designer` = FAIL della macrotask UI. UXML scritto a mano come primo passo = FAIL.

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
3. **Game slot (parti di gioco dentro la UI)**: se il designer ha scritto `design/ui-slots.json` (`game-slots.mjs scan`), ogni slot è un punto dove va un render del gioco, non UI (ritratto/corpo del giocatore, item, veicolo, minimappa, mondo dietro).
   - Per ogni slot crea la sorgente nel motore: camera dedicata + `RenderTexture` (Unity) / `SceneCapture2D` (Unreal) / `SubViewport` (Godot), inquadratura come da `framing`, soggetto come da `subject`.
   - Sostituisci il placeholder (`slot-<id>`, classe `game-slot`) con la texture: `style.backgroundImage = Background.FromRenderTexture(rt)`. Lo slot `world` resta trasparente con `picking-mode="Ignore"`: il mondo è la scena 3D dietro.
   - Rifai lo screenshot e verifica che non resti nessun placeholder tratteggiato visibile.

---

## 4. Qualità di base (ESSENZIALE, ogni schermata)

Dettaglio: [quality-baseline.md](quality-baseline.md) §1-2. Va previsto già nei mock delle varianti, non aggiunto dopo.
- **Hover + focus** su ogni pulsante (mouse, tastiera, pad): scala ~1,05 o contorno/riempimento più chiaro, ~0,1 s, cursore a mano. Il focus del pad non salta e non resta su un elemento nascosto.
- **Transizioni** tra scene: dissolvenza ≤ 0,5 s, saltabile con qualsiasi tasto.
- **Testo al 150 %** e lingue più lunghe (DE/RU) senza sovrapposizioni: screenshot di ogni schermata a 100 % e 150 %.
- **Nessuna stringa nel UXML o nel controller**: solo chiavi di `strings.csv`; i prompt (`[E]`) leggono il binding corrente.
- Notifiche brevi e una alla volta, se il GDD le ha scelte (`notifications`).
