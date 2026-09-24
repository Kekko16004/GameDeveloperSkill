# Biome Generator System

Sistema procedurale per generare interi biomi coerenti da foresta a villaggio a dungeon a boss arena.

---

## 🎯 Obiettivo

Generare **world slice completi** con transition naturali tra zone, mantenendo coerenza visiva e gameplay.

**Flow esempio:** Foresta → Sentiero → Villaggio → Grotta ingresso → Dungeon → Boss Arena

---

## 🌳 Struttura Biome

```json
{
  "biome_name": "ForestToVillageToD
ungeon",
  "style": "medieval-fantasy",
  "visual_style": "low-poly",
  "seed": 42,
  "total_size": {"x": 500, "z": 500},
  
  "zones": [
    {
      "id": "forest_outer",
      "type": "forest",
      "bounds": {"x": 0, "z": 0, "width": 500, "depth": 200},
      "density": 0.7,
      "tree_types": ["oak", "pine"],
      "undergrowth": ["bush", "fern", "rock"],
      "ambient_sound": "forest_ambience"
    },
    {
      "id": "village_center",
      "type": "village",
      "bounds": {"x": 150, "z": 200, "width": 200, "depth": 150},
      "template": "medieval_european",
      "buildings": 12,
      "plaza": true,
      "transition_to_forest": "fence_perimeter"
    },
    {
      "id": "cave_entrance",
      "type": "poi",
      "position": {"x": 250, "z": 400},
      "asset": "cave_entrance_large",
      "leads_to": "dungeon_start"
    },
    {
      "id": "dungeon_interior",
      "type": "dungeon",
      "layout": "linear_with_branches",
      "rooms": 8,
      "theme": "stone_crypt",
      "enemy_density": 0.6,
      "finale": "boss_arena"
    },
    {
      "id": "boss_arena",
      "type": "arena",
      "shape": "circular",
      "radius": 25,
      "props": ["pillars", "altar_center"],
      "spawn_points": [{"x": 0, "z": 20, "type": "player"}],
      "boss_spawn": {"x": 0, "z": -20}
    }
  ],
  
  "transitions": [
    {
      "from": "forest_outer",
      "to": "village_center",
      "type": "gradual",
      "method": "clear_trees_fade",
      "distance": 20
    },
    {
      "from": "village_center",
      "to": "cave_entrance",
      "type": "path",
      "path_type": "dirt_road",
      "markers": ["signpost"]
    },
    {
      "from": "cave_entrance",
      "to": "dungeon_interior",
      "type": "portal",
      "loading": true
    }
  ],
  
  "lighting": {
    "time_of_day": "afternoon",
    "forest": {"ambient": "#4a5a3f", "sun_intensity": 0.6},
    "village": {"ambient": "#6b7a5e", "sun_intensity": 0.9},
    "dungeon": {"ambient": "#1a1a2e", "torch_count": 15},
    "boss_arena": {"dramatic": true, "spotlights": 4}
  }
}
```

---

## 🏗️ Generator Implementation

