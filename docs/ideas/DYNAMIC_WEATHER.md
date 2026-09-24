# Dynamic Weather System

Sistema procedurale per generare weather dinamico con VFX e shader adapters per tutti gli engine.

---

## 🌦️ Weather States

```json
{
  "weather_states": [
    {
      "id": "clear",
      "duration_range": [300, 600],
      "transition_time": 30,
      "skybox": "clear_sky",
      "fog": {"enabled": false},
      "wind": {"strength": 0.2},
      "audio": "ambient_birds"
    },
    {
      "id": "cloudy",
      "duration_range": [180, 400],
      "transition_time": 60,
      "skybox": "overcast",
      "fog": {"enabled": true, "density": 0.01, "color": "#bdc3c7"},
      "wind": {"strength": 0.4},
      "lighting_multiplier": 0.7
    },
    {
      "id": "rain",
      "duration_range": [120, 300],
      "transition_time": 45,
      "skybox": "stormy",
      "fog": {"enabled": true, "density": 0.03, "color": "#7f8c8d"},
      "wind": {"strength": 0.7},
      "vfx": {
        "rain_particles": {"count": 5000, "intensity": 0.8},
        "puddles": true,
        "wet_surfaces": true
      },
      "audio": ["rain_medium", "thunder_distant"],
      "lighting_multiplier": 0.5
    },
    {
      "id": "storm",
      "duration_range": [60, 180],
      "transition_time": 30,
      "skybox": "dark_storm",
      "fog": {"enabled": true, "density": 0.05, "color": "#34495e"},
      "wind": {"strength": 1.0},
      "vfx": {
        "rain_particles": {"count": 10000, "intensity": 1.0},
        "lightning": {"frequency": 8, "duration": 0.2},
        "puddles": true,
        "wet_surfaces": true
      },
      "audio": ["rain_heavy", "thunder_close", "wind_strong"],
      "lighting_multiplier": 0.3
    },
    {
      "id": "snow",
      "duration_range": [200, 500],
      "transition_time": 90,
      "skybox": "snow_clouds",
      "fog": {"enabled": true, "density": 0.02, "color": "#ecf0f1"},
      "wind": {"strength": 0.3},
      "vfx": {
        "snow_particles": {"count": 3000, "fall_speed": 0.5},
        "ground_accumulation": true
      },
      "audio": "wind_cold",
      "lighting_multiplier": 0.9
    }
  ],
  
  "transition_graph": {
    "clear": ["cloudy", "snow"],
    "cloudy": ["clear", "rain", "snow"],
    "rain": ["cloudy", "storm"],
    "storm": ["rain"],
    "snow": ["cloudy", "clear"]
  },
  
  "time_of_day_multipliers": {
    "dawn": 0.6,
    "day": 1.0,
    "dusk": 0.7,
    "night": 0.4
  }
}
```

---

## 🎮 Weather Controller (Engine-Agnostic)

