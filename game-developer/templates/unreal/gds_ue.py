"""GDS for Unreal Engine 5.8 — deterministic helpers for the `realistic` route.

Run inside the Unreal Editor (Python Editor Script Plugin enabled), through the Unreal MCP
`execute_tool_script` / Python tool, or from the Output Log:  py "<path>/gds_ue.py" lookdev realistic-golden

    import gds_ue
    gds_ue.lookdev("realistic-overcast")      # sun + sky atmosphere + sky light + clouds + height fog + post volume
    gds_ue.lint(autofix=True)                 # buried / floating static meshes, snapped by line trace
    gds_ue.shot("Saved/Screenshots/gds/035-lookdev.png")
    gds_ue.import_folder("D:/Fab/Library/rock_cliff", "/Game/_Game/Megascans/rock_cliff")
    gds_ue.heightmap("C:/proj/art/world/overworld_height.png", seed=42)   # 16-bit PNG for Landscape > Import

Status: written against the documented UE 5.x Python API; NOT yet run on a 5.8 editor on this machine
(only UE 5.4 is installed). The first worker that uses it records any API mismatch in docs/gates/.
"""
import json
import math
import os
import random
import struct
import sys
import zlib

try:
    import unreal
except ImportError:  # heightmap() works outside the editor
    unreal = None

PRESETS = {
    #                 sun pitch/yaw, intensity (lux, UE default sun = 10 with auto exposure), colour temp K, fog, exposure bias, bloom, vignette, saturation
    "realistic-overcast": dict(pitch=-55, yaw=-40, lux=6, temp=6800, fog=0.02, fog_color=(0.62, 0.66, 0.72), bias=0.3, bloom=0.4, vignette=0.2, sat=0.92, clouds=0.9),
    "realistic-golden":   dict(pitch=-12, yaw=-55, lux=8, temp=4200, fog=0.015, fog_color=(0.85, 0.66, 0.48), bias=0.5, bloom=0.8, vignette=0.3, sat=1.05, clouds=0.45),
    "realistic-noon":     dict(pitch=-65, yaw=-20, lux=12, temp=6000, fog=0.008, fog_color=(0.55, 0.68, 0.85), bias=0.0, bloom=0.5, vignette=0.15, sat=1.0, clouds=0.35),
    "realistic-night":    dict(pitch=-35, yaw=30, lux=0.3, temp=9000, fog=0.03, fog_color=(0.05, 0.07, 0.12), bias=2.5, bloom=1.2, vignette=0.4, sat=0.8, clouds=0.6),
}


def _actors():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def _world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def _find_or_spawn(cls, label, location=(0, 0, 0)):
    for a in _actors().get_all_level_actors():
        if isinstance(a, cls):
            return a
    a = _actors().spawn_actor_from_class(cls, unreal.Vector(*location), unreal.Rotator(0, 0, 0))
    a.set_actor_label(label)
    return a


