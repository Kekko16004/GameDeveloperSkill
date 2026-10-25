# Installazione

Serve **Node.js 18+**. Se manca, `install.bat` propone di installarlo con winget. git è consigliato: senza git le dipendenze arrivano come zip da GitHub.

```bat
install.bat                      :: interattivo: host e moduli rilevati già selezionati (frecce, spazio, invio)
install.bat --yes                :: nessuna domanda: host rilevati + moduli consigliati (alias: -Quiet)
install.bat --hosts claude,codex --skip blenderMcp
install.bat --dry-run            :: mostra cosa farebbe, non scrive niente
install.bat --dev                :: la copia canonica diventa un link a questo repo (modifiche live, niente reinstallazione)
update.bat                       :: git pull + dipendenze all'ultima versione + reinstalla con le scelte salvate
node installer\install.mjs doctor [--fix]   :: controlla copia canonica, link, duplicati, comandi, MCP
node installer\install.mjs uninstall        :: toglie solo quello che l'installer ha creato
```

Su macOS / Linux gli stessi comandi sono `./install.sh` e `./update.sh`. Opzioni comuni: `--lang it|en`, `--json`, `--verbose`, `--no-color`.

## Come funziona

1. **Una copia sola.** La skill va in `~/.agents/skills/game-developer`. È la cartella condivisa che leggono già Codex, Gemini CLI, Cursor, OpenCode, Kilo, Windsurf, Copilot e Roo. Hanno un link (junction, niente admin) solo gli host che non la leggono:
   - Claude Code → `~/.claude/skills`
   - Antigravity → `~/.gemini/config/skills`
   - Cline → `~/.cline/skills`
