# Sistema di Varietà Villaggi

Libreria di template e generatori procedurali per creare villaggi con varietà architettonica e layout diversificati.

---

## 🏘️ Template Culturali Disponibili

### 1. **Medieval European** (Default)
- **Architettura:** Timber frame, pietra, tetti spioventi
- **Layout:** Strada principale + piazza centrale con pozzo
- **Edifici:** Cottage, locande, fucine, chiese
- **Materiali:** Legno scuro, pietra grigia, tetti rosso mattone
- **Props:** Lanterne, barili, recinzioni in legno

**Blueprint:** `templates/villages/medieval_european.json`

---

### 2. **Nordic/Viking**
- **Architettura:** Longhouse, tetti erba/paglia ripidi, log cabin
- **Layout:** Case lungo fiume/fiordo, nessuna piazza centrale
- **Edifici:** Longhouse, capanne pescatori, magazzini
- **Materiali:** Legno chiaro, pietra grezza, tetti verdi
- **Props:** Torce, rune stones, barche tirate a riva

**Blueprint:** `templates/villages/nordic_viking.json`

---

### 3. **Asian/Japanese**
- **Architettura:** Tetti curvi, shoji screens, pilastri rossi
- **Layout:** Giardini zen, ponti su stagni, templi in altura
- **Edifici:** Case tradizionali, santuari torii, tea house
- **Materiali:** Legno naturale, carta bianca, tetti scuri curvi
- **Props:** Lanterne di carta, sakura trees, statue di pietra

**Blueprint:** `templates/villages/asian_japanese.json`

---

### 4. **Middle Eastern/Desert**
- **Architettura:** Adobe, tetti piatti, archi, cortili interni
- **Layout:** Strade strette ombreggiate, mercato coperto centrale
- **Edifici:** Case cubic terrazzate, bazar, moschea con cupola
- **Materiali:** Terracotta, sabbia, tessuti colorati
- **Props:** Tappeti, vasi, palme, fontane

**Blueprint:** `templates/villages/desert_middle_eastern.json`

---

### 5. **Tropical Island**
- **Architettura:** Capanne palafitta, tetti foglie palma, bamboo
- **Layout:** Circolare attorno a falò/totem, su spiaggia
- **Edifici:** Hut tondo, warehouse aperto, dock pescatori
- **Materiali:** Bamboo, foglie intrecciate, legno grezzo
- **Props:** Torce tiki, canoe, reti da pesca, palme

**Blueprint:** `templates/villages/tropical_island.json`

---

### 6. **Cyberpunk/Sci-Fi Slum**
- **Architettura:** Container stacked, neon signs, metal panels
- **Layout:** Verticale (edifici multi-piano), vicoli stretti
- **Edifici:** Shop container, neon bar, clinic improvvisata
- **Materiali:** Metallo arrugginito, plastica, luci neon
- **Props:** Cables hanging, vending machines, holograms

**Blueprint:** `templates/villages/cyberpunk_slum.json`

---

### 7. **Fantasy Elven**
- **Architettura:** Treehouse interconnesse, ponti sospesi, spirali organiche
- **Layout:** Multi-livello verticale su alberi giganti
- **Edifici:** Casa su rami, libreria tronco, platform osservazione
- **Materiali:** Legno chiaro liscio, foglie dorate, cristalli
- **Props:** Luci fatate, vines, scale a spirale

**Blueprint:** `templates/villages/fantasy_elven.json`

---

### 8. **Steampunk Industrial**
- **Architettura:** Mattoni rossi, gears visibili, ciminiere
- **Layout:** Lungo binari ferroviari, warehouse cluster
- **Edifici:** Factory, clocktower, workshop con forgia
- **Materiali:** Brick rosso, ferro, steam pipes
- **Props:** Gears decorativi, lampposts gas, carts

**Blueprint:** `templates/villages/steampunk_industrial.json`

---

## 🎲 Sistema di Variazione Procedurale

### Building Variation System

Ogni template ha **varianti procedurali** per evitare ripetizione:

```json
{
  "buildingTypes": [
    {
      "id": "cottage",
      "baseSpec": "specs/cottage_base.json",
      "variations": [
        {
          "id": "cottage_a",
          "styleOverride": { "roof": "#8B7355", "shutters": true },
          "volumeRandomScale": { "w": [0.9, 1.1], "d": [0.9, 1.1] },
          "windowRandomCount": { "min": 2, "max": 4 },
          "chimneyProbability": 0.7,
          "balconyProbability": 0.3,
          "gardenProbability": 0.6
        },
        {
          "id": "cottage_b",
          "styleOverride": { "roof": "#6B5A4E", "shutters": false },
          "volumeRandomScale": { "w": [1.0, 1.2], "d": [0.8, 1.0] },
          "windowRandomCount": { "min": 3, "max": 5 },
          "chimneyProbability": 0.9,
          "doorStyle": "arched"
        }
      ],
      "weight": 5
    },
    {
      "id": "inn",
      "file": "building_inn_hero.fbx",
      "weight": 1,
      "unique": true
    }
  ]
}
```

