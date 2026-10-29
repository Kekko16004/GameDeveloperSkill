"""Optional offline instance authoring extension for the external nc_gds builder.

Standard library only. install(namespace) wraps an existing builder; this module
does not connect to an editor, change a project or execute the external tool.
"""

from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path


MAX_INSTANCES = 100000  # entity_add transforms schema
FLOAT_MAX = 3.4028234663852886e38


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(label + " must be a number")
    value = float(value)
    if not math.isfinite(value) or abs(value) > FLOAT_MAX:
        raise ValueError(label + " must fit a finite engine float")
    return value


def _vec(value, label, scale=False):
    if scale and isinstance(value, (int, float)) and not isinstance(value, bool):
        value = [value] * 3
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(label + " must contain three numbers")
    result = [_number(v, label) for v in value]
    if scale and any(v < 1.401298464324817e-45 for v in result):
        raise ValueError(label + " must be positive: instance records cannot preserve mirrored or zero scales")
    return result


def _object(value, label):
    if not isinstance(value, dict):
        raise ValueError(label + " must be an object")
    return value


def _wind(value):
    if isinstance(value, str):
        value = {"type": value}
    value = dict(_object(value, "wind"))
    limits = {"sway": -1, "branch": -1, "flutter": -1,
              "swayFrequency": 0, "flutterFrequency": 0, "disableDistance": -1}
    if set(value) - ({"type"} | set(limits)):
        raise ValueError("unknown wind field; use type, sway, branch, flutter, swayFrequency, flutterFrequency, disableDistance")
    if value.get("type", "none") not in ("none", "grass", "bush", "tree"):
        raise ValueError("wind.type must be none, grass, bush or tree")
    value.setdefault("type", "none")
    for key, minimum in limits.items():
        if key in value:
            value[key] = _number(value[key], "wind." + key)
            if value[key] < minimum:
                raise ValueError("wind." + key + " is below its supported minimum")
    # Native type defaults include amplitudes and cutoff: grass 40 m, bush 100 m,
    # tree 250 m. Do not infer vegetation from names or impose culling/shadow changes.
    return value


def _policies(value):
    result = {"collision": value.get("collision", "mesh"),
              "cull_distance": _number(value.get("cull_distance", 0), "cull_distance"),
              "cast_shadows": value.get("cast_shadows", True)}
    if result["collision"] not in ("mesh", "none", "box", "capsule"):
        # the engine's runtime gives an `instances` entity a box or a capsule collider per instance: "mesh" is accepted by the
        # editor but the runtime falls back to a box and logs a warning on every Play (docs/NUCLEON-ENGINE-NOTES.md, D2): say box
        raise ValueError("GDS instances collision must be none, box, capsule or mesh (mesh = box at runtime); automatic collider substitution is disabled")
    if result["cull_distance"] < 0 or not isinstance(result["cast_shadows"], bool):
        raise ValueError("cull_distance must be nonnegative and cast_shadows must be boolean")
    if "wind" in value:
        result["wind"] = _wind(value["wind"])
    return result


def _transform(value, label, kit_scale=1):
    value = _object(value, label)
    if set(value) - {"position", "rotation", "scale"}:
        raise ValueError(label + ": per-instance identity/properties are unsupported; author these as excluded models")
    if "position" not in value:
        raise ValueError(label + ".position is required")
    return {"position": _vec(value["position"], label + ".position"),
            "rotation": _vec(value.get("rotation", [0, 0, 0]), label + ".rotation"),
            "scale": _vec([v * kit_scale for v in _vec(value.get("scale", 1), label + ".scale", scale=True)],
                          label + ".scale", scale=True)}


