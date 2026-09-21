import bpy
import sys
import argparse

def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["asset", "scene"], default="asset")
    parser.add_argument("--pivot", choices=["center_bottom", "corner"], default="center_bottom")
    parser.add_argument("--output", default="")
    return parser.parse_args(argv)

def sanitize_asset(pivot_mode="center_bottom"):
    to_delete = [obj for obj in bpy.data.objects if obj.type in {"LIGHT", "CAMERA"}]
    for obj in to_delete:
        bpy.data.objects.remove(obj, do_unlink=True)

    mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    if not mesh_objects:
        return

    bpy.ops.object.select_all(action="DESELECT")
    for obj in mesh_objects:
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
    
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    min_x = min([obj.bound_box[0][0] + obj.location.x for obj in mesh_objects])
    max_x = max([obj.bound_box[6][0] + obj.location.x for obj in mesh_objects])
    min_y = min([obj.bound_box[0][1] + obj.location.y for obj in mesh_objects])
    max_y = max([obj.bound_box[6][1] + obj.location.y for obj in mesh_objects])
    min_z = min([obj.bound_box[0][2] + obj.location.z for obj in mesh_objects])

    if pivot_mode == "corner":
        target_pivot = (min_x, min_y, min_z)
    else:
        target_pivot = ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0, min_z)

    bpy.context.scene.cursor.location = target_pivot
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")
    bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)

    for obj in mesh_objects:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode="OBJECT")

def sanitize_scene():
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    if mesh_objects:
        bpy.ops.object.select_all(action="DESELECT")
        for obj in mesh_objects:
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

def export_glb(filepath):
    if not filepath:
        return
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format="GLB",
        use_selection=False,
        export_apply=True
    )

def main():
    args = parse_args()
    if args.mode == "asset":
        sanitize_asset(args.pivot)
    else:
        sanitize_scene()
    
    if args.output:
        export_glb(args.output)

if __name__ == "__main__":
    main()
