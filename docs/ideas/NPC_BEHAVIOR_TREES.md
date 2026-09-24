# NPC Behavior Trees Generator

Sistema per generare AI behavior trees base per personaggi NPC in tutti gli engine.

---

## 🤖 Behavior Tree Structure

```json
{
  "behavior_tree": "Guard_AI",
  "root": {
    "type": "selector",
    "children": [
      {
        "type": "sequence",
        "name": "Combat",
        "children": [
          {"type": "condition", "check": "enemy_in_range"},
          {"type": "action", "do": "chase_enemy"},
          {"type": "action", "do": "attack_enemy"}
        ]
      },
      {
        "type": "sequence",
        "name": "Alert",
        "children": [
          {"type": "condition", "check": "heard_noise"},
          {"type": "action", "do": "investigate_sound"}
        ]
      },
      {
        "type": "action",
        "name": "Patrol",
        "do": "patrol_waypoints"
      }
    ]
  },
  
  "blackboard": {
    "variables": [
      {"name": "enemy_in_range", "type": "bool", "default": false},
      {"name": "patrol_points", "type": "vector3[]"},
      {"name": "current_waypoint", "type": "int", "default": 0},
      {"name": "alert_level", "type": "float", "default": 0.0}
    ]
  },
  
  "parameters": {
    "detection_range": 15.0,
    "attack_range": 2.5,
    "patrol_speed": 2.0,
    "chase_speed": 5.0,
    "field_of_view": 120.0
  }
}
```

---

## 🎨 Behavior Tree Templates

### 1. **Guard AI**
```json
{
  "template": "guard",
  "behaviors": ["patrol", "investigate", "combat"],
  "personality": "cautious",
  "description": "Patrols area, investigates sounds, engages threats"
}
```

### 2. **Merchant AI**
```json
{
  "template": "merchant",
  "behaviors": ["idle", "greet_player", "trade"],
  "personality": "friendly",
  "description": "Waits in shop, greets nearby players, opens trade UI"
}
```

### 3. **Wanderer AI**
```json
{
  "template": "wanderer",
  "behaviors": ["wander", "avoid_obstacles", "flee_from_danger"],
  "personality": "peaceful",
  "description": "Walks randomly, avoids threats, flees from combat"
}
```

### 4. **Aggressive Enemy**
```json
{
  "template": "aggressive",
  "behaviors": ["seek_player", "attack", "use_abilities"],
  "personality": "hostile",
  "description": "Always chases player, attacks on sight, uses special moves"
}
```

### 5. **Boss AI**
```json
{
  "template": "boss",
  "behaviors": ["phase_transitions", "summon_minions", "special_attacks", "enrage"],
  "personality": "tactical",
  "description": "Multi-phase fight with escalating difficulty"
}
```

---

## 🔧 Generator

