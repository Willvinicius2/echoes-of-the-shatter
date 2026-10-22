"""Monta a estátua da Cripta a partir das partes e exporta .glb.
bpy: python build_estatua.py -- <saida.glb> [pasta_previas]
Env: PARTES=plinto,corpo,capuz,maos (filtra) · VISTAS=frente,tras,... · AMOSTRAS=16 · TEXTURAS=0 (sem textura) · PINTAR=0 · PAREDE=1 (wireframe)
Cada parte é um módulo com build(L) que cria objetos via L.new_obj; o acabamento (UV, cor de vértice, sombreamento) é feito aqui."""
import bpy, bmesh, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, lib as L
from mathutils import Vector, noise

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT = argv[0] if argv else "SM_Cripta_Estatua.glb"
PREV = argv[1] if len(argv) > 1 else None
ONLY = os.environ.get("PARTES", "plinto,corpo,capuz,maos").split(",")

def fbm(p, f, oct=3):
    v, a = 0.0, 1.0
    for _ in range(oct): v += noise.noise(p * f) * a; f *= 2.1; a *= 0.5
    return v

def pintar(o):
    """Cor de vértice (multiplica a pedra): cavidades escuras, arestas claras, sujeira embaixo/nas dobras, líquen em manchas orgânicas
    suaves (gradiente por vértice, nada de quadradinhos) e desgaste assimétrico. Ouro: variação e riscos."""
    bm = bmesh.new(); bm.from_mesh(o.data); bm.normal_update(); mw = o.matrix_world
    cav = {}
    for v in bm.verts:
        viz = [e.other_vert(v).co for e in v.link_edges]
        cav[v.index] = ((sum(viz, Vector()) / len(viz) - v.co).dot(v.normal)) if viz else 0.0
    mats = [m.name for m in o.data.materials]
    layer = bm.loops.layers.float_color.new("Color")
    for f in bm.faces:
        nm = mats[f.material_index] if f.material_index < len(mats) else ""; ouro = nm == "M_Ouro"; corte = nm == "M_PedraCorte"
        for l in f.loops:
            v = l.vert; c = mw @ v.co; k = max(-1.0, min(1.0, cav[v.index] * 70))
            val = 0.86 + 0.40 * (-k if k < 0 else 0) - 0.55 * (k if k > 0 else 0)
            val *= 0.80 + 0.30 * (fbm(c + Vector((3.1, 1.7, 0.4)), 1.7, 3) + 0.5)          # desgaste assimétrico em manchas largas
            val *= 0.70 + 0.30 * min(1.0, max(0.0, (c.z - 0.0) / 1.6))                       # sujeira perto do chão
            r = g = b = val
            if ouro:
                d = 0.75 + 0.35 * (fbm(c, 9, 2) + 0.5); r = g = b = d * (0.9 + 0.2 * (fbm(c + Vector((7, 1, 2)), 22, 2)))
            elif corte:
                r = g = b = min(1.0, val * 0.95) * (0.9 + 0.1 * fbm(c, 14, 2))                 # corte claro, sem líquen
            else:
                n = fbm(c + Vector((0.37, 0.71, 0.13)), 2.6, 3)                               # líquen: manchas suaves, mais em cima e na base
                up = max(0.0, v.normal.z) if False else max(0.0, (mw.to_3x3() @ v.normal).z)
                m = max(0.0, min(1.0, (n - 0.30 + 0.10 * up + 0.45 * max(0.0, 1 - c.z / 1.5)) * 5)) * (0.4 + 0.6 * up) * (0.35 if c.z > 1.8 else 1.0)
                r, g, b = r * (1 - 0.45 * m), g * (1 + 0.05 * m), b * (1 - 0.65 * m)
            l[layer] = (max(0.05, min(1.4, r)), max(0.05, min(1.4, g)), max(0.05, min(1.4, b)), 1)
    bm.to_mesh(o.data); bm.free()

bpy.ops.wm.read_factory_settings(use_empty=True)
L.init_materiais(os.environ.get("TEXTURAS", "1") == "1")
for nome in ONLY:
    importlib.import_module(nome).build(L); print("parte", nome, "ok;", len(L.objs), "objetos")

