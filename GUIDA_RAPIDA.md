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

### 7. L'Intervista Guidata (A Blocchi Liberi ed Esaustivi)
L'agente pone blocchi ampi (anche 5–10 domande). Una domanda è **quali tool usare per tutto il gioco** (stack raccomandato: ProBuilder + una famiglia kit + Poly Pizza per i buchi + UI DesignerSkill). Confermi o override, poi LOCK.

---

### 8. Livelli (ProBuilder) + Kit CC0, non Blender-from-code
- **Stanze / muri / scale**: Unity ProBuilder via `manage_probuilder`, griglia Geometra (pareti 4×3m, pavimenti 4×4m, porte 1×2.2m). Zero export.
- **Props / moduli visibili**: pack **Kenney** o **KayKit** CC0 (`scripts/fetch-cc0-kits.ps1`). Una famiglia per slice. Screenshot `030-import-*.png`.
- **Blender MCP**: `uvx blender-mcp` (stdio) parla col socket TCP 9876 dell’addon. **Non** usare `http://localhost:9876/mcp`. Import Poly Pizza (`search` + `download` + `export_scene`). Vietato creare mesh in Python.
- **Sloyd / Meshy / Tripo**: vietati di default (Guest Sloyd = 1 modello/giorno, licenza personale — inutile per un gioco intero).
- **Interfaccia Grafica**: L'agente crea i mock HTML/CSS con `DesignerSkill`, te li mostra tramite screenshot Playwright e, appena ne approvi uno, lo script `ui-transpiler.mjs` lo converte in **UXML/USS nativo per Unity UI Toolkit**.

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