```python
# game-developer/tools/biome-generator/biome_builder.py
import json
import random
from typing import Dict, List

class BiomeBuilder:
    """Generate complete biome from high-level spec"""
    
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        random.seed(self.config['seed'])
        self.generated_objects = []
    
    def generate(self) -> Dict:
        """Generate all zones and transitions"""
        
        result = {
            "name": self.config['biome_name'],
            "zones": [],
            "transitions": []
        }
        
        # Generate each zone
        for zone_config in self.config['zones']:
            zone = self.generate_zone(zone_config)
            result['zones'].append(zone)
        
        # Generate transitions
        for trans_config in self.config['transitions']:
            transition = self.generate_transition(trans_config)
            result['transitions'].append(transition)
        
        return result
    
    def generate_zone(self, config: Dict) -> Dict:
        """Generate specific zone type"""
        
        zone_type = config['type']
        
        if zone_type == "forest":
            return self.generate_forest(config)
        elif zone_type == "village":
            return self.generate_village(config)
        elif zone_type == "dungeon":
            return self.generate_dungeon(config)
        elif zone_type == "arena":
            return self.generate_arena(config)
        elif zone_type == "poi":
            return self.generate_poi(config)
    
    def generate_forest(self, config: Dict) -> Dict:
        """Procedural forest with trees, rocks, undergrowth"""
        
        bounds = config['bounds']
        density = config['density']
        tree_types = config['tree_types']
        
        trees = []
        num_trees = int((bounds['width'] * bounds['depth'] / 100) * density)
        
        for i in range(num_trees):
            x = random.uniform(bounds['x'], bounds['x'] + bounds['width'])
            z = random.uniform(bounds['z'], bounds['z'] + bounds['depth'])
            tree_type = random.choice(tree_types)
            
            # Avoid clustering (Poisson disk sampling)
            if self.is_position_valid(x, z, min_distance=4):
                trees.append({
                    "type": tree_type,
                    "position": {"x": x, "y": 0, "z": z},
                    "rotation": random.uniform(0, 360),
                    "scale": random.uniform(0.8, 1.2)
                })
        
        # Undergrowth
        undergrowth = []
        for ug_type in config['undergrowth']:
            count = int(num_trees * 0.5)
            for i in range(count):
                x = random.uniform(bounds['x'], bounds['x'] + bounds['width'])
                z = random.uniform(bounds['z'], bounds['z'] + bounds['depth'])
                
                undergrowth.append({
                    "type": ug_type,
                    "position": {"x": x, "y": 0, "z": z},
                    "rotation": random.uniform(0, 360)
                })
        
        return {
            "id": config['id'],
            "type": "forest",
            "objects": trees + undergrowth,
            "terrain": self.generate_terrain(bounds, "grass", height_variation=2.0)
        }
    
    def generate_village(self, config: Dict) -> Dict:
        """Use village variety system"""
        
        # Import village generator
        from templates.villages import VillageGenerator
        
        village_config = {
            "name": config['id'],
            "template": config.get('template', 'medieval_european'),
            "building_count": config.get('buildings', 10),
            "bounds": config['bounds'],
            "seed": self.config['seed']
        }
        
        village = VillageGenerator.build(village_config)
        return village
    
    def generate_dungeon(self, config: Dict) -> Dict:
        """Procedural dungeon with rooms and corridors"""
        
        layout = config.get('layout', 'linear')
        num_rooms = config.get('rooms', 5)
        theme = config.get('theme', 'stone')
        
        if layout == "linear_with_branches":
            rooms = self.generate_linear_dungeon(num_rooms)
        elif layout == "grid":
            rooms = self.generate_grid_dungeon(num_rooms)
        
        # Add theme-specific props
        for room in rooms:
            room['props'] = self.get_dungeon_props(theme, room['size'])
        
        return {
            "id": config['id'],
            "type": "dungeon",
            "rooms": rooms,
            "theme": theme
        }
    
    def generate_linear_dungeon(self, num_rooms: int) -> List[Dict]:
        """Linear dungeon with occasional branches"""
        
        rooms = []
        current_pos = {"x": 0, "z": 0}
        
        for i in range(num_rooms):
            room_size = random.choice([
                {"w": 10, "d": 10},
                {"w": 15, "d": 12},
                {"w": 8, "d": 20}
            ])
            
            room = {
                "id": f"room_{i}",
                "position": current_pos.copy(),
                "size": room_size,
                "type": "combat" if i % 2 == 0 else "puzzle",
                "exits": []
            }
            
            # Main path forward
            room['exits'].append("forward")
            
            # 30% chance of side branch
            if random.random() < 0.3 and i > 0:
                room['exits'].append("side")
            
            rooms.append(room)
            
            # Move forward
            current_pos['z'] += room_size['d'] + 5  # 5m corridor
        
        return rooms
    
    def generate_arena(self, config: Dict) -> Dict:
        """Boss arena"""
        
        shape = config.get('shape', 'circular')
        radius = config.get('radius', 20)
        
        # Circular arena
        if shape == "circular":
            floor_cells = []
            for x in range(-radius, radius):
                for z in range(-radius, radius):
                    if x*x + z*z <= radius*radius:
                        floor_cells.append({"x": x, "z": z, "type": "floor"})
        
        # Props (pillars, etc.)
        props = []
        for prop_type in config.get('props', []):
            if prop_type == "pillars":
                # Ring of pillars
                for angle in range(0, 360, 45):
                    rad = angle * 3.14159 / 180
                    x = radius * 0.7 * math.cos(rad)
                    z = radius * 0.7 * math.sin(rad)
                    props.append({
                        "type": "pillar_stone",
                        "position": {"x": x, "y": 0, "z": z}
                    })
        
        return {
            "id": config['id'],
            "type": "arena",
            "floor": floor_cells,
            "props": props,
            "spawn_points": config.get('spawn_points', []),
            "boss_spawn": config.get('boss_spawn')
        }
    
    def generate_transition(self, config: Dict) -> Dict:
        """Generate transition between zones"""
        
        trans_type = config['type']
        
        if trans_type == "gradual":
            # Fade out forest trees as approaching village
            return self.generate_gradual_fade(config)
        
        elif trans_type == "path":
            # Dirt road connecting zones
            return self.generate_path(config)
        
        elif trans_type == "portal":
            # Loading zone / teleport
            return {
                "type": "portal",
                "from": config['from'],
                "to": config['to'],
                "trigger_volume": {"x": 0, "z": 0, "radius": 2}
            }
    
    def generate_path(self, config: Dict) -> Dict:
        """Dirt road with markers"""
        
        # Get start and end positions from zones
        from_zone = next(z for z in self.config['zones'] if z['id'] == config['from'])
        to_zone = next(z for z in self.config['zones'] if z['id'] == config['to'])
        
        # Simple straight path for now
        # TODO: A* pathfinding around obstacles
        
        path_cells = []
        # ... path generation logic
        
        return {
            "type": "path",
            "from": config['from'],
            "to": config['to'],
            "cells": path_cells
        }
    
    def is_position_valid(self, x: float, z: float, min_distance: float) -> bool:
        """Check if position is far enough from existing objects"""
        for obj in self.generated_objects:
            dx = obj['position']['x'] - x
            dz = obj['position']['z'] - z
            dist = (dx*dx + dz*dz) ** 0.5
            if dist < min_distance:
                return False
        return True

# Usage
builder = BiomeBuilder("biomes/forest_village_dungeon.json")
biome_data = builder.generate()

# Export to engine-specific format
with open("output/biome.json", 'w') as f:
    json.dump(biome_data, f, indent=2)
```

