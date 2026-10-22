"""Módulo 3D da Cripta: aglomerado de velas de cera derretida (referência: referencias-cripta/objetos.png).
blender -b --factory-startup -P velas.py -- <saida.glb> [previa.png] [previa_wire.png]
Metros, pivô no centro da base, +Z para cima no Blender.
Fluxo de jogo: alta resolução (velas torneadas com borda derretida, escorridos, poça) -> baixa (~8 mil tris) ->
bake de cor (cera com manchas, fuligem, âmbar nos escorridos), normal (veios e poros) e oclusão para uma textura de 1024.
O glb leva a cera com textura, o pavio e as chamas (duas camadas) com material emissivo próprio."""
import bpy, bmesh, math, sys, random
import numpy as np
from mathutils import Vector, noise

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "SM_Cripta_Velas.glb"
PREV = argv[1] if len(argv) > 1 else None
WIRE = argv[2] if len(argv) > 2 else None
TEX = 1024
random.seed(11)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'

# (x, y, raio, altura, tom) — 5 velas: alta, duas médias, duas baixas; tom 0 = marfim, 1 = envelhecida amarelada
VELAS = [(0.00, 0.02, 0.078, 0.46, 0.25), (-0.17, -0.07, 0.066, 0.27, 0.6), (0.17, -0.02, 0.062, 0.31, 0.1),
         (-0.06, -0.19, 0.056, 0.17, 0.8), (0.09, -0.20, 0.046, 0.12, 0.4)]
Z0 = 0.0

def fbm(p, o=4):
    s, a, f = 0.0, 1.0, 1.0
    for _ in range(o):
        s += a * noise.noise(p * f); a *= 0.5; f *= 2.0
    return s

def blob(loc, scale, rot=(0, 0, 0), sub=3):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=1, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = scale; bpy.ops.object.transform_apply(scale=True); return o

def from_bm(bm, name):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); return o

# ------------------------------------------------------------------ alta resolução
parts = []
SEG = 64