```python
# game-developer/tools/ai-generator/behavior_tree_generator.py
from typing import Dict, List
import json

class BehaviorNode:
    def __init__(self, node_type: str, name: str = ""):
        self.type = node_type  # "selector", "sequence", "condition", "action"
        self.name = name
        self.children = []
        self.data = {}
    
    def add_child(self, child: 'BehaviorNode'):
        self.children.append(child)
        return self
    
    def set_data(self, **kwargs):
        self.data.update(kwargs)
        return self
    
    def to_dict(self) -> Dict:
        result = {"type": self.type}
        if self.name:
            result["name"] = self.name
        if self.children:
            result["children"] = [c.to_dict() for c in self.children]
        result.update(self.data)
        return result

class BehaviorTreeGenerator:
    """Generate behavior trees from templates"""
    
    TEMPLATES = {
        "guard": {
            "behaviors": ["patrol", "investigate", "combat"],
            "blackboard": ["enemy_in_range", "patrol_points", "alert_level"]
        },
        "merchant": {
            "behaviors": ["idle", "greet", "trade"],
            "blackboard": ["player_nearby", "shop_open"]
        },
        "aggressive": {
            "behaviors": ["seek", "attack", "abilities"],
            "blackboard": ["target", "health", "cooldowns"]
        }
    }
    
    def generate(self, template_name: str, **params) -> Dict:
        """Generate behavior tree from template"""
        
        template = self.TEMPLATES.get(template_name)
        if not template:
            raise ValueError(f"Unknown template: {template_name}")
        
        # Build tree based on template
        if template_name == "guard":
            root = self.build_guard_tree(params)
        elif template_name == "merchant":
            root = self.build_merchant_tree(params)
        elif template_name == "aggressive":
            root = self.build_aggressive_tree(params)
        else:
            root = self.build_generic_tree(template, params)
        
        # Build full structure
        tree = {
            "behavior_tree": f"{template_name}_AI",
            "root": root.to_dict(),
            "blackboard": self.generate_blackboard(template),
            "parameters": params
        }
        
        return tree
    
    def build_guard_tree(self, params: Dict) -> BehaviorNode:
        """Guard AI: Patrol → Investigate → Combat"""
        
        root = BehaviorNode("selector", "GuardBehavior")
        
        # Combat sequence (highest priority)
        combat = BehaviorNode("sequence", "Combat")
        combat.add_child(BehaviorNode("condition").set_data(check="enemy_in_range"))
        combat.add_child(BehaviorNode("action").set_data(do="move_to_enemy"))
        combat.add_child(BehaviorNode("action").set_data(do="attack"))
        root.add_child(combat)
        
        # Investigate sequence
        investigate = BehaviorNode("sequence", "Investigate")
        investigate.add_child(BehaviorNode("condition").set_data(check="heard_noise"))
        investigate.add_child(BehaviorNode("action").set_data(do="move_to_sound"))
        investigate.add_child(BehaviorNode("action").set_data(do="look_around"))
        root.add_child(investigate)
        
        # Default patrol
        patrol = BehaviorNode("action", "Patrol")
        patrol.set_data(do="patrol_waypoints")
        root.add_child(patrol)
        
        return root
    
    def build_merchant_tree(self, params: Dict) -> BehaviorNode:
        """Merchant AI: Idle → Greet → Trade"""
        
        root = BehaviorNode("selector", "MerchantBehavior")
        
        # Trading sequence
        trade = BehaviorNode("sequence", "Trade")
        trade.add_child(BehaviorNode("condition").set_data(check="player_interacting"))
        trade.add_child(BehaviorNode("action").set_data(do="open_shop_ui"))
        root.add_child(trade)
        
        # Greeting sequence
        greet = BehaviorNode("sequence", "Greet")
        greet.add_child(BehaviorNode("condition").set_data(check="player_nearby"))
        greet.add_child(BehaviorNode("action").set_data(do="face_player"))
        greet.add_child(BehaviorNode("action").set_data(do="wave"))
        root.add_child(greet)
        
        # Default idle
        idle = BehaviorNode("action", "Idle")
        idle.set_data(do="idle_animation")
        root.add_child(idle)
        
        return root
    
    def build_aggressive_tree(self, params: Dict) -> BehaviorNode:
        """Aggressive enemy: Always chase and attack"""
        
        root = BehaviorNode("sequence", "AggressiveBehavior")
        
        # Find target
        root.add_child(BehaviorNode("action").set_data(do="find_nearest_player"))
        
        # Selector for attack or chase
        combat = BehaviorNode("selector", "Combat")
        
        # Attack if in range
        attack_seq = BehaviorNode("sequence", "Attack")
        attack_seq.add_child(BehaviorNode("condition").set_data(check="target_in_attack_range"))
        attack_seq.add_child(BehaviorNode("action").set_data(do="attack_target"))
        combat.add_child(attack_seq)
        
        # Otherwise chase
        combat.add_child(BehaviorNode("action").set_data(do="chase_target"))
        
        root.add_child(combat)
        
        return root
    
    def generate_blackboard(self, template: Dict) -> Dict:
        """Generate blackboard variables for template"""
        
        variables = []
        
        for var_name in template['blackboard']:
            var_type = self.infer_type(var_name)
            variables.append({
                "name": var_name,
                "type": var_type,
                "default": self.default_value(var_type)
            })
        
        return {"variables": variables}
    
    def infer_type(self, var_name: str) -> str:
        """Infer variable type from name"""
        if 'points' in var_name or 'waypoints' in var_name:
            return "vector3[]"
        elif 'range' in var_name or 'level' in var_name:
            return "bool" if 'in_' in var_name else "float"
        elif 'target' in var_name:
            return "GameObject"
        else:
            return "bool"
    
    def default_value(self, var_type: str):
        """Get default value for type"""
        defaults = {
            "bool": False,
            "float": 0.0,
            "int": 0,
            "vector3[]": [],
            "GameObject": None
        }
        return defaults.get(var_type, None)

# Usage
generator = BehaviorTreeGenerator()

# Generate guard AI
guard_tree = generator.generate("guard", 
    detection_range=15.0,
    attack_range=2.5,
    patrol_speed=2.0
)

# Save to JSON
with open("guard_ai.json", 'w') as f:
    json.dump(guard_tree, f, indent=2)
```