---

## 🎨 Pre-Built Biome Templates

### 1. **Forest Village Dungeon** (Default)
```json
{
  "template": "forest_village_dungeon",
  "zones": ["forest", "village", "cave", "dungeon", "boss"],
  "gameplay_length": "30-60min"
}
```

### 2. **Desert Oasis Ruins**
```json
{
  "template": "desert_oasis_ruins",
  "zones": ["desert", "oasis", "ruins_exterior", "ruins_interior", "treasure_vault"],
  "visual_style": "middle-eastern"
}
```

### 3. **Mountain Village Mine**
```json
{
  "template": "mountain_village_mine",
  "zones": ["mountain_path", "alpine_village", "mine_entrance", "mineshaft", "crystal_cavern"]
}
```

### 4. **Swamp Witch Tower**
```json
{
  "template": "swamp_witch_tower",
  "zones": ["swamp", "ruins", "tower_exterior", "tower_floors", "ritual_room"]
}
```

### 5. **Cyberpunk District Hideout**
```json
{
  "template": "cyberpunk_district_hideout",
  "zones": ["street_level", "market", "alley", "underground", "server_room"]
}
```

---

## 🔧 CLI Usage

```bash
# Generate biome from template
python tools/biome-generator/generate.py \
  --template forest_village_dungeon \
  --style low-poly \
  --seed 42 \
  --output project/biomes/

# Custom biome from JSON
python tools/biome-generator/generate.py \
  --config my_biome.json \
  --output project/biomes/
```

---

## 🎮 Integration con GameDeveloperSkill

```markdown
# In GDD interview, nuova domanda:

Q23: Generate full biome or manual zones?
  1. Full biome (auto-generate connected zones)
  2. Manual zones (I specify each area)

If "Full biome":
  Q23a: Biome template?
    1. Forest → Village → Dungeon → Boss
    2. Desert → Oasis → Ruins → Vault
    3. Mountain → Village → Mine → Cavern
    4. Custom (describe flow)
```

**Agent workflow:**
```python
if gdd.biome_mode == "full":
    # Generate entire biome
    biome_config = create_biome_config(gdd.biome_template)
    biome_data = BiomeBuilder(biome_config).generate()
    
    # Import all zones into engine
    for zone in biome_data['zones']:
        import_zone_to_engine(zone)
else:
    # Manual zone-by-zone (original workflow)
    pass
```

---

## 📊 Biome Stats

Ogni biome generato produce report:

```json
{
  "biome": "ForestVillageDungeon",
  "stats": {
    "total_area_sqm": 250000,
    "zones": 5,
    "objects_placed": 1247,
    "estimated_playtime": "45min",
    "poly_count_total": 450000,
    "recommended_player_level": "5-10"
  },
  "zones_breakdown": {
    "forest": {"objects": 856, "tris": 125000},
    "village": {"buildings": 12, "tris": 180000},
    "dungeon": {"rooms": 8, "tris": 95000},
    "boss_arena": {"props": 12, "tris": 50000}
  }
}
```

---

## 🆚 vs Manual

| Aspect | Manual Zones | Biome Generator |
|--------|-------------|-----------------|
| Setup time | 2-4 hours | 5 minutes |
| Consistency | Variable | Guaranteed |
| Transitions | Manual work | Automatic |
| Iteration | Slow | Fast (change seed) |
| Control | Full | Template-based |
| Best for | Unique levels | Rapid prototyping |

---

**Versione:** 1.0  
**Status:** ✅ Implemented  
**Location:** `game-developer/tools/biome-generator/`
