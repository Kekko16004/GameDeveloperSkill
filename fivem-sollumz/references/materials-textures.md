# Materiali e texture

## Shader
Usa sempre materiali Sollumz (`sz.material(obj, "<shader>", {...})`). Scelta rapida e catalogo completo in
[shaders-catalog.md](shaders-catalog.md). Un materiale Blender normale (Principled) NON esporta: convertilo con
`sz.convert_existing_materials(obj)` (auto: default / normal / spec / normal_spec in base ai collegamenti).

Parametri utili (`sz.set_shader_params(mat, ...)` o `"params"` nella spec):
| Parametro | Shader | Effetto |
|---|---|---|
| `bumpiness` | normal* | intensita' normal map (1.0) |
| `specularIntensityMult` | spec/normal_spec | forza riflesso (0-1+) |
| `specularFalloffMult` | spec | "lucidita'": alto = riflesso stretto |
| `specularFresnel` | spec | riflesso radente |
| `specMapIntMask` | *spec | quali canali della spec map pesano l'intensita' (vettore RGB) |
| `emissiveMultiplier` | emissive* | luminosita' (1-20) |
| `HardAlphaBlend` | default/normal/spec | ritaglio alpha piu' netto |
| `reflectivePower` | reflect/glass | riflesso ambiente |
| `matMaterialColorScale` | default | scala colore |

## Texture: regole
- Formato **DDS**, lati **potenza di 2** (256, 512, 1024, 2048; non serve quadrata), **mipmap completi**.
  `scripts/dds_convert.py` fa tutto (texconv se presente, altrimenti Pillow).
- Il **nome file** (senza .dds, minuscolo) e' il nome della texture in gioco: deve essere unico se va in un ytd
  condiviso e deve corrispondere a quello usato da `AddReplaceTexture` (DUI).
- Compressione: diffuse senza alpha BC1/DXT1; con alpha BC3/DXT5; normal BC3; spec BC3; palette tint e texture DUI
  placeholder A8R8G8B8 senza mip (`--format RGBA --no-mips`). Texture `script_rt_*` (render target): A8R8G8B8, no mip.
- Dimensioni: prop piccoli 256-512, medi 1024, grandi/hero 2048. Oltre 2048 solo con `+hi` (HD). Le texture sono la
  causa n.1 di asset "oversized" (FiveM avvisa sopra ~16 MB per file: [fivem-integration.md](fivem-integration.md#limiti)).

## Normal map
GTA V usa normal map in convenzione **DirectX** (verde invertito rispetto a Blender/glTF/OpenGL: Sollumz inserisce
un nodo che inverte il verde per l'anteprima). La pipeline assume sorgenti **OpenGL** e inverte il verde in
conversione; se la tua normal e' gia' DirectX (es. Substance "DirectX") metti `"normal_format": "directx"` nel
materiale o nella spec. Sintomo di convenzione sbagliata: rilievi che sembrano incavati con luce dall'alto.

## Specular <a id="specular"></a>
`SpecSampler` (shader *spec*): convenzione comunemente usata - **R** = intensita' del riflesso, **G** = glossiness
(quanto e' stretto), **B** = fresnel/maschera aggiuntiva; `specMapIntMask` decide quali canali contano per
l'intensita'. Conversione da PBR (approssimata, va bene per prop):
- R = (1 - roughness) * 0.6 + metallic * 0.4
- G = 1 - roughness
- B = metallic
Metallo nudo: spec alta + diffuse scura e colorata; plastica: spec media; legno/stoffa: spec bassa (20-40/255).
Nel dubbio importa un prop vanilla simile (CodeWalker > export XML > import Sollumz) e copia texture/parametri.

## Embedded vs YTD
- **Embedded** (`embedded: true`, default): le texture vanno dentro il `.ydr`/`.yft`. Semplice, un file.
- **YTD esterno** (`embedded: false` + `texture_dictionary` nella spec, o `sz.make_txd`): texture condivise tra piu'
  modelli (pack di prop), oppure texture che vuoi **sostituire a runtime** (DUI, `AddReplaceTexture`). L'archetipo
  deve avere `textureDictionary = <nome ytd>` (la spec lo fa).
- Puoi mischiare: embedded per i dettagli + ytd per la texture schermo.
- HD (`+hi`): `img.sz_is_hd = True` sull'immagine -> Sollumz esporta `<asset>+hidr.ytd` (o `<ytd>+hi.ytd`) a piena
  risoluzione e mezza risoluzione nel file base. Va dichiarato nel `_manifest.ymf` (`HDTxdBindingArray`) - vedi
  [recipe-map-placement.md](recipe-map-placement.md). Distanza di caricamento: `hdTextureDist` dell'archetipo.

## Alpha / trasparenze
- Ritagli netti (foglie, reti, scritte): shader `cutout`/`*_cutout` + alpha 0/255. Niente problemi di ordinamento.
- Semitrasparenze vere: `alpha`, `normal_spec_alpha`, `glass*`. Separa in un materiale dedicato SOLO la parte
  trasparente. Se si vede "attraverso" male: flag archetipo `draw_last` o `disable_alpha_sorting`.
- Vetri di prop: `glass` / `glass_env`; vetri che si rompono: fragment con collisione `GLASS_*`.

## Emissive
`emissive` (sempre acceso), `emissivenight` (solo di notte), `emissivestrong` (piu' forte), `*_alpha` (con
trasparenza). `emissiveMultiplier` 2-10 tipico. L'emissive NON illumina l'ambiente: aggiungi una luce embedded
([recipe-lights-emissive.md](recipe-lights-emissive.md)).

## Tint (varianti colore) <a id="tint"></a>
Shader `*_tnt` (`default_tnt`, `normal_tnt`, `normal_spec_tnt`, `cutout_tnt`, `emissive_tnt`...): la diffuse viene
moltiplicata per un colore preso dalla **palette** (`TintPaletteSampler`):
- **riga** della palette = variante scelta in gioco con `SetObjectTextureVariation(obj, riga)` (oppure tint del ymap)
- **colonna** = canale **Blu** del vertex color `Color 1` del vertice (0-255) (`Color 2` per `trees_*_tnt`)

Spec:
```json
"material": { "shader": "normal_spec_tnt", "textures": {"diffuse": "...", "normal": "...", "spec": "..."},
              "tint_palette": ["#ffffff", "#b03030", "#3050c0", ["#202020", "#d0a020"]], "tint_column": 0 }
```
Ogni elemento di `tint_palette` e' una variante (riga); un elemento-lista = colori per colonna (zone diverse del
modello con `sz.set_tint_column(obj, col)` su selezioni diverse). Diffuse in scala di grigi chiari = colori fedeli.
Python: `dds_convert.make_tint_palette(varianti, "x_pal.dds")` + `sz.set_tint_column(obj, 0)`.
