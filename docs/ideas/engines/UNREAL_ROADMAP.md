# Unreal Engine 5 Support (Roadmap)

Supporto completo per Unreal Engine 5.3+ con pipeline equivalente a Unity/Godot.

---

## ✅ Status: MCP Wrapper Approach (Recommended)

**Current:** MCP wrapper custom che wrappa Python API  
**Benefit:** Consistency con Unity/Godot MCP pipeline  
**Fallback:** Python API native (90% già pronto)  
**Future:** Migrazione a MCP nativo quando disponibile  

**Vedi:** `UNREAL_MCP_APPROACH.md` per dettagli completi

---

## 🎯 Planned Features

✅ **Blueprint Visual Scripting:** Generation automatica da blueprint JSON  
✅ **Nanite/Lumen:** Auto-setup per high-fidelity graphics  
✅ **Level Streaming:** World Partition per large worlds  
✅ **Asset Import:** FBX/GLB con Datasmith  
✅ **Material System:** Physically Based Rendering completo  
✅ **Landscape:** Terrain generation con World Machine integration  
🚧 **MCP Server:** Unreal Editor MCP in sviluppo  
🚧 **Playtest:** Automated testing via Python API  

---

## 🔧 Setup (Preview)

### 1. Install Unreal Engine

```powershell
# Via Epic Games Launcher
# https://www.unrealengine.com/download

# Oppure via scoop (community version)
scoop bucket add games
scoop install unreal-engine
```

**Config:**
```json
// game-developer/config.json
{
  "paths": {
    "unreal": "C:\\Program Files\\Epic Games\\UE_5.4",
    "unrealEditor": "C:\\Program Files\\Epic Games\\UE_5.4\\Engine\\Binaries\\Win64\\UnrealEditor.exe"
  },
  "engines": {
    "unrealEnabled": true,
    "unrealVersion": "5.4"
  }
}
```

### 2. Unreal Python API (Built-in - NO MCP NEEDED)

Unreal Engine ha **Python scripting nativo** molto più stabile di qualsiasi MCP:

**Enable Python:**
```
1. Edit -> Plugins -> "Python Editor Script Plugin" (Enable)
2. Restart Editor
3. Python console disponibile in: Window -> Developer Tools -> Output Log (Python tab)
```

**Python Scripts Path:**
```
<Project>/Content/Python/
```

**Vantaggi vs MCP:**
- ✅ Nativo in Unreal (zero dipendenze esterne)
- ✅ Accesso completo a tutte le API Unreal
- ✅ Esecuzione sincrona e affidabile
- ✅ Debug diretto nell'Editor
- ✅ Documentazione ufficiale Epic Games

---

## 📐 Architecture Mapping

| Unity | Unreal | Notes |
|-------|--------|-------|
| `GameObject` | `Actor` | Base scene object |
| `Transform` | `Transform` | Position/rotation/scale |
| `MeshRenderer` | `StaticMeshComponent` | Render mesh |
| `Collider` | `CollisionComponent` | Physics collision |
| `Rigidbody` | `PhysicsBody` | Physics simulation |
| `CharacterController` | `CharacterMovementComponent` | Player movement |
| `Camera` | `CameraComponent` | View camera |
| `Light` | `LightComponent` | Lighting |
| `Scene` | `Level` (.umap) | Scene/level file |
| C# Script | Blueprint / C++ | Logic |
| Prefab | Blueprint Class | Reusable instance |
| Material | `Material` | PBR material |
| URP | Nanite/Lumen | Render pipeline |
| ProBuilder | Geometry Scripting | Procedural geometry |

---

## 🏗️ Level Builder Unreal

### Blueprint JSON → Unreal Level

Stesso blueprint JSON, output Unreal level:

```python
# Content/Python/level_builder.py
import unreal

CELL_SIZE = 200.0  # Unreal units (cm)

def build_from_blueprint(blueprint_path):
    # Load blueprint data
    with open(blueprint_path) as f:
        data = json.load(f)
    
    # Get current level
    level = unreal.EditorLevelLibrary.get_editor_world()
    
    # Create parent actor
    root_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.Actor,
        unreal.Vector(0, 0, 0)
    )
    root_actor.set_actor_label(data['name'])
    
    # Build cells
    for cell in data['cells']:
        mesh_actor = create_cell(cell['type'])
        location = unreal.Vector(
            cell['x'] * CELL_SIZE,
            cell['y'] * CELL_SIZE,
            0
        )
        mesh_actor.set_actor_location(location, False, False)
        mesh_actor.attach_to_actor(root_actor, "", unreal.AttachmentRule.KEEP_WORLD)
    
    # Place props
    for prop in data['props']:
        prop_asset = unreal.EditorAssetLibrary.load_asset(
            f"/Game/_Game/Art/Props/{prop['kit']}"
        )
        instance = unreal.EditorLevelLibrary.spawn_actor_from_object(
            prop_asset,
            unreal.Vector(prop['x'] * 100, prop['z'] * 100, prop['y'] * 100)
        )
        instance.set_actor_rotation(unreal.Rotator(0, prop.get('ry', 0), 0))
        instance.attach_to_actor(root_actor, "", unreal.AttachmentRule.KEEP_WORLD)
    
    return root_actor

def create_cell(cell_type):
    """Create geometry for floor/wall cell"""
    if cell_type == "floor":
        size = unreal.Vector(CELL_SIZE, CELL_SIZE, 20)
        location = unreal.Vector(0, 0, -10)
    elif cell_type == "wall_n":
        size = unreal.Vector(CELL_SIZE, 20, 300)
        location = unreal.Vector(0, -CELL_SIZE/2, 150)
    
    # Use Geometry Script to create procedural mesh
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.StaticMeshActor,
        location
    )
    
    # Create box mesh
    mesh = create_box_mesh(size)
    actor.static_mesh_component.set_static_mesh(mesh)
    
    # Add collision
    actor.static_mesh_component.set_collision_enabled(
        unreal.CollisionEnabled.QUERY_AND_PHYSICS
    )
    
    return actor

def create_box_mesh(size):
    """Create procedural box mesh using Geometry Script"""
    # This is simplified - real implementation uses Geometry Script plugin
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    mesh = asset_tools.create_asset(
        "ProceduralBox",
        "/Game/_Game/Generated/Meshes",
        unreal.StaticMesh,
        None
    )
    # ... geometry generation code
    return mesh
```

---

## 🎨 Asset Import Pipeline

### FBX/GLB Import

```python
# Content/Python/asset_importer.py
import unreal

def import_assets(source_dir, dest_path="/Game/_Game/Art"):
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    
    # Import options
    import_task = unreal.AssetImportTask()
    import_task.automated = True
    import_task.replace_existing = True
    import_task.save = True
    
    # FBX import options
    fbx_options = unreal.FbxImportUI()
    fbx_options.import_mesh = True
    fbx_options.import_materials = True
    fbx_options.import_textures = True
    fbx_options.static_mesh_import_data.combine_meshes = False
    fbx_options.static_mesh_import_data.auto_generate_collision = True
    fbx_options.static_mesh_import_data.generate_lightmap_u_vs = True
    
    import_task.options = fbx_options
    
    # Import all FBX files
    for file in os.listdir(source_dir):
        if file.endswith(('.fbx', '.glb')):
            import_task.filename = os.path.join(source_dir, file)
            import_task.destination_path = dest_path
            asset_tools.import_asset_tasks([import_task])
            
            unreal.log(f"Imported: {file}")
```

### Auto Nanite Conversion

```python
def enable_nanite_for_assets(asset_path="/Game/_Game/Art"):
    """Enable Nanite for all static meshes"""
    asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
    assets = asset_registry.get_assets_by_path(asset_path, recursive=True)
    
    for asset_data in assets:
        if asset_data.asset_class == "StaticMesh":
            mesh = unreal.EditorAssetLibrary.load_asset(asset_data.object_path)
            
            # Check poly count
            if mesh.get_num_triangles(0) > 5000:  # Only for high-poly
                # Enable Nanite
                mesh.set_editor_property("nanite_settings.enabled", True)
                unreal.EditorAssetLibrary.save_asset(asset_data.object_path)
                unreal.log(f"Nanite enabled: {asset_data.asset_name}")
```

---

## 🎮 Blueprint Generation

### Visual Script from Logic

```python
def create_player_controller_blueprint():
    """Generate Blueprint for player controller"""
    
    # Create Blueprint asset
    factory = unreal.BlueprintFactory()
    factory.parent_class = unreal.Character
    
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    blueprint = asset_tools.create_asset(
        "BP_PlayerCharacter",
        "/Game/_Game/Blueprints",
        unreal.Blueprint,
        factory
    )
    
    # Get Blueprint graph
    graph = blueprint.ubergraph_pages[0]
    
    # Add Input Action for Movement
    # This is simplified - real implementation uses Blueprint API
    input_node = add_node(graph, "InputAction MoveForward")
    move_node = add_node(graph, "Add Movement Input")
    
    connect_nodes(input_node, "Pressed", move_node, "Execute")
    
    # Compile Blueprint
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    
    return blueprint
```

---

## 🌍 Landscape Generation

### Heightmap Import

