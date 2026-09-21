# Unity CLI — lifecycle only

Official binary `unity` (beta). **Use it for Hub jobs**, not for building the level.

Docs: https://docs.unity.com/en-us/unity-cli/use-unity-cli.md  
Skill extra (optional): `npx skills add Unity-Technologies/skills`

## Use CLI for

- `unity --version` / `unity doctor --format json`
- `unity auth login` / `status` / `license activate`
- `unity install lts --yes --accept-eula` (only if user wants the Editor downloaded)
- `unity editors --installed --format json`
- `unity templates list --editor lts --format json`
- `unity projects create` / `unity open <path>`
- `unity test <project> --mode EditMode --format json` if MCP `run_tests` is down
- `unity mcp configure` if the official MCP path is requested

Always `--format json` when parsing. Always `--non-interactive --yes` when not waiting for a human. Windows GUI agents: call `unity.exe` via full path if `unity` is missing from PATH (`unity env --format json`).

## Do not use CLI as the primary scene tool

`unity command eval` / Pipeline live Editor is a **fallback**. Prefer CoplayDev unity-mcp for:

- create GameObjects, components, prefabs
- `create_script` + compile wait + `read_console`
- `manage_camera screenshot include_image=true`
- `run_tests`

Why: MCP returns structured scene state and inline screenshots. CLI `eval` is opaque and easy to desync.

If MCP is missing: `unity pipeline install` then `unity status` — if `ready`, you may `unity command`. Still copy screenshots into `screenshots/`.

## Create project recipe

```
unity auth status --format json
unity license status --format json
unity editors --installed --format json
unity templates list --editor lts --format json
unity projects create "Name" --path "C:\Users\FRANCY\Desktop" --editor-version lts --template <urp-or-3d> --yes --non-interactive --format json
unity open "C:\Users\FRANCY\Desktop\Name"
```

`--path` is the **parent** folder. Name is the first positional.

## Targeting

Several Editors: `--project-path <game>`. Sandbox may hide instances — ask if Unity is actually open before assuming it is down.

## Safe Mode

Compile errors → Pipeline/MCP live tools fail. Fix C#, restart Editor. Do not edit `.unity` YAML.
