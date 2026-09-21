# Blender MCP — import + sanitize, never model from code

Rooms = ProBuilder. Modular look = Kenney / KayKit / Quaternius Standard. Missing prop = **Poly Pizza** via native MCP tools. Blender is a live importer, not a Python modeller.

> [!IMPORTANT]
> **USA TUTTI I TOOL NATIVI DI BLENDER — MAI FOSSILIZZARSI SU `execute_blender_code`**
> Gli agenti tendono a fermarsi o bloccarsi in loop tentando di eseguire script Python complessi con `execute_blender_code`.
> **Non farlo**: sfrutta la suite completa di tool nativi:
> - Cerca modelli con `search_polypizza_models`
> - Scarica e normalizza la scala con `download_polypizza_model`
> - Leggi gerarchia e vertici con `get_scene_info` e `get_object_info`
> - Cattura la prova visiva con `get_viewport_screenshot`
> - Esporta con `export_scene`
> [!CAUTION]
> **REGOLA ZERO ASSOLUTA: RESET E PULIZIA SCENA PRE-IMPORT (OBBLIGATORIO)**
> Prima di qualsiasi operazione di ricerca, download o modellazione su Blender, controlla lo stato della scena (`get_scene_info`).
> Se sono presenti oggetti residui da task precedenti, **ESEGUI IMMEDIATAMENTE IL RESET TOTALE DELLA SCENA**:
> ```python
> import bpy
> for obj in list(bpy.data.objects): bpy.data.objects.remove(obj, do_unlink=True)
> for mesh in list(bpy.data.meshes): bpy.data.meshes.remove(mesh, do_unlink=True)
> for mat in list(bpy.data.materials): bpy.data.materials.remove(mat, do_unlink=True)
> ```
> È SEVERAMENTE VIETATO importare o comporre un nuovo modello in una scena che contiene già elementi. Causa l'unione accidentale di asset diversi in un unico file GLB ("modelli mostro").

Live addon (this machine): protocol 7, Blender 5.1, Poly Pizza **enabled**. Sketchfab: enable with a free API token (CC0 filter) — allowed for hero props. Poly Haven models/HDRI: no key, allowed (HDRI only as skybox via `GDS.LookDev.Apply(..., hdriPath)`). Hyper3D / Hunyuan: **only if `GDD.md gen3d:` says so** ([gen3d.md](gen3d.md)); otherwise keep them off.

## Client config (stdio uvx — NOT http://localhost:9876/mcp)

Two hops:

1. Kilo launches **`uvx blender-mcp`** over **stdio** (MCP JSON-RPC). That process is the tool list you see (`search_polypizza_models`, `export_scene`, …).
2. The addon in Blender listens on **raw TCP** `localhost:9876` (JSON socket). Not HTTP. There is no `/mcp` path.

```json
"blender": {
  "command": "cmd",
  "args": ["/c", "uvx", "blender-mcp"],
  "env": { "BLENDER_HOST": "localhost", "BLENDER_PORT": "9876" }
}
```

Windows GUI clients often miss `uvx` on PATH → wrap with `cmd /c`.

**Do not** set `"serverUrl": "http://localhost:9876/mcp"`. That URL is for other stacks (Blender Lab HTTP ~8400, or Streamable HTTP addons). Against ahujasid/MCP-for-Blender it 404s or hangs: 9876 is not an HTTP server.

If tools vanish: Blender open → N → MCP for Blender → Start MCP Server → restart the Kilo MCP session. Do not switch to HTTP.

## Catalogo Completo dei 31 Tool Nativo Blender MCP