def _explicit(spec):
    groups = spec.get("instances", [])
    if not isinstance(groups, list):
        raise ValueError("instances must be a list of explicit groups")
    if not groups:
        return []
    origin = _vec(spec.get("origin", [0, 0, 0]), "origin")
    yaw = _number(spec.get("yaw", 0), "yaw")
    kit_scale = _number(spec.get("kitScale", 1), "kitScale")
    if kit_scale <= 0:
        raise ValueError("kitScale must be positive for instances")
    angle = math.radians(yaw)
    c, s = math.cos(angle), math.sin(angle)
    result = []
    allowed = {"name", "asset", "position", "rotation", "scale", "transforms",
               "collision", "cull_distance", "cast_shadows", "wind"}
    for index, group in enumerate(groups):
        group = _object(group, "instances[%d]" % index)
        if set(group) - allowed:
            raise ValueError("instances[%d]: unknown group field or identity/property data; keep identity-bearing entities as models" % index)
        asset = group.get("asset")
        name = group.get("name", "instances%d" % index)
        if not isinstance(asset, str) or not asset or asset.lower().endswith(".ncactor"):
            raise ValueError("instances[%d].asset must name a model, not an actor" % index)
        if not isinstance(name, str) or not name:
            raise ValueError("instance group name must be nonempty")
        transforms = group.get("transforms")
        if not isinstance(transforms, list) or not 1 <= len(transforms) <= MAX_INSTANCES:
            raise ValueError("instance groups require 1 to %d transforms" % MAX_INSTANCES)
        position = _vec(group.get("position", [0, 0, 0]), name + ".position")
        rotation = _vec(group.get("rotation", [0, 0, 0]), name + ".rotation")
        call = {"type": "instances", "name": name, "asset": asset,
                "position": _vec([origin[0] + c * position[0] - s * position[1],
                                  origin[1] + s * position[0] + c * position[1], origin[2] + position[2]], name + ".world_position"),
                "rotation": _vec([rotation[0], rotation[1], rotation[2] + yaw], name + ".world_rotation"),
                "scale": _vec(group.get("scale", 1), name + ".scale", scale=True),
                "transforms": [_transform(t, name + ".transforms[%d]" % i, kit_scale)
                               for i, t in enumerate(transforms)]}
        call.update(_policies(group))
        result.append(call)
    return result


def _group(calls, options, spec, warnings):
    minimum = options.get("min_group", 4)
    if isinstance(minimum, bool) or not isinstance(minimum, int) or not 2 <= minimum <= MAX_INSTANCES:
        raise ValueError("performance.min_group must be an integer from 2 to %d" % MAX_INSTANCES)
    excluded = options.get("exclude_names", [])
    if not isinstance(excluded, list) or any(not isinstance(n, str) for n in excluded):
        raise ValueError("performance.exclude_names must be a list of exact entity names")
    excluded = set(excluded)
    # The legacy builder passes properties through but does not pass authoring metadata.
    # Preserve explicitly marked story/interactive pieces even when they have no properties.
    for piece in spec.get("pieces", []):
        if piece.get("preserve_identity") or piece.get("story") or piece.get("interactive"):
            if not piece.get("name"):
                raise ValueError("identity-bearing pieces require an explicit name for safe auto-group exclusion")
            excluded.add(piece["name"])
    groups = defaultdict(list)
    allowed = {"type", "name", "asset", "position", "rotation", "scale", "properties",
               "collision", "cull_distance", "cast_shadows", "wind"}
    names = Counter(c.get("name") for c in calls)
    for index, call in enumerate(calls):
        if (call.get("type") != "model" or call.get("name") in excluded or
                call.get("properties") or set(call) - allowed or names[call.get("name")] > 1):
            continue
        if not isinstance(call.get("asset"), str) or call["asset"].lower().endswith(".ncactor"):
            continue
        try:
            transform = _transform({k: call[k] for k in ("position", "rotation", "scale") if k in call}, "model " + str(call.get("name")))
            policy = _policies({"collision": options.get("collision", "mesh"), **call})
        except ValueError as error:
            warnings.append("Auto-group kept %s as a model: %s" % (call.get("name"), error))
            continue
        key = json.dumps([call["asset"], policy], sort_keys=True, allow_nan=False)
        groups[key].append((index, call, transform, policy))
    replacement, removed = {}, set()
    used_names = {c.get("name") for c in calls}
    for members in groups.values():
        if len(members) < minimum:
            continue
        for start in range(0, len(members), MAX_INSTANCES):
            chunk = members[start:start + MAX_INSTANCES]
            if len(chunk) < minimum:
                continue
            first_index, first, _, policy = chunk[0]
            stem = str(first.get("name", "model")) + "_instances"
            name, suffix = stem, 1
            while name in used_names:
                name = stem + "_" + str(suffix)
                suffix += 1
            used_names.add(name)
            replacement[first_index] = {"type": "instances", "name": name, "asset": first["asset"],
                                        "position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1],
                                        "transforms": [entry[2] for entry in chunk], **policy}
            removed.update(entry[0] for entry in chunk)
            warnings.append("Auto-group %s replaces %d model entities; individual names are not retained. Add story/interactive names to performance.exclude_names." % (name, len(chunk)))
    return [replacement[i] if i in replacement else c for i, c in enumerate(calls)
            if i not in removed or i in replacement]