```python
def create_landscape_from_heightmap(heightmap_path, size=1024):
    """Import heightmap as Unreal Landscape"""
    
    # Load heightmap texture
    import_task = unreal.AssetImportTask()
    import_task.filename = heightmap_path
    import_task.destination_path = "/Game/_Game/Terrain"
    import_task.automated = True
    
    # Import as texture
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks([import_task])
    
    # Create Landscape
    landscape_info = unreal.LandscapeImportDescriptor()
    landscape_info.heightmap_file = heightmap_path
    landscape_info.scale = unreal.Vector(100, 100, 100)
    landscape_info.material = unreal.EditorAssetLibrary.load_asset(
        "/Game/_Game/Materials/M_Landscape"
    )
    
    landscape = unreal.EditorLevelLibrary.create_landscape_proxy(
        unreal.EditorLevelLibrary.get_editor_world(),
        landscape_info
    )
    
    return landscape
```

---

## 🎨 Material System

### PBR Material Creation

```python
def create_pbr_material(name, textures):
    """Create PBR material from texture maps"""
    
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    factory = unreal.MaterialFactoryNew()
    
    material = asset_tools.create_asset(
        name,
        "/Game/_Game/Materials",
        unreal.Material,
        factory
    )
    
    # Add texture samples
    if 'albedo' in textures:
        albedo_node = add_texture_sample(material, textures['albedo'])
        connect_to_material(albedo_node, "RGB", material, "Base Color")
    
    if 'normal' in textures:
        normal_node = add_texture_sample(material, textures['normal'])
        connect_to_material(normal_node, "RGB", material, "Normal")
    
    if 'roughness' in textures:
        roughness_node = add_texture_sample(material, textures['roughness'])
        connect_to_material(roughness_node, "R", material, "Roughness")
    
    if 'metallic' in textures:
        metallic_node = add_texture_sample(material, textures['metallic'])
        connect_to_material(metallic_node, "R", material, "Metallic")
    
    # Compile material
    unreal.MaterialEditingLibrary.recompile_material(material)
    
    return material
```

---

## 💡 Lumen Global Illumination

### Auto-Setup

```python
def setup_lumen_lighting():
    """Configure Lumen for realistic lighting"""
    
    # Get world settings
    world = unreal.EditorLevelLibrary.get_editor_world()
    settings = world.get_world_settings()
    
    # Enable Lumen
    unreal.SystemLibrary.execute_console_command(
        world,
        "r.DynamicGlobalIlluminationMethod 1"  # 1 = Lumen
    )
    unreal.SystemLibrary.execute_console_command(
        world,
        "r.ReflectionMethod 1"  # 1 = Lumen Reflections
    )
    
    # Lumen quality settings
    unreal.SystemLibrary.execute_console_command(world, "r.Lumen.TraceMeshSDFs 1")
    unreal.SystemLibrary.execute_console_command(world, "r.LumenScene.SurfaceCache.MeshCardsMergeInstancesMaxCount 8192")
    
    # Add post-process volume
    pp_volume = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.PostProcessVolume,
        unreal.Vector(0, 0, 0)
    )
    pp_volume.unbound = True
    
    # Configure Lumen in post-process
    pp_volume.settings.lumen_scene_lighting_quality = 2.0  # Higher = better quality
    pp_volume.settings.lumen_scene_detail = 2.0
    pp_volume.settings.lumen_final_gather_quality = 2.0
    
    unreal.log("Lumen configured for high-quality GI")
```

---

## 🎮 Playtest Automation

### Python-based Testing

```python
# Content/Python/autotest.py
import unreal
import time

class AutoTester:
    def __init__(self):
        self.test_sequence = []
        self.screenshots_dir = "C:/Projects/MyGame/Screenshots"
        
    def load_test_sequence(self, json_path):
        with open(json_path) as f:
            self.test_sequence = json.load(f)
    
    def run_tests(self):
        for step in self.test_sequence:
            self.execute_step(step)
            time.sleep(step.get('delay', 0))
    
    def execute_step(self, step):
        if step['type'] == 'input':
            self.simulate_input(step['key'], step['pressed'])
        elif step['type'] == 'screenshot':
            self.take_screenshot(step['filename'])
        elif step['type'] == 'check':
            self.verify_condition(step['condition'])
    
    def simulate_input(self, key, pressed):
        # Use Unreal Input system
        player = unreal.GameplayStatics.get_player_controller(
            unreal.EditorLevelLibrary.get_editor_world(),
            0
        )
        # Input simulation via Python
        # Note: Requires custom C++ plugin for full input injection
        pass
    
    def take_screenshot(self, filename):
        path = f"{self.screenshots_dir}/{filename}"
        unreal.AutomationLibrary.take_high_res_screenshot(
            1920, 1080, path
        )
        unreal.log(f"Screenshot saved: {path}")

# Run tests
tester = AutoTester()
tester.load_test_sequence("Content/Tests/playtest_sequence.json")
tester.run_tests()
```

---

## 🚀 Pipeline Workflow

### 1. Project Creation