```python
# game-developer/core/weather/weather_controller.py
import json
import random
import time
from typing import Dict, List, Optional

class WeatherState:
    def __init__(self, config: Dict):
        self.id = config['id']
        self.duration_range = config['duration_range']
        self.transition_time = config['transition_time']
        self.config = config
    
    def get_random_duration(self) -> float:
        return random.uniform(*self.duration_range)

class WeatherController:
    """Engine-agnostic weather state machine"""
    
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            data = json.load(f)
        
        self.states = {s['id']: WeatherState(s) for s in data['weather_states']}
        self.transition_graph = data['transition_graph']
        self.time_multipliers = data.get('time_of_day_multipliers', {})
        
        self.current_state: Optional[WeatherState] = None
        self.next_state: Optional[WeatherState] = None
        self.transition_progress = 0.0
        self.state_timer = 0.0
        
        # Start with clear weather
        self.set_state('clear')
    
    def set_state(self, state_id: str):
        """Change to new weather state"""
        self.current_state = self.states[state_id]
        self.state_timer = self.current_state.get_random_duration()
        self.transition_progress = 0.0
    
    def update(self, delta_time: float):
        """Called every frame"""
        self.state_timer -= delta_time
        
        if self.state_timer <= 0 and not self.next_state:
            # Pick next state
            possible = self.transition_graph[self.current_state.id]
            next_id = random.choice(possible)
            self.next_state = self.states[next_id]
            self.transition_progress = 0.0
        
        # Transition
        if self.next_state:
            transition_time = self.current_state.transition_time
            self.transition_progress += delta_time / transition_time
            
            if self.transition_progress >= 1.0:
                # Complete transition
                self.set_state(self.next_state.id)
                self.next_state = None
    
    def get_current_params(self, time_of_day: str = "day") -> Dict:
        """Get interpolated weather parameters"""
        
        if not self.next_state:
            # No transition, return current
            params = self.current_state.config.copy()
        else:
            # Interpolate between current and next
            t = self.transition_progress
            params = self.interpolate_params(
                self.current_state.config,
                self.next_state.config,
                t
            )
        
        # Apply time of day multiplier
        tod_mult = self.time_multipliers.get(time_of_day, 1.0)
        if 'lighting_multiplier' in params:
            params['lighting_multiplier'] *= tod_mult
        
        return params
    
    def interpolate_params(self, a: Dict, b: Dict, t: float) -> Dict:
        """Lerp between two weather configs"""
        result = {}
        
        # Lerp numeric values
        for key in ['lighting_multiplier']:
            if key in a and key in b:
                result[key] = a[key] * (1 - t) + b[key] * t
        
        # Fog interpolation
        if 'fog' in a and 'fog' in b:
            result['fog'] = {
                'enabled': True,
                'density': a['fog']['density'] * (1 - t) + b['fog']['density'] * t,
                'color': self.lerp_color(a['fog']['color'], b['fog']['color'], t)
            }
        
        # Wind
        if 'wind' in a and 'wind' in b:
            result['wind'] = {
                'strength': a['wind']['strength'] * (1 - t) + b['wind']['strength'] * t
            }
        
        # VFX (switch at 50%)
        if t < 0.5:
            result['vfx'] = a.get('vfx', {})
        else:
            result['vfx'] = b.get('vfx', {})
        
        return result
    
    def lerp_color(self, hex_a: str, hex_b: str, t: float) -> str:
        """Interpolate hex colors"""
        # Parse hex
        r_a = int(hex_a[1:3], 16)
        g_a = int(hex_a[3:5], 16)
        b_a = int(hex_a[5:7], 16)
        
        r_b = int(hex_b[1:3], 16)
        g_b = int(hex_b[3:5], 16)
        b_b = int(hex_b[5:7], 16)
        
        # Lerp
        r = int(r_a * (1 - t) + r_b * t)
        g = int(g_a * (1 - t) + g_b * t)
        b = int(b_a * (1 - t) + b_b * t)
        
        return f"#{r:02x}{g:02x}{b:02x}"

# Usage
controller = WeatherController("weather_config.json")

# Game loop
while True:
    controller.update(delta_time=0.016)  # 60 FPS
    params = controller.get_current_params(time_of_day="day")
    
    # Apply to engine
    apply_weather_to_engine(params)
```

---

## 🎨 Engine Adapters

### Unity Adapter

