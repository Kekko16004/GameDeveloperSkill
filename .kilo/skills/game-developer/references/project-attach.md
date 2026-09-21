# Attach or create the game project

User preference: they create Unity (or Godot) and you attach. If there is no project after GDD lock, **you create it with Unity CLI**.

## Detect

Walk from cwd up looking for:

- Unity: `ProjectSettings/ProjectVersion.txt` and `Assets/`
- Godot: `project.godot`

If found: set `projectPath`, `phase: scaffold`, create folders below. Do not create a second project.

## Ask once if nothing found

Options: existing path | create with Unity CLI (recommended when engine=unity) | abort.

Godot v1: user must create the Godot project. You do not scaffold Godot from CLI.

## Create (Unity)

Read [unity-cli.md](unity-cli.md). Sequence:

```
unity --version
unity auth status --format json
unity license status --format json
unity editors --installed --format json
unity templates list --editor lts --format json
```

If signed out → tell the user to finish `unity auth login` in the browser, then retry. If no license → `unity license activate`. If no Editor → print `unity install lts --yes --accept-eula` (large download; only run if they asked).

Pick template: first id matching URP 3D from the list; else `com.unity.template.3d`.

```
unity projects create "<Name>" --path "<parent>" --editor-version lts --template <id> --yes --non-interactive --format json
unity open "<project>"
```

Wait until the Editor is up. Prefer CoplayDev MCP `editor/state` `ready_for_tools`. Fallback `unity status --format json`.

Then add CoplayDev package (Package Manager git URL from config `unity.coplayGitUrl`). Optional: `unity pipeline install` for CLI live commands.

## Scaffold inside the project

```
GDD.md
ASSET-LEDGER.md
screenshots/000-index.md
art/blender/
art/voxel/
art/cc0/
art/exports/
ui/mocks/
ui/unity/
docs/playtest.md
```

Unity also:

```
Assets/_Game/Art
Assets/_Game/Prefabs
Assets/_Game/Scenes
Assets/_Game/Scripts
Assets/_Game/Scripts/Tests
Assets/_Game/UI
Assets/_Game/Audio
```

Copy `GDD.md` here if it lived elsewhere. Set `projectPath` and `phase: greybox`.

Add a Unity `.gitignore` if git init is requested (`https://raw.githubusercontent.com/github/gitignore/main/Unity.gitignore`). Never commit `Library/`.
