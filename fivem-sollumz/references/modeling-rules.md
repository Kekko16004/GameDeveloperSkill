# Regole di modellazione per GTA V / FiveM

## Unita', assi, pivot
- 1 unita' Blender = 1 metro (Scene > Units: Metric, Unit Scale 1.0). Riferimenti: porta 0.9 x 2.1 m, sedia seduta
  0.45 m, tavolo 0.75 m, ped alto ~1.8 m.
- Z in alto. Il "fronte" va verso **-Y** (il player tipicamente lo guarda da -Y). `SetEntityHeading` ruota attorno a Z.
- **Origine = pivot**: prop a terra -> centro della base (z=0 della base). Oggetti in mano -> punto di presa.
  Porte -> cardine a terra. Parti animate -> asse di rotazione (diventa la testa dell'osso).
- Applica rotazione e scala (`sz.prepare_mesh` lo fa). Scala non applicata = collisioni/bbox sbagliati.

## Topologia e budget
| Tipo | Triangoli LOD High (indicativi) |
|---|---|
| oggetto piccolo in mano (telefono, bottiglia) | 300 - 2 000 |
| prop medio (sedia, cassa, monitor) | 1 000 - 8 000 |
| prop grande (bancone, macchinario, insegna) | 5 000 - 25 000 |
| hero prop vicino alla camera | fino a ~40 000 + LOD obbligatori |
- Max ~65 000 vertici per geometria (Sollumz divide per materiale; il conteggio vertici in gioco ~ numero di "face
  corner" unici, quindi > vertici di Blender: valuta i triangoli).
- Ogni materiale = una geometria = una draw call: tieni i materiali al minimo (1-3 per prop). Enhanced: max 128.
- Niente n-gon problematici (Sollumz triangola), niente facce doppie/sovrapposte (z-fighting), normali verso
  l'esterno (GTA fa backface culling: le facce interne non si vedono). Superfici sottili visibili da entrambi i
  lati: duplica le facce invertite oppure flag archetipo `double_sided` (solo vegetazione/teli).
- Smooth/sharp: usa Auto Smooth/Sharp edges; le normali custom vengono esportate.
- Modificatori: applicati prima della conversione (lo fa `build_from_spec`), tranne Armature.

## UV
- Obbligatorie, senza sovrapposizioni dove serve una texture unica. Nome: `UVMap 0` (seconda: `UVMap 1`, usata da
  alcuni shader per dirt/detail/lightmap). `sz.ensure_uv_names`.
- Texel density coerente (~ 512 px/m per prop medi visti da vicino).

## Vertex color (`Color 1`, Face Corner, Byte Color)
Per i prop gli shader standard leggono il vertex color come illuminazione ambientale:
- **R** = luce ambiente naturale (cielo) -> esterni.
- **G** = luce ambiente artificiale (interni) -> MLO.
- Esterni: (1,0,0,1). Interni MLO: (0,1,0,1). Prop usato ovunque: (1,1,0,1) e' un compromesso. Puoi sfumare
  (zone in ombra piu' scure = AO "cotto" nel vertex color).
- Alpha: alcuni shader (decal, tint, vegetazione) lo usano: lascia 1 se non sai.
- Senza vertex color il prop appare nero o rosa/brillante di notte.
- Vestiti ped: `Color 1` = #FF8000 (1, 0.5, 0, 1), `Color 2` = (0,0,0,0).
- Veicoli: R = AO, G = deformazione, B = livello bruciatura.

## Naming
- Asset (file/archetipo): `prefisso_nome[_variante]`, minuscolo, `[a-z0-9_]`, <= 63 char, unico in tutto il server
  (due risorse con lo stesso nome file si sovrascrivono!). Evita prefissi vanilla.
- Texture: `<asset>_d` (diffuse), `_n` (normal), `_s` (spec), `_e` (emissive mask) - il nome file e' il nome in gioco.
- YCD: `<asset>_anims` o `anim@<prefisso>_<asset>`. Clip: verbi brevi (`open`, `close`, `idle`, `spin`).
- YTD condivisi: `<prefisso>_<pack>_txd`.

## Sorgenti esterne (Sketchfab, AI 3D, store)
- Verifica la licenza (CC0/CC-BY/commerciale) prima di metterlo su un server.
- Tipico: troppi poligoni, scala sbagliata (cm o pollici), pivot al centro, texture 4K PBR.
  Fix: `source.scale`, decimate (`lods` / modificatore Decimate), `origin`, riduzione texture a 1024-2048.
- PBR -> GTA: BaseColor -> Diffuse; Normal (OpenGL, Y+) va bene; Roughness/Metallic -> specular map
  (vedi [materials-textures.md](materials-textures.md#specular)).
