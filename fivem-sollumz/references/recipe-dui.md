# Ricetta: materiale sostituito da DUI (schermi, monitor, cartelloni web)

DUI = "Direct-rendered UI": FiveM renderizza una pagina web (NUI/CEF) su una **runtime texture**; con
`AddReplaceTexture` quella texture prende il posto di una texture del modello. Tutte le istanze del modello mostrano
la stessa pagina (la sostituzione e' per nome texture, globale).

## Lato modello (cosa deve avere il prop)
1. La superficie dello schermo e' una **geometria/materiale separato** dal resto (cornice, scocca).
2. UV dello schermo che coprono **tutto lo spazio 0..1** dritte (niente rotazioni/specchi: il contenuto web
   apparirebbe ruotato/specchiato). Rapporto UV = rapporto della pagina (16:9 -> schermo 16:9).
3. La texture placeholder dello schermo va in un **YTD esterno** (non embedded), con un **nome univoco**:
   es. `myrp_tv_screen` dentro `myrp_tv_txd.ytd`. Formato A8R8G8B8 senza mip (la build lo fa con `"dui": true`).
4. Shader dello schermo: `emissive` (si vede anche al buio, consigliato) o `default`. `emissiveMultiplier` 1-2
   (troppo alto = slavato).
5. Archetipo con `textureDictionary = myrp_tv_txd`. Le altre texture possono restare embedded.

```json
{ "type": "dui", "name": "myrp_tv",
  "source": { "file": "models/tv.glb" },
  "material": { "slots": {
      "Frame":  { "shader": "normal_spec", "textures": {"diffuse": "...", "normal": "...", "spec": "..."} },
      "Screen": { "shader": "emissive", "embedded": false, "dui": true,
                  "textures": { "diffuse": "textures/myrp_tv_screen.png" }, "params": { "emissiveMultiplier": 1.5 } } } },
  "texture_dictionary": "myrp_tv_txd", "screen_texture": "myrp_tv_screen", "screen_size": [1280, 720],
  "collision": { "mode": "box", "material": "PLASTIC" } }
```
(Con un solo materiale usa `"material": {...}` diretto come in `templates/spec_examples/all_types.json`.)

## Lato FiveM
`client/sz_lib.lua` (incluso nella risorsa) gestisce tutto:
```lua
-- crea la pagina e sostituisce la texture: origTxd = nome YTD, origTxn = nome texture schermo
SZ.CreateScreen('tv1', 'myrp_tv_txd', 'myrp_tv_screen', 'nui://' .. GetCurrentResourceName() .. '/html/screen.html', 1280, 720)
SZ.ScreenSend('tv1', { title = 'Benvenuto', sub = 'Prossima corsa 21:00' })   -- SendDuiMessage -> window 'message'
SZ.ScreenSetUrl('tv1', 'https://www.youtube.com/embed/<id>?autoplay=1&mute=1') -- URL esterno
SZ.DestroyScreen('tv1')                                                         -- RemoveReplaceTexture + DestroyDui
```
Native usate (in ordine):
```lua
local txd = CreateRuntimeTxd('sz_rt_tv1')                    -- dizionario runtime
local dui = CreateDui(url, 1280, 720)                        -- browser offscreen
while not IsDuiAvailable(dui) do Wait(0) end
local handle = GetDuiHandle(dui)
CreateRuntimeTextureFromDuiHandle(txd, 'screen', handle)     -- texture runtime dal browser
AddReplaceTexture('myrp_tv_txd', 'myrp_tv_screen', 'sz_rt_tv1', 'screen')   -- origTxd, origTxn, newTxd, newTxn
```
- `fxmanifest.lua`: `files { 'html/screen.html' }` (la risorsa generata lo include). URL locale:
  `nui://<risorsa>/html/screen.html`.
- Pagina: `html/screen.html` ascolta `window.addEventListener('message', e => e.data)`; dimensioni CSS = dimensioni
  della DUI (100% x 100%). Video: `muted autoplay` (l'audio DUI non e' posizionale; per audio 3D usa librerie come
  xsound o gestisci il volume in base alla distanza).
- Performance: ogni DUI e' un browser. Crea la DUI solo quando il player e' vicino (es. < 30 m) e distruggila quando
  si allontana. Risoluzioni 1280x720 / 1024x512 bastano.
- Schermi diversi con contenuti diversi = **texture diverse**: crea modelli/texture distinti (`myrp_tv_a_screen`,
  `myrp_tv_b_screen`...) oppure usa la tecnica render target sotto.
- Interazione mouse: `SendDuiMouseMove/Down/Up/Wheel(dui, ...)` calcolando le coordinate dal raycast sullo schermo.

## Alternativa: render target (`script_rt_*`)
Per disegnare con le native di disegno (`DrawSprite`, scaleform, testo) per-modello:
1. Texture dello schermo chiamata `script_rt_<nome>` (es. `script_rt_myrp_tv`), embedded, A8R8G8B8 senza mip.
2. Lua:
```lua
local rt = 'myrp_tv'
if not IsNamedRendertargetRegistered(rt) then RegisterNamedRendertarget(rt, false) end
LinkNamedRendertarget(GetHashKey('myrp_tv'))           -- hash del modello
local id = GetNamedRendertargetRenderId(rt)
CreateThread(function()
  while true do
    SetTextRenderId(id)
    SetScriptGfxDrawOrder(4)
    DrawRect(0.5, 0.5, 1.0, 1.0, 0, 0, 0, 255)
    -- DrawSprite('sz_rt_tv1', 'screen', 0.5, 0.5, 1.0, 1.0, 0.0, 255, 255, 255, 255)   -- anche una DUI!
    SetTextRenderId(GetDefaultScriptRendertargetRenderId())
    Wait(0)
  end
end)
```
Enhanced: le texture `script_rt_*` devono essere A8R8G8B8 senza mip (altrimenti ERR_GFX_STATE).

## Verifica
- `CwXmlToBin --info stream/myrp_tv_txd.ytd` -> deve elencare `myrp_tv_screen`.
- Il `.ydr` non deve avere `myrp_tv_screen` tra le texture embedded.
- In gioco: `/sz_myrp_tv` e lo schermo mostra la pagina; se resta il placeholder: nome txd/txn sbagliato o archetipo
  senza `textureDictionary`.
