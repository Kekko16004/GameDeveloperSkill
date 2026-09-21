# Blender MCP — live only, no crash, no dump

## Vietato (crash o pigrizia)

```
bpy.ops.wm.read_homefile()
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.wm.read_factory_settings()
blender --background
blender -b
un unico execute_blender_code che fa cubo+export
```

`read_homefile` UCCIDE il thread socket (porta 9876). Se un worker lo chiama, il parent marca FAIL e retry.

## Pulizia scena (unica ammessa)

```python
import bpy
if bpy.context.object and bpy.context.object.mode != "OBJECT":
    bpy.ops.object.mode_set(mode="OBJECT")
for obj in list(bpy.data.objects):
    if obj.type in ("MESH", "CURVE", "EMPTY", "LIGHT", "CAMERA"):
        if obj.name in ("Camera", "Light", "Cube") or obj.type == "MESH":
            bpy.data.objects.remove(obj, do_unlink=True)
for mesh in list(bpy.data.meshes):
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
for mat in list(bpy.data.materials):
    if mat.users == 0:
        bpy.data.materials.remove(mat)
```

Non cancellare l’addon. Non toccare world in modo che spegna il viewport.

## Avvio (agente, non utente)

1. `blender_get_addon_status`. Se down:
2. TerminalMCP `shell_exec` avvia `blender.exe` (path da doctor). Attendi 8s.
3. TCP 9876. Se chiuso: **un** messaggio utente, poi STOP la macrotask (non modellare in Unity):

```
RUN: In Blender premi N → MCP for Blender → Start MCP Server
Poi in chat nuova: /resumegame
```

Niente “salto Blender, uso cubi”.

## Modellazione: 5 CHIAMATE MCP minime (non 1 script)

Ogni passo = `execute_blender_code` (o tool mesh) **poi** `blender_get_viewport_screenshot` salvato su disco.

| step | file PNG | contenuto |
|---|---|---|
| 1 blockout | `screenshots/blender-$ID-1-blockout.png` | volumi Geometra, Y=0 |
| 2 layer+bevel | `screenshots/blender-$ID-2-bevel.png` | pezzi separati + bevel 1 seg |
| 3 ferramenta | `screenshots/blender-$ID-3-hardware.png` | chiodi/staffe |
| 4 materiali | `screenshots/blender-$ID-4-mats.png` | 3 PBR roughness/metal |
| 5 export | `screenshots/blender-$ID.png` (finale) | GLB scritto |

Meno di 5 PNG = FAIL. Un solo PNG finale = FAIL (dump). Parent **Read** almeno lo step 2 e il finale. Cubo / default cube / scena vuota = FAIL retry.

Export: `art/exports/$ID.glb` ≥ 15KB. `get_scene_info` dopo export: mesh count ≥ 3 oggetti o ≥ 80 vertici.

Look shader by **type** (`BSDF_PRINCIPLED`), mai `nodes["Principled BSDF"]`.