### Layout Variation

```json
{
  "layoutPatterns": [
    {
      "id": "cross_roads",
      "description": "Due strade che si incrociano al centro con piazza",
      "roads": [
        { "axis": "x", "length": 120, "width": 5 },
        { "axis": "z", "length": 100, "width": 4 }
      ],
      "plaza": { "shape": "circle", "radius": 15 }
    },
    {
      "id": "river_linear",
      "description": "Villaggio lungo fiume con ponte",
      "roads": [
        { "points": [{"x":-80,"z":-10},{"x":80,"z":-10}], "width": 4 }
      ],
      "river": { "path": [{"x":-100,"z":0},{"x":100,"z":0}], "width": 12 },
      "bridge": { "x": 0, "z": 0, "width": 5 }
    },
    {
      "id": "circular_plaza",
      "description": "Case disposte a cerchio attorno a piazza centrale",
      "plaza": { "shape": "circle", "radius": 20 },
      "lotPattern": "radial",
      "lotCount": 12
    },
    {
      "id": "hill_terraced",
      "description": "Edifici su terrazze di collina",
      "terrain": { "type": "hill", "height": 20, "centerElevation": true },
      "lotPattern": "terraced",
      "levels": 3
    }
  ]
}
```

---

## 🏗️ Generatore Hybrid (Blueprint + Blender)

### Mix di Tecniche per Massima Varietà

```json
{
  "name": "hamlet_mixed",
  "culturalTemplate": "medieval_european",
  "layoutPattern": "cross_roads",
  "seed": 42,
  
  "buildings": [
    // Hero building: Blender procedurale con spec completa
    {
      "type": "inn",
      "blenderSpec": "specs/inn_hero.json",
      "weight": 1,
      "placement": "plaza_facing"
    },
    
    // Cottage variati: Blender con random params
    {
      "type": "cottage",
      "blenderSpec": "specs/cottage_base.json",
      "variations": 3,
      "randomizeParams": {
        "volumes[0].w": [8, 12],
        "volumes[0].d": [6, 9],
        "windowsOverride[0].count": [2, 4],
        "styleOverride.roof": ["#8B7355", "#6B5A4E", "#7A6850"]
      },
      "weight": 4
    },
    
    // Modular kit buildings: pronti dal kit
    {
      "kitBuilding": "house_modular_a",
      "kitFamily": "kaykit-medieval",
      "weight": 2
    },
    
    // Blueprint ProBuilder: case semplici generate
    {
      "blueprint": "blueprints/simple_house.json",
      "weight": 3
    }
  ],
  
  "props": {
    "gardens": {
      "probability": 0.5,
      "perBuilding": true,
      "contents": ["fence_low", "flower_patch", "vegetable_plot"]
    },
    "streets": {
      "lanterns": { "every": 12, "alternate": true },
      "benches": { "probability": 0.3, "every": 20 },
      "wells": { "count": 2, "placement": "plaza_and_intersections" }
    }
  }
}
```

---

## 🎨 Color Palette Variation

Ogni villaggio ha **palette procedurale** basata su seed:

```csharp
// GDS.Village.ColorPalette.cs
public static Dictionary<string, Color> GeneratePalette(int seed, string culturalStyle) {
    Random.InitState(seed);
    
    var basePalette = CulturalPalettes[culturalStyle];
    var variation = new Dictionary<string, Color>();
    
    foreach(var kv in basePalette) {
        // Varia hue ±10°, saturation ±15%, value ±10%
        Color.RGBToHSV(kv.Value, out float h, out float s, out float v);
        h += Random.Range(-0.028f, 0.028f); // ±10° in 0-1 range
        s = Mathf.Clamp01(s + Random.Range(-0.15f, 0.15f));
        v = Mathf.Clamp01(v + Random.Range(-0.1f, 0.1f));
        variation[kv.Key] = Color.HSVToRGB(h, s, v);
    }
    
    return variation;
}
```

---

## 🏠 Dettagli Architettonici Randomizzati

### Per edificio Blender-generato:

