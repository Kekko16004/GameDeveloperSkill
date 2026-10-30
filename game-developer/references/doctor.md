# Doctor

Run `scripts/doctor.ps1` from the skill folder (or pass `-ProjectPath`). Prints `PASS|FAIL|WARN | id | fix`. Exit 0 always unless the script itself crashed — the report is the result.

| id | need |
|---|---|
| node | Node ≥ 18 |
| python | Python ≥ 3.10 |
| uvx | uv / uvx on PATH or `%USERPROFILE%\.local\bin\uvx.exe` |
| unity-cli | `unity --version` |
| unity-editor | `unity editors --installed` has at least one 6000.x if engine=unity |
| unity-auth | `unity auth status` (WARN if logged out) |
| blender-exe | blender.exe |
| blender-socket | TCP 9876 (WARN if Blender closed) |
| voxelai | folder with `mcp_server` |
| playwright | skip if kilo already has MCP playwright |
| design-skill | `designer` skill folder |
| hardware | `scripts/hwdetect.py` detects GPU + VRAM once (nvidia-smi, else the OS query) and caches it in `~/.game-developer/hardware.json`; INFO only, never a question to the user ([styles.md](styles.md) "Hardware gate") |
| gdd | if projectPath set: GDD status |
| screenshots-dir | create if missing when projectPath set |

Godot FAIL is OK when engine is Unity.

The installer runs this script at the end of every install/update and shows the PASS/WARN/FAIL counts. Install-level checks (canonical copy, host links, duplicate copies, commands, MCP entries) are a separate command: `node <repo>/installer/install.mjs doctor [--fix]`.
