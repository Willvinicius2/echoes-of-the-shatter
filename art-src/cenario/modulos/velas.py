"""Módulo 3D da Cripta: aglomerado de velas de cera derretida (referência: referencias-cripta/objetos.png).
blender -b --factory-startup -P velas.py -- <saida.glb> [previa.png]
Metros, pivô no centro da base, +Z para cima no Blender. Cera = uma malha só (voxel remesh une velas, escorridos e poça),
cor por vértice (cera mais amarela na poça e nos escorridos); chama emissiva separada, estilizada."""
import bpy, bmesh, math, sys, random
from mathutils import Vector, noise

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "SM_Cripta_Velas.glb"
PREV = argv[1] if len(argv) > 1 else None
random.seed(11)
bpy.ops.wm.read_factory_settings(use_empty=True)

# (x, y, raio, altura) — 5 velas agrupadas: uma alta, duas médias, duas baixas
VELAS = [(0.00, 0.02, 0.075, 0.46), (-0.17, -0.07, 0.065, 0.27), (0.17, -0.02, 0.060, 0.31),
         (-0.06, -0.19, 0.055, 0.17), (0.09, -0.20, 0.045, 0.12)]

def mk(name, color, rough=0.6, emit=None, strength=0.0, vcol=False):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = strength
    if vcol:
        a = nt.nodes.new("ShaderNodeVertexColor"); a.layer_name = "Col"
        nt.links.new(a.outputs["Color"], b.inputs["Base Color"])
        try: b.inputs["Subsurface Weight"].default_value = 0.25; b.inputs["Subsurface Radius"].default_value = (0.5, 0.35, 0.2)
        except KeyError: pass
    return m

M_CERA = mk("M_Cera", (0.88, 0.80, 0.62), 0.55, vcol=True)
M_PAVIO = mk("M_Pavio", (0.03, 0.025, 0.02), 0.9)
M_CHAMA = mk("M_Chama", (1.0, 0.5, 0.1), 0.5, emit=(1.0, 0.42, 0.06), strength=3.5)

parts = []
def blob(loc, scale, sub=2, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=1, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = scale; bpy.ops.object.transform_apply(scale=True); parts.append(o); return o

# corpo de cada vela: cilindro levemente cônico (mais largo na base), 28 lados, topo com borda derretida
for (x, y, r, h) in VELAS:
    bpy.ops.mesh.primitive_cone_add(vertices=28, radius1=r * 1.12, radius2=r * 0.97, depth=h, location=(x, y, 0.03 + h / 2))
    o = bpy.context.object
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 0.01], cuts=8, use_grid_fill=True)
    for v in bm.verts:
        ang = math.atan2(v.co.y, v.co.x); t = (v.co.z + h / 2) / h
        w = noise.noise(Vector((x * 9 + math.cos(ang) * 1.4, y * 9 + math.sin(ang) * 1.4, v.co.z * 7)))
        k = 1 + 0.07 * w * (0.4 + t)
        v.co.x *= k; v.co.y *= k
        if t > 0.94:   # borda de cima: lábio derretido, ondulado, com cavidade no meio
            rr = math.hypot(v.co.x, v.co.y)
            v.co.z += 0.010 * math.sin(ang * 3 + x * 20) + (-0.03 if rr < r * 0.6 else 0.012)
    bm.to_mesh(o.data); bm.free()
    parts.append(o)
    # escorridos: gotas alongadas coladas na lateral, descendo do topo, com bulbo na ponta
    n = 6 + int(r * 60)
    for i in range(n):
        a = random.uniform(0, 2 * math.pi) + i * 2 * math.pi / n * 0.5
        ln = random.uniform(0.3, 0.85) * h
        rr = r * 0.98
        cx, cy = x + rr * math.cos(a), y + rr * math.sin(a)
        zt = 0.03 + h - random.uniform(0.0, 0.03)
        w = random.uniform(0.020, 0.032)
        blob((cx, cy, zt - ln / 2), (w, w, ln / 2), 2)                                  # fio
        blob((cx, cy, zt - ln), (w * 1.45, w * 1.45, w * 1.7), 2)                       # bulbo
    # pavio
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.006, depth=0.05, location=(x, y, 0.03 + h + 0.005))
    p = bpy.context.object; p.data.materials.append(M_PAVIO); parts.append(("pavio", p))

# poça de cera: lajota irregular de gotas achatadas ao redor da base
bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=0.36, depth=0.045, location=(0, -0.06, 0.0225))
pc = bpy.context.object; bm = bmesh.new(); bm.from_mesh(pc.data)
for v in bm.verts:
    ang = math.atan2(v.co.y, v.co.x)
    k = 0.72 + 0.28 * noise.noise(Vector((math.cos(ang) * 1.6 + 5, math.sin(ang) * 1.6 + 5, 0))) + 0.05 * math.sin(ang * 7)
    v.co.x *= k * 1.0; v.co.y *= k * 0.88
