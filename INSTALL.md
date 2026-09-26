# Installazione

```bat
install.bat            :: interattivo: host rilevati e moduli consigliati già selezionati
install.bat -Quiet     :: host rilevati + moduli consigliati, nessuna domanda
install.bat -All       :: tutto
install.bat -Hosts claude,kilo -SkipModules voxelMcp
install.bat -Copy      :: copia la skill in ogni host invece di collegarla (host che non seguono le junction)
```

## Cosa fa

1. **Rileva** (cerca, niente percorsi fissi): host installati (`.claude`, `.config/kilo`, `.codex`, `.gemini`, `.cursor`, ...), Unity CLI ed Editor, Unreal (Launcher + cartelle `UE_*`), Blender più recente, FabCLI, uvx, VoxelAI, TerminalMCP, le skill `real-world-design` e `unity-cli` ovunque siano (cartelle skill degli host, Desktop/Documents fino a 3 livelli).
2. **Installa una volta** in `%USERPROFILE%\.agents\skills\game-developer` e crea una **junction** da ogni host a quella cartella (niente admin, niente copie che divergono: un aggiornamento arriva ovunque).
3. **Config**: `config.json` = default + percorsi rilevati + valori che avevi già (i tuoi vincono sempre, anche da vecchie copie negli host).
4. Comandi `/game /gdd /playtest /resumegame` negli host che li supportano, MCP Blender / VoxelAI / TerminalMCP senza toccare gli altri server, skill ufficiali Unity (`npx skills add Unity-Technologies/skills`), addon Blender, `doctor`.

## Una volta a mano

- Unity CLI (se manca): `$env:UNITY_CLI_CHANNEL='beta'; irm https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.ps1 | iex`, poi `unity auth login`.
- Blender (solo per edifici/hero prop): pannello N → MCP → Start MCP Server.
- Realistico: Unreal **5.8+** dal Launcher; in Claude Code `/plugin install unreal-engine-skills-for-claude-code@claude-plugins-official`; nel progetto abilita Unreal MCP + All Toolsets ([unreal-loop.md](game-developer/references/unreal-loop.md)).

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
- Aprire Unity / Blender / Unreal prima del lock del GDD
