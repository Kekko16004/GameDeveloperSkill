# Installazione Game Developer Skill

Wizard come DesignerSkill: copia la skill, inietta MCP, verifica i tool, stampa cosa manca.

```
game-developer\install.bat
```

Non-interattivo:

```
install.bat -Quiet
install.bat -All
install.bat -Hosts kilo,claude -SkipModules godotMcp,terminalMcp
```

Poi chiudi e riapri i client.

## Cosa viene scritto

| Host | Skill |
|---|---|
| Kilo | `%USERPROFILE%\.config\kilo\skills\game-developer\` |
| Claude Code | `%USERPROFILE%\.claude\skills\game-developer\` |
| Codex | `%USERPROFILE%\.codex\skills\` e `\.agents\skills\` |
| Antigravity | `%USERPROFILE%\.gemini\antigravity\skills\` |
| Cursor / OpenCode / Copilot / Windsurf | solo se li selezioni |

Comandi Kilo: `%USERPROFILE%\.config\kilo\command\game.md` (+ `gdd.md`, `playtest.md`).

## MCP (nessun segreto)

L'installer aggiunge, senza toccare Playwright / 21st / Originkit:

- **blender** — `cmd /c uvx blender-mcp` + `BLENDER_PORT=9876`. Non `serverUrl http://localhost:9876/mcp` (quel porto è TCP JSON, non HTTP MCP)
- **voxelai** — `python "<VoxelAIArtist>\mcp_server"` (niente `--workdir` globale)
- **terminal** — TerminalMCP con `--tools all`: shell, jobs, browser, screen, input, il pc intero. Solo stdio locale, mai `--http`

Se TerminalMCP non è sul disco, l'installer lo clona da https://github.com/Fonlogen/TerminalMCP in `Desktop\Dev Things\TerminalMCP`.

Unity MCP non sta nel json globale: si configura dal package CoplayDev nel progetto (`Window → MCP for Unity → Configure All Detected Clients`).

## Tool che l'installer monta o indica

1. Node ≥ 18, Python ≥ 3.10
2. **uv** — https://docs.astral.sh/uv/getting-started/installation/  
   Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
3. **Unity CLI** (beta) — create/open/auth, non scarica l'Editor da solo  
   `winget install Unity.CLI`  
   oppure `$env:UNITY_CLI_CHANNEL='beta'; irm https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.ps1 | iex`  
   Poi: `unity auth login` → `unity license activate` → se manca l'Editor `unity install lts --yes --accept-eula`
4. **Blender** 4.2+ sul PATH o in Program Files. Addon: `uvx blender-mcp install-addon`. In Blender: Add-ons → MCP for Blender → viewport **N** → Start MCP Server
5. **VoxelAI** default `C:\Users\FRANCY\Desktop\Dev Things\VoxelAIArtist`
6. **real-world-design** già installata (DesignerSkill). Se manca, installala prima
7. Opzionale: `npx skills add Unity-Technologies/skills -g -y` (unity-cli + ui-uitk)

L'installer **non** scarica Unity Editor (GB) e **non** avvia Blender. `scripts\doctor.ps1` dice cosa manca.

## Dopo il primo progetto Unity

Package Manager → Add from git URL:

```
https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity
```

`Window → MCP for Unity → Configure All Detected Clients`. Attendi compile + `ready_for_tools`.

## Vietato

- Meshy / Tripo / Rodin / Sloyd Guest come path primario (Sloyd Plus è a pagamento; Guest = 1 gen/giorno + licenza personale)
- Mix Kenney + KayKit nello stesso slice
- HDRI / luci studio su asset di gioco
- TerminalMCP `--http` su `0.0.0.0`
- Aprire Blender/Voxel/scena prima del GDD lock