bm.to_mesh(pc.data); bm.free(); parts.append(pc)
for i in range(14):
    a = i * 2 * math.pi / 14 + random.uniform(-0.2, 0.2); d = random.uniform(0.24, 0.34)
    s = random.uniform(0.05, 0.10)
    blob((math.cos(a) * d, -0.06 + math.sin(a) * d * 0.88, 0.02), (s * 1.3, s, 0.028))

# separar peças de cera dos pavios e juntar
wicks = [p[1] for p in parts if isinstance(p, tuple)]
wax = [p for p in parts if not isinstance(p, tuple)]
bpy.ops.object.select_all(action='DESELECT')
for o in wax: o.select_set(True)
bpy.context.view_layer.objects.active = wax[0]; bpy.ops.object.join()
cera = bpy.context.object; cera.name = "Cera"
cera.data.materials.clear(); cera.data.materials.append(M_CERA)
# união suave: voxel remesh, depois suaviza e reduz
bpy.ops.object.mode_set(mode='OBJECT')
cera.data.remesh_voxel_size = 0.0055; bpy.ops.object.voxel_remesh()
sm = cera.modifiers.new("s", 'SMOOTH'); sm.factor = 0.6; sm.iterations = 3
bpy.ops.object.modifier_apply(modifier="s")
dc = cera.modifiers.new("d", 'DECIMATE'); dc.ratio = 0.05
bpy.ops.object.modifier_apply(modifier="d")
bpy.ops.object.shade_smooth()

# cor por vértice: base marfim, amarelada e mais escura perto do chão/poça, ruído fino
col = cera.data.color_attributes.new("Col", 'FLOAT_COLOR', 'POINT')
for i, v in enumerate(cera.data.vertices):
    low = max(0.0, min(1.0, 1 - v.co.z / 0.14))
    n = noise.noise(v.co * 38) * 0.5 + 0.5
    n2 = noise.noise(v.co * 9) * 0.5 + 0.5
    base = Vector((0.90, 0.82, 0.64)); amar = Vector((0.80, 0.62, 0.34))
    c = base.lerp(amar, low * 0.7 + n2 * 0.25) * (0.86 + 0.14 * n)
    col.data[i].color = (c.x ** 1.0, c.y ** 1.0, c.z ** 1.0, 1)

# chamas: gota estilizada alongada, mais larga embaixo, com curvatura leve; uma por vela
flames = []
for (x, y, r, h) in VELAS:
    top = 0.03 + h
    f = blob((x, y, top + 0.075), (0.024, 0.024, 0.07), 3)
    parts.remove(f)
    bm = bmesh.new(); bm.from_mesh(f.data)
    for v in bm.verts:
        t = (v.co.z - (top)) / 0.15
        if t > 0.35: s = max(0.0, 1 - (t - 0.35) * 1.5) ** 0.7; v.co.x = x + (v.co.x - x) * s; v.co.y = y + (v.co.y - y) * s
        v.co.x += 0.01 * max(0, t) ** 2
    bm.to_mesh(f.data); bm.free(); f.data.materials.append(M_CHAMA); flames.append(f)

bpy.ops.object.select_all(action='DESELECT')
allo = [cera] + wicks + flames
for o in allo: o.select_set(True)
bpy.context.view_layer.objects.active = cera; bpy.ops.object.join()
final = bpy.context.object; final.name = "SM_Cripta_Velas"
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
final.data.validate(); tris = sum(len(p.vertices) - 2 for p in final.data.polygons)
print("tris", tris, "dim", tuple(round(d, 3) for d in final.dimensions))
bpy.ops.export_scene.gltf(filepath=OUT, use_selection=True, export_format='GLB', export_yup=True, export_vertex_color='ACTIVE')

if PREV:
    sc = bpy.context.scene
    sc.world = bpy.data.worlds.new("w"); sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.02, 0.03, 1)
    for loc, en, colr in (((0.7, -0.9, 0.9), 40, (1, 0.6, 0.3)), ((-1, -0.6, 0.6), 15, (0.5, 0.6, 1))):
        l = bpy.data.objects.new("l", bpy.data.lights.new("l", 'POINT')); l.data.energy = en; l.data.color = colr; l.location = loc
        sc.collection.objects.link(l)
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam)
    cam.location = (0.95, -1.25, 0.75); cam.rotation_euler = (Vector((0, -0.05, 0.25)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.device = 'CPU'; sc.cycles.use_denoising = False; sc.render.resolution_x = 800; sc.render.resolution_y = 800
    sc.render.filepath = PREV; bpy.ops.render.render(write_still=True)
