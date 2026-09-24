# Sistema Multi-Stile

GameDeveloperSkill supporta diversi stili visuali oltre al low poly default.

---

## 🎨 Stili Disponibili

### 1. **Low Poly** (Default)
- **Kit families:** Kenney, KayKit, Quaternius Standard
- **Poly count:** 100-500 tris/object
- **Materials:** Flat colors, simple lighting
- **Shaders:** URP/Lit or URP/Simple Lit
- **Gen3D:** Meshy con prompt "low poly, flat colors"
- **Best for:** Stylized, performance-critical, mobile

**Lookdev preset:** `stylized-day`, `stylized-sunset`, `pastel-bright`

---

### 2. **Realistic-Stylized**
- **Asset sources:** Poly Haven models (decimated), MegaScan (se disponibile), Sketchfab PBR
- **Poly count:** 2k-10k tris/object
- **Materials:** PBR con normal/roughness/metallic maps
- **Shaders:** URP/Lit con normal mapping
- **Gen3D:** Hyper3D, Tripo (PBR output)
- **Best for:** AAA-style indie, semi-realistic environments

**Lookdev preset:** `realistic-day`, `sunset-warm`, `night-moon`

**Packages extra:**
```json
{
  "renderingPackages": [
    "com.unity.render-pipelines.universal",
    "SSAO", "Screen Space Reflections"
  ]
}
```

---

