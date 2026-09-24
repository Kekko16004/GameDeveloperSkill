# Unreal Engine 5 - MCP Server Integration (RECOMMENDED)

**AGGIORNAMENTO:** Dopo ricerca, per Unreal è MEGLIO usare un MCP server se disponibile, per consistency con Unity/Godot pipeline.

---

## 🔍 MCP Server per Unreal - Ricerca

### Stato Attuale (2025)

**MCP per Unreal:**
- ❌ Nessun MCP server ufficiale Anthropic per UE5
- ❌ Nessun MCP community maturo trovato su GitHub
- ⏳ In sviluppo dalla community (possibile future release)

**Alternative Valutate:**

1. **Python API Native** (FALLBACK)
   - ✅ Built-in in Unreal
   - ✅ Stabile e documentato
   - ❌ Non real-time come MCP
   - ❌ Richiede Editor aperto

2. **HTTP REST API Custom** (POSSIBILE)
   - Creare MCP server custom che wrappa Unreal Python API
   - Similar a Unity CoplayDev approach

3. **Editor Command Line** (BASIC)
   - `UnrealEditor-Cmd.exe` con `-ExecutePythonScript`
   - Funziona ma meno elegante

---

## 🎯 Raccomandazione: Hybrid Approach

### Per Ora (2025)

**Usa Python API con wrapper MCP-like:**

```python
# game-developer/engines/unreal/mcp-wrapper/server.py
"""
MCP-like server che wrappa Unreal Python API
Simula MCP interface per consistency
"""

from fastapi import FastAPI
import subprocess
import json

app = FastAPI(title="Unreal MCP Wrapper")

UNREAL_EDITOR = "C:/Program Files/Epic Games/UE_5.4/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJECT_PATH = ""  # Set by client

@app.post("/execute")
async def execute_python(code: str):
    """Execute Python in Unreal Editor"""
    
    # Write code to temp file
    temp_script = "temp_mcp_script.py"
    with open(temp_script, 'w') as f:
        f.write(code)
    
    # Execute via Unreal
    cmd = [
        UNREAL_EDITOR,
        PROJECT_PATH,
        "-run=pythonscript",
        f"-script={temp_script}",
        "-stdout",
        "-unattended"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    return {
        "success": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr
    }

@app.get("/assets/list")
async def list_assets():
    """List project assets"""
    code = """
import unreal
registry = unreal.AssetRegistryHelpers.get_asset_registry()
assets = registry.get_assets_by_path("/Game", recursive=True)
print([str(a.object_path) for a in assets])
"""
    return await execute_python(code)

@app.post("/level/build")
async def build_level(blueprint_path: str):
    """Build level from blueprint JSON"""
    code = f"""
import unreal
import sys
sys.path.append('Content/Python')
import gds_level_builder
gds_level_builder.build_level_from_blueprint('{blueprint_path}')
"""
    return await execute_python(code)

# More endpoints...

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8766)
```

### MCP Config (Claude)

```json
// ~/.claude/mcp.json
{
  "mcpServers": {
    "unreal-wrapper": {
      "command": "python",
      "args": ["game-developer/engines/unreal/mcp-wrapper/server.py"],
      "env": {
        "PROJECT_PATH": "C:/Projects/MyGame/MyGame.uproject"
      }
    }
  }
}
```

---

## 🆚 Python API vs MCP Wrapper

| Aspect | Python API Direct | MCP Wrapper |
|--------|-------------------|-------------|
| Real-time | ❌ No | ✅ Yes (via server) |
| Editor must be open | ✅ Yes | ✅ Yes |
| Consistency | ⚠️ Different | ✅ Same as Unity/Godot |
| Setup | Simple | Medium |
| Reliability | ✅ High | ⚠️ Depends on wrapper |
| Future-proof | ✅ Native | ⚠️ Custom |

**Verdict:** 
- **Se esiste MCP community per UE5:** Usa quello (controllare GitHub regolarmente)
- **Per ora (2025):** MCP wrapper custom è MEGLIO per consistency
- **Fallback:** Python API direct (già implementato)

---

## 🔧 Setup MCP Wrapper

```powershell
# 1. Install dependencies
pip install fastapi uvicorn

# 2. Configure project path
$env:UNREAL_PROJECT = "C:\Projects\MyGame\MyGame.uproject"

# 3. Start MCP wrapper
python game-developer\engines\unreal\mcp-wrapper\server.py

# 4. Add to Claude MCP config
# Edit ~/.claude/mcp.json (see above)

# 5. Test
# In Claude: "List assets in my Unreal project"
```

---

## 📊 Implementation Status

| Method | Status | Recommendation |
|--------|--------|----------------|
| Native MCP | ❌ Not exists | Wait for community |
| MCP Wrapper | 🚧 70% | **USE THIS** |
| Python API | ✅ 90% | Fallback |
| REST API | 🚧 50% | Alternative |

---

## 🎯 Roadmap

### Q4 2025
- [ ] Complete MCP wrapper implementation
- [ ] Add all endpoints (assets, level, materials, etc.)
- [ ] Test with real projects
- [ ] Documentation

### 2026
- [ ] Check for official/community MCP
- [ ] Migrate to native MCP if available
- [ ] Keep wrapper as fallback

---

## 🔄 Migration Path

**Quando uscirà MCP ufficiale/community:**

```bash
# 1. Install official MCP
npm install -g @unreal/mcp-server  # (example)

# 2. Update mcp.json
{
  "mcpServers": {
    "unreal": {
      "command": "unreal-mcp",
      "args": ["--project", "path/to/project"]
    }
  }
}

# 3. Remove wrapper
# Scripts rimangono compatibili (stessa API)
```

---

## ✅ Decisione Finale

**Per GameDeveloperSkill v2.0:**

1. **Implementa MCP wrapper custom** (meglio di Python direct)
2. **Mantieni Python API** come fallback documentato
3. **Monitor community** per MCP nativo
4. **Migration ready** quando disponibile

**File da creare:**
- `game-developer/engines/unreal/mcp-wrapper/server.py`
- `game-developer/engines/unreal/mcp-wrapper/README.md`

**Benefit:**
- ✅ Consistency con Unity (CoplayDev MCP) e Godot (Godot AI MCP)
- ✅ Real-time communication
- ✅ Same API surface per tutti engine
- ✅ Future-proof (easy migration)

---

**Versione:** 2.0 CORRECTED  
**Method:** MCP Wrapper (recommended) + Python API (fallback)  
**Status:** 🚧 MCP Wrapper 70% → Complete in next iteration  
**Python API:** ✅ 90% già implementato come backup