def _shape_lint(calls, options, warnings):
    total_budget = options.get("shape_budget", 256)
    repeat_budget = options.get("repeated_shape_budget", 32)
    for name, value in (("shape_budget", total_budget), ("repeated_shape_budget", repeat_budget)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError("performance.%s must be a positive integer" % name)
    shapes = [c for c in calls if c.get("type") == "shape"]
    if len(shapes) > total_budget:
        warnings.append("Shape budget advisory: %d procedural entities exceed %d; consider authored reusable meshes/instances without changing collision or appearance." % (len(shapes), total_budget))
    signatures = Counter(json.dumps(c.get("shape", {}), sort_keys=True, allow_nan=False) for c in shapes)
    for signature, count in sorted(signatures.items()):
        if count > repeat_budget:
            kind = json.loads(signature).get("kind", "shape")
            warnings.append("Repeated-shape advisory: %d identical %s definitions exceed %d; geometry sharing does not remove entity/submission costs." % (count, kind, repeat_budget))


def build_calls(original, spec, catalog=None):
    """Keep the legacy result unchanged unless instances/performance is authored."""
    if "instances" not in spec and "performance" not in spec:
        return original(spec, catalog)
    options = _object(spec.get("performance", {}), "performance")
    if set(options) - {"auto_group", "exclude_names", "min_group", "collision", "shape_budget", "repeated_shape_budget"}:
        raise ValueError("unknown performance option")
    if not isinstance(options.get("auto_group", False), bool):
        raise ValueError("performance.auto_group must be boolean; grouping is opt-in")
    calls, warnings = original(spec, catalog)
    calls, warnings = deepcopy(calls), list(warnings)
    explicit = _explicit(spec)
    names = Counter(call.get("name") for call in calls + explicit)
    if any(names[call["name"]] != 1 for call in explicit):
        raise ValueError("explicit instance names must be unique across the blueprint")
    calls.extend(explicit)
    if options.get("auto_group", False):
        calls = _group(calls, options, spec, warnings)
    if "performance" in spec:
        _shape_lint(calls, options, warnings)
    return calls, warnings


def _bounds(original, calls):
    if not any(c.get("type") == "instances" for c in calls):
        return original(calls)
    # Conservative bounds of instance origins, as legacy bounds cover entity
    # origins only. A sphere avoids duplicating the engine's Euler conventions.
    points = [c for c in calls if c.get("type") != "instances"]
    for call in calls:
        if call.get("type") != "instances":
            continue
        center = call["position"]
        scale = call.get("scale", [1, 1, 1])
        if not any(call.get("rotation", [0, 0, 0])):
            points.extend({"position": [c + p * s for c, p, s in zip(center, t["position"], scale)]}
                          for t in call["transforms"])
            continue  # auto-grouped world-space placements keep their original tight bounds
        radius = max(math.hypot(*(p * s for p, s in zip(t["position"], scale))) for t in call["transforms"])
        points.extend({"position": [v + sign * radius for v in center]} for sign in (-1, 1))
    return original(points)


def install(namespace):
    """Install once into nc_gds globals; preserve CLI/import entry points."""
    if namespace.get("_nc_gds_performance_installed"):
        return
    original_build = namespace["build_calls"]
    original_hash = namespace["spec_hash"]
    original_bounds = namespace["calls_bounds"]

    def wrapped_build(spec, catalog=None):
        return build_calls(original_build, spec, catalog)

    def wrapped_hash(*args, **kwargs):
        # Include this separately installed source in ncli's existing build cache.
        digest = hashlib.sha1(original_hash(*args, **kwargs).encode("ascii"))
        digest.update(Path(__file__).read_bytes())
        return digest.hexdigest()[:16]

    namespace["build_calls"] = wrapped_build
    namespace["spec_hash"] = wrapped_hash
    namespace["calls_bounds"] = lambda calls: _bounds(original_bounds, calls)
    namespace["_nc_gds_performance_installed"] = True