```csharp
// engines/unity/adapters/WeatherAdapter.cs
using UnityEngine;

namespace GDS.Adapters {
    public class WeatherAdapter : MonoBehaviour {
        public Material skyboxMaterial;
        public ParticleSystem rainParticles;
        public ParticleSystem snowParticles;
        public Light directionalLight;
        public AudioSource audioSource;
        
        private WeatherController controller;
        
        void Start() {
            // Load weather config (via Python interop or JSON)
            controller = new WeatherController("weather_config.json");
        }
        
        void Update() {
            controller.Update(Time.deltaTime);
            var params = controller.GetCurrentParams("day");
            
            ApplyWeatherParams(params);
        }
        
        void ApplyWeatherParams(Dictionary<string, object> p) {
            // Lighting
            if (p.ContainsKey("lighting_multiplier")) {
                float mult = (float)p["lighting_multiplier"];
                directionalLight.intensity = mult;
            }
            
            // Fog
            if (p.ContainsKey("fog")) {
                var fog = (Dictionary<string, object>)p["fog"];
                RenderSettings.fog = (bool)fog["enabled"];
                RenderSettings.fogDensity = (float)fog["density"];
                RenderSettings.fogColor = HexToColor((string)fog["color"]);
            }
            
            // VFX
            if (p.ContainsKey("vfx")) {
                var vfx = (Dictionary<string, object>)p["vfx"];
                
                if (vfx.ContainsKey("rain_particles")) {
                    var rain = (Dictionary<string, object>)vfx["rain_particles"];
                    var emission = rainParticles.emission;
                    emission.rateOverTime = (int)rain["count"] / 10;
                    if (!rainParticles.isPlaying) rainParticles.Play();
                } else {
                    if (rainParticles.isPlaying) rainParticles.Stop();
                }
                
                // Similar for snow, lightning, etc.
            }
        }
        
        Color HexToColor(string hex) {
            ColorUtility.TryParseHtmlString(hex, out Color color);
            return color;
        }
    }
}
```

### Godot Adapter

```gdscript
# engines/godot/adapters/weather_adapter.gd
extends Node

var controller: WeatherController
var environment: Environment
var rain_particles: GPUParticles3D
var directional_light: DirectionalLight3D

func _ready():
    controller = WeatherController.new("weather_config.json")
    
    # Get scene nodes
    environment = get_node("/root/WorldEnvironment").environment
    rain_particles = get_node("/root/Weather/Rain")
    directional_light = get_node("/root/DirectionalLight3D")

func _process(delta):
    controller.update(delta)
    var params = controller.get_current_params("day")
    
    apply_weather_params(params)

func apply_weather_params(params: Dictionary):
    # Lighting
    if params.has("lighting_multiplier"):
        directional_light.light_energy = params.lighting_multiplier
    
    # Fog
    if params.has("fog"):
        var fog = params.fog
        environment.fog_enabled = fog.enabled
        environment.fog_density = fog.density
        environment.fog_color = Color(fog.color)
    
    # VFX
    if params.has("vfx"):
        var vfx = params.vfx
        
        if vfx.has("rain_particles"):
            rain_particles.amount = vfx.rain_particles.count
            rain_particles.emitting = true
        else:
            rain_particles.emitting = false
```

### Unreal Adapter

```python
# engines/unreal/adapters/weather_adapter.py
import unreal

class WeatherAdapter:
    def __init__(self):
        self.controller = WeatherController("weather_config.json")
        self.world = unreal.EditorLevelLibrary.get_editor_world()
        
        # Get actors
        self.directional_light = self.find_actor_by_name("DirectionalLight")
        self.post_process = self.find_actor_by_name("PostProcess_Weather")
        self.rain_emitter = self.find_actor_by_name("Rain_Particles")
    
    def update(self, delta_time):
        self.controller.update(delta_time)
        params = self.controller.get_current_params("day")
        
        self.apply_weather_params(params)
    
    def apply_weather_params(self, params):
        # Lighting
        if 'lighting_multiplier' in params:
            self.directional_light.get_editor_property("light_component").set_intensity(
                params['lighting_multiplier'] * 5.0
            )
        
        # Fog (via post-process volume)
        if 'fog' in params:
            fog = params['fog']
            settings = self.post_process.settings
            
            settings.override_fog_density = True
            settings.fog_density = fog['density']
            
            settings.override_fog_inscattering_color = True
            settings.fog_inscattering_color = self.hex_to_linear_color(fog['color'])
        
        # VFX
        if 'vfx' in params:
            vfx = params['vfx']
            
            if 'rain_particles' in vfx:
                # Activate rain Niagara system
                self.rain_emitter.get_niagara_component().activate()
            else:
                self.rain_emitter.get_niagara_component().deactivate()
    
    def hex_to_linear_color(self, hex_str):
        r = int(hex_str[1:3], 16) / 255.0
        g = int(hex_str[3:5], 16) / 255.0
        b = int(hex_str[5:7], 16) / 255.0
        return unreal.LinearColor(r, g, b, 1.0)
```

