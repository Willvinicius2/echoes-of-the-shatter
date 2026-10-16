"""Biblioteca graybox: construtor de malhas por primitivas, materiais planos, exportacao e previa."""
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix, Euler

ROOT = "D:/openclaude/EchoesOfTheShatter/art-src/graybox"
FBX = ROOT + "/fbx"
PREV = ROOT + "/previews"
for d in (FBX, PREV):
    os.makedirs(d, exist_ok=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.unit_settings.system = 'METRIC'
    s.unit_settings.scale_length = 1.0


def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexrgba(h):
    h = h.lstrip('#')
    r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return (srgb_to_lin(r), srgb_to_lin(g), srgb_to_lin(b), 1.0)


def material(name, hexcolor, emit=False):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    col = hexrgba(hexcolor)
    bsdf.inputs["Base Color"].default_value = col
    bsdf.inputs["Roughness"].default_value = 0.85
    if emit:
        bsdf.inputs["Emission Color"].default_value = col
        bsdf.inputs["Emission Strength"].default_value = 1.0
    m.diffuse_color = col
    return m


def rotm(rot):
    if rot is None:
        return Matrix.Identity(3)
    if isinstance(rot, Matrix):
        return rot.to_3x3()
    return Euler((math.radians(rot[0]), math.radians(rot[1]), math.radians(rot[2])), 'XYZ').to_matrix()


def aim(a, b):
    """Matriz 3x3 que alinha +Z ao vetor a->b."""
    d = (Vector(b) - Vector(a))
    return d.to_track_quat('Z', 'Y').to_matrix()


class Builder:
    """Acumula primitivas num unico bmesh, com slots de material e grupos de vertices (skinning rigido)."""

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.mats = []
        self.groups = []
        self.deform = self.bm.verts.layers.deform.verify()

    def add(self, shape, dim, loc, color, rot=None, bone=None, taper=1.0, seg=8, matname=None, emit=False):
        bm = self.bm
        if shape == 'box':
            r = bmesh.ops.create_cube(bm, size=1.0)
        elif shape == 'cyl':
            r = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                                      radius1=0.5, radius2=0.5 * taper, depth=1.0)
        elif shape == 'sph':
            r = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(2, seg // 2), radius=0.5)
        else:
            raise ValueError(shape)
        verts = r['verts']
        S = Matrix.Diagonal(Vector((dim[0], dim[1], dim[2], 1.0)))
        R = rotm(rot).to_4x4()
        T = Matrix.Translation(Vector(loc))
        bmesh.ops.transform(bm, matrix=T @ R @ S, verts=verts)
        mname = matname or ("GB_" + color.lstrip('#').upper())
        mat = material(mname, color, emit)
        if mat not in self.mats:
            self.mats.append(mat)
        mi = self.mats.index(mat)
        faces = {f for v in verts for f in v.link_faces}
        for f in faces:
            f.material_index = mi
            f.smooth = False
        if bone:
            if bone not in self.groups:
                self.groups.append(bone)
            gi = self.groups.index(bone)
            for v in verts:
                v[self.deform][gi] = 1.0

    def limb(self, a, b, r0, color, bone=None, taper=1.0, seg=8, **kw):
        a, b = Vector(a), Vector(b)
        self.add('cyl', (r0 * 2, r0 * 2, (b - a).length), (a + b) / 2, color, rot=aim(a, b), bone=bone, taper=taper, seg=seg, **kw)

    def build(self, coll=None, mesh_name=None):
        me = bpy.data.meshes.new(mesh_name or self.name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(self.name, me)
        (coll or bpy.context.scene.collection).objects.link(ob)
        for g in self.groups:
            ob.vertex_groups.new(name=g)
        return ob


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def bbox(objs):
    pts = []
    for o in objs:
        for c in o.bound_box:
            pts.append(o.matrix_world @ Vector(c))
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def new_coll(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    return c


def export_fbx(objs, path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, global_scale=1.0,
        apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
        bake_space_transform=True, axis_forward='Z', axis_up='Y',
        object_types={'MESH', 'ARMATURE'}, use_mesh_modifiers=True,
        mesh_smooth_type='FACE', add_leaf_bones=False, use_armature_deform_only=False,
        bake_anim=False, path_mode='COPY' if False else 'AUTO')


def save_blend(path):
    bpy.ops.wm.save_as_mainfile(filepath=path)


# ---------- previa ----------
def setup_render(w=1280, h=800):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.film_transparent = False
    sh = sc.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'MATERIAL'
    sh.show_shadows = True
    sh.show_cavity = False
    sc.display.shading.background_type = 'VIEWPORT'
    sc.display.shading.background_color = (0.17, 0.16, 0.2)
    if sc.world is None:
        sc.world = bpy.data.worlds.new("W")
    sc.world.color = (0.17, 0.16, 0.2)
    sc.view_settings.view_transform = 'Standard'


def game_camera(center, dist, ortho_scale=None, yaw=45.0, pitch=-55.0, focal=None):
    """Camera 3/4: yaw 45, pitch -55 (pitch -55 = olhando 55 graus para baixo)."""
    cam = bpy.data.cameras.new("Cam")
    co = bpy.data.objects.new("Cam", cam)
    bpy.context.scene.collection.objects.link(co)
    if ortho_scale:
        cam.type = 'ORTHO'
        cam.ortho_scale = ortho_scale
    else:
        cam.type = 'PERSP'
        cam.lens = focal or 85
    cam.clip_end = 500
    # olhar para o centro vindo do lado -Y rotacionado por yaw; elevacao = -pitch
    el = math.radians(-pitch)
    yw = math.radians(yaw)
    d = Vector((math.sin(yw) * math.cos(el), math.cos(yw) * math.cos(el), math.sin(el))) * dist
    co.location = Vector(center) + d
    direction = Vector(center) - co.location
    co.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = co
    return co


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)