bpy.ops.object.select_all(action='DESELECT')
for o in L.objs: o.select_set(True)
bpy.context.view_layer.objects.active = L.objs[0]; bpy.ops.object.join()
o = bpy.context.object; o.name = "SM_Cripta_Estatua"
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
n0 = len(o.data.polygons)
mod = o.modifiers.new("plano", 'DECIMATE'); mod.decimate_type = 'DISSOLVE'; mod.angle_limit = math.radians(float(os.environ.get("DISSOLVE_GRAUS", "5")))
mod.delimit = {'MATERIAL'}; bpy.ops.object.modifier_apply(modifier="plano")
print("dissolve", n0, "->", len(o.data.polygons))
L.uv_triplanar(o, 1.3)
if os.environ.get("PINTAR", "1") == "1": pintar(o)
bpy.ops.object.shade_smooth_by_angle(angle=math.radians(36))
bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, use_selection=True, export_format='GLB', export_yup=True, export_vertex_color='ACTIVE', export_image_format='JPEG', export_jpeg_quality=88)
print("exportado", OUT, L.stats(o))

if PREV:
    os.makedirs(PREV, exist_ok=True); sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get("AMOSTRAS", "24")); sc.cycles.device = 'CPU'; sc.cycles.use_denoising = True
    w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.09, 0.10, 0.14, 1); sc.world = w
    def sun(rot, e, color=(1, 1, 1)):
        s = bpy.data.objects.new("s", bpy.data.lights.new("s", 'SUN')); s.data.energy = e; s.data.color = color; s.rotation_euler = rot; bpy.context.collection.objects.link(s)
    sun((math.radians(55), 0, math.radians(215)), 5.0, (1.0, 0.88, 0.75)); sun((math.radians(70), 0, math.radians(40)), 2.2, (0.6, 0.7, 1.0)); sun((math.radians(30), 0, math.radians(100)), 1.2, (1, 1, 1))
    views = {"frente": ((0, 8.5, 2.1), (0, 0, 1.55), 700, 900), "tres_quartos": ((5.2, 6.3, 3.0), (0, 0, 1.55), 700, 900), "tras": ((-1.5, -8.5, 2.3), (0, 0, 1.55), 700, 900),
             "lado": ((9.0, 0.3, 2.1), (0, 0, 1.55), 700, 900), "cima": ((0.8, 2.2, 10.0), (0, 0, 1.5), 800, 800),
             "close_capuz": ((0.4, 3.2, 3.0), (0, 0, 2.75), 800, 800), "close_maos": ((0.5, 2.6, 1.9), (0, 0.2, 1.8), 800, 800), "close_plinto": ((1.8, 3.2, 0.9), (0, 0, 0.5), 800, 800)}
    only_v = os.environ.get("VISTAS")
    for nome, (loc, tgt, rx, ry) in views.items():
        if only_v and nome not in only_v.split(","): continue
        cam = bpy.data.cameras.new("c"); cam.lens = 55; co = bpy.data.objects.new("c", cam); bpy.context.collection.objects.link(co)
        co.location = loc; co.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        sc.camera = co; sc.render.resolution_x = rx; sc.render.resolution_y = ry
        sc.render.filepath = os.path.join(PREV, f"estatua_{nome}.png"); bpy.ops.render.render(write_still=True)
    if os.environ.get("PAREDE", "1") == "1" and not only_v:
        wf = o.modifiers.new("wf", 'WIREFRAME'); wf.thickness = 0.004
        cam = sc.camera; co = bpy.data.objects.new("c2", bpy.data.cameras.new("c2")); bpy.context.collection.objects.link(co)
        co.location = views["tres_quartos"][0]; co.rotation_euler = (Vector(views["tres_quartos"][1]) - Vector(co.location)).to_track_quat('-Z', 'Y').to_euler(); sc.camera = co
        sc.cycles.samples = 8; sc.render.resolution_x, sc.render.resolution_y = 700, 900
        sc.render.filepath = os.path.join(PREV, "estatua_wireframe.png"); bpy.ops.render.render(write_still=True)