def vela_torneada(x, y, r, h):
    """Superfície de revolução com perfil explícito: base alargada, fuste com veios verticais, lábio derretido e cavidade."""
    prof = []
    for i in range(0, 41):                       # fuste
        t = i / 40
        prof.append((r * (1.14 - 0.15 * t ** 0.7), Z0 + h * t * 0.985))
    top = Z0 + h
    prof += [(r * 0.98, top - 0.004), (r * 1.02, top + 0.012), (r * 0.94, top + 0.018), (r * 0.80, top + 0.008),
             (r * 0.62, top - 0.014), (r * 0.38, top - 0.026), (r * 0.16, top - 0.030), (0.016, top - 0.024)]
    bm = bmesh.new(); rings = []
    n_drip = 9 + int(r * 70)
    drip_ang = sorted(random.uniform(0, 2 * math.pi) for _ in range(n_drip))
    for (rr, z) in prof:
        ring = []
        for j in range(SEG):
            a = j / SEG * 2 * math.pi
            k = 1.0
            if rr > r * 0.7:
                k += 0.055 * fbm(Vector((math.cos(a) * 2.2 + x * 11, math.sin(a) * 2.2 + y * 11, z * 1.6)), 3)   # veios compridos
                k += 0.018 * noise.noise(Vector((math.cos(a) * 8, math.sin(a) * 8, z * 5)))
            zz = z
            if z > top - 0.02:                    # lábio ondulado e rebaixado onde a cera transbordou
                zz += 0.006 * math.sin(a * 2 + x * 25) + 0.002 * noise.noise(Vector((a * 3, x * 9, 1.7)))
                for da in drip_ang:
                    d = abs((a - da + math.pi) % (2 * math.pi) - math.pi)
                    if d < 0.4: zz -= 0.010 * math.cos(d / 0.4 * math.pi / 2) ** 2 * (1 if rr > r * 0.7 else 0.3)
            ring.append(bm.verts.new((x + rr * k * math.cos(a), y + rr * k * math.sin(a), zz)))
        rings.append(ring)
    base = [bm.verts.new((x, y, Z0))]
    rings.insert(0, [bm.verts.new((x + r * 1.14 * math.cos(j / SEG * 2 * math.pi), y + r * 1.14 * math.sin(j / SEG * 2 * math.pi), Z0)) for j in range(SEG)])
    for i in range(len(rings) - 1):
        for j in range(SEG):
            bm.faces.new((rings[i][j], rings[i][(j + 1) % SEG], rings[i + 1][(j + 1) % SEG], rings[i + 1][j]))
    for j in range(SEG):                          # fecha base e poço do pavio
        bm.faces.new((base[0], rings[0][(j + 1) % SEG], rings[0][j]))
    c = bm.verts.new((x, y, top - 0.022))
    for j in range(SEG):
        bm.faces.new((c, rings[-1][j], rings[-1][(j + 1) % SEG]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return from_bm(bm, "vela"), drip_ang

for (x, y, r, h, tom) in VELAS:
    o, drips = vela_torneada(x, y, r, h); parts.append(o)
    top = Z0 + h
    for a in drips:                               # escorridos: língua achatada na parede + fio + bulbo na ponta
        ln = random.uniform(0.15, 0.85) * h
        rr = r * 0.985
        w = random.uniform(0.011, 0.020)
        e = (0, 0, a)
        cx, cy = x + rr * math.cos(a), y + rr * math.sin(a)
        blob((cx, cy, top - 0.02 - ln * 0.18), (0.012, w * 1.5, ln * 0.2), e, 3)          # lençol largo saindo do lábio
        blob((cx, cy, top - 0.012 - ln / 2), (0.010, w * 0.75, ln / 2), e, 3)             # fio que afina
        blob((cx, cy, top - 0.012 - ln), (0.014, w * 1.1, w * 1.4), e, 3)                 # bulbo
        if random.random() < 0.35:                # gota suspensa solta, quase caindo
            blob((cx + 0.004 * math.cos(a), cy + 0.004 * math.sin(a), top - 0.012 - ln - w * 2.6), (0.011, 0.011, w * 1.2), e, 3)

# poça: vários discos de contorno irregular, finos na borda e mais grossos junto das velas
def disco(cx, cy, R, hz, lobulos):
    bm = bmesh.new(); RINGS = 14; S = 72; rows = []
    ph = random.uniform(0, 6.28)
    for i in range(RINGS + 1):
        t = i / RINGS; row = []
        for j in range(S):
            a = j / S * 2 * math.pi
            edge = R * (0.78 + 0.22 * math.sin(a * lobulos + ph) * 0.8 + 0.18 * fbm(Vector((math.cos(a) * 1.5 + cx * 7, math.sin(a) * 1.5 + cy * 7, 3)), 3))
            rr = edge * t
            z = 0.005 + (hz - 0.005) * (1 - t ** 3) ** 0.7
            z += 0.003 * noise.noise(Vector((rr * 40 + cx, a * 3, 0)))
            row.append(bm.verts.new((cx + rr * math.cos(a), cy + rr * math.sin(a), max(0.0, z))))
        rows.append(row)
    for i in range(RINGS):
        for j in range(S):
            bm.faces.new((rows[i][j], rows[i][(j + 1) % S], rows[i + 1][(j + 1) % S], rows[i + 1][j]))
    cen = bm.verts.new((cx, cy, hz))
    for j in range(S): bm.faces.new((cen, rows[0][(j + 1) % S], rows[0][j]))
    low = [bm.verts.new((v.co.x, v.co.y, -0.004)) for v in rows[-1]]          # fundo plano: o disco precisa ser sólido
    for j in range(S): bm.faces.new((rows[-1][j], rows[-1][(j + 1) % S], low[(j + 1) % S], low[j]))
    bc = bm.verts.new((cx, cy, -0.004))
    for j in range(S): bm.faces.new((bc, low[j], low[(j + 1) % S]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return from_bm(bm, "poca")

parts.append(disco(0.0, -0.05, 0.30, 0.040, 5))
for i in range(6):
    a = i * 2 * math.pi / 6 + random.uniform(-0.3, 0.3); d = random.uniform(0.2, 0.3)
    parts.append(disco(math.cos(a) * d, -0.05 + math.sin(a) * d * 0.9, random.uniform(0.09, 0.15), random.uniform(0.014, 0.024), random.randint(3, 6)))

bpy.ops.object.select_all(action='DESELECT')
for o in parts: o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]; bpy.ops.object.join()
alta = bpy.context.object; alta.name = "Alta"
alta.data.remesh_voxel_size = 0.0032; bpy.ops.object.voxel_remesh()
sm = alta.modifiers.new("s", 'SMOOTH'); sm.factor = 0.5; sm.iterations = 7
bpy.ops.object.modifier_apply(modifier="s")
bpy.ops.object.shade_smooth()
print("alta tris", sum(len(p.vertices) - 2 for p in alta.data.polygons))

# cor por vértice na alta: tom por vela mais próxima, âmbar embaixo/nos escorridos, fuligem no topo, manchas
col = alta.data.color_attributes.new("Col", 'FLOAT_COLOR', 'POINT')
ivory = Vector((0.93, 0.86, 0.69)); aged = Vector((0.80, 0.66, 0.42)); amber = Vector((0.72, 0.45, 0.17)); soot = Vector((0.10, 0.075, 0.055))
for i, v in enumerate(alta.data.vertices):
    p = v.co
    d, tom, hv = 9, 0, 0.3
    for (x, y, r, h, t) in VELAS:
        dd = math.hypot(p.x - x, p.y - y)
        if dd < d: d, tom, hv = dd, t, h
    low = max(0.0, min(1.0, 1 - p.z / 0.07))
    c = ivory.lerp(aged, max(0.0, min(1.0, tom * 0.5 + 0.35 * (fbm(p * 14) * 0.5 + 0.5) - 0.15)))
    c = c.lerp(amber, min(1.0, low * 0.5 + max(0.0, fbm(p * 5 + Vector((5, 5, 5)))) * 0.12))        # poça âmbar, escorridos mais escuros
    rel = (p.z - 0.0) / max(hv, 0.05)
    if p.z > 0.1 and d < 0.1:                                       # fuligem no cimo da vela e na borda
        c = c.lerp(soot, max(0.0, (rel - 0.93) * 8) * (0.5 + 0.5 * (noise.noise(p * 40) * 0.5 + 0.5)))
    c = c * (0.9 + 0.1 * (noise.noise(p * 60) * 0.5 + 0.5))
    col.data[i].color = (c.x, c.y, c.z, 1)


# material da alta (só para o bake): cor de vértice + poros e veios no normal
ma = bpy.data.materials.new("Alta"); ma.use_nodes = True
nt = ma.node_tree; bsdf = nt.nodes["Principled BSDF"]
vc = nt.nodes.new("ShaderNodeVertexColor"); vc.layer_name = "Col"
nt.links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])
n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 70; n1.inputs["Detail"].default_value = 8; n1.inputs["Roughness"].default_value = 0.65
vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 150; vor.feature = 'DISTANCE_TO_EDGE'
mix = nt.nodes.new("ShaderNodeMath"); mix.operation = 'ADD'
nt.links.new(n1.outputs["Fac"], mix.inputs[0]); nt.links.new(vor.outputs["Distance"], mix.inputs[1])
bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.35; bump.inputs["Distance"].default_value = 0.004
nt.links.new(mix.outputs["Value"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
alta.data.materials.append(ma)

# ------------------------------------------------------------------ baixa resolução + UV
bpy.ops.object.select_all(action='DESELECT')
alta.select_set(True); bpy.context.view_layer.objects.active = alta
bpy.ops.object.duplicate(); baixa = bpy.context.object; baixa.name = "SM_Cripta_Velas_Cera"
baixa.data.materials.clear()
baixa.data.remesh_voxel_size = 0.0055; bpy.ops.object.voxel_remesh()
dc = baixa.modifiers.new("d", 'DECIMATE'); dc.ratio = 0.085
bpy.ops.object.modifier_apply(modifier="d")
while len(baixa.data.color_attributes): baixa.data.color_attributes.remove(baixa.data.color_attributes[0])
bpy.ops.object.select_all(action='DESELECT'); baixa.select_set(True); bpy.context.view_layer.objects.active = baixa
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(70), island_margin=0.006)
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.shade_smooth()
print("baixa tris", sum(len(p.vertices) - 2 for p in baixa.data.polygons))

# ------------------------------------------------------------------ bake
mb = bpy.data.materials.new("M_Cera"); mb.use_nodes = True
baixa.data.materials.append(mb)
bt = mb.node_tree; bb = bt.nodes["Principled BSDF"]

def imagem(nome, cor=False):
    im = bpy.data.images.new(nome, TEX, TEX, alpha=False); im.colorspace_settings.name = 'sRGB' if cor else 'Non-Color'; return im

def bake(tipo, im, **kw):
    n = bt.nodes.new("ShaderNodeTexImage"); n.image = im; bt.nodes.active = n
    bpy.ops.object.select_all(action='DESELECT'); alta.select_set(True); baixa.select_set(True); bpy.context.view_layer.objects.active = baixa
    sc.cycles.samples = 24; sc.cycles.use_denoising = False
    bpy.ops.object.bake(type=tipo, use_selected_to_active=True, cage_extrusion=0.012, max_ray_distance=0.05, margin=6, **kw)
    return n

im_c = imagem("T_Velas_Cor", True); im_n = imagem("T_Velas_Normal"); im_ao = imagem("T_Velas_AO")
n_c = bake('DIFFUSE', im_c, pass_filter={'COLOR'})
n_n = bake('NORMAL', im_n)
n_ao = bake('AO', im_ao)
# oclusão multiplicada na cor (suave): aprofunda as frestas entre velas e embaixo dos escorridos
c = np.array(im_c.pixels[:]).reshape(-1, 4); ao = np.array(im_ao.pixels[:]).reshape(-1, 4)
c[:, :3] *= (0.55 + 0.45 * ao[:, :1])
im_c.pixels = c.ravel().tolist(); im_c.pack(); im_n.pack()
for n in (n_c, n_ao, n_n): bt.nodes.remove(n)
tc = bt.nodes.new("ShaderNodeTexImage"); tc.image = im_c
tn = bt.nodes.new("ShaderNodeTexImage"); tn.image = im_n
nm = bt.nodes.new("ShaderNodeNormalMap")
bt.links.new(tc.outputs["Color"], bb.inputs["Base Color"])
bt.links.new(tn.outputs["Color"], nm.inputs["Color"]); bt.links.new(nm.outputs["Normal"], bb.inputs["Normal"])
bb.inputs["Roughness"].default_value = 0.5
try: bb.inputs["Specular IOR Level"].default_value = 0.6
except KeyError: pass

# ------------------------------------------------------------------ pavio e chamas
def mk_emit(nome, base, em, forca):
    m = bpy.data.materials.new(nome); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*base, 1); b.inputs["Roughness"].default_value = 0.6
    b.inputs["Emission Color"].default_value = (*em, 1); b.inputs["Emission Strength"].default_value = forca
    return m
M_PAVIO = bpy.data.materials.new("M_Pavio"); M_PAVIO.use_nodes = True
M_PAVIO.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.02, 0.016, 0.012, 1)
M_PAVIO.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.95
M_CHAMA = mk_emit("M_Chama", (1.0, 0.45, 0.08), (1.0, 0.40, 0.05), 3.5)
M_NUCLEO = mk_emit("M_ChamaNucleo", (1.0, 0.85, 0.5), (1.0, 0.82, 0.45), 6.0)

