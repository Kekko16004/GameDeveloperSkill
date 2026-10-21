#!/usr/bin/env python3
"""
make_resource.py - impacchetta l'export Sollumz in una risorsa FiveM pronta (non richiede Blender).

  python make_resource.py <export_dir> <resource_dir> --name myrp_props [--spec spec.json] [--ytyp myrp_props]
                          [--cwconv path/CwXmlToBin.exe]

Struttura prodotta:
  <resource_dir>/
    fxmanifest.lua
    stream/              Gen8  -> FiveM (Legacy)
    stream_enhanced/     Gen9  -> FiveM for GTAV Enhanced (se presente sostituisce stream/)
    client/sz_lib.lua    libreria (spawn, anim, DUI, porte, tint, attach) + exports
    client/main.lua      codice per gli asset della spec (comandi di test, schermi DUI, ...)
    server/sz_lib.lua    spawn networked + anim sincronizzate (state bag)
    server/main.lua
    html/screen.html     pagina DUI di esempio (se ci sono asset 'dui')
    _needs_codewalker/   SOLO se mancano binari: .xml da convertire (YCD sempre) + istruzioni
    README.md

Regole sui formati (verificate su Sollumz 2.9 / docs Cfx):
  - .ydr/.yft/.ydd/.ytd/.ybn binari (export NATIVE, richiede PyMateria su Windows) -> copiati.
  - .ytyp.xml / .ymap.xml -> FiveM li legge come XML grezzo se rinominati in .ytyp / .ymap.
  - .ydr.xml/.yft.xml/.ytd.xml/... senza binario -> vanno convertiti (CodeWalker RPF Explorer > Import XML,
    oppure tools/CwXmlToBin). Messi in _needs_codewalker/.
  - .ycd: Sollumz esporta SOLO .ycd.xml -> conversione sempre necessaria; il .ycd e' identico Gen8/Gen9
    (Alchemist non converte YCD), va copiato in stream/ e stream_enhanced/.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
TPL = HERE.parent / "templates" / "resource"
BIN_EXT = (".ydr", ".yft", ".ydd", ".ytd", ".ybn", ".ytyp", ".ymap", ".ycd", ".yld")
RAW_XML_OK = (".ytyp", ".ymap")


def _version_dirs(export_dir: Path, versions) -> dict[str, Path]:
    out = {}
    if (export_dir / "gen8").is_dir() or (export_dir / "gen9").is_dir():
        if (export_dir / "gen8").is_dir():
            out["stream"] = export_dir / "gen8"
        if (export_dir / "gen9").is_dir():
            out["stream_enhanced"] = export_dir / "gen9"
    else:
        key = "stream_enhanced" if list(versions) == ["GEN9"] else "stream"
        out[key] = export_dir
    return out


def _collect(src: Path, dst: Path, pending: Path, log: list):
    dst.mkdir(parents=True, exist_ok=True)
    files = [p for p in src.iterdir() if p.is_file()]
    binaries = {p.name.lower() for p in files if p.suffix.lower() in BIN_EXT}
    for p in files:
        name = p.name.lower()
        if p.suffix.lower() in BIN_EXT:
            shutil.copy2(p, dst / name)
            log.append(f"{dst.name}/{name}")
        elif name.endswith(".xml"):
            base = name[:-4]                     # es. myrp.ytyp
            ext = Path(base).suffix
            if base in binaries:
                continue
            if ext in RAW_XML_OK:
                shutil.copy2(p, dst / base)      # XML grezzo accettato da FiveM
                log.append(f"{dst.name}/{base} (XML grezzo)")
            elif ext == ".ycd":
                continue                          # gestito a parte
            else:
                pdir = pending / dst.name
                pdir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, pdir / name)
                tex = src / Path(base).stem      # cartella texture embedded per CodeWalker
                if tex.is_dir():
                    shutil.copytree(tex, pdir / tex.name, dirs_exist_ok=True)
                log.append(f"_needs_codewalker/{dst.name}/{name}")


def _try_convert(cwconv: str | None, pending: Path, res: Path, log: list):
    """
    Con CwXmlToBin disponibile:
      1. _needs_codewalker/stream/*.xml  -> binari Gen8 in stream/
      2. _needs_codewalker/ycd/*.ycd.xml -> .ycd in stream/ e stream_enhanced/ (formato unico)
      3. stream_enhanced/: per ogni binario Gen8 in stream/ che non ha gia' il gemello Gen9 nativo,
         CwXmlToBin --gen9 (stessa conversione dell'Asset Converter di CodeWalker). Gli XML Gen9 esportati da
         Sollumz NON vengono passati a CodeWalker (CodeWalker da XML scrive solo Gen8).
    """
    if not cwconv or not pending.exists():
        return
    stream, enh = res / "stream", res / "stream_enhanced"
    stream.mkdir(exist_ok=True)

    def run(*args):
        r = subprocess.run([cwconv, *map(str, args)], capture_output=True, text=True)
        if r.returncode != 0:
            log.append(f"CONVERSIONE FALLITA {' '.join(map(str, args))}: {r.stdout}{r.stderr}")
            return False
        return True

    native_g9 = {p.name for p in enh.glob("*")} if enh.exists() else set()
    for xml in sorted((pending / "stream").glob("*.xml")) if (pending / "stream").exists() else []:
        out = stream / xml.name[:-4]
        if run(xml, out):
            log.append(f"convertito {out.name} -> stream/")
    for xml in sorted((pending / "ycd").glob("*.xml")) if (pending / "ycd").exists() else []:
        out = stream / xml.name[:-4]
        if run(xml, out):
            enh.mkdir(exist_ok=True)
            shutil.copy2(out, enh / out.name)
            log.append(f"convertito {out.name} -> stream/, stream_enhanced/")
    made_g9 = False
    if ((pending / "stream_enhanced").exists() or enh.exists()) and any(stream.iterdir()):
        enh.mkdir(exist_ok=True)
        made_g9 = True
        for f in sorted(stream.iterdir()):
            if f.name in native_g9 or (enh / f.name).exists() and f.suffix == ".ycd":
                continue
            if f.suffix in (".ydr", ".ydd", ".yft", ".ytd", ".ypt"):
                if run("--gen9", f, enh / f.name):
                    log.append(f"gen9 {f.name} -> stream_enhanced/")
            elif not (enh / f.name).exists():
                shutil.copy2(f, enh / f.name)
    for sub in ("stream", "ycd") + (("stream_enhanced",) if made_g9 else ()):
        shutil.rmtree(pending / sub, ignore_errors=True)
    if pending.exists() and not any(pending.rglob("*.xml")):
        shutil.rmtree(pending, ignore_errors=True)
    elif pending.exists():
        log.append("ATTENZIONE: restano XML Gen9 senza binari Gen8 da cui derivarli: esporta anche GEN8 o usa NATIVE")


def _lua_str(s: str) -> str:
    return "'" + str(s).replace("\\", "\\\\").replace("'", "\\'") + "'"


def _client_main(name: str, assets: list) -> str:
    L = [
        "-- Generato da fivem-sollumz. Modifica liberamente.",
        "Config = Config or {}",
        "Config.DevCommands = true   -- comandi /sz_* per testare gli asset in gioco (disattiva in produzione)",
        "",
        "local function inFront(dist)",
        "    local ped = PlayerPedId()",
        "    local c = GetOffsetFromEntityInWorldCoords(ped, 0.0, dist or 2.0, 0.0)",
        "    local ok, gz = GetGroundZFor_3dCoord(c.x, c.y, c.z + 1.0, false)",
        "    return vector3(c.x, c.y, ok and gz or c.z - 1.0), GetEntityHeading(ped)",
        "end",
        "",
    ]
    for a in assets:
        n, t = a["name"], a.get("type", "static")
        L.append(f"-- ===== {n} ({t}) =====")
        freeze = "false" if t in ("dynamic", "fragment") else "true"
        L += [
            "if Config.DevCommands then",
            f"    RegisterCommand('sz_{n}', function()",
            "        local pos, h = inFront(2.0)",
            f"        local obj = SZ.SpawnProp({_lua_str(n)}, pos, h, false, {freeze})",
            f"        if obj then print('spawnato {n}', obj) end",
            "    end, false)",
        ]
        if t == "animated":
            for clip in a.get("clips", []):
                d = clip.get("dict", a.get("clip_dictionary", f"{n}_anims"))
                L += [
                    f"    -- /sz_{n}_{clip['name']} : riproduce '{clip['name']}' sul {n} piu' vicino",
                    f"    RegisterCommand('sz_{n}_{clip['name']}', function()",
                    f"        local obj = SZ.GetClosestProp({_lua_str(n)}, GetEntityCoords(PlayerPedId()), 5.0)",
                    "        if obj == 0 then print('nessun prop vicino') return end",
                    f"        SZ.PlayPropAnim(obj, {_lua_str(d)}, {_lua_str(clip['name'])}, {str(bool(clip.get('loop'))).lower()}, true)",
                    "    end, false)",
                ]
        if t == "door":
            L += [
                f"    -- /sz_{n}_lock : blocca/sblocca la porta {n} piu' vicina (deve essere piazzata da ymap o spawnata)",
                f"    RegisterCommand('sz_{n}_lock', function()",
                f"        local obj = SZ.GetClosestProp({_lua_str(n)}, GetEntityCoords(PlayerPedId()), 5.0)",
                "        if obj == 0 then print('nessuna porta vicina') return end",
                "        local c = GetEntityCoords(obj)",
                f"        local h = SZ.RegisterDoor(('{n}_%d_%d_%d'):format(math.floor(c.x), math.floor(c.y), math.floor(c.z)), {_lua_str(n)}, c)",
                "        local locked = DoorSystemGetDoorState(h) == 1",
                "        SZ.SetDoorLocked(h, not locked)",
                "        print(locked and 'sbloccata' or 'bloccata')",
                "    end, false)",
            ]
        L.append("end")
        if t == "dui":
            txd = a.get("texture_dictionary", f"{n}_txd")
            txn = a.get("screen_texture") or "<nome_texture_schermo>"
            w, h = a.get("screen_size", [1280, 720])
            L += [
                f"-- Schermo DUI: sostituisce la texture '{txn}' del ytd '{txd}' con una pagina web",
                "CreateThread(function()",
                f"    SZ.CreateScreen({_lua_str(n)}, {_lua_str(txd)}, {_lua_str(txn)},",
                f"        ('nui://%s/html/screen.html'):format(GetCurrentResourceName()), {w}, {h})",
                f"    Wait(1000) SZ.ScreenSend({_lua_str(n)}, {{ title = {_lua_str(n)}, sub = 'DUI ok' }})",
                "end)",
            ]
        if t == "uv_scroll":
            L.append("-- UV anim: parte da sola (flag 'UV anims' + 'Auto Start Anim' nell'archetipo). Nessun codice.")
        L.append("")
    return "\n".join(L) + "\n"


def find_cwconv(explicit: str | None = None) -> str | None:
    """CwXmlToBin: argomento, env SZ_CWXML2BIN, oppure tools/CwXmlToBin/bin/ della skill."""
    import os
    for c in (explicit, os.environ.get("SZ_CWXML2BIN"),
              HERE.parent / "tools" / "CwXmlToBin" / "bin" / "CwXmlToBin.exe",
              HERE.parent / "tools" / "CwXmlToBin" / "bin" / "CwXmlToBin"):
        if c and Path(c).is_file():
            return str(c)
    return shutil.which("CwXmlToBin")


def make_resource(export_dir, resource_dir, name: str, assets: list | None = None, ytyp: str | None = None,
                  versions=("GEN8", "GEN9"), cwconv: str | None = None) -> dict:
    export_dir, res = Path(export_dir), Path(resource_dir)
    cwconv = find_cwconv(cwconv)
    assets = assets or []
    res.mkdir(parents=True, exist_ok=True)
    pending = res / "_needs_codewalker"
    log: list[str] = []
    for folder, src in _version_dirs(export_dir, versions).items():
        _collect(src, res / folder, pending, log)
    for ycd in export_dir.glob("*.ycd.xml"):
        (pending / "ycd").mkdir(parents=True, exist_ok=True)
        shutil.copy2(ycd, pending / "ycd" / ycd.name.lower())
        log.append(f"_needs_codewalker/ycd/{ycd.name.lower()}")
    _try_convert(cwconv, pending, res, log)

    (res / "client").mkdir(exist_ok=True)
    (res / "server").mkdir(exist_ok=True)
    shutil.copy2(TPL / "client_lib.lua", res / "client" / "sz_lib.lua")
    shutil.copy2(TPL / "server_lib.lua", res / "server" / "sz_lib.lua")
    (res / "client" / "main.lua").write_text(_client_main(name, assets), encoding="utf-8")
    if not (res / "server" / "main.lua").exists():
        (res / "server" / "main.lua").write_text(
            "-- Esempio: prop networked + animazione sincronizzata\n"
            "-- RegisterCommand('sz_net_spawn', function(src)\n"
            "--     local p = GetEntityCoords(GetPlayerPed(src))\n"
            "--     local obj = SZS.SpawnNetworkedProp('<modello>', p + vector3(0, 2, 0), 0.0)\n"
            "--     SZS.PlayPropAnimForAll(obj, '<ycd>', '<clip>', false, true)\n"
            "-- end, true)\n", encoding="utf-8")
    has_dui = any(a.get("type") == "dui" for a in assets)
    if has_dui:
        (res / "html").mkdir(exist_ok=True)
        shutil.copy2(TPL / "html" / "screen.html", res / "html" / "screen.html")

    ytyps = sorted({p.name for p in (res / "stream").glob("*.ytyp")} |
                   {p.name for p in (res / "stream_enhanced").glob("*.ytyp")}) if (res / "stream").exists() or \
        (res / "stream_enhanced").exists() else []
    if ytyp and f"{ytyp}.ytyp" not in ytyps:
        ytyps.append(f"{ytyp}.ytyp")
    has_ymap = any(any((res / f).glob("*.ymap")) for f in ("stream", "stream_enhanced") if (res / f).exists())
    man = [
        "fx_version 'cerulean'",
        "game 'gta5'",
        "lua54 'yes'",
        "",
        f"name '{name}'",
        "description 'Prop generati con fivem-sollumz (Blender + Sollumz)'",
        "",
        "client_scripts { 'client/sz_lib.lua', 'client/main.lua' }",
        "server_scripts { 'server/sz_lib.lua', 'server/main.lua' }",
    ]
    if has_dui:
        man += ["", "files { 'html/screen.html' }"]
    if ytyps:
        man += ["", "-- Archetipi: FiveM carica i .ytyp in streaming; la riga esplicita e' la forma classica e sicura.",
                "-- (il riferimento e' per nome file: vale sia per stream/ che per stream_enhanced/)"]
        man += [f"data_file 'DLC_ITYP_REQUEST' 'stream/{y}'" for y in ytyps]
    if has_ymap:
        man += ["", "this_is_a_map 'yes'"]
    (res / "fxmanifest.lua").write_text("\n".join(man) + "\n", encoding="utf-8")

    readme = [f"# {name}", "", "Generata da fivem-sollumz.", "",
              "## Installazione", f"1. Copia la cartella in `resources/` e aggiungi `ensure {name}` al server.cfg.",
              "2. Avvia il server, entra, prova i comandi `/sz_<nome>` (Config.DevCommands in client/main.lua).", "",
              "## Contenuto", *[f"- `{x}`" for x in log], ""]
    if pending.exists() and any(pending.rglob("*.xml")):
        readme += ["## AZIONE RICHIESTA: conversione XML -> binario", "",
                   "Alcuni file sono in formato CodeWalker XML (export senza PyMateria, oppure .ycd che Sollumz",
                   "esporta solo in XML). Convertili e metti i binari nella cartella indicata:", "",
                   "**CodeWalker RPF Explorer**: Tools > RPF Explorer, apri una cartella di lavoro (o un .rpf in",
                   "edit mode), tasto destro > *Import XML...* sul file `.xml` (le cartelle texture omonime devono",
                   "stare accanto), poi *Export* / estrai il binario risultante.",
                   "**Oppure** `tools/CwXmlToBin` (vedi references/codewalker-conversion.md):",
                   "`CwXmlToBin <file.xml> <file binario>`", "",
                   "- `_needs_codewalker/stream/*` -> binari in `stream/`",
                   "- `_needs_codewalker/stream_enhanced/*` -> binari in `stream_enhanced/`",
                   "- `_needs_codewalker/ycd/*` -> il `.ycd` in **entrambe** `stream/` e `stream_enhanced/`", ""]
    (res / "README.md").write_text("\n".join(readme), encoding="utf-8")
    summary = {"resource": str(res), "files": log,
               "needs_conversion": sorted(str(p.relative_to(res)) for p in pending.rglob("*.xml")) if pending.exists() else []}
    print(json.dumps(summary, indent=2))
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export_dir")
    ap.add_argument("resource_dir")
    ap.add_argument("--name", required=True)
    ap.add_argument("--spec")
    ap.add_argument("--ytyp")
    ap.add_argument("--versions", default="GEN8,GEN9")
    ap.add_argument("--cwconv")
    a = ap.parse_args()
    assets = json.loads(Path(a.spec).read_text())["assets"] if a.spec else []
    make_resource(a.export_dir, a.resource_dir, a.name, assets, a.ytyp, a.versions.split(","), a.cwconv)


if __name__ == "__main__":
    main()