```json
{
  "architecturalDetails": {
    "chimneys": { "probability": 0.7, "positionRandom": true },
    "shutters": { "probability": 0.5, "colorVariation": ["#8B4513", "#654321"] },
    "balconies": { "probability": 0.3, "floorPreference": [1, 2] },
    "awnings": { "doorProbability": 0.6, "windowProbability": 0.2 },
    "plinthHeight": { "min": 0.2, "max": 0.5 },
    "roofPitch": { "min": 0.5, "max": 0.7 },
    "beams": { "probability": 0.8, "style": "timber_frame" }
  }
}
```

---

## 🌳 Scatter Variation (natura e clutter)

```json
{
  "scatter": [
    // Alberi in anello esterno
    {
      "type": "trees",
      "species": ["oak", "pine", "birch"],
      "speciesWeights": [0.5, 0.3, 0.2],
      "count": { "min": 100, "max": 150 },
      "radius": 95,
      "minDist": 4,
      "avoidVillageRadius": 55,
      "clumping": { "enabled": true, "clumpSize": [3, 7], "clumpProbability": 0.4 }
    },
    
    // Rocce sparse
    {
      "type": "rocks",
      "variants": ["rock_small_a", "rock_small_b", "rock_medium"],
      "count": { "min": 30, "max": 50 },
      "scaleVariation": [0.8, 1.5],
      "rotationRandom": true
    },
    
    // Erba/fiori sui lotti vuoti
    {
      "type": "grass_patches",
      "count": { "min": 20, "max": 40 },
      "onlyOnLots": true,
      "avoidBuildings": 2.0
    }
  ]
}
```

---

## 🔧 API Utilizzo

### Genera villaggio con template
```csharp
// Usa template predefinito
GDS.Village.BuildFromTemplate("medieval_european", seed: 123);

// Usa template con override
var overrides = new VillageOverrides {
    layoutPattern = "river_linear",
    buildingCount = 15,
    colorPaletteSeed = 456
};
GDS.Village.BuildFromTemplate("nordic_viking", seed: 789, overrides);
```

### Genera villaggio random mix
```csharp
// Sistema sceglie random da tutti i template
GDS.Village.BuildRandom(seed: 999, culturalMix: true);

// Parametri procedurali puri
var config = new ProceduralVillageConfig {
    buildingCount = 12,
    layoutComplexity = 0.7f, // 0-1
    architecturalVariety = 0.8f, // 0-1
    culturalBlend = new[] { "medieval_european", "fantasy" }
};
GDS.Village.BuildProcedural(seed: 111, config);
```

---

## 📁 File Structure

```
game-developer/
└── templates/
    └── villages/
        ├── medieval_european.json
        ├── nordic_viking.json
        ├── asian_japanese.json
        ├── desert_middle_eastern.json
        ├── tropical_island.json
        ├── cyberpunk_slum.json
        ├── fantasy_elven.json
        ├── steampunk_industrial.json
        ├── _base_template.json (schema)
        └── README.md
```

---

## 🎯 Garantire Varietà

### Checklist Varietà
✅ **Layout:** Almeno 3 pattern diversi per cultural style  
✅ **Edifici:** 4+ varianti per ogni tipo (cottage, shop, etc.)  
✅ **Colori:** Palette seed-based con ±15% variation  
✅ **Props:** Randomized placement e rotation  
✅ **Scatter:** Clumping naturale per alberi, distribution uniforme per rocce  
✅ **Architettura:** Probability-based details (balconi, camini, shutters)  

### Anti-Repetition System
```csharp
// Evita edifici identici vicini
private static void EnsureVariety(List<Building> buildings) {
    for(int i = 0; i < buildings.Count; i++) {
        var current = buildings[i];
        var neighbors = GetNeighbors(current, radius: 20f);
        
        // Se il vicino è troppo simile, forza variazione
        foreach(var neighbor in neighbors) {
            if(AreTooSimilar(current, neighbor)) {
                ApplyForcedVariation(current);
            }
        }
    }
}

private static bool AreTooSimilar(Building a, Building b) {
    return a.type == b.type 
        && Vector3.Distance(a.dimensions, b.dimensions) < 2f
        && ColorDistance(a.roofColor, b.roofColor) < 0.15f;
}
```

---

## 🚀 Quick Examples

```bash
# Villaggio medievale classico
/game Medieval village with 15 houses, cross-roads layout

# Villaggio nordico lungo fiume
/game Nordic viking settlement along a river, 10 longhouses

# Villaggio fantasy elven multi-livello
/game Elven village in giant trees, treehouse platforms

# Mix cyberpunk + desert
/game Sci-fi desert outpost, container buildings and neon signs
```

L'agente detecta lo stile dal prompt e carica il template appropriato.

---

**Versione:** 1.0  
**Compatibile con:** GameDeveloperSkill v2.0+  
**Contribuisci:** Aggiungi nuovi template in `templates/villages/`!
