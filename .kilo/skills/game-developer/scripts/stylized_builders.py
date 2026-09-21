import bpy
import bmesh
import math

def safe_clean_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh, do_unlink=True)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat, do_unlink=True)

def get_or_create_material(name, hex_color, metallic=0.0, roughness=0.8):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        r = int(hex_color[1:3], 16) / 255.0
        g = int(hex_color[3:5], 16) / 255.0
        b = int(hex_color[5:7], 16) / 255.0
        bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
    return mat

def apply_bevel(obj, width=0.02, segments=1):
    bev = obj.modifiers.new(name="Bevel", type='BEVEL')
    bev.width = width
    bev.segments = segments
    bev.limit_method = 'ANGLE'
    bev.angle_limit = math.radians(35)

def build_stylized_crate(width=0.7, depth=0.7, height=0.6):
    mat_wood = get_or_create_material("Mat_DarkWood", "#3B2618", metallic=0.0, roughness=0.85)
    mat_iron = get_or_create_material("Mat_ForgedIron", "#1E1E22", metallic=0.85, roughness=0.45)

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, height / 2.0))
    hull = bpy.context.active_object
    hull.name = "Crate_Hull"
    hull.scale = (width * 0.94, depth * 0.94, height * 0.94)
    bpy.ops.object.transform_apply(scale=True)
    hull.data.materials.append(mat_wood)
    apply_bevel(hull, width=0.015)

    post_w = 0.07
    post_h = height
    offsets = [
        (-width/2 + post_w/2, -depth/2 + post_w/2),
        ( width/2 - post_w/2, -depth/2 + post_w/2),
        (-width/2 + post_w/2,  depth/2 - post_w/2),
        ( width/2 - post_w/2,  depth/2 - post_w/2),
    ]
    posts = []
    for x, y in offsets:
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, y, post_h / 2.0))
        p = bpy.context.active_object
        p.scale = (post_w, post_w, post_h)
        bpy.ops.object.transform_apply(scale=True)
        p.data.materials.append(mat_wood)
        apply_bevel(p, width=0.01)
        posts.append(p)

    rim_thickness = 0.05
    rims = []
    for z in [rim_thickness/2.0, height - rim_thickness/2.0]:
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, z))
        r = bpy.context.active_object
        r.scale = (width, depth, rim_thickness)
        bpy.ops.object.transform_apply(scale=True)
        r.data.materials.append(mat_iron)
        apply_bevel(r, width=0.008)
        rims.append(r)

    ctx_objs = [hull] + posts + rims
    bpy.ops.object.select_all(action='DESELECT')
    for o in ctx_objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = hull
    bpy.ops.object.join()
    hull.name = "Prop_Crate_Stylized"
    return hull

def build_stylized_barricade(width=1.2, height=2.0):
    mat_wood = get_or_create_material("Mat_PlankWood", "#442D1C", metallic=0.0, roughness=0.88)
    mat_iron = get_or_create_material("Mat_StudIron", "#1A1A1E", metallic=0.9, roughness=0.4)

    plank_data = [
        (0.40, 0.18, 0.045,  1.8),
        (0.95, 0.22, 0.050, -2.2),
        (1.50, 0.19, 0.042,  1.2),
    ]

    created = []
    for z, h_plank, thick, angle in plank_data:
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, z))
        pl = bpy.context.active_object
        pl.scale = (width * 1.05, thick, h_plank)
        bpy.ops.object.transform_apply(scale=True)
        pl.rotation_euler.y = math.radians(angle)
        bpy.ops.object.transform_apply(rotation=True)
        pl.data.materials.append(mat_wood)
        apply_bevel(pl, width=0.015)
        created.append(pl)

        for x_sign in [-1, 1]:
            stud_x = x_sign * (width * 0.45)
            for z_off in [-h_plank * 0.25, h_plank * 0.25]:
                bpy.ops.mesh.primitive_cylinder_add(
                    vertices=6, radius=0.018, depth=0.02,
                    location=(stud_x, -thick/2.0 - 0.008, z + z_off)
                )
                stud = bpy.context.active_object
                stud.rotation_euler.x = math.radians(90)
                bpy.ops.object.transform_apply(rotation=True)
                stud.data.materials.append(mat_iron)
                created.append(stud)

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0.02, 1.0))
    brace = bpy.context.active_object
    brace.scale = (0.12, 0.04, 1.7)
    bpy.ops.object.transform_apply(scale=True)
    brace.rotation_euler.y = math.radians(35)
    bpy.ops.object.transform_apply(rotation=True)
    brace.data.materials.append(mat_wood)
    apply_bevel(brace, width=0.012)
    created.append(brace)

    bpy.ops.object.select_all(action='DESELECT')
    for o in created:
        o.select_set(True)
    bpy.context.view_layer.objects.active = created[0]
    bpy.ops.object.join()
    created[0].name = "Prop_Barricade_Stylized"
    return created[0]
