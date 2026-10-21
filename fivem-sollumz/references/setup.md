# Setup e modi di esecuzione

## Componenti

| Componente | Versione | Ruolo | Obbligatorio |
|---|---|---|---|
| Blender | 4.2+ (consigliato 4.5 LTS o 5.x; testato 5.2.2 LTS) | modellazione + host Python | si |
| Sollumz | 2.9.0+ | import/export asset RAGE | si |
| szio | installato da Sollumz (dipendenza richiesta) | I/O formati | si (automatico) |
| PyMateria (Cfx.re) | 0.2.x, **solo Windows** | export binario NATIVE (.ydr/.yft/.ytd/... diretti, Gen8 e Gen9), shattermap veicoli | fortemente consigliato |
| CodeWalker | ultima (Discord CodeWalker #releases) | anteprima, ymap, conversione XML manuale | consigliato |
| `tools/CwXmlToBin` | in questa skill | conversione XML->binario e Gen8->Gen9 da riga di comando, `--info` | consigliato (obbligatorio per YCD senza CodeWalker) |
| texconv (DirectXTex) | qualsiasi | DDS di qualita' migliore | opzionale (fallback Pillow) |
| Pillow | >= 11 | fallback DDS, lettura immagini | si (nel Python che esegue dds_convert) |

## Installare Sollumz

Blender 4.2+: `Edit > Preferences > Get Extensions > Repositories > + > Add Remote Repository` ->
`https://repo.sollumz.org/`, cerca **Sollumz** (release; "Sollumz (Development)" e' la build instabile), Install.
Alla prima attivazione Sollumz propone di installare le dipendenze: accetta **szio** e (su Windows) **PyMateria**
(licenza Cfx: https://static.cfx.re/PyMateria-License-Agreement.pdf). Si reinstallano da
`Preferences > Add-ons > Sollumz > Dependencies`.

Alternativa: zip da https://github.com/Sollumz/Sollumz/releases > `Get Extensions > Install from Disk`.

Da Python (headless, una volta sola):

```python
import bpy
# installazione da zip scaricato dalle release GitHub:
bpy.ops.extensions.package_install_files(filepath=r"C:\path\Sollumz.zip", repo="user_default",
                                         enable_on_install=True)
bpy.ops.wm.save_userpref()
# (alternativa: aggiungere il repo remoto e installare da li')
# bpy.ops.preferences.extension_repo_add(name="sollumz", remote_url="https://repo.sollumz.org/", type="REMOTE")
```

## Verifica ambiente (sempre come primo passo)

```python
import sys; sys.path.append(r"<skill>/scripts")
import sz_fivem as sz
sz.env_report()
# {"blender": "5.2.2 LTS", "sollumz_version": "2.9.0", "native_gen8": true, "native_gen9": true, "cwxml": true}
```

- `native_gen8/gen9 = false` -> PyMateria assente (Linux/macOS o non installato): l'export produce solo `.xml`.
  La pipeline funziona lo stesso: `make_resource` converte con CwXmlToBin (Gen8, poi Gen8->Gen9).
- Errore "Sollumz non e' abilitato" -> abilitalo o installalo (sopra).

## Compilare CwXmlToBin

Richiede .NET SDK 8+ (`winget install Microsoft.DotNet.SDK.8`, oppure `apt install dotnet-sdk-8.0`).

```powershell
powershell -File <skill>\tools\CwXmlToBin\build.ps1      # Windows -> tools\CwXmlToBin\bin\CwXmlToBin.exe
bash <skill>/tools/CwXmlToBin/build.sh                    # Linux/macOS
```

Lo script clona CodeWalker (GitHub dexyfex/CodeWalker) in `tools/CodeWalker` e pubblica il tool. `make_resource`
lo trova da solo (oppure variabile d'ambiente `SZ_CWXML2BIN`).

## texconv (opzionale)

Scarica `texconv.exe` da https://github.com/microsoft/DirectXTex/releases e mettilo nel PATH. `dds_convert.py` lo usa
automaticamente; altrimenti usa Pillow (risultato valido, compressione leggermente inferiore).

## Modi di eseguire il codice

### A) Blender MCP (agente che parla con Blender aperto)
Il server MCP di Blender espone un tool tipo `execute_blender_code` / `execute_python`. Invia blocchi brevi:

```python
import sys, importlib
sys.path.append(r"C:\...\fivem-sollumz\scripts")
import sz_fivem as sz; importlib.reload(sz)
import build_from_spec as b; importlib.reload(b)
report = b.build(r"C:\...\mio_progetto\spec.json")
print(report["audit"])
```
Dopo ogni build: screenshot della viewport per controllo (se il server MCP lo offre).

### B) Headless (nessuna UI, ideale per agenti/CI)
```bash
blender -b -P <skill>/scripts/build_from_spec.py -- <progetto>/spec.json
blender -b mio.blend -P mio_script.py            # script che importa sz_fivem e fa operazioni custom
```

### C) Blender come modulo Python (`pip install bpy`)
`bpy` su PyPI = Blender completo come modulo (es. `bpy==5.2.2` per Python 3.13). Sollumz va reso importabile e
abilitato manualmente:
```python
import sys, addon_utils
sys.path.append(r"<cartella che contiene la cartella 'sollumz' estratta dallo zip>")
addon_utils.enable("sollumz", default_set=True)   # richiede `pip install szio` nella stessa venv
```
E' l'ambiente con cui questa skill e' stata testata (export CW XML; PyMateria solo su Windows).

### D) Vision model che guida la UI
Puo' usare comunque i pulsanti Sollumz, ma e' piu' affidabile eseguire gli script di questa skill dalla
**Python Console** di Blender (Scripting workspace) incollando i blocchi dell'opzione A.

## Struttura di lavoro consigliata

```
mio_progetto/
  spec.json                 descrizione asset (vedi python-pipeline.md)
  models/                   sorgenti .glb/.fbx/.obj/.blend
  textures/                 png/tga sorgenti (nome file = nome texture in gioco)
  build/<nome>/             output: _textures/ (dds), export/, resource/, <ytyp>.blend, build_report.json
```
