# Conversione XML -> binario, Gen8 -> Gen9, verifica

## Quando serve
| Situazione | Cosa e' in XML | Cosa serve |
|---|---|---|
| Windows + PyMateria (export NATIVE) | solo `.ycd.xml` | convertire i YCD |
| Senza PyMateria (Linux/macOS o non installato) | tutto (`.ydr.xml`, `.yft.xml`, `.ytd.xml`, `.ycd.xml`, `.ytyp.xml`) | convertire tutto tranne ytyp/ymap (FiveM li legge in XML rinominati) |

## A) Automatico con `tools/CwXmlToBin` (consigliato)
Compila una volta (`build.ps1` / `build.sh`, vedi [setup.md](setup.md)). `make_resource.py` lo trova da solo e:
1. converte `gen8/*.xml` -> binari in `stream/`;
2. converte `*.ycd.xml` -> `.ycd` in `stream/` **e** `stream_enhanced/` (il formato YCD e' lo stesso);
3. crea `stream_enhanced/` convertendo i binari Gen8 con `--gen9` (stesso codice dell'Asset Converter di
   CodeWalker), salvo i file gia' esportati nativi Gen9 da Sollumz.

Uso manuale:
```bash
CwXmlToBin myrp_crate.ydr.xml                 # -> myrp_crate.ydr (texture embedded dalla cartella myrp_crate/)
CwXmlToBin --dir export/gen8 out/stream       # tutta una cartella
CwXmlToBin --gen9 stream/myrp_crate.ydr stream_enhanced/myrp_crate.ydr
CwXmlToBin --gen9-dir stream stream_enhanced
CwXmlToBin --info stream/*.ydr stream/*.ycd   # VERIFICA: modelli/LOD, texture (formato, mip), ossi+tag, luci, bound, clip
```
Le texture embedded devono stare nella cartella con lo stesso nome dell'asset accanto all'XML (Sollumz la crea).

Esempio di `--info` atteso per un prop animato:
```
== myrp_chest.ydr (2917 bytes, RSC v165 => Gen8/Legacy)
  models H/M/L/VL: 2/0/0/0  lodDist H/M/L/VL: 9998/9998/9998/9998
  embedded textures: myrp_crate_d 512x256 D3DFMT_DXT1 mips=10
  bones: root#0, lid#21060
  lights: 0  embedded bound: Composite
== myrp_chest_anims.ycd (483 bytes, RSC v46 => Gen8/Legacy)
  clip: close (hash close) type=Animation
  clip: open (hash open) type=Animation
```
Versioni risorsa: Gen8 ydr/ydd 165, yft 162, ytd 13; Gen9 ydr/ydd 159, yft 171, ytd 5; ycd 46 (uguale).

## B) Manuale con CodeWalker (GUI, Windows)
1. CodeWalker RPF Explorer (Edit mode attivo).
2. Apri una cartella di lavoro o un `.rpf` di test (nuovo RPF: tasto destro > New > RPF Archive).
3. Trascina dentro i `.xml` (con le cartelle texture accanto) oppure tasto destro > **Import XML...**: CodeWalker crea
   il binario corrispondente.
4. Estrai i binari (tasto destro > Extract) e mettili in `stream/`.
5. Enhanced: RPF Explorer > Tools > **Asset Converter** (cartella Legacy -> cartella Gen9), oppure Cfx **Alchemist**
   (`AlchemistCli.exe input output`, supporta YDR/YTD/YFT/YPT/YDD).

## C) Alchemist (Cfx.re) - per asset Legacy esistenti
Converte cartelle di risorse Legacy in Enhanced e "raffina" asset fatti con tool vecchi (`--refine`). Solo
Windows 11. Utile per portare su Enhanced risorse gia' fatte.