> **Parametro fondamentale `user_prompt`**: quasi tutti i tool richiedono `user_prompt` (la frase esatta dell'utente passata verbatim senza parafrasi). Passa sempre l'intento per collegare l'azione al goal.

### 1. Controllo Stato, Telemetria & Traiettoria
| Tool | Scopo | Parametri Chiave |
|---|---|---|
| `get_addon_status` | Verifica versione addon e compatibilità con MCP server. Mostra consenso telemetria. | Nessuno |
| `disable_telemetry` | Disattiva immediatamente raccolta dati/prompt/screenshot su Blender. | Nessuno |
| `record_trajectory_feedback` | Registra feedback su uno step (accept, reject, undo, correction). | `feedback`, `correction_text`, `step_index`, `user_prompt` |

### 2. Ispezione Scena & Viewport (SENZA SCRIVERE SCRIPT)
*Non scrivere codice Python solo per sapere quanti oggetti ci sono o dove si trova il pivot.*
| Tool | Scopo | Parametri Chiave |
|---|---|---|
| `get_scene_info` | Ottiene elenco dettagliato oggetti, gerarchia e stato della scena attiva. | `user_prompt` (richiesto) |
| `get_object_info` | Restituisce dimensioni esatte, bounding box, origine e vertici dell'oggetto. | `object_name`, `user_prompt` |
| `get_viewport_screenshot` | Cattura screenshot del viewport 3D come Image. Indispensabile per le prove visive gate. | `max_size` (default 800), `user_prompt` |

### 3. Ricerca & Download Poly Pizza (Bassa Poligonazione CC0)
*Fonte primaria per riempire i buchi dei kit modulari con prop low-poly puliti.*
| Tool | Scopo | Parametri Chiave |
|---|---|---|
| `get_polypizza_status` | Controlla se l'integrazione Poly Pizza è abilitata nell'addon. | Nessuno |
| `search_polypizza_models` | Cerca modelli su Poly Pizza con filtri su licenza e categoria. | `query`, `category`, `licence` ("CC0" o "CC-BY"), `limit` (max 32), `user_prompt` |
| `download_polypizza_model` | Scarica e importa il modello impostando la scala Geometra in metri. | `model_id`, `normalize_size=True`, `target_size` (metri), `user_prompt` |

### 4. Texture PBR & Materiali Poly Haven
*Per applicare materiali fotorealistici/stilizzati PBR senza toccare gli shader a mano.*
| Tool | Scopo | Parametri Chiave |
|---|---|---|
| `get_polyhaven_status` | Controlla disponibilità integrazione Poly Haven. | Nessuno |
| `get_polyhaven_categories` | Elenca categorie disponibili (textures, models, hdris). | `asset_type`, `user_prompt` |
| `search_polyhaven_assets` | Cerca texture/modelli filtrati per categoria. | `asset_type`, `categories`, `user_prompt` |
| `download_polyhaven_asset` | Scarica l'asset alla risoluzione desiderata (1k, 2k). | `asset_id`, `asset_type`, `resolution`, `file_format`, `user_prompt` |
| `set_texture` | Applica la texture scaricata a un oggetto specifico della scena. | `object_name`, `texture_id`, `user_prompt` |

### 5. Ricerca & Download Sketchfab
*Per scaricare modelli CC0/CC-BY da Sketchfab con anteprima visiva.*
| Tool | Scopo | Parametri Chiave |
|---|---|---|
| `get_sketchfab_status` | Controlla disponibilità integrazione Sketchfab. | Nessuno |
| `search_sketchfab_models` | Cerca modelli scaricabili per query e categoria. | `query`, `categories`, `count`, `downloadable=True`, `user_prompt` |
| `get_sketchfab_model_preview` | Ottiene la miniatura (thumbnail) del modello prima del download. | `uid`, `user_prompt` |
| `download_sketchfab_model` | Scarica e importa il modello scalato a dimensione metrica reale. | `uid`, `target_size` (obbligatorio in metri), `user_prompt` |

### 6. Generatori AI 3D (Hyper3D Rodin & Tencent Hunyuan3D)
*Strumenti generativi cloud/locali supportati direttamente dall'addon.*
| Tool | Scopo | Parametri Chiave |
|---|---|---|
| `get_hyper3d_status` | Verifica disponibilità Hyper3D Rodin. | Nessuno |
| `generate_hyper3d_model_via_text` | Genera modello 3D con materiali via prompt testuale inglese. | `text_prompt`, `bbox_condition`, `user_prompt` |
| `generate_hyper3d_model_via_images` | Genera modello 3D da immagini reference (path o URL). | `input_image_paths` / `input_image_urls`, `user_prompt` |
| `poll_rodin_job_status` | Polling asincrono dello stato di generazione Rodin. | `subscription_key` o `request_id` |
| `import_generated_asset` | Importa nella scena l'asset generato da Rodin. | `name`, `task_uuid` o `request_id` |
| `get_hunyuan3d_status` | Verifica disponibilità Tencent Hunyuan3D. | Nessuno |
| `generate_hunyuan3d_model` | Genera asset 3D PBR da testo o immagine reference. | `text_prompt`, `input_image_url`, `user_prompt` |
| `poll_hunyuan_job_status` | Polling dello stato del job Hunyuan3D (ritorna URL GLB). | `job_id` |
| `import_generated_asset_hunyuan` | Importa nella scena l'asset generato da Hunyuan3D. | `name`, `zip_file_url` (preferisci .glb) |

### 7. Esportazione File di Gioco (GLB / FBX)
*Il tool dedicato per salvare gli asset finiti su disco per Unity/Godot.*
| Tool | Scopo | Parametri Chiave |
|---|---|---|
| `export_scene` | Esporta l'intera scena o solo gli oggetti specificati in GLB/FBX. | `filepath` (assoluto), `format` ("glb"/"fbx"), `object_names` (array), `apply_modifiers=True`, `user_prompt` |

### 8. Introspezione Shader & API Blender
*Per evitare di indovinare nomi di nodi o socket negli shader.*
| Tool | Scopo | Parametri Chiave |
|---|---|---|
| `describe_node_type` | Ispeziona input/output, socket e tipi di un nodo senza toccare la scena. | `bl_idname` (es. "ShaderNodeBsdfPrincipled"), `property_overrides`, `user_prompt` |
| `bpy_api_lookup` | Consulta firme, tipi di parametri ed enum validi per operatori e tipi RNA. | `query` (es. "bpy.ops.mesh.primitive_cube_add"), `user_prompt` |

### 9. Esecuzione Codice Python Arbitrario (USO LIMITATO)
| Tool | Scopo | Restrizioni |
|---|---|---|
| `execute_blender_code` | Esegue codice Python in Blender. | **Ammesso solo per il micro-blocco di sanitize finale**: rimozione luci/camere residue e reset pivot a terra ($Y=0$). **Vietato** usarlo per modellare da zero, cercare o esportare. |

## Casistiche Anti-Panico & Decision Tree per l'Agente

Un modello LLM non deve applicare rigidità da compilatore a elementi artistici 3D. Segui questo albero decisionale:

### 1. Tolleranza Dimensionale (Non fare mai FAIL per proporzioni differenti)
- **Situazione**: Il GDD stima `prop_plague_well` a $1.2\times 1.2\times 0.9\text{ m}$. Poly Pizza o Sketchfab restituiscono un pozzo con tetto alto da $0.64\times 0.96\times 1.20\text{ m}$.
- **Comportamento ERRATO**: Fare FAIL o dire che il modello è incompatibile.
- **Comportamento CORRETTO**: Le dimensioni del GDD sono stime di massima. Usa `normalize_size=True` sull'asse principale (`target_size=1.2`). Centra il pivot alla base e procedi. Una variazione del $\pm 30\%$ nell'ingombro di un prop è normale e desiderabile per lo stile artistico.

### 2. Gestione Gerarchie (Empty, RootNode, Multi-Part)
- Molti asset importati contengono un `RootNode` (EMPTY) o più mesh figlie.
- **Procedura standard nello snippet di sanitize**:
  ```python
  if obj.parent:
      matrix = obj.matrix_world.copy()
      obj.parent = None
      obj.matrix_world = matrix
  # Rimuovi empty residui
  for o in list(bpy.data.objects):
      if o.type == 'EMPTY': bpy.data.objects.remove(o, do_unlink=True)
  ```

### 3. Quando il Modello non Esiste Online o l'Utente chiede Creazione Custom
- Se la ricerca non dà risultati o se l'utente richiede un asset specifico (es. tavolo alchemico magico):
  - **NON arrenderti e non fare FAIL**.
  - Crea il modello proceduralmente rispettando il **Contratto Bel Low-Poly** (`blender-game-assets.md`):
    1. Geometria composita a strati (mai un monoblocco).
    2. Modificatore `Bevel` a 1 segmento per catturare la luce lungo i bordi.
    3. Almeno 2 o 3 materiali PBR contrastanti (es. Legno `#3D2719`, Ferro `#1E1E22`, Accento Magico `#00FFAA` con emissione).
    4. Pivot sempre al centro della base d'appoggio a $Y=0$ (quota terra).

### 4. Gestione Errori Script Python in execute_blender_code
- Se uno script fallisce, non ripeterlo uguale:
  - Ispeziona prima la scena con `get_scene_info` per verificare i veri nomi degli oggetti.
  - Cerca sempre i nodi per tipo (es. `n.type == 'BSDF_PRINCIPLED'`) e mai per nome localizzato.
  - Prima di manipolare geometrie, assicurati di essere in Object Mode (`bpy.ops.object.mode_set(mode='OBJECT')`).

## Avvio

1. `blender_get_addon_status`. If down: TerminalMCP start `blender.exe`, wait 8s.
2. TCP 9876 closed → one user line, STOP:

```
RUN: In Blender premi N → MCP for Blender → Start MCP Server
Poi in chat nuova: /resumegame
```

3. `blender_get_polypizza_status`. If disabled: tell user to tick **Use assets from Poly Pizza** (key already in addon prefs / `BLENDERMCP_POLYPIZZA_API_KEY`). Do not invent geometry.

## Protocollo Fast-Track Poly Pizza (Batch fino a 3 modelli, 1 solo PNG finale)

Se il modello viene prelevato pronto da Poly Pizza (`source: polypizza`), **è inutile fare 5 step e catturare 4 screenshot intermedi**. È consentito processare fino a **3 task/modelli in batch** nella stessa sessione.

| step | PNG | operazione |
|---|---|---|
| 0. Wipe | (nessuno) | `execute_blender_code`: pulizia totale oggetti/mesh/materiali. |
| 1. Fetch | (nessuno) | `search_polypizza_models` + `download_polypizza_model` (`normalize_size=true`, dimensioni Geometra). |
| 2. Sanitize & Export | (nessuno) | Pivot a terra Y=0, rimozione luci/camere residue + `export_scene` in `art/exports/$ID.glb`. |
| 3. Verifica | `screenshots/blender-$ID.png` | **1 singolo screenshot finale** del modello in viewport. |

Ripeti per max 3 asset del ledger nello stesso turno. Parent verifica unicamente lo screenshot finale `blender-$ID.png` per ciascun modello.

*(Nota: Solo per modelli procedurali composti/assemblati da zero con più parti si applicano gli step multi-screenshot descritti in [procedural-prop-recipe.md](procedural-prop-recipe.md)).*

GLB ≥ 15KB. Ledger `source: polypizza`, `licence: CC0|CC-BY`, `polypizza_id`, attribution string dal download.

## Key

Do not paste keys into chat, GDD, or SKILL.md. Installer injects `BLENDERMCP_POLYPIZZA_API_KEY` from `config.json` → `art.polypizzaApiKey`. Addon prefs also work (user already set it).