def lookdev(preset="realistic-overcast"):
    """Sun (atmosphere sun light), SkyAtmosphere, real-time SkyLight, VolumetricCloud, ExponentialHeightFog, unbound PostProcessVolume."""
    p = PRESETS.get(preset)
    if p is None:
        return json.dumps({"status": "FAIL", "error": "unknown preset", "presets": list(PRESETS)})
    applied = []
    sun = _find_or_spawn(unreal.DirectionalLight, "GDS_Sun", (0, 0, 1000))
    sun.set_actor_rotation(unreal.Rotator(roll=0, pitch=p["pitch"], yaw=p["yaw"]), False)
    lc = sun.get_component_by_class(unreal.DirectionalLightComponent)
    lc.set_editor_property("intensity", float(p["lux"]))
    lc.set_editor_property("use_temperature", True)
    lc.set_editor_property("temperature", float(p["temp"]))
    lc.set_editor_property("atmosphere_sun_light", True)
    lc.set_editor_property("cast_shadows", True)
    applied.append("sun")

    _find_or_spawn(unreal.SkyAtmosphere, "GDS_SkyAtmosphere"); applied.append("sky-atmosphere")
    sky = _find_or_spawn(unreal.SkyLight, "GDS_SkyLight")
    sc = sky.get_component_by_class(unreal.SkyLightComponent)
    sc.set_editor_property("real_time_capture", True)
    applied.append("skylight-realtime")

    clouds = _find_or_spawn(unreal.VolumetricCloud, "GDS_Clouds")
    try:
        clouds.get_component_by_class(unreal.VolumetricCloudComponent).set_editor_property("layer_height", 5.0 * p["clouds"] + 1.0)
    except Exception:
        pass
    applied.append("clouds")

    fog = _find_or_spawn(unreal.ExponentialHeightFog, "GDS_HeightFog")
    fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    fc.set_editor_property("fog_density", p["fog"])
    fc.set_editor_property("volumetric_fog", True)
    fc.set_editor_property("fog_inscattering_luminance", unreal.LinearColor(*p["fog_color"], 1.0))
    applied.append("height-fog")

    ppv = _find_or_spawn(unreal.PostProcessVolume, "GDS_Post")
    ppv.set_editor_property("unbound", True)
    s = ppv.get_editor_property("settings")
    for name, value in (
        ("auto_exposure_bias", p["bias"]),
        ("bloom_intensity", p["bloom"]),
        ("vignette_intensity", p["vignette"]),
        ("color_saturation", unreal.Vector4(p["sat"], p["sat"], p["sat"], 1.0)),
    ):
        try:
            s.set_editor_property("override_" + name, True)
            s.set_editor_property(name, value)
        except Exception as e:  # property names drift between versions: record, don't crash
            applied.append("skip:" + name)
    ppv.set_editor_property("settings", s)
    applied.append("post-volume")
    return json.dumps({"status": "PASS", "preset": preset, "applied": applied})


def _trace_down(start, end, ignore):
    hit = unreal.SystemLibrary.line_trace_single(_world(), start, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                                                 True, [ignore], unreal.DrawDebugTrace.NONE, True)
    if hit is None:
        return None
    t = hit.to_tuple()
    # (blocking_hit, initial_overlap, time, distance, location, impact_point, normal, impact_normal, phys_mat, hit_actor, ...)
    return (t[5], t[9]) if t[0] else None


def lint(autofix=False, buried_tol=2.0, float_tol=5.0, write_to=None):
    """Static mesh actors that sit below (buried) or above (floating) the surface under their bounds centre. Units: cm."""
    report = {"checked": 0, "issues": 0, "buried": 0, "floating": 0, "noGround": 0, "list": []}
    for a in _actors().get_all_level_actors():
        if not isinstance(a, unreal.StaticMeshActor):
            continue
        label = a.get_actor_label()
        if label.lower().startswith(("landscape", "floor", "wall", "ground", "sm_floor", "sm_wall")):
            continue
        origin, extent = a.get_actor_bounds(False)
        if extent.x > 1500 or extent.y > 1500:
            continue  # terrain-scale pieces are not props
        report["checked"] += 1
        bottom = origin.z - extent.z
        hit = _trace_down(unreal.Vector(origin.x, origin.y, origin.z + extent.z + 50), unreal.Vector(origin.x, origin.y, bottom - 5000), a)
        if hit is None:
            report["noGround"] += 1; report["list"].append({"type": "noGround", "obj": label}); continue
        delta = bottom - hit[0].z
        kind = "buried" if delta < -buried_tol else "floating" if delta > float_tol else None
        if kind:
            report[kind] += 1
            fixed = False
            if autofix:
                loc = a.get_actor_location(); a.set_actor_location(unreal.Vector(loc.x, loc.y, loc.z - delta), False, False); fixed = True
            report["list"].append({"type": kind, "obj": label, "value_cm": round(delta, 1), "fixed": fixed})
    report["issues"] = sum(1 for i in report["list"] if not i.get("fixed"))
    out = json.dumps(report, indent=2)
    if write_to:
        os.makedirs(os.path.dirname(write_to), exist_ok=True)
        open(write_to, "w").write(out)
    return out


