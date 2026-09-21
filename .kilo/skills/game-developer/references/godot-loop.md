# Godot loop (optional)

v1: user creates the Godot 4.7+ project. You attach when `project.godot` exists.

MCP: [hi-godot/godot-ai](https://github.com/hi-godot/godot-ai) — plugin `addons/godot_ai`, client `godot-ai attach`. Installer module is **off** by default.

## Same gates as Unity

Greybox `CharacterBody3D` + `move_and_slide`, camera from GDD, tests (GUT or godot-ai `run_tests`) per verb, screenshots in `screenshots/`.

Import `art/exports/*.glb` under `res://_game/art/`.

UI: after real-world-design mock, rebuild as `Control` + Theme from the same tokens. No WebView.

If Godot MCP is missing: edit scenes/scripts on disk only when the editor is **closed**, or tell the user to enable the plugin. Prefer live editor tools when connected.
