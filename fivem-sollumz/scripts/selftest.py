"""
selftest.py - verifica l'ambiente e l'intera pipeline costruendo tutti i tipi di asset d'esempio.

  blender -b -P <skill>/scripts/selftest.py -- [cartella_output]
  (o da MCP: import selftest; selftest.run("C:/tmp/sz_selftest"))

Genera texture finte, costruisce templates/spec_examples/all_types.json, esporta, crea la risorsa e, se
CwXmlToBin e' compilato, converte e verifica i binari (ossi, clip, texture, Gen9). Stampa PASS/FAIL per controllo.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _textures(dst: Path):
    import dds_convert
    dds_convert.ensure_pillow()
    from PIL import Image, ImageDraw
    dst.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (512, 256), (150, 100, 60))
    d = ImageDraw.Draw(im)
    for x in range(0, 512, 64):
        d.line([(x, 0), (x, 256)], fill=(90, 60, 30), width=6)
    im.save(dst / "myrp_crate_d.png")
    Image.new("RGB", (256, 256), (128, 128, 255)).save(dst / "myrp_crate_n.png")
    Image.new("RGB", (256, 256), (60, 60, 60)).save(dst / "myrp_crate_s.png")
    a = Image.new("RGBA", (128, 128), (255, 255, 255, 0))
    ImageDraw.Draw(a).ellipse([20, 20, 100, 100], fill=(255, 0, 0, 255))
    a.save(dst / "myrp_sign_d.png")
    Image.new("RGB", (512, 256), (0, 0, 0)).save(dst / "myrp_tv_screen.png")


def run(out_dir=None) -> bool:
    import build_from_spec
    import make_resource
    out = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="sz_selftest_"))
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    _textures(out / "textures")
    spec_src = HERE.parent / "templates" / "spec_examples" / "all_types.json"
    spec = json.loads(spec_src.read_text(encoding="utf-8"))
    spec["output"] = "build"
    spec["resource"]["path"] = "build/resource"
    (out / "spec.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")

    checks = []
    rep = build_from_spec.build(out / "spec.json")
    checks.append(("audit senza errori", all(not a["errors"] for a in rep["audit"].values())))
    checks.append(("export scritto", bool(rep.get("written"))))
    res = out / "build" / "resource"
    checks.append(("fxmanifest", (res / "fxmanifest.lua").exists()))
    checks.append(("ytyp in stream", (res / "stream" / "myrp_demo.ytyp").exists()))

    cw = make_resource.find_cwconv()
    if cw:
        info = subprocess.run([cw, "--info", *map(str, sorted((res / "stream").glob("*.y??")))],
                              capture_output=True, text=True).stdout
        checks.append(("ydr binari", (res / "stream" / "myrp_crate.ydr").exists()))
        checks.append(("ossi prop animato", "lid#21060" in info))
        checks.append(("clip open/close", "clip: open" in info and "clip: close" in info))
        checks.append(("fragment groups", "physics groups: myrp_sign_break, pole, board" in info))
        checks.append(("ytd DUI", "myrp_tv_screen" in info))
        g9 = subprocess.run([cw, "--info", str(res / "stream_enhanced" / "myrp_crate.ydr")],
                            capture_output=True, text=True).stdout
        checks.append(("stream_enhanced Gen9", "Gen9/Enhanced" in g9))
    else:
        print("[selftest] CwXmlToBin non compilato: salto la verifica dei binari (vedi references/setup.md)")
        checks.append(("XML in attesa di conversione (atteso senza tool)", bool(rep["resource"]["needs_conversion"])
                       or (res / "stream" / "myrp_crate.ydr").exists()))

    ok = True
    for name, passed in checks:
        ok = ok and passed
        print(f"[selftest] {'PASS' if passed else 'FAIL'}  {name}")
    print(f"[selftest] {'TUTTO OK' if ok else 'CI SONO ERRORI'} -> {out}")
    return ok


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    sys.exit(0 if run(argv[0] if argv else None) else 1)
