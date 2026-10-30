#!/usr/bin/env python3
"""Detect the machine's GPU and VRAM once (Windows / Linux), never by asking the user.

Used silently where the hardware matters: local gen3d eligibility (gen3d.md) and the look/quality
defaults (styles.md "Hardware gate"). Measuring the frame time of a game is a separate job (ncli play-test).

  python hwdetect.py              JSON on stdout (reads the cache, detects on the first run)
  python hwdetect.py --refresh    detect again and rewrite the cache
  python hwdetect.py --text       one human line (doctor.ps1 prints this)
  python hwdetect.py --gdd GDD.md an old GDD with `gpu:` / `vram:` keeps working: they override the detection

Cache: ~/.game-developer/hardware.json (outside the skill folder, so an update never touches it).
Standard library only. Exit code is always 0: an unknown machine reports tier "unknown", it is not an error.
"""
import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys

CACHE = os.path.join(os.path.expanduser("~"), ".game-developer", "hardware.json")


def _run(cmd, timeout=15):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return out.stdout if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def parse_nvidia_smi(text):
    """`nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits` -> [(name, GB)] (largest first)."""
    gpus = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2 and parts[0]:
            try:
                gpus.append((parts[0], round(float(parts[1]) / 1024.0, 1)))
            except ValueError:
                gpus.append((parts[0], None))
    gpus.sort(key=lambda g: g[1] or 0, reverse=True)
    return gpus


def parse_windows_json(text):
    """Output of the PowerShell query below -> [(name, GB or None)]."""
    try:
        data = json.loads(text) if text.strip() else []
    except ValueError:
        return []
    if isinstance(data, dict):
        data = [data]
    gpus = []
    for d in data:
        name = (d.get("Name") or "").strip()
        if not name:
            continue
        q = d.get("QwMem")
        legacy = d.get("AdapterRAM")
        gb = None
        if isinstance(q, (int, float)) and q > 0:
            gb = round(q / 2**30, 1)
        elif isinstance(legacy, (int, float)) and legacy > 0:
            gb = round(legacy / 2**30, 1)  # 32-bit field: caps at 4 GB, only a lower bound
            if gb >= 3.9:
                gb = None
        gpus.append((name, gb))
    return gpus


WIN_QUERY = (
    "$k='HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Class\\{4d36e968-e325-11ce-bfc1-08002be10318}';"
    "$q=@{};Get-ChildItem $k -ErrorAction SilentlyContinue | ForEach-Object {"
    "$p=Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue;"
    "if($p.DriverDesc -and $p.'HardwareInformation.qwMemorySize'){$q[$p.DriverDesc]=[int64]$p.'HardwareInformation.qwMemorySize'}};"
    "@(Get-CimInstance Win32_VideoController | ForEach-Object {[pscustomobject]@{Name=$_.Name;AdapterRAM=$_.AdapterRAM;QwMem=$q[$_.Name]}})"
    " | ConvertTo-Json -Compress"
)


def parse_lspci(text):
    gpus = []
    for line in text.splitlines():
        if re.search(r"VGA|3D controller|Display controller", line):
            name = line.split(": ", 1)[-1].strip()
            gpus.append((name, None))
    return gpus


def linux_vram_gb():
    best = None
    base = "/sys/class/drm"
    try:
        for card in os.listdir(base):
            p = os.path.join(base, card, "device", "mem_info_vram_total")
            if os.path.isfile(p):
                gb = round(int(open(p).read().strip()) / 2**30, 1)
                best = max(best or 0, gb)
    except (OSError, ValueError):
        pass
    return best


def detect():
    system = platform.system()
    gpus = []
    smi = shutil.which("nvidia-smi")
    if smi:
        gpus = parse_nvidia_smi(_run([smi, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"]))
    if not gpus and system == "Windows":
        ps = shutil.which("powershell") or shutil.which("pwsh")
        if ps:
            gpus = parse_windows_json(_run([ps, "-NoProfile", "-NonInteractive", "-Command", WIN_QUERY], timeout=30))
    if not gpus and system == "Linux":
        gpus = parse_lspci(_run(["lspci"]))
        vram = linux_vram_gb()
        if gpus and vram:
            gpus = [(gpus[0][0], vram)] + gpus[1:]
    # real adapters first: the software ones are only a fallback
    real = [g for g in gpus if not re.search(r"Basic Render|llvmpipe|Microsoft Remote|Hyper-V|SwiftShader", g[0], re.I)]
    gpus = real or gpus
    gpus.sort(key=lambda g: g[1] or 0, reverse=True)
    name, vram = (gpus[0] if gpus else ("", None))
    return build(name, vram, system)


def build(name, vram, system=""):
    nvidia = bool(re.search(r"nvidia|geforce|rtx|gtx|quadro", name or "", re.I))
    rtx = bool(re.search(r"\bRTX\b", name or "", re.I))
    if not name:
        tier = "unknown"
    elif vram is None:
        tier = "unknown"
    elif vram >= 8:
        tier = "high"
    elif vram >= 5:
        tier = "mid"
    else:
        tier = "low"
    return {
        "gpu": name,
        "vramGb": vram,
        "os": system or platform.system(),
        "tier": tier,  # high >= 8 GB | mid 5-8 GB | low < 5 GB | unknown
        "rtx": rtx,
        "gen3dLocalEligible": bool(nvidia and vram is not None and vram >= 8),  # Modly (gen3d.md)
    }


def read_gdd_override(path):
    """Old GDDs carry `gpu:` and `vram:`; they stay valid and win over the detection. Never asked for any more."""
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return None, None
    g = re.search(r"^gpu:\s*([^#\n]+)", text, re.M)
    v = re.search(r"^vram:\s*([\d.]+)", text, re.M)
    return (g.group(1).strip() if g else None), (float(v.group(1)) if v else None)


def load(refresh=False, gdd=None):
    info = None
    if not refresh:
        try:
            info = json.load(open(CACHE, encoding="utf-8"))
        except (OSError, ValueError):
            info = None
    if info is None:
        info = detect()
        try:
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            json.dump(info, open(CACHE, "w", encoding="utf-8"), indent=2)
        except OSError:
            pass
    if gdd:
        g, v = read_gdd_override(gdd)
        if g or v:
            info = build(g or info["gpu"], v if v is not None else info["vramGb"], info["os"])
            info["source"] = "GDD override"
    return info


def text_line(info):
    vram = "%.1f GB" % info["vramGb"] if info.get("vramGb") else "VRAM unknown"
    return "%s, %s, tier %s, local gen3d %s" % (info.get("gpu") or "GPU not found", vram, info["tier"],
                                                 "yes" if info["gen3dLocalEligible"] else "no")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--text", action="store_true")
    ap.add_argument("--gdd")
    a = ap.parse_args(argv)
    info = load(a.refresh, a.gdd)
    print(text_line(info) if a.text else json.dumps(info))
    return 0


if __name__ == "__main__":
    sys.exit(main())
