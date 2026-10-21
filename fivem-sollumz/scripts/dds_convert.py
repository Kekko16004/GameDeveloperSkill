#!/usr/bin/env python3
"""
dds_convert.py - PNG/TGA/JPG -> DDS pronti per GTA V / FiveM (potenza di 2, mipmap completi, BC1/BC3).

Il NOME DEL FILE e' il nome della texture in gioco: usa minuscolo [a-z0-9_] (es. myrp_crate_d.dds).

Backend (in ordine):
  1. texconv.exe (DirectXTex, Windows)  -> qualita' migliore. Cercato nel PATH o con --texconv.
  2. Pillow >= 11 (puro Python, ovunque) -> mipmap generati qui, compressione DXT1/DXT5.

Formati consigliati:
  diffuse senza alpha  -> BC1 (DXT1)
  diffuse con alpha    -> BC3 (DXT5)        (cutout/alpha/decal/vetri)
  normal map           -> BC3 (DXT5)        (convenzione DirectX: da OpenGL/glTF usa --flip-green)
  specular             -> BC3 (DXT5)        (R=intensita', G=glossiness, B=fresnel/... per normal_spec)
  palette tint / UI DUI placeholder / script_rt_* -> A8R8G8B8 non compresso, senza mip (--format RGBA --no-mips)

Uso:
  python dds_convert.py in.png [out.dds] [--format BC1|BC3|RGBA] [--max 2048] [--no-mips] [--kind diffuse|normal|spec|alpha]
  python dds_convert.py cartella_png/ cartella_dds/ --kind auto      (auto: *_n -> normal, *_s -> spec, alpha -> BC3)
Da Python:
  from dds_convert import convert ; convert("a.png", "a.dds", fmt="BC1")
"""
from __future__ import annotations

import argparse
import io
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