def chama(x, y, base_z, alt, larg, mat, flexao):
    """Gota estilizada: bojo embaixo, ponta fina curvada; perfil por anéis."""
    bm = bmesh.new(); R = 16; N = 14; rows = []
    for i in range(N + 1):
        t = i / N
        w = larg * (math.sin(math.pi * min(1.0, t * 1.0) ** 0.62) ** 0.9) * (1 - t ** 3) if t > 0 else larg * 0.45
        w = max(w, 0.0006)
        cx = flexao * t ** 2.2
        z = base_z + alt * t
        rows.append([bm.verts.new((x + cx + w * math.cos(j / R * 6.2832), y + w * math.sin(j / R * 6.2832) * 0.9, z)) for j in range(R)])
    for i in range(N):
        for j in range(R): bm.faces.new((rows[i][j], rows[i][(j + 1) % R], rows[i + 1][(j + 1) % R], rows[i + 1][j]))
    top = bm.verts.new((x + flexao, y, base_z + alt)); bot = bm.verts.new((x, y, base_z - 0.002))
    for j in range(R):
        bm.faces.new((top, rows[-1][j], rows[-1][(j + 1) % R])); bm.faces.new((bot, rows[0][(j + 1) % R], rows[0][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = from_bm(bm, "chama"); o.data.materials.append(mat)
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.shade_smooth()
    return o

extras = []
for (x, y, r, h, tom) in VELAS:
    top = Z0 + h
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.0055, depth=0.034, location=(x, y, top - 0.006))
    p = bpy.context.object; p.data.materials.append(M_PAVIO); extras.append(p)
    ff = 0.012 * (1 if random.random() > 0.5 else -1)
    extras.append(chama(x, y, top + 0.008, 0.115 + 0.01 * r * 10, 0.021, M_CHAMA, ff))
    extras.append(chama(x, y, top + 0.012, 0.062, 0.011, M_NUCLEO, ff * 0.5))

bpy.ops.object.select_all(action='DESELECT')
bpy.data.objects.remove(alta, do_unlink=True)
for o in [baixa] + extras: o.select_set(True)
bpy.context.view_layer.objects.active = baixa; bpy.ops.object.join()
final = bpy.context.object; final.name = "SM_Cripta_Velas"
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
final.data.validate()
tris = sum(len(p.vertices) - 2 for p in final.data.polygons)
print("tris", tris, "dim", tuple(round(d, 3) for d in final.dimensions))
bpy.ops.export_scene.gltf(filepath=OUT, use_selection=True, export_format='GLB', export_yup=True)

# ------------------------------------------------------------------ prévia
if PREV:
    sc.world = bpy.data.worlds.new("w"); sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.03, 0.03, 0.045, 1)
    for loc, en, colr in (((0.55, -0.7, 0.62), 22, (1, 0.6, 0.3)), ((-0.8, -0.4, 0.5), 9, (0.5, 0.6, 1)), ((0.0, 0.0, 0.62), 5, (1, 0.5, 0.2))):
        l = bpy.data.objects.new("l", bpy.data.lights.new("l", 'POINT')); l.data.energy = en; l.data.color = colr; l.location = loc
        sc.collection.objects.link(l)
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam)
    cam.location = (0.95, -1.25, 0.8); cam.rotation_euler = (Vector((0, -0.05, 0.25)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    sc.cycles.samples = 40; sc.cycles.use_denoising = False
    sc.render.resolution_x = 900; sc.render.resolution_y = 900
    sc.render.filepath = PREV; bpy.ops.render.render(write_still=True)
    if WIRE:
        w = final.modifiers.new("w", 'WIREFRAME'); w.thickness = 0.0012
        sc.render.filepath = WIRE; bpy.ops.render.render(write_still=True)
