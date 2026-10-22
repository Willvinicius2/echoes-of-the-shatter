"""Módulo 3D: entulho da Cripta (referência: referencias-cripta/objetos.png, pilha de blocos cortados com musgo).
python entulho.py <pasta_saida> [pasta_previas]    (módulo bpy) ou  blender -b --factory-startup -P entulho.py -- <saida> [previas]
Escala em metros (~1,6 x 1,3 m, altura ~0,7 m), pivô no centro da base, +Z para cima no Blender.
Blocos cúbicos chanfrados e tortos, pedras menores espalhadas, musgo nas faces de cima. Materiais M_Pedra/M_PedraEscura recebem a textura triplanar no Godot."""
import bpy, bmesh, math, sys, os, random
from mathutils import Vector, Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = argv[0] if argv else "."
PREV = argv[1] if len(argv) > 1 else None
rnd = random.Random(21)

bpy.ops.wm.read_factory_settings(use_empty=True)
objs = []

def mat(name, color, rough=0.9):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    return m

M_PEDRA = mat("M_Pedra", (0.42, 0.40, 0.38))
M_ESCURA = mat("M_PedraEscura", (0.20, 0.19, 0.19))
M_MUSGO = mat("M_Musgo", (0.12, 0.17, 0.05), 1.0)

def bloco(loc, size, rot, m, jit=0.05, bev=0.035):
    """Cubo subdividido com vértices deslocados e chanfro: pedra cortada e gasta, não caixa perfeita."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
        v.co += Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * jit * min(size)
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bev * min(size), segments=2, affect='EDGES')
    me = bpy.data.meshes.new("b"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("b", me); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot
    me.materials.append(m)
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    for p in me.polygons: p.use_smooth = False
    objs.append(o); return o

def musgo(loc, r, esc=(1, 1, 0.22)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=r, location=loc)
    o = bpy.context.object; o.scale = esc
    for v in o.data.vertices:
        v.co += Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.3, 0.3))) * r * 0.25
    bpy.ops.object.transform_apply(scale=True); o.data.materials.append(M_MUSGO); objs.append(o)

# ---- pilha principal: blocos grandes empilhados, de baixo para cima
H = math.radians
bloco((-0.25, -0.05, 0.22), (0.80, 0.70, 0.44), (0, 0, H(12)), M_PEDRA)
bloco((0.40, 0.10, 0.19), (0.62, 0.66, 0.38), (0, H(3), H(-20)), M_ESCURA)
bloco((-0.10, 0.50, 0.17), (0.55, 0.45, 0.34), (H(4), 0, H(35)), M_PEDRA)
bloco((0.10, -0.50, 0.15), (0.60, 0.40, 0.30), (0, H(-4), H(-8)), M_ESCURA)
bloco((-0.20, 0.00, 0.60), (0.58, 0.52, 0.40), (H(6), H(-8), H(28)), M_PEDRA)
bloco((0.38, 0.12, 0.50), (0.46, 0.42, 0.34), (H(-9), H(7), H(-40)), M_PEDRA)
bloco((0.00, -0.38, 0.42), (0.40, 0.36, 0.30), (H(10), H(12), H(52)), M_ESCURA)
bloco((-0.05, 0.05, 0.92), (0.34, 0.30, 0.26), (H(14), H(-10), H(15)), M_PEDRA)   # cume torto
# ---- pedras soltas ao redor e lascas
for _ in range(14):
    a = rnd.uniform(0, 6.283); r = rnd.uniform(0.7, 1.0)
    s = rnd.uniform(0.07, 0.2)
    bloco((math.cos(a) * r * 1.1, math.sin(a) * r * 0.85, s * 0.45), (s * rnd.uniform(1.0, 1.7), s * rnd.uniform(0.8, 1.4), s * rnd.uniform(0.6, 1.0)),
          (rnd.uniform(-.3, .3), rnd.uniform(-.3, .3), rnd.uniform(0, 6.28)), M_PEDRA if rnd.random() > 0.4 else M_ESCURA, jit=0.12, bev=0.08)
# ---- musgo nos topos e nas fendas
for _ in range(8):
    a = rnd.uniform(0, 6.283); r = rnd.uniform(0.3, 0.9)
    musgo((math.cos(a) * r, math.sin(a) * r * 0.8, 0.03), rnd.uniform(0.07, 0.14), (1.2, 1, 0.3))

# ---- junta, assenta no chão (base em z=0) e centraliza em XY
bpy.ops.object.select_all(action='DESELECT')
for o in objs: o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.object.join()
o = bpy.context.object
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
zs = [v.co.z for v in o.data.vertices]
for v in o.data.vertices: v.co.z -= min(zs)
o.name = "SM_Cripta_Entulho"
# musgo: faces voltadas para cima, em manchas (ruído por posição), pelo slot M_Musgo
if M_MUSGO.name not in [m.name for m in o.data.materials]: o.data.materials.append(M_MUSGO)
mi = [m.name for m in o.data.materials].index(M_MUSGO.name)
from mathutils import noise
for p in o.data.polygons:
    c = p.center
    if p.normal.z > 0.55 and c.z > 0.08 and noise.noise(c * 4.0) > -0.15:
        p.material_index = mi
for p in o.data.polygons: p.use_smooth = False
os.makedirs(OUT, exist_ok=True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "SM_Cripta_Entulho.glb"), use_selection=True, export_format='GLB', export_yup=True)
print("exportado SM_Cripta_Entulho", len(o.data.polygons), "faces", tuple(round(d, 2) for d in o.dimensions))

# ---- prévia: materiais procedurais só para o render (o .glb sai com cores sólidas)
if PREV:
    os.makedirs(PREV, exist_ok=True)
    def proc(m, base, mossy=False):
        nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        tc = nt.nodes.new("ShaderNodeTexCoord"); n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 9; n.inputs["Detail"].default_value = 8
        cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (*[c * 0.7 for c in base], 1); cr.color_ramp.elements[1].color = (*[min(1, c * 1.3) for c in base], 1)
        nt.links.new(tc.outputs["Object"], n.inputs["Vector"]); nt.links.new(n.outputs["Fac"], cr.inputs["Fac"])
        nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
        bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.6
        nt.links.new(n.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    proc(M_PEDRA, (0.20, 0.18, 0.16)); proc(M_ESCURA, (0.09, 0.085, 0.085)); proc(M_MUSGO, (0.10, 0.11, 0.025))
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.use_denoising = False
    sc.render.resolution_x = 640; sc.render.resolution_y = 480
    w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.07, 1); sc.world = w
    sun = bpy.data.objects.new("s", bpy.data.lights.new("s", 'SUN')); sun.data.energy = 2.2; sun.rotation_euler = (0.9, 0.2, 0.6); bpy.context.collection.objects.link(sun)
    fill = bpy.data.objects.new("f", bpy.data.lights.new("f", 'AREA')); fill.data.energy = 40; fill.data.size = 3; fill.location = (-2, -2, 2); fill.rotation_euler = (1.0, 0, -0.8); bpy.context.collection.objects.link(fill)
    chao = bpy.data.objects.new("g", bpy.data.meshes.new("g")); bpy.context.collection.objects.link(chao)
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=4); bm.to_mesh(chao.data); bm.free()
    chao.data.materials.append(mat("g", (0.07, 0.07, 0.08)))
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); bpy.context.collection.objects.link(cam); sc.camera = cam
    for nome, (x, y, z) in {"a": (2.6, -2.8, 2.0), "b": (-3.0, 1.5, 1.4)}.items():
        cam.location = (x, y, z)
        cam.rotation_euler = (Vector((0, 0, 0.3)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(PREV, f"entulho_{nome}.png"); bpy.ops.render.render(write_still=True)