2. **Niente duplicati.** Le copie vecchie della skill nelle cartelle degli host (`~/.codex/skills`, `~/.cursor/skills`, `~/.config/kilo/skills`, …) vengono **spostate** in `~/.agents/skillkit/backup/<data>/`, non cancellate. Lo stesso vale per i nomi vecchi come `real-world-design`. Prima comparivano due volte, oppure restavano indietro di versione.
3. **Dipendenze dal loro repo, sempre all'ultima versione.**

   | Modulo | Fonte | Cosa fa l'installer |
   |---|---|---|
   | designer | [Kekko16004/DesignerSkill](https://github.com/Kekko16004/DesignerSkill) | Usa l'installazione che c'è già, altrimenti clona il repo e lancia il suo installer. Viene aggiornata anche da `update.bat`. |
   | game-launch-strategist (opzionale) | [Kekko16004/GameLaunchAnalyzer](https://github.com/Kekko16004/GameLaunchAnalyzer) | Proposta nella lista dei moduli: già spuntata se è installata, così resta aggiornata insieme a questa. Dopo la slice le due skill si passano il lavoro ([launch-link.md](game-developer/references/launch-link.md)). Il suo installer propone game-developer allo stesso modo. |
   | Skill ufficiali Unity | [Unity-Technologies/skills](https://github.com/Unity-Technologies/skills) | Copia tutte le skill (unity-cli, ui-uitk, urp, …) in `~/.agents/skills`. |
   | TerminalMCP | [Fonlogen/TerminalMCP](https://github.com/Fonlogen/TerminalMCP) | Clona in `~/.agents/skillkit/repos`, installa la skill `terminalmcp` e registra l'MCP `terminal` (`node …/bin/terminalmcp.js --tools all`). |
   | Blender MCP | `uvx mcp-for-blender` | Registra l'MCP `blender` e installa l'addon. |
   | VoxelAI MCP | [Kekko16004/VoxelAIArtist](https://github.com/Kekko16004/VoxelAIArtist) | Usa il checkout locale se c'è, altrimenti clona il repo. |

   I cloni gestiti stanno in `~/.agents/skillkit/repos/` e vengono aggiornati con `fetch` + `reset` al branch principale. Se trova modifiche locali le mette prima in uno stash, così non si perdono.
4. **MCP in ogni host, nel suo formato.**
   - Claude Code: `claude mcp add-json -s user`.
   - Codex: `config.toml`.
   - Kilo / OpenCode: `mcp`.
   - Cursor, Gemini, Antigravity, Windsurf, Copilot: `mcpServers`.

   Un server che hai configurato a mano non viene mai sovrascritto. Vengono aggiornate solo le voci create dall'installer o riconosciute come sue (per esempio un vecchio `terminal` che puntava a un'altra cartella di TerminalMCP). Prima di modificare un file di configurazione ne salva una copia `.skillkit-bak`.
5. **Comandi** `/game /gdd /playtest /resumegame`:
   - Claude Code: `~/.claude/commands`.
   - Kilo: solo `~/.config/kilo/commands`. Le copie in `command/`, `~/.kilo/…` venivano caricate più volte e vengono tolte.
   - OpenCode: `~/.config/opencode/commands`.
   - Gemini CLI: `~/.gemini/commands/*.toml`.
   - I vecchi prompt di Codex (deprecati) vengono tolti.
6. **`config.json`.** Parte dai default, aggiunge i percorsi rilevati (Unity CLI ed Editor, Unreal, Nucleon, Blender, FabCLI, uv, Python, VoxelAI) e tiene **sempre** i valori che avevi già impostato. Alla fine lancia `scripts/doctor.ps1`.
7. **Ricevuta.** `~/.agents/skillkit/game-developer.json` registra host, moduli, link, comandi e MCP creati. Serve a `update`, `doctor` e `uninstall`. Gli host e i moduli nuovi rilevati dopo l'ultima installazione vengono aggiunti da soli.

Dall'interno della skill installata, l'agente aggiorna con `node scripts/update.mjs`: trova il repo dalla ricevuta e, se non c'è più, lo riclona.

## Una volta a mano

- Unity CLI (se manca): `$env:UNITY_CLI_CHANNEL='beta'; irm https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.ps1 | iex`, poi `unity auth login`. L'installer ti avvisa se la sessione è scaduta.
- FabCLI (solo stile realistico): estrai lo zip delle [release](https://github.com/zirklerite/FabCLI/releases) in `%LOCALAPPDATA%\fabcli\`. L'installer lo trova lì o sul PATH.
- Blender (solo edifici e hero prop): pannello N → MCP → Start MCP Server.
- Realistico: Unreal **5.8+** dal Launcher. In Claude Code: `/plugin install unreal-engine-skills-for-claude-code@claude-plugins-official`. Nel progetto abilita Unreal MCP + All Toolsets ([unreal-loop.md](game-developer/references/unreal-loop.md)).

## Nucleon (engine: nucleon)

- Una volta: se l'installer non l'ha trovata, imposta in `config.json` → `paths.nucleon` la cartella di `NucleonEditor.exe` (con accanto `Nucleon.exe` della stessa build). Serve Python 3.9+.
- Con l'editor aperto: Editor Preferences > AI > **Enable Server** (porta 47420). `ncli.py` legge porta e token da `editor-settings.lua`.
- Senza editor aperto i worker usano `--stdio`.

## Per ogni progetto Unity

Lo fa il worker `project`:

```
powershell -File game-developer\scripts\install-gds-editor.ps1 -ProjectPath <progetto> [-WithToonShader] [-WithOutline]
```

Verifica: `unity command gds_ping`. CoplayDev unity-mcp è opzionale (fallback): `https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity`.

## Vietato

- Sloyd; gen3d (Meshy / Tripo / Rodin / Modly) fuori dal tier e dal budget scelti nell'intervista
- Mischiare famiglie di asset nello stesso gioco (riga di `styles.md`)
- HDRI sui materiali dei prop (come skybox va bene)
- Piazzare muri / alberi uno a uno: si scrive la spec
- TerminalMCP `--http`
- Aprire Unity / Nucleon / Blender / Unreal / Godot prima del lock del GDD (l'engine lo sceglie l'utente alla domanda Q0)