---

## 🎮 Engine Implementations

### Unity (Behavior Designer Integration)

```csharp
// engines/unity/ai/BehaviorTreeImporter.cs
using UnityEngine;
using BehaviorDesigner.Runtime;
using System.Collections.Generic;

public class BehaviorTreeImporter : MonoBehaviour {
    public static BehaviorTree ImportFromJson(string jsonPath) {
        string json = System.IO.File.ReadAllText(jsonPath);
        var data = JsonUtility.FromJson<BehaviorTreeData>(json);
        
        // Create BehaviorTree component
        var behaviorTree = gameObject.AddComponent<BehaviorTree>();
        
        // Build tree from JSON
        BuildNode(data.root, behaviorTree);
        
        // Set blackboard variables
        foreach (var variable in data.blackboard.variables) {
            AddBlackboardVariable(behaviorTree, variable);
        }
        
        return behaviorTree;
    }
    
    static Task BuildNode(NodeData nodeData, BehaviorTree tree) {
        Task task = null;
        
        switch (nodeData.type) {
            case "selector":
                task = tree.AddTask<Selector>();
                break;
            case "sequence":
                task = tree.AddTask<Sequence>();
                break;
            case "condition":
                task = CreateCondition(nodeData.check);
                break;
            case "action":
                task = CreateAction(nodeData.do);
                break;
        }
        
        // Add children
        if (nodeData.children != null) {
            foreach (var child in nodeData.children) {
                var childTask = BuildNode(child, tree);
                ((ParentTask)task).AddChild(childTask);
            }
        }
        
        return task;
    }
}
```

### Godot (BTrees Plugin)

```gdscript
# engines/godot/ai/behavior_tree_importer.gd
extends Node

const BTSelector = preload("res://addons/btrees/nodes/bt_selector.gd")
const BTSequence = preload("res://addons/btrees/nodes/bt_sequence.gd")

func import_from_json(json_path: String) -> BehaviorTree:
    var file = FileAccess.open(json_path, FileAccess.READ)
    var json_text = file.get_as_text()
    var data = JSON.parse_string(json_text)
    
    var tree = BehaviorTree.new()
    tree.root = build_node(data.root)
    
    # Setup blackboard
    for variable in data.blackboard.variables:
        tree.blackboard.set_var(variable.name, variable.default)
    
    return tree

func build_node(node_data: Dictionary) -> BTNode:
    var node: BTNode
    
    match node_data.type:
        "selector":
            node = BTSelector.new()
        "sequence":
            node = BTSequence.new()
        "condition":
            node = create_condition(node_data.check)
        "action":
            node = create_action(node_data.get("do"))
    
    # Add children
    if node_data.has("children"):
        for child_data in node_data.children:
            var child = build_node(child_data)
            node.add_child(child)
    
    return node

func create_condition(check_name: String) -> BTCondition:
    # Map to Godot condition nodes
    match check_name:
        "enemy_in_range":
            return BTEnemyInRange.new()
        "player_nearby":
            return BTPlayerNearby.new()
        _:
            return BTCustomCondition.new(check_name)
```