### 3. **Toon/Cel-Shaded**
- **Kit families:** KayKit, custom toon assets
- **Poly count:** 500-2k tris/object
- **Materials:** Toon ramp shaders, outline
- **Shaders:** 
  - [Delt06 URP Toon Shader](https://github.com/Delt06/urp-toon-shader)
  - [CristianQiu URP Outline](https://github.com/CristianQiu/Unity-URP-Outline)
- **Gen3D:** Meshy con prompt "anime style, cel shaded"
- **Best for:** Anime-inspired, cartoony games

**Lookdev preset:** `toon-bright`, `toon-sunset`

**Auto-install packages:**
```bash
# Aggiunto automaticamente se GDD specifica "toon"
https://github.com/Delt06/urp-toon-shader.git?path=Packages/com.deltation.toon-shader
https://github.com/CristianQiu/Unity-URP-Outline.git
```

---

### 4. **Voxel**
- **Asset sources:** MagicaVoxel exports, custom voxel generator
- **Poly count:** Variabile (1 voxel = 1 cube o optimized mesh)
- **Materials:** Blocky texture atlas
- **Shaders:** URP/Lit, vertex colors
- **Gen3D:** VoxelAI MCP, Modly con "voxel art" prompt
- **Best for:** Minecraft-like, retro 3D

**Lookdev preset:** `voxel-bright`, `voxel-ambient`

**Integration:** Richiede VoxelAI MCP configurato.

---

### 5. **Hand-Painted**
- **Asset sources:** Sketchfab hand-painted, custom
- **Poly count:** 1k-5k tris/object
- **Materials:** Hand-painted diffuse textures, minimal specular
- **Shaders:** URP/Simple Lit (no PBR)
- **Gen3D:** Meshy con prompt "hand-painted texture, stylized, painterly"
- **Best for:** Fantasy RPG, storybook aesthetics

**Lookdev preset:** `fantasy-warm`, `painterly-soft`

---

### 6. **Sci-Fi/Cyberpunk**
- **Kit families:** Kenney Modular Space, KayKit Sci-Fi, custom
- **Poly count:** 1k-8k tris/object
- **Materials:** Emissive panels, metallic surfaces, neon
- **Shaders:** URP/Lit + Emission
- **Gen3D:** Tripo/Hyper3D con "sci-fi, cyberpunk, neon"
- **Best for:** Space stations, futuristic cities

**Lookdev preset:** `scifi-cold`, `cyberpunk-neon`

**VFX:** Volumetric lights (CristianQiu URP Volumetric Light)

---

### 7. **Pixel-Art 3D**
- **Asset sources:** Custom low-res textures su geometria semplice
- **Poly count:** 50-200 tris/object (super low poly)
- **Materials:** Point-filtered textures (no bilinear), palette 16-64 colors
- **Shaders:** Custom unlit shader con texture filtering disabled
- **Gen3D:** Non raccomandato (usa sprites → extrude)
- **Best for:** Retro PSX style, demake aesthetics

**Lookdev preset:** `retro-psx`, `pixel-art-bright`

---

### 8. **Realistic (High-End)**
- **Asset sources:** MegaScan OBBLIGATORIO, Poly Haven PBR, Sketchfab scans
- **Poly count:** 10k-50k tris/object (LOD system needed)
- **Materials:** Full PBR (albedo, normal, roughness, metallic, AO)
- **Shaders:** URP/Lit con tutte le features
- **Gen3D:** Hyper3D, Rodin (alta qualità)
- **Best for:** Portfolio pieces, cinematic demos (NON mobile)

**Lookdev preset:** `realistic-exterior`, `realistic-interior-hdri`

**Requirements:**
- Unity 6 con SSGI/SSAO
- MegaScan library access
- Git LFS per texture grandi

---

## 📋 Come Scegliere lo Stile nel GDD

Durante l'intervista GDD (Q4), l'agente chiede:

```
Q4: Visual style and art direction?
Options:
1. Low Poly (default - Kenney/KayKit, performance)
2. Realistic-Stylized (PBR, Poly Haven + decimation)
3. Toon/Cel-Shaded (outline + ramp shader)
4. Voxel (blocky, MagicaVoxel-like)
5. Hand-Painted (fantasy textures)
6. Sci-Fi/Cyberpunk (neon, metallic)
7. Pixel-Art 3D (PSX retro)
8. Realistic High-End (MegaScan required)
```

**Risposta esempio:**
```
Style: 3 (Toon)
Palette: pastels, high saturation, outline thickness 2px
```

---

## ⚙️ Implementazione Tecnica

### Style Config Schema

Ogni stile ha un file JSON in `styles/presets/<style>.json`:

```json
{
  "id": "toon",
  "label": "Toon/Cel-Shaded",
  "polyRange": [500, 2000],
  "preferredKits": ["kaykit", "kenney-cartoon"],
  "shaderPackages": [
    "https://github.com/Delt06/urp-toon-shader.git?path=Packages/com.deltation.toon-shader",
    "https://github.com/CristianQiu/Unity-URP-Outline.git"
  ],
  "lookdevPresets": ["toon-bright", "toon-sunset"],
  "materialSettings": {
    "useToonRamp": true,
    "outlineEnabled": true,
    "outlineThickness": 0.02,
    "smoothness": 0.1
  },
  "gen3dPromptSuffix": "anime style, cel shaded, clean outlines, flat colors",
  "assetSources": {
    "priority": ["kaykit", "kenney", "polypizza-stylized", "meshy"],
    "polyHavenDecimate": true,
    "targetTris": 1500
  },
  "postProcessing": {
    "bloom": { "intensity": 0.3, "threshold": 1.1 },
    "colorAdjustments": { "saturation": 15 },
    "vignette": { "intensity": 0.2 }
  }
}
```

### Loading Style in Pipeline

```csharp
// GDS.StyleManager.cs
public static void ApplyStyle(string styleId) {
    var config = LoadStyleConfig(styleId);
    
    // 1. Install shader packages
    foreach(var pkg in config.shaderPackages) {
        PackageManager.Add(pkg);
    }
    
    // 2. Setup lookdev
    LookDev.Apply(config.lookdevPresets[0]);
    
    // 3. Configure material settings
    foreach(var mat in GetAllMaterials()) {
        if(config.materialSettings.useToonRamp) {
            mat.shader = Shader.Find("Toon/Lit");
        }
        if(config.materialSettings.outlineEnabled) {
            mat.SetFloat("_OutlineWidth", config.materialSettings.outlineThickness);
        }
    }
    
    // 4. Apply post-processing
    ApplyPostProcessing(config.postProcessing);
}
```

---

## 🔧 Asset Adaptation per Stile

### Poly Haven Decimation (per low poly/toon)
```python
# In Blender sanitize block
if style in ["low_poly", "toon", "voxel"]:
    if tris > target_tris:
        decimate_ratio = target_tris / tris
        bpy.ops.object.modifier_add(type='DECIMATE')
        bpy.context.object.modifiers["Decimate"].ratio = decimate_ratio
        bpy.ops.object.modifier_apply(modifier="Decimate")
```

### Material Conversion
```csharp
// Realistic → Toon conversion
public static void ConvertMaterialToToon(Material mat) {
    var albedo = mat.GetTexture("_BaseMap");
    mat.shader = Shader.Find("Toon/Lit");
    mat.SetTexture("_BaseMap", albedo);
    mat.SetFloat("_Smoothness", 0.1f);
    mat.EnableKeyword("_NORMALMAP_OFF");
}
```

---

## 🎯 Style Coherence Check

Prima di ogni import, `GDS.StyleCoherence.Check()` verifica:

✅ Poly count nel range dello stile  
✅ Materials compatibili con shader stack  
✅ Kit family matches preferred list  
✅ Textures resolution appropriate (512px per low poly, 2k+ per realistic)  

**Fail = warning + auto-adapt o block import.**

---

## 📦 MegaScan Integration (Realistic style)

### Setup Quixel Bridge
```json
// game-developer/config.json
{
  "paths": {
    "quixelBridge": "C:\\Program Files\\Quixel\\Bridge",
    "megaScanLibrary": "C:\\Users\\YOURNAME\\Documents\\Megascans Library"
  },
  "art": {
    "megaScanEnabled": true
  }
}
```

### Workflow
1. Agent genera lista asset needed (rocks, ground, foliage)
2. Cerca in local MegaScan library (`megaScanLibrary/3d/`)
3. Se non trovato: skip (oppure prompt user to download via Bridge)
4. Import con LOD groups automatici
5. Material setup per URP

### Auto-LOD System
```csharp
// Per MegaScan assets
public static void SetupLODGroup(GameObject obj) {
    var lods = obj.GetComponentsInChildren<MeshRenderer>()
        .Where(mr => mr.name.Contains("LOD"))
        .OrderBy(mr => mr.name)
        .ToArray();
    
    if(lods.Length < 2) return; // No LODs
    
    var lodGroup = obj.AddComponent<LODGroup>();
    var lodArray = new LOD[lods.Length];
    for(int i = 0; i < lods.Length; i++) {
        float dist = 1f / (i + 1);
        lodArray[i] = new LOD(dist, new Renderer[] { lods[i] });
    }
    lodGroup.SetLODs(lodArray);
}
```

---

## 🚀 Quick Style Templates

```bash
# Crea gioco low poly
/game Create a dungeon crawler, low poly style

# Crea gioco toon
/game Create a fantasy RPG, toon cel-shaded anime style

# Crea gioco realistic con MegaScan
/game Create a survival horror, realistic style with MegaScan assets
```

L'agente rileva lo stile dal prompt e configura tutto automaticamente.

---

## 🆕 Coming Soon

- **Watercolor style** (NPR shaders)
- **Claymation** (stop-motion look)
- **Synthwave** (neon + retro + grid floors)
- **Isometric pixel** (2.5D orthographic)
- **VR-optimized** (mobile VR poly budget + instancing)

---

**Versione:** 1.0  
**Autore:** GameDeveloperSkill Team  
**Contribuisci:** Crea un preset in `styles/presets/` e PR!
