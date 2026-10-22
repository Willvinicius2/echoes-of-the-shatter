"""Módulo 3D do braseiro da Cripta, versão detalhada para o Godot (referência: referencias-cripta/objeto.png).
Roda com o Blender (ou com o módulo `bpy` do pip):
  blender -b --factory-startup -P braseiro_godot.py -- <saida.glb> [pasta_previas]
Metros, pivô no centro da base, +Z para cima no Blender (o glTF vira Y-up). Altura ~1,5 m; a chama fica por conta do FirePool.
Arestas chanfradas em 2 segmentos, desgaste (lascas e amassados) por ruído determinístico, rebites, cintas e brasas."""
import bpy, bmesh, math, sys, os, random
from mathutils import Vector, noise

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "SM_Cripta_Braseiro.glb"
PREV = argv[1] if len(argv) > 1 else None
random.seed(11)

bpy.ops.wm.read_factory_settings(use_empty=True)
objs = []

def mat(name, color, metal=0.7, rough=0.5, emit=None, strength=3.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metal; b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = strength
    return m

IRON = mat("M_Braseiro_Ferro", (0.075, 0.07, 0.08), 0.7, 0.5)
TRIM = mat("M_Braseiro_Cinta", (0.16, 0.12, 0.09), 0.6, 0.4)       # cintas e rebites: ferro mais quente
WORN = mat("M_Braseiro_Gasto", (0.27, 0.21, 0.15), 0.8, 0.32)      # arestas lascadas, metal vivo
ASH = mat("M_Braseiro_Cinza", (0.05, 0.045, 0.045), 0.0, 1.0)
EMBER = mat("M_Braseiro_Brasa", (0.35, 0.05, 0.01), 0.0, 0.8, emit=(1.0, 0.22, 0.03), strength=1.6)

def finish(o, material, bev=0.0, wear=0.0, cut=0.0, seed=0, smooth=False, chip=0.0):
    """Chanfro de 2 segmentos, subdivisão leve e desgaste por ruído (mais forte perto das arestas)."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    if bev:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bev, segments=2, profile=0.55, affect='EDGES')
    if cut:
        long_edges = [e for e in bm.edges if e.calc_length() > cut]
        bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=1, use_grid_fill=True)
    if wear:
        bm.verts.ensure_lookup_table(); bm.normal_update()
        for v in bm.verts:
            edge_k = 1.0 - min(1.0, sum(f.normal.dot(v.normal) for f in v.link_faces) / max(1, len(v.link_faces)))
            n = noise.noise(v.co * 9.0 + Vector((seed, seed * 0.7, 0)))
            v.co += v.normal * n * wear * (0.35 + 2.5 * edge_k)
    if chip:                                          # lascas: cantos escolhidos puxados para dentro, quebrando a silhueta
        c = sum((v.co for v in bm.verts), Vector()) / max(1, len(bm.verts))
        for v in bm.verts:
            if len(v.link_edges) >= 3 and random.random() < chip:
                v.co += (c - v.co).normalized() * random.uniform(0.012, 0.03)
    bm.to_mesh(o.data); bm.free()
    o.data.materials.append(material)
    for p in o.data.polygons: p.use_smooth = smooth
    objs.append(o); return o

def box(loc, size, rot=(0, 0, 0), m=IRON, bev=0.014, wear=0.003, cut=0.09, seed=0, chip=0.22):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = size; bpy.ops.object.transform_apply(scale=True)
    return finish(o, m, bev, wear, cut, seed, chip=chip)

def cone(loc, r, h, sides=4, rot=(0, 0, 0), m=IRON, r2=0.0, wear=0.004, seed=0):
    bpy.ops.mesh.primitive_cone_add(vertices=sides, radius1=r, radius2=r2, depth=h, location=(loc[0], loc[1], loc[2] + h / 2), rotation=rot)
    return finish(bpy.context.object, m, 0.008, wear, 0.07, seed)

def rivet(loc, r=0.022, rot=(0, 0, 0), m=WORN):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=4, radius=r, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = (1, 1, 0.55); bpy.ops.object.transform_apply(scale=True)
    return finish(o, m)

def ring(z, R, r, m=TRIM, seg=24):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=seg, minor_segments=8, location=(0, 0, z))
    o = bpy.context.object
    return finish(o, m, 0, 0.004, 0, 3, smooth=False)

# ---- pernas: 4 colunas com sapata escalonada, cintas, rebites, capitel e ponta de canto
LEG = 0.42
for i, (sx, sy) in enumerate([(-1, -1), (-1, 1), (1, -1), (1, 1)]):
    x, y = sx * LEG, sy * LEG
    box((x, y, 0.045), (0.46, 0.46, 0.09), m=IRON, bev=0.02, wear=0.01, seed=i)                 # sapata baixa
    box((x, y, 0.145), (0.38, 0.38, 0.11), m=TRIM, bev=0.016, seed=i + 4)                       # sapata alta
    box((x, y, 0.62), (0.22, 0.22, 0.80), m=IRON, bev=0.018, wear=0.008, seed=i + 8)            # fuste
    box((x, y, 0.30), (0.27, 0.27, 0.05), m=WORN, bev=0.01, seed=i + 12)                        # cinta de ferro vivo
    box((x, y, 0.80), (0.27, 0.27, 0.05), m=WORN, bev=0.01, seed=i + 16)
    box((x, y, 0.96), (0.32, 0.32, 0.10), m=TRIM, bev=0.016, seed=i + 20)                       # capitel
    cone((x, y, 1.01), 0.11, 0.22, rot=(0, 0, math.pi / 4), seed=i)                              # ponta de canto
    for k in range(4):                                                                           # rebites nas faces do fuste
        a = k * math.pi / 2
        for z in (0.40, 0.70):
            rivet((x + 0.114 * math.cos(a), y + 0.114 * math.sin(a), z), rot=(0, math.pi / 2, a))
# ---- travessas em X e diamante central
for j, ang in enumerate((math.pi / 4, -math.pi / 4)):
    box((0, 0, 0.38), (1.28, 0.075, 0.075), rot=(0, 0, ang), m=IRON, bev=0.012, seed=30 + j, cut=0.1)
box((0, 0, 0.38), (0.22, 0.22, 0.22), rot=(math.pi / 4, 0, math.pi / 4), m=TRIM, bev=0.02, seed=33)
cone((0, 0, 0.14), 0.12, 0.24, rot=(math.pi, 0, math.pi / 4), seed=34)
ring(0.38, 0.17, 0.018, m=WORN, seg=16)

# ---- bacia martelada (hemisfério subdividido, com amassados) e lábio
bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=9, radius=0.68, location=(0, 0, 1.12))
bowl = bpy.context.object
bm = bmesh.new(); bm.from_mesh(bowl.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > 1.121 - 1.12 + 0.02], context='VERTS')
bm.to_mesh(bowl.data); bm.free()
bowl.scale = (1, 1, 0.55); bpy.ops.object.transform_apply(scale=True)
bm = bmesh.new(); bm.from_mesh(bowl.data); bm.normal_update()
for v in bm.verts:                                   # marteladas: ruído de baixa e de alta frequência
    v.co += v.normal * random.uniform(-0.014, 0.014)   # facetas marteladas, sem suavizar
bm.to_mesh(bowl.data); bm.free()
bowl.data.materials.append(IRON)
for p in bowl.data.polygons: p.use_smooth = False
objs.append(bowl)
for a in range(4):                                   # cintas meridianas sob a bacia
    box((0, 0, 0.97), (0.06, 1.32, 0.05), rot=(0, 0, a * math.pi / 4), m=TRIM, bev=0.01, wear=0.004, seed=40 + a, cut=0.12)

# ---- gaiola: dois anéis, ripas com rebites e cintas verticais
Z0, Z1 = 1.12, 1.40
ring(Z0 + 0.03, 0.68, 0.04); ring(Z1 - 0.03, 0.68, 0.04)
ring(Z0 + 0.075, 0.70, 0.014, m=WORN, seg=32)
N = 14
for i in range(N):
    a = i * 2 * math.pi / N
    x, y = 0.68 * math.cos(a), 0.68 * math.sin(a)
    box((x, y, (Z0 + Z1) / 2), (0.05, 0.05, Z1 - Z0), rot=(0, 0, a), m=IRON, bev=0.008, wear=0.003, seed=50 + i, cut=0.2)
    if i % 2 == 0:
        box((x, y, (Z0 + Z1) / 2 + 0.02), (0.075, 0.075, 0.075), rot=(math.pi / 4, 0, a), m=TRIM, bev=0.008, wear=0.003, seed=70 + i, cut=0.2)
    else:
        rivet((x + 0.027 * math.cos(a), y + 0.027 * math.sin(a), (Z0 + Z1) / 2), r=0.018, rot=(0, math.pi / 2, a))
# ---- espigões no aro: 8 médios + 4 altos nos cantos com espinhos laterais
for i in range(8):
    a = (i + 0.5) * 2 * math.pi / 8
    cone((0.70 * math.cos(a), 0.70 * math.sin(a), Z1 - 0.02), 0.075, 0.20 + 0.04 * ((i * 7) % 3), sides=4, rot=(0, 0, a), seed=80 + i)
for i, (sx, sy) in enumerate([(-1, -1), (-1, 1), (1, -1), (1, 1)]):
    a = math.atan2(sy, sx)
    x, y = 0.74 * math.cos(a), 0.74 * math.sin(a)
    box((x, y, 1.20), (0.14, 0.14, 0.40), rot=(0, 0, a), m=IRON, bev=0.016, wear=0.008, seed=90 + i)
    box((x, y, 1.40), (0.18, 0.18, 0.04), rot=(0, 0, a), m=WORN, bev=0.008, seed=94 + i)
    cone((x, y, 1.42), 0.11, 0.30, sides=4, rot=(0, 0, a), seed=98 + i)
    for sgn in (-1, 1):
        cone((x + sgn * 0.11 * -math.sin(a), y + sgn * 0.11 * math.cos(a), 1.26), 0.05, 0.16, sides=4, rot=(sgn * math.pi / 2 * 0.9, 0, a), seed=100 + i)
    for z in (1.12, 1.30):
        rivet((x + 0.073 * math.cos(a), y + 0.073 * math.sin(a), z), r=0.02, rot=(0, math.pi / 2, a))

# ---- correntes penduradas sob a bacia (elos alternados) entre as pernas
for k in range(4):
    a = k * math.pi / 2 + math.pi / 4
    for j in range(5):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.045, minor_radius=0.012, major_segments=10, minor_segments=5,
                                         location=(0.30 * math.cos(a), 0.30 * math.sin(a), 0.93 - j * 0.075),
                                         rotation=(math.pi / 2, 0, a + (j % 2) * math.pi / 2))
        o = bpy.context.object; o.scale = (1, 1.5, 1); bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        finish(o, WORN)

# ---- cinza no fundo e brasas irregulares
bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.60, depth=0.05, location=(0, 0, 1.17))
finish(bpy.context.object, ASH, 0, 0.012, 0.1, 7)
for i in range(11):
    r = 0.36 * math.sqrt(random.random()); a = random.random() * 2 * math.pi
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.09 + random.random() * 0.07, location=(r * math.cos(a), r * math.sin(a), 1.22 + random.random() * 0.08))
    o = bpy.context.object; o.scale = (1, 1, 0.65); o.rotation_euler = (random.random() * 3, random.random() * 3, random.random() * 3)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    finish(o, EMBER, 0, 0.03, 0, i)

# ---- juntar por material (1 malha, 5 materiais) e exportar
for o in bpy.data.objects: o.select_set(o in objs)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.object.join()
body = bpy.context.object; body.name = "SM_Cripta_Braseiro"
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bm = bmesh.new(); bm.from_mesh(body.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0004)
bm.to_mesh(body.data); bm.free()
bpy.ops.object.shade_flat()                          # facetado pintado à mão
tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
bpy.ops.object.select_all(action='DESELECT'); body.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, use_selection=True, export_format='GLB', export_yup=True)
print("tris", tris, "->", OUT)

if PREV:
    os.makedirs(PREV, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get("SAMPLES", "24")); sc.cycles.device = 'CPU'
    sc.view_settings.view_transform = 'Standard'; sc.render.resolution_x = 800; sc.render.resolution_y = 800
    sc.world = bpy.data.worlds.new("w"); sc.world.color = (0.03, 0.03, 0.045)
    for loc, en, col in (((3, -3, 5), 3.0, (1, 0.95, 0.9)), ((-3, 2, 2), 1.5, (0.5, 0.6, 1.0))):
        bpy.ops.object.light_add(type='SUN', location=loc); L = bpy.context.object
        L.data.energy = en; L.data.color = col; L.rotation_euler = (Vector((0, 0, 0.8)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    bpy.ops.object.light_add(type='POINT', location=(0, 0, 1.3)); bpy.context.object.data.energy = 120; bpy.context.object.data.color = (1, 0.5, 0.15)
    for name, loc, tgt in (("braseiro_tres_quartos", (2.6, -2.6, 2.2), (0, 0, 0.8)), ("braseiro_frente", (0, -3.6, 1.0), (0, 0, 0.8)),
                           ("braseiro_close_borda", (0.6, -1.5, 1.7), (0.1, 0, 1.3)), ("braseiro_cima", (0.01, -0.8, 3.0), (0, 0, 1.2))):
        bpy.ops.object.camera_add(location=loc); cam = bpy.context.object
        cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        cam.data.lens = 45 if "close" not in name else 60
        sc.camera = cam; sc.render.filepath = os.path.join(PREV, name + ".png")
        bpy.ops.render.render(write_still=True)