```python
# Create new UE5 project via Python
import subprocess

subprocess.run([
    "C:/Program Files/Epic Games/UE_5.4/Engine/Binaries/Win64/UnrealEditor-Cmd.exe",
    "-run=Project",
    "-create",
    "-name=MyDungeonCrawler",
    "-path=C:/Projects/MyDungeonCrawler",
    "-template=ThirdPerson"
])
```

### 2. Asset Import (Batch)

```powershell
# Import all assets from art/exports
python Content/Python/asset_importer.py --source "C:\Projects\MyDungeonCrawler\art\exports"
```

### 3. Level Generation

```python
# Generate level from blueprint
python Content/Python/level_builder.py --blueprint "Content/Blueprints/level_01.json"
```

### 4. Nanite/Lumen Setup

```python
# Auto-configure for next-gen graphics
python Content/Python/setup_lumen.py
python Content/Python/enable_nanite.py --path "/Game/_Game/Art"
```

### 5. Playtest

```powershell
# Run game in standalone
UnrealEditor-Cmd.exe "C:/Projects/MyDungeonCrawler/MyDungeonCrawler.uproject" -game -log

# With autotest
UnrealEditor-Cmd.exe "C:/Projects/MyDungeonCrawler/MyDungeonCrawler.uproject" -game -ExecCmds="py Content/Python/autotest.py"
```

---

## 📋 GDD Interview (Unreal-specific)

Domande extra per Unreal:

```markdown
Q20-Unreal: Graphics fidelity target?
  1. Nanite + Lumen (high-end PC, next-gen consoles)
  2. Standard forward renderer (mid-range PC)
  3. Mobile-optimized (mobile devices, low-end PC)

Q21-Unreal: Use World Partition?
  1. Yes (large open world, streaming)
  2. No (small levels, single scene)

Q22-Unreal: Blueprint or C++?
  1. Blueprint Visual Scripting (faster iteration)
  2. C++ (performance-critical)
  3. Mix (Blueprint + C++ classes)

Q23-Unreal: Target platform?
  1. PC (Windows/Mac/Linux)
  2. Console (PlayStation 5, Xbox Series X/S)
  3. Mobile (Android/iOS)
  4. All platforms
```

---

## 🆚 Feature Parity Table

| Feature | Unity | Godot | Unreal | Status |
|---------|-------|-------|--------|--------|
| Level Builder | ✅ | ✅ | 🚧 | 70% |
| Asset Import | ✅ | ✅ | ✅ | 90% |
| Material System | URP | Standard3D | PBR Full | ✅ 100% |
| Procedural Geo | ProBuilder | CSG | Geometry Script | 🚧 60% |
| Lighting | URP | Forward+ | Lumen | ✅ 100% |
| Playtest Auto | TerminalMCP | Built-in | Python API | 🚧 50% |
| Blueprint Gen | - | - | ✅ | 🚧 40% |
| MCP Server | ✅ | ✅ | ❌ | 0% (planned) |
| UI Generation | UI Toolkit | Control | UMG | 🚧 30% |

---

## 🔮 Roadmap

### Phase 1: Core Pipeline (Q1 2025)
- ✅ Python asset importer
- ✅ Basic level builder
- ✅ Material system
- 🚧 Nanite/Lumen auto-setup

### Phase 2: MCP Integration (Q2 2025)
- ❌ Unreal Editor MCP server
- ❌ Live scene editing via MCP
- ❌ Real-time Blueprint generation

### Phase 3: Full Parity (Q3 2025)
- ❌ UI generation (UMG widgets)
- ❌ Automated playtest sistema completo
- ❌ Geometry Script integration
- ❌ World Partition setup

### Phase 4: Advanced Features (Q4 2025)
- ❌ Sequencer cinematics generation
- ❌ Metahuman character integration
- ❌ Chaos physics setup
- ❌ Quixel MegaScan direct integration

---

## 📦 Current Workaround (Senza MCP)

Fino al completamento del MCP server:

1. **Agent genera Python scripts** in `Content/Python/`
2. **Utente esegue script** in Unreal Editor console:
   ```
   py Content/Python/build_level.py
   ```
3. **Agent legge output** da log files
4. **Iterazione** fino a completamento

**Limitazioni:**
- Non real-time (require manual script execution)
- No live preview durante generazione
- No automatic screenshot capture

---

## 🤝 Contribuisci

Il supporto Unreal è in sviluppo attivo! Contribuisci:

- **MCP Server:** Implementa Unreal Editor MCP protocol
- **Blueprint API:** Migliora visual scripting generation
- **Python Scripts:** Espandi automation utilities
- **Testing:** Test su diverse versioni UE5

**Repository:** `game-developer/engines/unreal/` (coming soon)

---

**Versione:** 0.5 (Preview)  
**Status:** 🚧 In Development  
**Target:** Full support in GameDeveloperSkill v2.5  
**Unreal Version:** 5.3, 5.4, 5.5+
