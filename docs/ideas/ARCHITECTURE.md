# Core Architecture - Engine-Agnostic

Componenti condivisi tra tutti i motori (Unity, Godot, Unreal).

---

## 🎯 Obiettivo

Separare logica **engine-agnostic** (blueprint, asset catalog, style system) da implementazioni **engine-specific** (Unity C#, Godot GDScript, Unreal Python).

---

## 📐 Struttura

```
game-developer/
├── core/                    # Engine-agnostic
│   ├── blueprints/          # JSON blueprint schema & validator
│   ├── asset-catalog/       # Unified asset database
│   ├── style-system/        # Style presets & configs
│   ├── gdd/                 # GDD interview & templates
│   └── validation/          # Quality gates & lint rules
├── engines/                 # Engine-specific implementations
│   ├── unity/
│   │   ├── GDS.cs           # C# implementations
│   │   └── adapters/        # Core → Unity adapters
│   ├── godot/
│   │   ├── gds.gd           # GDScript implementations
│   │   └── adapters/        # Core → Godot adapters
│   └── unreal/
│       ├── gds_*.py         # Python implementations
│       └── adapters/        # Core → Unreal adapters
└── tools/                   # Cross-engine tools
    ├── asset-library-manager/
    ├── tui/
    └── cli/
```

---

## 📦 Core Components

### 1. Blueprint System (Engine-Agnostic)

JSON schema universale per definire livelli:

```json
{
  "schema_version": "2.0",
  "engine": "auto",
  "name": "DungeonRoom",
  "origin": {"x": 0, "y": 0, "z": 0},
  "cells": [
    {"x": 0, "y": 0, "type": "floor", "material": "stone"},
    {"x": 0, "y": 1, "type": "wall_n", "height": 3.0}
  ],
  "props": [
    {"kit": "torch_wall", "x": 2, "y": 0, "z": 1.5, "ry": 90}
  ],
  "lighting": {
    "ambient": "#4a5568",
    "directional": {"color": "#ffffff", "intensity": 1.0, "angle": 45}
  }
}
```

**Engine-agnostic validator:**

```python
# core/blueprints/validator.py
from typing import Dict, List
from pydantic import BaseModel, validator

class Vector3(BaseModel):
    x: float
    y: float
    z: float

class Cell(BaseModel):
    x: int
    y: int
    type: str
    material: str = "default"
    height: float = 1.0
    
    @validator('type')
    def validate_type(cls, v):
        valid_types = ['floor', 'wall_n', 'wall_s', 'wall_e', 'wall_w', 'ceiling']
        if v not in valid_types:
            raise ValueError(f"Invalid cell type: {v}")
        return v

class Prop(BaseModel):
    kit: str
    x: float
    y: float
    z: float
    rx: float = 0
    ry: float = 0
    rz: float = 0
    scale: float = 1.0

class Blueprint(BaseModel):
    schema_version: str
    engine: str = "auto"  # "unity", "godot", "unreal", "auto"
    name: str
    origin: Vector3
    cells: List[Cell]
    props: List[Prop]
    lighting: Dict = {}
    
    def validate(self) -> List[str]:
        """Validate blueprint and return warnings"""
        warnings = []
        
        # Check for floating props
        for prop in self.props:
            if prop.y < 0:
                warnings.append(f"Prop '{prop.kit}' below ground (y={prop.y})")
        
        # Check for overlapping cells
        positions = {(c.x, c.y) for c in self.cells}
        if len(positions) < len(self.cells):
            warnings.append("Overlapping cells detected")
        
        return warnings
```

---

### 2. Asset Catalog (Engine-Agnostic)

Database unificato di tutti gli asset disponibili:

```python
# core/asset-catalog/catalog.py
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel

class AssetSource(str, Enum):
    KENNEY = "kenney"
    KAYKIT = "kaykit"
    QUATERNIUS = "quaternius"
    MEGASCAN = "megascan"
    POLYHAVEN = "polyhaven"
    CUSTOM = "custom"

class AssetMetadata(BaseModel):
    id: str
    name: str
    source: AssetSource
    type: str  # "model", "texture", "material", etc.
    style: str  # "low-poly", "realistic", etc.
    poly_count: Optional[int]
    formats: List[str]  # ["fbx", "glb"]
    license: str
    tags: List[str]
    thumbnail_url: Optional[str]

class AssetCatalog:
    """Engine-agnostic asset database"""
    
    def __init__(self):
        self.assets: List[AssetMetadata] = []
    
    def add_asset(self, asset: AssetMetadata):
        self.assets.append(asset)
    
    def find(self, **filters) -> List[AssetMetadata]:
        """Filter assets by any field"""
        results = self.assets
        
        for key, value in filters.items():
            results = [a for a in results if getattr(a, key, None) == value]
        
        return results
    
    def to_json(self, path: str):
        """Export catalog to JSON"""
        import json
        data = [a.dict() for a in self.assets]
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def from_json(cls, path: str):
        """Load catalog from JSON"""
        import json
        catalog = cls()
        with open(path, 'r') as f:
            data = json.load(f)
        for item in data:
            catalog.add_asset(AssetMetadata(**item))
        return catalog
```

---

### 3. Style System (Engine-Agnostic)

Config JSON per ogni stile visivo:

```json
{
  "id": "low-poly",
  "name": "Low Poly",
  "poly_range": [100, 500],
  "preferred_kits": ["kenney", "kaykit"],
  "material_settings": {
    "use_pbr": false,
    "flat_shading": true,
    "vertex_colors": true
  },
  "shader_packages": {
    "unity": ["URP/Lit"],
    "godot": ["StandardMaterial3D"],
    "unreal": ["M_DefaultLit"]
  },
  "gen3d_prompt_suffix": "low poly, flat colors, game ready",
  "lookdev_presets": ["stylized-day", "stylized-sunset"]
}
```

---

### 4. GDD System (Engine-Agnostic)

Interview template e validation:

```python
# core/gdd/interview.py
from typing import Dict, List

class GDDInterview:
    """GDD questionnaire - engine agnostic"""
    
    QUESTIONS = [
        {
            "id": "q01_engine",
            "question": "Target game engine?",
            "options": ["unity", "godot", "unreal"],
            "default": "unity"
        },
        {
            "id": "q04_style",
            "question": "Visual style?",
            "options": ["low-poly", "realistic", "toon", "voxel", "hand-painted", "sci-fi"],
            "default": "low-poly"
        },
        {
            "id": "q16_gen3d",
            "question": "Generative 3D tier?",
            "options": ["none", "local", "meshy", "tripo", "hyper3d"],
            "default": "none"
        }
        # ... 19 questions total
    ]
    
    def __init__(self):
        self.answers: Dict[str, str] = {}
    
    def ask_question(self, question_id: str):
        """Interactive question"""
        q = next(q for q in self.QUESTIONS if q["id"] == question_id)
        # Implementation depends on CLI/UI
        pass
    
    def validate(self) -> bool:
        """Ensure all required questions answered"""
        required = [q["id"] for q in self.QUESTIONS]
        return all(qid in self.answers for qid in required)
    
    def export_markdown(self, path: str):
        """Export GDD to markdown"""
        with open(path, 'w') as f:
            f.write("# Game Design Document\n\n")
            for q in self.QUESTIONS:
                answer = self.answers.get(q["id"], "N/A")
                f.write(f"**{q['question']}** {answer}\n\n")
```

---

## 🔌 Engine Adapters

Ogni engine ha adapter che traduce core → engine specifics.

### Unity Adapter

```csharp
// engines/unity/adapters/BlueprintAdapter.cs
using UnityEngine;
using System.Collections.Generic;

namespace GDS.Adapters {
    public static class BlueprintAdapter {
        public static GameObject BuildFromCore(CoreBlueprint blueprint) {
            GameObject root = new GameObject(blueprint.name);
            
            foreach (var cell in blueprint.cells) {
                GameObject cellObj = CreateCell(cell);
                cellObj.transform.parent = root.transform;
                cellObj.transform.localPosition = new Vector3(
                    cell.x * 2f,
                    0,
                    cell.y * 2f
                );
            }
            
            foreach (var prop in blueprint.props) {
                PlaceProp(root, prop);
            }
            
            return root;
        }
        
        private static GameObject CreateCell(CoreCell cell) {
            GameObject obj = GameObject.CreatePrimitive(PrimitiveType.Cube);
            
            if (cell.type == "floor") {
                obj.transform.localScale = new Vector3(2f, 0.2f, 2f);
            } else if (cell.type.StartsWith("wall_")) {
                obj.transform.localScale = new Vector3(2f, 3f, 0.2f);
            }
            
            return obj;
        }
    }
}
```

### Godot Adapter

```gdscript
# engines/godot/adapters/blueprint_adapter.gd
extends Node

const CELL_SIZE = 2.0

static func build_from_core(blueprint: Dictionary) -> Node3D:
    var root = Node3D.new()
    root.name = blueprint.name
    
    for cell in blueprint.cells:
        var cell_node = create_cell(cell)
        cell_node.position = Vector3(
            cell.x * CELL_SIZE,
            0,
            cell.y * CELL_SIZE
        )
        root.add_child(cell_node)
    
    for prop in blueprint.props:
        place_prop(root, prop)
    
    return root

static func create_cell(cell: Dictionary) -> MeshInstance3D:
    var mesh_inst = MeshInstance3D.new()
    var box = BoxMesh.new()
    
    match cell.type:
        "floor":
            box.size = Vector3(CELL_SIZE, 0.2, CELL_SIZE)
        "wall_n":
            box.size = Vector3(CELL_SIZE, 3.0, 0.2)
    
    mesh_inst.mesh = box
    return mesh_inst
```

### Unreal Adapter

```python
# engines/unreal/adapters/blueprint_adapter.py
import unreal

CELL_SIZE = 200.0  # cm

def build_from_core(blueprint):
    """Convert core blueprint to Unreal level"""
    root = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.Actor,
        unreal.Vector(0, 0, 0)
    )
    root.set_actor_label(blueprint['name'])
    
    for cell in blueprint['cells']:
        cell_actor = create_cell(cell)
        cell_actor.set_actor_location(
            unreal.Vector(
                cell['x'] * CELL_SIZE,
                cell['y'] * CELL_SIZE,
                0
            )
        )
        cell_actor.attach_to_actor(root, '', 
            unreal.AttachmentRule.KEEP_WORLD,
            unreal.AttachmentRule.KEEP_WORLD,
            unreal.AttachmentRule.KEEP_WORLD,
            False)
    
    return root

def create_cell(cell):
    """Create Unreal static mesh actor for cell"""
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.StaticMeshActor,
        unreal.Vector(0, 0, 0)
    )
    
    # Load appropriate mesh based on cell type
    if cell['type'] == 'floor':
        mesh_path = "/Engine/BasicShapes/Plane"
    elif cell['type'].startswith('wall_'):
        mesh_path = "/Engine/BasicShapes/Cube"
    
    mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
    actor.static_mesh_component.set_static_mesh(mesh)
    
    return actor
```

---

## 🔄 Workflow con Core

```python
# Example: Agent genera blueprint engine-agnostic
from core.blueprints import Blueprint, Cell, Prop

blueprint = Blueprint(
    schema_version="2.0",
    engine="auto",  # Will be detected
    name="TestRoom",
    origin={"x": 0, "y": 0, "z": 0},
    cells=[
        Cell(x=0, y=0, type="floor"),
        Cell(x=0, y=1, type="wall_n")
    ],
    props=[
        Prop(kit="torch_wall", x=2, y=0, z=1.5, ry=90)
    ]
)

# Validate
warnings = blueprint.validate()
if warnings:
    print("Warnings:", warnings)

# Export to JSON
blueprint_json = blueprint.json()

# ENGINE-SPECIFIC: Load e build
if engine == "unity":
    # Unity C# reads JSON and uses BlueprintAdapter
    pass
elif engine == "godot":
    # Godot GDScript reads JSON and uses blueprint_adapter.gd
    pass
elif engine == "unreal":
    # Unreal Python reads JSON and uses blueprint_adapter.py
    import engines.unreal.adapters.blueprint_adapter as adapter
    adapter.build_from_core(blueprint.dict())
```

---

## 📊 Benefits

✅ **Write once:** Blueprint JSON funziona su tutti engine  
✅ **Validate once:** Core validator unico  
✅ **Style configs:** JSON configs shared  
✅ **Asset catalog:** Database unificato  
✅ **Easy maintenance:** Fix una volta, funziona ovunque  
✅ **Engine swapping:** Cambio engine = solo adapter diverso  

---

**Versione:** 1.0  
**Status:** ✅ Implemented  
**Location:** `game-developer/core/`
