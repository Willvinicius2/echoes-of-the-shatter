"""Utilidades e contrato de medidas do estandarte (compartilhado pelas partes).
Metros, +Z para cima no Blender, frente do módulo = +Y. Pivô no centro da base do poste (x=PX do módulo, origem do mundo)."""
import bpy, bmesh, math, os, random
from mathutils import Vector

# ---- contrato de medidas (todas as partes usam estes valores)
PX = -0.64          # eixo do poste (x)
POST_TOP = 3.15     # topo do fuste
ARM_Z = 2.88        # altura do eixo do braço
AX1 = 0.74          # ponta direita do braço
W = 0.84            # largura do pano no topo
TOP = ARM_Z - 0.06  # linha de cima do pano
LEN = 2.25          # comprimento nominal do pano
CX = 0.0            # centro x do pano
TEX_DIR = os.environ.get("ESTANDARTE_TEX", "/tmp/estandarte_tex")  # onde as partes gravam PNGs
os.makedirs(TEX_DIR, exist_ok=True)
objs = []           # objetos criados (a main junta e exporta)

def rng(seed): return random.Random(seed)

def mat(name, color, metal=0.0, rough=0.85, image=None, normal=None, alpha_clip=False):
    """Material Principled. image/normal = caminhos de PNG (vai embutido no .glb). alpha_clip usa o alfa do PNG (MASK)."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metal; b.inputs["Roughness"].default_value = rough
    if image:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(image); t.image.pack()
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
        if alpha_clip:
            nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"]); m.blend_method = 'BLEND' if False else m.blend_method
    if normal:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(normal); t.image.pack(); t.image.colorspace_settings.name = 'Non-Color'
        n = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(t.outputs["Color"], n.inputs["Color"]); nt.links.new(n.outputs["Normal"], b.inputs["Normal"])
    return m

def add(o, m):
    if m is not None: o.data.materials.append(m)
    objs.append(o); return o

def new_obj(name, bm_or_mesh, m=None):
    if isinstance(bm_or_mesh, bmesh.types.BMesh):
        me = bpy.data.meshes.new(name); bm_or_mesh.to_mesh(me); bm_or_mesh.free()
    else: me = bm_or_mesh
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return add(o, m)

def bevel_obj(o, width=0.01, segments=2, angle=30):
    """Bevel real só nas arestas vivas (ângulo), aplicado."""
    mod = o.modifiers.new("bev", 'BEVEL'); mod.width = width; mod.segments = segments
    mod.limit_method = 'ANGLE'; mod.angle_limit = math.radians(angle); mod.harden_normals = False
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier="bev")

def box(loc, size, m=None, rot=(0, 0, 0), bev=0.01, seg=2):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = size; bpy.ops.object.transform_apply(scale=True)
    if bev: bevel_obj(o, bev, seg)
    return add(o, m)

def cyl(loc, r, h, m=None, sides=12, r2=None, rot=(0, 0, 0), bev=0):
    if r2 is None: bpy.ops.mesh.primitive_cylinder_add(vertices=sides, radius=r, depth=h, location=loc, rotation=rot)
    else: bpy.ops.mesh.primitive_cone_add(vertices=sides, radius1=r, radius2=r2, depth=h, location=loc, rotation=rot)
    o = bpy.context.object
    if bev: bevel_obj(o, bev, 2)
    return add(o, m)

def shade_smooth_auto(o, angle=35):
    me = o.data
    for p in me.polygons: p.use_smooth = True
    if hasattr(me, "use_auto_smooth"): me.use_auto_smooth = True
    try: bpy.ops.object.shade_auto_smooth(angle=math.radians(angle))
    except Exception: pass

def chip_corners(o, n, size, seed, depth=0.5):
    """Lascas reais: corta cantos/arestas de um objeto de pedra com cubos girados (boolean DIFFERENCE aplicado)."""
    r = rng(seed); dx, dy, dz = o.dimensions
    c = o.location
    for i in range(n):
        sx, sy, sz = r.choice((-1, 1)), r.choice((-1, 1)), r.choice((-1, 1))
        p = (c.x + sx * dx / 2, c.y + sy * dy / 2, c.z + sz * dz / 2)
        s = size * r.uniform(0.6, 1.4)
        bpy.ops.mesh.primitive_cube_add(size=1, location=p, rotation=(r.uniform(0, 1.5), r.uniform(0, 1.5), r.uniform(0, 1.5)))
        cut = bpy.context.object; cut.scale = (s, s * r.uniform(0.7, 1.3), s * r.uniform(0.7, 1.3)); bpy.ops.object.transform_apply(scale=True)
        mod = o.modifiers.new("chip", 'BOOLEAN'); mod.operation = 'DIFFERENCE'; mod.object = cut; mod.solver = 'EXACT'
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier="chip")
        bpy.data.objects.remove(cut, do_unlink=True)
