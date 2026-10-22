"""Base comum do piso da Cripta: layout das lajotas, materiais e câmera de prévia.
Todas as partes (lajotas, desgaste, poças) leem o MESMO layout, por isso a posição das juntas bate.
Módulo de 8 x 8 m, periódico em x e y (emenda sem costura). Topo das lajotas em z = 0, +Z para cima no Blender.
Referência de arte: referencias-cripta/terreno.png (lajotas azul-ardósia escuras, tamanhos variados, quinas lascadas,
rachaduras, poças com reflexo, sujeira e musgo nas juntas)."""
import bpy, bmesh, math, os, random
from mathutils import Vector

TILE = 8.0          # lado do módulo (m)
JUNTA = 0.045       # largura da junta (m)
ESPESSURA = 0.14    # espessura da lajota (m); topo em z=0, base em z=-ESPESSURA
SEED = 1744

def layout(seed=SEED):
    """Fileiras de alturas variadas; dentro de cada fileira lajotas de larguras variadas, fileiras com emenda deslocada.
    Retorna lista de dict(id,x0,y0,x1,y1) já SEM a junta (cada lajota encolhida JUNTA/2 por lado). Periódico em TILE."""
    r = random.Random(seed)
    alturas = []
    while True:
        alturas = []; s = 0.0
        while s < TILE - 0.6:
            h = r.choice([0.8, 1.0, 1.0, 1.2, 1.6, 2.0]); alturas.append(h); s += h
        if s < TILE:
            alturas.append(TILE - s); s = TILE
        if abs(sum(alturas) - TILE) < 1e-6 and min(alturas) > 0.5: break
    lajes = []; y = 0.0; i = 0
    for h in alturas:
        larg = []; s = 0.0
        while s < TILE - 0.5:
            w = r.choice([0.9, 1.2, 1.5, 1.5, 2.0, 2.4]); larg.append(w); s += w
        if s < TILE: larg.append(TILE - s)
        else: larg[-1] -= (s - TILE)
        if larg[-1] < 0.5: larg[-2] += larg[-1]; larg.pop()
        x = r.uniform(0, 1.2)   # deslocamento da fileira; a lajota que cruza a borda é dividida em duas
        for w in larg:
            x0, x1 = x, x + w
            for ox in (0.0, -TILE):
                a, b = x0 + ox, x1 + ox
                if b > 0 and a < TILE:
                    a, b = max(a, 0.0), min(b, TILE)
                    if b - a > 0.05: lajes.append(dict(id=i, x0=a, y0=y, x1=b, y1=y + h, w_full=w, cortada=(a > x0 + ox + 1e-6 or b < x1 + ox - 1e-6)))
            x += w; i += 1
        y += h
    j = JUNTA / 2
    for l in lajes:
        l["x0"] += j; l["x1"] -= j; l["y0"] += j; l["y1"] -= j
    return lajes

def limpar_cena():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def material(nome, cor, rough=0.8, metal=0.0):
    m = bpy.data.materials.new(nome); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*cor, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    return m

def novo_objeto(nome, bm, mats=()):
    me = bpy.data.meshes.new(nome); bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    o = bpy.data.objects.new(nome, me); bpy.context.collection.objects.link(o)
    return o

def previa(saida_png, olhar=(4, 4, 0), cam=(4 + 5.5, 4 - 7.5, 8.5), res=(960, 640), amostras=32, lente=35, extras=None, luz_quente=True):
    """Render Cycles de prévia: luz de lua azulada vinda da esquerda + luz quente baixa (tocha) para rasar o relevo."""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = amostras; sc.cycles.use_denoising = True
    try: sc.cycles.device = 'CPU'
    except Exception: pass
    sc.render.resolution_x, sc.render.resolution_y = res
    w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.10, 0.13, 0.19, 1); sc.world = w
    sol = bpy.data.objects.new("lua", bpy.data.lights.new("lua", 'SUN')); sol.data.energy = 1.6; sol.data.color = (0.6, 0.7, 1.0)
    sol.rotation_euler = (math.radians(55), 0, math.radians(35)); bpy.context.collection.objects.link(sol)
    if luz_quente:
        t = bpy.data.objects.new("tocha", bpy.data.lights.new("tocha", 'POINT')); t.data.energy = 900; t.data.color = (1.0, 0.6, 0.25); t.data.shadow_soft_size = 0.15
        t.location = (olhar[0] - 1.5, olhar[1] + 1.0, 1.1); bpy.context.collection.objects.link(t)
    c = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); c.data.lens = lente; bpy.context.collection.objects.link(c); sc.camera = c
    c.location = cam
    c.rotation_euler = (Vector(olhar) - c.location).to_track_quat('-Z', 'Y').to_euler()
    os.makedirs(os.path.dirname(saida_png), exist_ok=True)
    sc.render.filepath = saida_png; bpy.ops.render.render(write_still=True)

def materiais_previa(tons=None):
    """Aplica nós procedurais (ruído + bump) às lajotas só para a prévia; o .glb leva cores sólidas + os mapas definidos nas partes."""
    for m in bpy.data.materials:
        if not m.use_nodes or "preview_ok" in m: continue
        m["preview_ok"] = 1
