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
| design-skill | `real-world-design` skill folder |
| gdd | if projectPath set: GDD status |
| screenshots-dir | create if missing when projectPath set |

Godot FAIL is OK when engine is Unity.

Installer writes `last-doctor.txt` next to the installed skill.
