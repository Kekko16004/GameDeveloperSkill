# Guida Rapida: Inizializzazione e Avvio della Pipeline

Questa guida ti spiega passo dopo passo come installare, avviare i server MCP su **Blender** e **Unity**, e far partire la pipeline con qualsiasi coding agent (Kilo, Claude Code, Codex, Antigravity).

---

### 1. Verifica dei Programmi Base
Assicurati di avere installati sul tuo computer:
- **Node.js** (versione 18 o superiore)
- **Python** (versione 3.10 o superiore) con `uv` / `uvx`
- **Blender** (versione 4.2 o 5.x)
- **Unity Hub** (con un Editor LTS installato, es. Unity 6)

---

### 2. Installazione Automatica della Skill
Apri la cartella `C:\Users\FRANCY\Desktop\GameDeveloperSkill` e fai doppio click su:
👉 **`install.bat`** (oppure esegui `powershell ./game-developer/install.ps1 -All`)

Cosa fa in automatico:
1. Registra la skill per tutti i tuoi agenti (**Kilo**, **Claude Code**, **Codex**, **Antigravity**).
2. Rileva i percorsi locali di `VoxelAIArtist`, `DesignerSkill` e `TerminalMCP`.
3. Registra i server MCP nei file di configurazione degli agenti.
4. Scarica e registra l'addon per Blender (`uvx blender-mcp install-addon`).

---

