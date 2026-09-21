# Screenshots

Every visual judgment uses a **file on disk** in `<game>/screenshots/`. Then Read that file. Chat images without a copy on disk do not count.

## Names

`NNN-phase-short-slug.png` zero-padded. Examples:

- `010-greybox-play.png`
- `020-blender-prop-crate.png`
- `030-unity-import-crate.png`
- `040-ui-hud-mock.png`
- `050-playtest-move.png`

Keep `000-index.md`:

```
| file | phase | expected | pass |
| 010-greybox-play.png | greybox | player on plane | yes |
```

## Sources

| Phase | Capture | Then |
|---|---|---|
| UI mock | Playwright 1440×900 | copy into screenshots **and** `ui/mocks/` |
| Blender | MCP viewport / orthographic, **no extra lights** | save here |
| Voxel | `voxel_preview` plus PNG export if available | save here |
| Unity | `manage_camera(action="screenshot", include_image=true)` | **copy** out of `Assets/` into `screenshots/` |
| Godot | godot-ai screenshot | save here |
| Fallback | TerminalMCP `screen shot` | only if editor MCP is down |

Unity often writes under `Assets/`. That is not the archive. Copy/rename into `screenshots/`.