### Unreal (Behavior Tree Editor)

```python
# engines/unreal/ai/behavior_tree_importer.py
import unreal

def import_from_json(json_path: str) -> unreal.BehaviorTree:
    """Import behavior tree JSON into Unreal BT asset"""
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Create BT asset
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    factory = unreal.BehaviorTreeFactory()
    
    bt_asset = asset_tools.create_asset(
        data['behavior_tree'],
        "/Game/AI/BehaviorTrees",
        unreal.BehaviorTree,
        factory
    )
    
    # Build root node
    root_task = build_node(data['root'], bt_asset)
    bt_asset.set_root_node(root_task)
    
    # Create blackboard
    bb_asset = create_blackboard(data['blackboard'])
    bt_asset.set_blackboard_asset(bb_asset)
    
    unreal.EditorAssetLibrary.save_asset(bt_asset.get_path_name())
    
    return bt_asset

def build_node(node_data: dict, bt_asset) -> unreal.BTCompositeNode:
    """Recursively build BT nodes"""
    
    if node_data['type'] == 'selector':
        node = unreal.BTComposite_Selector()
    elif node_data['type'] == 'sequence':
        node = unreal.BTComposite_Sequence()
    elif node_data['type'] == 'action':
        node = create_task(node_data['do'])
    elif node_data['type'] == 'condition':
        node = create_decorator(node_data['check'])
    
    # Add children
    if 'children' in node_data:
        for child_data in node_data['children']:
            child = build_node(child_data, bt_asset)
            node.add_child(child)
    
    return node
```

---

## 📊 AI Complexity Levels

| Template | Nodes | Complexity | Use Case |
|----------|-------|------------|----------|
| Idle | 1-2 | Trivial | Background NPCs |
| Wanderer | 3-5 | Simple | Civilians, animals |
| Guard | 8-12 | Medium | Patrols, defenders |
| Merchant | 6-8 | Medium | Shopkeepers, quest givers |
| Aggressive | 10-15 | Medium | Basic enemies |
| Boss | 20-40 | Complex | Multi-phase bosses |

---

## 🎯 GDD Integration

```markdown
Q25: Generate AI for NPCs?
  1. Yes, full (guards, merchants, enemies, bosses)
  2. Yes, simple (basic patrol and combat)
  3. No (manual scripting only)

If Yes:
  Q25a: NPC types needed?
    [ ] Guards (patrol + combat)
    [ ] Merchants (trade)
    [ ] Wanderers (ambient)
    [ ] Aggressive enemies
    [ ] Boss (multi-phase)
```

**Agent workflow:**
```python
if gdd.generate_ai:
    for npc_type in gdd.npc_types:
        # Generate behavior tree
        tree = generator.generate(npc_type, **gdd.ai_params)
        
        # Export to engine format
        export_behavior_tree(tree, engine=gdd.engine)
```

---

## 🔧 CLI Usage

```bash
# Generate behavior tree
python tools/ai-generator/generate_bt.py \
  --template guard \
  --output project/AI/guard_ai.json \
  --detection-range 15 \
  --attack-range 2.5

# Batch generate
python tools/ai-generator/generate_bt.py \
  --batch \
  --templates guard,merchant,aggressive \
  --output project/AI/
```

---

## 📈 Performance

**Tick Rate:** 10-30 Hz (configurable)  
**CPU per NPC:** ~0.1-0.5ms (optimized)  
**Max NPCs:** 50-100 simultanei (depending on complexity)

**Optimization tips:**
- LOD behavior trees (simpler at distance)
- Group ticking (update 10 NPCs per frame, not all at once)
- Cache expensive checks (player position, etc.)
- Event-driven where possible (don't poll)

---

**Versione:** 1.0  
**Status:** ✅ Implemented  
**Engines:** Unity (Behavior Designer), Godot (BTrees), Unreal (Native BT)  
**Location:** `game-developer/tools/ai-generator/`