### 3. Avvio del Server MCP in Blender (Addon GitHub)
Usiamo l'addon open-source di GitHub:
* **Blender MCP (mcp-for-blender)**: [github.com/ahujasid/mcp-for-blender](https://github.com/ahujasid/mcp-for-blender) (fork/upstream di [RFingAdam/mcp-blender](https://github.com/RFingAdam/mcp-blender)).
* **Blender Agent Studio (Playbook & Riferimenti)**: [github.com/ifBars/blender-agent-studio](https://github.com/ifBars/blender-agent-studio).

**Come aggiornare l'Addon all'ultima versione:**
Se devi aggiornare l'addon all'ultima versione rilasciata, apri PowerShell ed esegui:
```powershell
uvx --upgrade mcp-for-blender install-addon
```
*(Se preferisci il download manuale dello zip: [Releases GitHub](https://github.com/ahujasid/mcp-for-blender/releases))*.

**Passaggi per attivarlo e avviarlo in Blender:**
1. Apri **Blender** (es. Blender 5.1).
2. Se è la prima volta: vai nel menu in alto `Edit` -> `Preferences` -> scheda `Add-ons`.
3. Nella barra di ricerca in alto a destra scrivi `MCP` o `MCP for Blender` e **attiva la spunta** per abilitarlo (se l'hai appena aggiornato, disattiva e riattiva la spunta).
4. Torna nella vista 3D principale e premi il tasto **`N`** sulla tastiera (apre la barra laterale destra).
5. Clicca sulla linguetta laterale denominata **`MCP for Blender`**.
6. Clicca sul pulsante **`Start MCP Server`** (la porta predefinita è `9876`).
7. **Fatto**: lascia Blender aperto in background con il server attivo. L'agente modellerà, applicherà le scale del Geometra ed esporterà i file GLB direttamente qui dentro.

---

### 4. Avvio del Server MCP in Unity (Package GitHub CoplayDev)
Usiamo il package open-source di GitHub **`CoplayDev/unity-mcp`** (`https://github.com/CoplayDev/unity-mcp`), lo standard più potente e versatile per controllare la gerarchia, compilare script C#, leggere la console e pilotare la Play Mode.

**Passaggi per installarlo e avviarlo nel progetto:**
1. Apri il tuo progetto Unity (oppure chiedi all'agente di crearlo con `unity projects create`).
2. Nella barra dei menu in alto di Unity, vai su: **`Window` -> `Package Manager`**.
3. Clicca sull'icona **`+`** in alto a sinistra nella finestra del Package Manager e seleziona:
   👉 **`Add package from git URL...`**
4. Incolla questo indirizzo esatto:
   ```text
   https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity
   ```
   e premi il pulsante **`Add`**.
5. Unity scaricherà e compilerà il pacchetto.
6. Una volta terminato, nella barra dei menu in alto di Unity vedrai comparire la nuova voce **`MCP`** (o sotto `Window` -> `MCP`).
7. Clicca su **`MCP`** -> **`Start Server`** (oppure `Configure / Start Server`).
8. **Fatto**: lascia Unity aperto. L'agente si collegherà automaticamente in tempo reale alla scena attiva.

---

### 5. Controllo dello Stato (Doctor)
Per verificare che tutti i componenti e i socket rispondano correttamente, apri un terminale PowerShell ed esegui:
```powershell
cd "C:\Users\FRANCY\Desktop\GameDeveloperSkill\game-developer"
powershell ./scripts/doctor.ps1
```
Quando vedi i componenti principali con `[PASS]`, il sistema è operativo al 100%.

---

### 6. Avvio del Workflow dall'Agente
Apri il tuo coding agent preferito (Kilo, Claude Code, Codex o Antigravity) e digita il comando con la tua idea di gioco:
```
/game Voglio fare un dungeon crawler isometrico con trappole e guerriero con martello
```
*(Se il tuo client non usa comandi slash `/`, scrivi semplicemente: "Avvia la pipeline game-developer con questa idea: ...")*

---

### 7. L'Intervista Guidata (19 domande, a blocchi — fondamentali)
L'agente pone blocchi ampi (anche 5–10 domande). Una domanda è **quali tool usare per tutto il gioco** (stack raccomandato: ProBuilder + una famiglia kit + Poly Pizza per i buchi + UI DesignerSkill). Confermi o override, poi LOCK.

---

### 8. Livelli da blueprint + LookDev: niente cubi, niente prop sottoterra
- **Layer deterministico** (`Assets/_Game/Editor/GDS/`, installato dal worker *project* con `scripts/install-gds-editor.ps1`): l'agente scrive un **blueprint JSON** (`art/blueprints/house_a.json`: celle, piani, porte, finestre, tetto, prop interni, scatter esterno) e chiama `GDS.LevelBuilder.BuildFromFile(...)` via CoplayDev `execute_code`. Una casa da 40 moduli = **una chiamata**, allineata per bounds (nessun pivot da indovinare) con collider. Vedi [level-builder.md](game-developer/references/level-builder.md).
- **Stanze / torri / scale**: `GDS.PB.Room / Tower / Stairs / Arch` = ProBuilder vero da C#, con vani porta/finestra senza CSG. `manage_probuilder` solo per ritocchi. Vedi [probuilder-levels.md](game-developer/references/probuilder-levels.md).
- **Lint scena**: `GDS.SceneLint.RunJson(autoFix:true)` snappa a terra e aggiunge collider; `RunJson()` deve dare `issues: 0` (sepolti > 2 cm, flottanti > 5 cm, senza collider, materiali rosa). È il gate: lo screenshot non decide più. Vedi [scene-lint.md](game-developer/references/scene-lint.md).
- **LookDev**: `GDS.LookDev.Apply("stylized-day")` (o sunset / dungeon-torch / night-moon / pastel-bright / scifi-cold) = sole, ambient, fog, skybox o HDRI Poly Haven, Volume ACES + bloom + vignette + color, SSAO, qualità URP. Palette dal GDD con `ApplyPalette`. Toon/outline opzionali (pacchetti GitHub gratis). Vedi [lookdev.md](game-developer/references/lookdev.md).
- **Kit**: **una** famiglia per slice — Kenney / KayKit / Quaternius Standard / Synty POLYGON Starter (Asset Store gratis, se lo consenti in intervista). `fetch-cc0-kits.ps1` + `GDS.KitCatalog` misura ogni pezzo (`art/kit-catalog.json`).
- **Personaggi**: KayKit / Kenney Animated / Quaternius Universal Animation Library (CC0) → `GDS.Characters` (Humanoid, Animator, CharacterController). NavMesh con lo skill `initialize-ai-navigation`. Vedi [characters.md](game-developer/references/characters.md).
- **VFX**: `GDS.VFX.CreateAll()` (dust/hit/pickup/torch/smoke/sparkle) + `manage_vfx` + Cartoon FX Free. Vedi [vfx.md](game-developer/references/vfx.md).
- **Hero prop**: Blender MCP nativo — Poly Pizza → Poly Haven models → Sketchfab CC0 → **tier generativo scelto in intervista** (`none` | Modly locale ≥ 8 GB VRAM | Meshy / Tripo con key e budget crediti | Hyper3D). Solo prop unici, mai moduli. Vedi [gen3d.md](game-developer/references/gen3d.md). `uvx blender-mcp` stdio, **non** `http://localhost:9876/mcp`. Vietato creare mesh in Python.
- **Interfaccia Grafica**: L'agente crea i mock HTML/CSS con `DesignerSkill` (`real-world-design`, obbligatoria), te li mostra tramite screenshot Playwright e, appena ne approvi uno, `ui-transpiler.mjs` lo converte in **UXML/USS nativo per Unity UI Toolkit**.
- **Unity**: 6000.0 / 6000.3 LTS consigliate. Su 6000.5+ l'installer fissa ProBuilder ≥ 6.1.2 (il 6.0.x non compila lì).

---

### 9. Playtest e Collaudo Autonomo con TerminalMCP
- L'agente avvia la modalità **Play** su Unity.
- **TerminalMCP** prende il comando, simula la pressione reale dei tasti (WASD, Spazio, Click) per testare movimento e fisica.
- Controlla la console per intercettare ed eliminare eventuali errori C#.
- Cattura gli screenshot del gioco in esecuzione in `<progetto>/screenshots/` e ti consegna il report finale in `docs/playtest.md`.

---

### 10. Task Atomici & Memoria di Progetto (Anti-Pigrizia)
Per impedire al modello di essere frettoloso o "pigro":
- **`GAME_TASKS.md`:** Nessun macro-task (vietato *"fai modelli 3D"*). Ogni singolo oggetto (tavolo, sedia, anta porta, maniglia, barili), script, collider, coordinata di piazzamento nella scena e hook UI ha un proprio ID e riga di spunta con evidenza su disco.
- **`GAME_CONTEXT.md`:** Lo snapshot vivente del gioco che memorizza game loop, scopo, regole win/fail, controlli, registro script C# (chi possiede cosa e perché), mappa completa degli oggetti nella scena e locazione fisica dei file.

---

### 11. Sessioni Infinite e Cambio Chat con `/resumegame`
Se devi sviluppare un gioco complesso per ore:
1. L'agente salva continuamente i progressi su `GAME_TASKS.md` e `GAME_CONTEXT.md`.
2. Ogni 5–8 task o a cambio di fase, emette un banner di **[CHECKPOINT REGISTRATO]**.
3. Apri semplicemente una **nuova chat** a zero token e digita:
   ```
   /resumegame
   ```
4. L'agente legge i file di memoria, identifica il prossimo task non completato e riprende all'istante a piena lucidità e senza alcuna perdita di qualità.