def shot(path, width=1920, height=1080):
    """High-res screenshot of the active viewport (lands under Saved/Screenshots when the path is relative)."""
    unreal.AutomationLibrary.take_high_res_screenshot(width, height, path)
    return json.dumps({"status": "PASS", "path": path})


def import_folder(src_dir, dest="/Game/_Game/Imported"):
    """Import every FBX/GLB/OBJ/texture in src_dir (e.g. a FabCLI download) into dest, no dialogs."""
    tasks = []
    for root, _, files in os.walk(src_dir):
        for f in files:
            if f.lower().endswith((".fbx", ".glb", ".gltf", ".obj", ".png", ".jpg", ".exr", ".tga")):
                t = unreal.AssetImportTask()
                t.filename = os.path.join(root, f); t.destination_path = dest
                t.automated = True; t.save = True; t.replace_existing = True
                tasks.append(t)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    return json.dumps({"status": "PASS", "imported": len(tasks), "dest": dest})


# ---------------------------------------------------------------- heightmap (pure python, no editor needed)
class _Perlin:
    def __init__(self, seed):
        rnd = random.Random(seed)
        p = list(range(256)); rnd.shuffle(p)
        self.p = p + p
        self.g = [(math.cos(i * 0.7853981633974483), math.sin(i * 0.7853981633974483)) for i in range(8)]

    def noise(self, px, py):
        p, g = self.p, self.g
        x0, y0 = math.floor(px), math.floor(py)
        xi, yi = int(x0) & 255, int(y0) & 255
        xf, yf = px - x0, py - y0
        u, v = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf)

        def d(h, dx, dy):
            gx, gy = g[h & 7]
            return gx * dx + gy * dy
        aa, ab, ba, bb = p[p[xi] + yi], p[p[xi] + yi + 1], p[p[xi + 1] + yi], p[p[xi + 1] + yi + 1]
        x1 = d(aa, xf, yf) + u * (d(ba, xf - 1, yf) - d(aa, xf, yf))
        x2 = d(ab, xf, yf - 1) + u * (d(bb, xf - 1, yf - 1) - d(ab, xf, yf - 1))
        return x1 + v * (x2 - x1)

    def fbm(self, x, y, octaves=6):
        total, amp, freq, norm = 0.0, 1.0, 1.0, 0.0
        for _ in range(octaves):
            total += self.noise(x * freq, y * freq) * amp
            norm += amp; amp *= 0.5; freq *= 2.0
        return total / norm


def heightmap(path, size=1009, seed=42, scale=0.004, island=False):
    """16-bit grayscale PNG sized for a UE Landscape (1009 = 8x8 components of 63 quads x 2 sections). Import: Landscape mode > Import from File."""
    pn = _Perlin(int(seed)); size = int(size); scale = float(scale)
    rows = []
    for y in range(size):
        row = bytearray(b"\x00")
        for x in range(size):
            h = pn.fbm(x * scale * 10, y * scale * 10) * 0.7 + 0.5
            if island:
                d = math.hypot(x / size - 0.5, y / size - 0.5) * 2
                h *= max(0.0, 1.0 - max(0.0, d - 0.55) / 0.4)
            v = max(0, min(65535, int(h * 65535)))
            row += struct.pack(">H", v)
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 16, 0, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    open(path, "wb").write(png)
    return json.dumps({"status": "PASS", "path": path, "size": size, "seed": seed})


if __name__ == "__main__" and len(sys.argv) > 1:
    fn = globals()[sys.argv[1]]
    print(fn(*sys.argv[2:]))
