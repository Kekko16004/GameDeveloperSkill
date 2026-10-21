# Installazione

```bat
install.bat            :: interattivo: host rilevati e moduli consigliati già selezionati
install.bat -Quiet     :: host rilevati + moduli consigliati, nessuna domanda
install.bat -All       :: tutto
install.bat -Hosts claude,kilo -SkipModules voxelMcp
install.bat -Copy      :: copia la skill in ogni host invece di collegarla (host che non seguono le junction)
```

## Cosa fa

1. **Rileva** (cerca, niente percorsi fissi): host installati (`.claude`, `.config/kilo`, `.codex`, `.gemini`, `.cursor`, ...), Unity CLI ed Editor, Unreal (Launcher + cartelle `UE_*`), NucleonEditor (PATH o Desktop/Documents/`C:\Dev`/`D:\Dev` fino a 4 livelli → `paths.nucleon`), Blender più recente, FabCLI, uvx, VoxelAI, TerminalMCP, le skill `real-world-design` e `unity-cli` ovunque siano (cartelle skill degli host, Desktop/Documents fino a 3 livelli).
2. **Installa una volta** in `%USERPROFILE%\.agents\skills\game-developer` e crea una **junction** da ogni host a quella cartella (niente admin, niente copie che divergono: un aggiornamento arriva ovunque).
3. **Config**: `config.json` = default + percorsi rilevati + valori che avevi già (i tuoi vincono sempre, anche da vecchie copie negli host).
4. Comandi `/game /gdd /playtest /resumegame` negli host che li supportano, MCP Blender / VoxelAI / TerminalMCP senza toccare gli altri server, skill ufficiali Unity (`npx skills add Unity-Technologies/skills`), addon Blender, `doctor`.

## Una volta a mano

- FabCLI (solo realistico): estrai lo zip delle [release](https://github.com/zirklerite/FabCLI/releases) in `%LOCALAPPDATA%\fabcli\` e aggiungi la cartella al PATH utente; l'installer lo rileva lì o sul PATH.
- Unity CLI (se manca): `$env:UNITY_CLI_CHANNEL='beta'; irm https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.ps1 | iex`, poi `unity auth login`.
- Blender (solo per edifici/hero prop): pannello N → MCP → Start MCP Server.
- Realistico: Unreal **5.8+** dal Launcher; in Claude Code `/plugin install unreal-engine-skills-for-claude-code@claude-plugins-official`; nel progetto abilita Unreal MCP + All Toolsets ([unreal-loop.md](game-developer/references/unreal-loop.md)).

## Nucleon (engine: nucleon)

- Una volta: `config.json` → `paths.nucleon` = la cartella di `NucleonEditor.exe` (con `Nucleon.exe` della stessa build accanto) se l'installer non l'ha trovata; Python 3.9+ sul PATH.
- Per lavorare con l'editor aperto: Editor Preferences > AI > **Enable Server** (porta 47420). `ncli.py` legge porta e token da `editor-settings.lua`, nessun token da copiare a mano.
- Senza editor aperto i worker usano `--stdio` (l'editor parte e si chiude per ogni comando).
- Opzionale, solo per sessioni interattive: `python game-developer\scripts\ncli.py --project <progetto> mcp-config` stampa i comandi `claude mcp add nucleon ...`. I worker non ne hanno bisogno.

## Per ogni progetto Unity

Lo fa il worker `project`:

```
powershell -File game-developer\scripts\install-gds-editor.ps1 -ProjectPath <progetto> [-WithToonShader] [-WithOutline]
```

Copia GDS Editor + Runtime, esempi `art/world/`, aggiunge ProBuilder / glTFast / Input System / AI Navigation con le versioni consigliate dall'Editor del progetto e installa `com.unity.pipeline` (`unity pipeline install`). Verifica: `unity command gds_ping`.

CoplayDev unity-mcp è opzionale (fallback): `https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity`.

## Controllo

`game-developer\scripts\doctor.ps1 [-ProjectPath <progetto>]` → righe `PASS | WARN | FAIL` con il fix.

## Vietato

- Sloyd; gen3d (Meshy / Tripo / Rodin / Modly) fuori dal tier e dal budget scelti nell'intervista
- Mischiare famiglie di asset nello stesso gioco (riga di `styles.md`)
- HDRI sui materiali dei prop (come skybox va bene)
- Piazzare muri / alberi uno a uno: si scrive la spec
- TerminalMCP `--http`
- Aprire Unity / Nucleon / Blender / Unreal / Godot prima del lock del GDD (l'engine lo sceglie l'utente alla domanda Q0)