def ensure_pillow():
    """Il Python incluso in Blender non ha Pillow: lo installa nella cartella utente al primo uso."""
    try:
        import PIL  # noqa: F401
        return
    except ImportError:
        pass
    import importlib
    import site
    subprocess.run([sys.executable, "-m", "ensurepip", "--user"], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # --user funziona col Python di Blender anche se installato in Program Files; nelle venv serve senza --user
    r = subprocess.run([sys.executable, "-m", "pip", "install", "--user", "pillow"])
    if r.returncode != 0:
        subprocess.run([sys.executable, "-m", "pip", "install", "pillow"], check=True)
    user_site = site.getusersitepackages()
    if user_site not in sys.path:
        sys.path.append(user_site)
    importlib.invalidate_caches()
    import PIL  # noqa: F401


DDSD_MIPMAPCOUNT = 0x20000
DDSCAPS_COMPLEX = 0x8
DDSCAPS_MIPMAP = 0x400000


def _pow2_floor(n: int) -> int:
    p = 1
    while p * 2 <= n:
        p *= 2
    return p


def _target_size(w: int, h: int, max_size: int) -> tuple[int, int]:
    # arrotonda alla potenza di 2 piu' vicina (verso il basso se > 1.5x), poi limita
    def r(n):
        lo = _pow2_floor(n)
        return lo * 2 if n >= lo * 1.5 else lo
    return min(r(w), max_size), min(r(h), max_size)


def find_texconv(explicit: str | None = None) -> str | None:
    if explicit and Path(explicit).is_file():
        return explicit
    return shutil.which("texconv") or shutil.which("texconv.exe")


def _texconv(src: Path, dst: Path, fmt: str, max_size: int, mips: bool, exe: str, extra=None):
    tfmt = {"BC1": "BC1_UNORM", "BC3": "BC3_UNORM", "RGBA": "B8G8R8A8_UNORM"}[fmt]
    from PIL import Image
    with Image.open(src) as im:
        w, h = _target_size(im.width, im.height, max_size)
    outdir = dst.parent
    cmd = [exe, "-nologo", "-y", "-f", tfmt, "-w", str(w), "-h", str(h), "-m", "0" if mips else "1",
           *(extra or []), "-o", str(outdir), str(src)]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    produced = outdir / (src.stem + ".dds")
    if produced.resolve() != dst.resolve():
        produced.replace(dst)


def _flip_green(im):
    from PIL import Image, ImageOps
    r, g, b, a = im.split()
    return Image.merge("RGBA", (r, ImageOps.invert(g), b, a))


def _pillow(src: Path, dst: Path, fmt: str, max_size: int, mips: bool, flip_green: bool = False):
    from PIL import Image
    im = Image.open(src)
    im = im.convert("RGBA")
    if flip_green:
        im = _flip_green(im)
    w, h = _target_size(im.width, im.height, max_size)
    if (w, h) != im.size:
        im = im.resize((w, h), Image.LANCZOS)
    levels = [im]
    if mips:
        while levels[-1].width > 1 or levels[-1].height > 1:
            lw, lh = max(1, levels[-1].width // 2), max(1, levels[-1].height // 2)
            levels.append(levels[-1].resize((lw, lh), Image.LANCZOS))
    if fmt == "RGBA":
        # A8R8G8B8 (BGRA in memoria) non compresso
        hdr = _dds_header_rgba(w, h, len(levels))
        body = b"".join(lv.tobytes("raw", "BGRA") for lv in levels)
        dst.write_bytes(hdr + body)
        return
    pf = {"BC1": "DXT1", "BC3": "DXT5"}[fmt]
    first = io.BytesIO()
    levels[0].save(first, format="DDS", pixel_format=pf)
    data = bytearray(first.getvalue())
    if data[:4] != b"DDS ":
        raise RuntimeError("Pillow non ha prodotto un DDS valido")
    chunks = [bytes(data[128:])]
    for lv in levels[1:]:
        # i blocchi DXT sono 4x4: per i mip piu' piccoli si codifica un 4x4 e si tiene 1 blocco
        tmp = lv if lv.width >= 4 and lv.height >= 4 else lv.resize((4, 4), Image.NEAREST)
        b = io.BytesIO()
        tmp.save(b, format="DDS", pixel_format=pf)
        blk = 8 if fmt == "BC1" else 16
        expected = max(1, (lv.width + 3) // 4) * max(1, (lv.height + 3) // 4) * blk
        chunks.append(b.getvalue()[128:128 + expected])
    if len(levels) > 1:
        flags = struct.unpack_from("<I", data, 8)[0] | DDSD_MIPMAPCOUNT
        struct.pack_into("<I", data, 8, flags)
        struct.pack_into("<I", data, 28, len(levels))
        caps = struct.unpack_from("<I", data, 108)[0] | DDSCAPS_COMPLEX | DDSCAPS_MIPMAP
        struct.pack_into("<I", data, 108, caps)
    dst.write_bytes(bytes(data[:128]) + b"".join(chunks))


def _dds_header_rgba(w: int, h: int, mips: int) -> bytes:
    flags = 0x1 | 0x2 | 0x4 | 0x1000 | 0x8 | (DDSD_MIPMAPCOUNT if mips > 1 else 0)
    caps = 0x1000 | ((DDSCAPS_COMPLEX | DDSCAPS_MIPMAP) if mips > 1 else 0)
    pf = struct.pack("<II4sIIIII", 32, 0x41, b"\0\0\0\0", 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    hdr = struct.pack("<4sIIIIIII", b"DDS ", 124, flags, h, w, w * 4, 0, mips) + b"\0" * 44 + pf + \
        struct.pack("<IIIII", caps, 0, 0, 0, 0)
    assert len(hdr) == 128
    return hdr


def guess_format(path: Path, kind: str = "auto") -> str:
    if kind == "diffuse":
        return "BC1"
    if kind in ("normal", "spec", "alpha"):
        return "BC3"
    stem = path.stem.lower()
    if stem.endswith(("_n", "_nrm", "_normal", "_bump", "_s", "_spec")):
        return "BC3"
    try:
        from PIL import Image
        with Image.open(path) as im:
            if im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info:
                alpha = im.convert("RGBA").getchannel("A")
                if alpha.getextrema()[0] < 250:
                    return "BC3"
    except Exception:
        pass
    return "BC1"


def convert(src, dst=None, fmt: str | None = None, max_size: int = 2048, mips: bool = True,
            kind: str = "auto", texconv: str | None = None, flip_green: bool = False) -> Path:
    """flip_green=True per normal map in convenzione OpenGL (Blender, glTF, Substance 'OpenGL'): GTA V usa
    DirectX (verde invertito)."""
    ensure_pillow()
    src = Path(src)
    dst = Path(dst) if dst else src.with_suffix(".dds")
    if dst.is_dir():
        dst = dst / (src.stem.lower() + ".dds")
    dst.parent.mkdir(parents=True, exist_ok=True)
    fmt = (fmt or guess_format(src, kind)).upper()
    exe = find_texconv(texconv)
    if exe and flip_green:
        # texconv: -inverty inverte il canale verde
        _texconv(src, dst, fmt, max_size, mips, exe, extra=["-inverty"])
    elif exe:
        _texconv(src, dst, fmt, max_size, mips, exe)
    else:
        _pillow(src, dst, fmt, max_size, mips, flip_green)
    return dst


def make_tint_palette(variants, out_dds, width: int = 256):
    """
    Palette per shader *_tnt. variants = lista di varianti (righe); ogni variante = lista di colori per colonna
    (hex '#RRGGBB' o (r,g,b) 0-255). Riga N = SetObjectTextureVariation(obj, N). Colonna = canale Blu del
    vertex color 'Color 1' del vertice (0-255) -> con un solo colore per variante usa colonna 0 (Blu = 0).
    Salvata A8R8G8B8 senza mip (niente sbavature tra righe/colonne).
    """
    ensure_pillow()
    from PIL import Image

    def rgb(c):
        if isinstance(c, str):
            c = c.lstrip("#")
            return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
        return tuple(int(x) for x in c[:3])
    rows = [[rgb(c) for c in (v if isinstance(v, (list, tuple)) and v and not isinstance(v[0], (int, float))
                              else [v])] for v in variants]
    h = 1
    while h < len(rows):
        h *= 2
    im = Image.new("RGBA", (width, h))
    for y in range(h):
        row = rows[min(y, len(rows) - 1)]
        for x in range(width):
            im.putpixel((x, y), row[min(x, len(row) - 1)] + (255,))
    out_dds = Path(out_dds)
    png = out_dds.with_suffix(".png")
    im.save(png)
    return convert(png, out_dds, fmt="RGBA", mips=False)


def dds_info(path) -> dict:
    b = Path(path).read_bytes()[:128]
    _, _, flags, h, w, _, _, mips = struct.unpack_from("<4sIIIIIII", b, 0)
    fourcc = b[84:88].decode("latin1")
    return {"w": w, "h": h, "mips": mips or 1, "fourcc": fourcc.strip("\0") or "RGBA"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("dst", nargs="?")
    ap.add_argument("--format", choices=["BC1", "BC3", "RGBA"])
    ap.add_argument("--kind", default="auto", choices=["auto", "diffuse", "normal", "spec", "alpha"])
    ap.add_argument("--max", type=int, default=2048)
    ap.add_argument("--no-mips", action="store_true")
    ap.add_argument("--texconv")
    ap.add_argument("--flip-green", action="store_true", help="normal map OpenGL -> DirectX (GTA)")
    a = ap.parse_args()
    src = Path(a.src)
    files = [p for p in src.iterdir() if p.suffix.lower() in (".png", ".tga", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")] \
        if src.is_dir() else [src]
    out_dir = Path(a.dst) if a.dst and (src.is_dir() or Path(a.dst).is_dir()) else None
    for f in files:
        dst = (out_dir / (f.stem.lower() + ".dds")) if out_dir else (Path(a.dst) if a.dst else None)
        r = convert(f, dst, a.format, a.max, not a.no_mips, a.kind, a.texconv, a.flip_green)
        print(f"{f.name} -> {r}  {dds_info(r)}")


if __name__ == "__main__":
    sys.exit(main())