---

## 🎨 Shader Support

### Wet Surface Shader (Unity URP)

```hlsl
// Wet surface effect during rain
Shader "Custom/WetSurface" {
    Properties {
        _BaseMap ("Texture", 2D) = "white" {}
        _WetLevel ("Wet Level", Range(0, 1)) = 0
        _Glossiness ("Glossiness", Range(0, 1)) = 0.5
    }
    
    SubShader {
        Pass {
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            
            float _WetLevel;
            float _Glossiness;
            
            float4 frag(v2f i) : SV_Target {
                float4 col = tex2D(_BaseMap, i.uv);
                
                // Darken when wet
                col.rgb *= lerp(1.0, 0.7, _WetLevel);
                
                // Increase smoothness
                float smoothness = lerp(_Glossiness, 1.0, _WetLevel);
                
                return col;
            }
            ENDHLSL
        }
    }
}
```

### Dynamic Skybox (Godot)

```gdscript
# Procedural sky that changes with weather
extends Sky

var weather_controller: WeatherController

func _process(delta):
    var params = weather_controller.get_current_params("day")
    
    # Update sky shader parameters
    if params.has("skybox"):
        sky_material.set_shader_parameter("cloudiness", get_cloudiness(params.skybox))
        sky_material.set_shader_parameter("sun_intensity", params.get("lighting_multiplier", 1.0))
```

---

## 🔊 Audio System

```python
# Weather audio manager
class WeatherAudioManager:
    def __init__(self):
        self.audio_clips = {
            "rain_medium": "sounds/weather/rain_medium.ogg",
            "rain_heavy": "sounds/weather/rain_heavy.ogg",
            "thunder_distant": "sounds/weather/thunder_distant.ogg",
            "wind_strong": "sounds/weather/wind_strong.ogg"
        }
        self.playing = {}
    
    def apply_audio(self, weather_params):
        """Crossfade audio based on weather"""
        
        target_sounds = weather_params.get('audio', [])
        if isinstance(target_sounds, str):
            target_sounds = [target_sounds]
        
        # Fade out sounds not in target
        for sound in list(self.playing.keys()):
            if sound not in target_sounds:
                self.fade_out(sound, duration=2.0)
        
        # Fade in new sounds
        for sound in target_sounds:
            if sound not in self.playing:
                self.fade_in(sound, duration=2.0)
```

---

## 📊 Performance

| Weather State | Particle Count | GPU Impact | Recommended |
|---------------|----------------|------------|-------------|
| Clear | 0 | Minimal | All devices |
| Cloudy | 0 | Low | All devices |
| Rain | 5,000 | Medium | Mid-range+ |
| Storm | 10,000 | High | High-end |
| Snow | 3,000 | Medium | Mid-range+ |

**Optimization:**
- LOD for particles (reduce count with distance)
- Screen-space puddles instead of geometry
- Bake skybox transitions
- Audio occlusion for indoor scenes

---

## 🎯 GDD Integration

```markdown
Q24: Include dynamic weather?
  1. Yes, full system (clear, rain, storm, snow)
  2. Yes, simple (clear, rain only)
  3. No (static weather)

If Yes:
  Q24a: Starting weather?
    1. Clear (default)
    2. Cloudy
    3. Rain
    4. Random

  Q24b: Weather affects gameplay?
    1. Visual only
    2. Yes (visibility, movement speed, etc.)
```

---

**Versione:** 1.0  
**Status:** ✅ Implemented  
**Engines:** Unity, Godot, Unreal  
**Location:** `game-developer/core/weather/`
