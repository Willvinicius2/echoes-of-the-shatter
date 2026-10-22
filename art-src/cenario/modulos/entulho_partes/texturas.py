"""Parte 4 (texturas): usa as imagens pintadas por pintar_pedra.py (albedo + normal, embutidas no .glb), UV por projeção em cubo,
e escurece frestas com oclusão por vértice (cor de vértice multiplicada no material)."""
import bpy, os
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import pintar_pedra

def _mat_img(nome, albedo, normal, tint=(1, 1, 1), rough=0.9):
    m = bpy.data.materials.new(nome); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    ta = nt.nodes.new("ShaderNodeTexImage"); ta.image = bpy.data.images.load(albedo); ta.image.pack()
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = bpy.data.images.load(normal); tn.image.pack(); tn.image.colorspace_settings.name = 'Non-Color'
    nm = nt.nodes.new("ShaderNodeNormalMap")
    ao = nt.nodes.new("ShaderNodeAttribute"); ao.attribute_name = "AO"
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0
    t2 = nt.nodes.new("ShaderNodeMix"); t2.data_type = 'RGBA'; t2.blend_type = 'MULTIPLY'; t2.inputs[0].default_value = 1.0; t2.inputs[7].default_value = (*tint, 1)
    nt.links.new(ta.outputs[0], t2.inputs[6]); nt.links.new(t2.outputs[2], mx.inputs[6]); nt.links.new(ao.outputs["Color"], mx.inputs[7])
    nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    nt.links.new(tn.outputs[0], nm.inputs["Color"]); nt.links.new(nm.outputs[0], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = rough
    return m

def aplicar(M, pasta, tam=1024):
    """Substitui os materiais de cor sólida por materiais com textura pintada (mesmos nomes M_Pedra, M_PedraEscura, M_Musgo, M_Terra)."""
    os.makedirs(pasta, exist_ok=True); pintar_pedra.gerar(pasta, tam=tam)
    pa, pn = os.path.join(pasta, "pedra_albedo.png"), os.path.join(pasta, "pedra_normal.png")
    ma, mn = os.path.join(pasta, "musgo_albedo.png"), os.path.join(pasta, "musgo_normal.png")
    novos = dict(pedra=_mat_img("M_Pedra", pa, pn, tint=(0.82, 0.9, 1.0)), escura=_mat_img("M_PedraEscura", pa, pn, tint=(0.5, 0.56, 0.66)),
                 musgo=_mat_img("M_Musgo", ma, mn, tint=(2.6, 2.9, 1.7), rough=1.0), terra=_mat_img("M_Terra", pa, pn, tint=(0.28, 0.22, 0.17), rough=1.0))
    return novos

def trocar_materiais(o, antigos, novos):
    for i, m in enumerate(o.data.materials):
        for k, a in antigos.items():
            if m == a: o.data.materials[i] = novos[k]

def preparar(o, tint=(1, 1, 1), tamanho=0.7):
    """UV em cubo com deslocamento aleatório por peça (a textura única não se repete igual) e cor de vértice 'TINT' por peça."""
    import random, zlib
    uv_cubo(o, tamanho)
    r = random.Random(zlib.crc32(o.name.encode())); du, dv = r.random(), r.random()
    for l in o.data.uv_layers[0].data: l.uv = (l.uv[0] + du, l.uv[1] + dv)
    at = o.data.color_attributes.new("TINT", 'FLOAT_COLOR', 'POINT')
    for i in range(len(o.data.vertices)): at.data[i].color = (*tint, 1)

def uv_cubo(o, tamanho=0.7):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cube_project(cube_size=tamanho); bpy.ops.object.mode_set(mode='OBJECT')

def oclusao_vertice(o, raios=10):
    """AO barato por vértice (atributo de cor 'AO'): escurece frestas e a base, clareia o topo."""
    import random, zlib
    r = random.Random(3)
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    me = o.data; attr = me.color_attributes.new("AO", 'FLOAT_COLOR', 'POINT')
    tint = me.color_attributes["TINT"]
    nrm = [Vector() for _ in me.vertices]
    for p in me.polygons:
        for vi in p.vertices: nrm[vi] += p.normal
    for v in me.vertices:
        n = nrm[v.index].normalized(); p0 = v.co + n * 0.004; livre = 0
        for _ in range(raios):
            d = (n + Vector((r.gauss(0, .8), r.gauss(0, .8), r.gauss(0, .8)))).normalized()
            if d.dot(n) < 0.1: d = n
            if bvh.ray_cast(p0, d, 0.5)[0] is None: livre += 1
        a = 0.55 + 0.45 * livre / raios
        a *= 0.88 + 0.12 * min(1.0, max(0.0, v.co.z / 0.6))     # base mais escura que o topo
        tc = tint.data[v.index].color
        attr.data[v.index].color = (a * tc[0], a * tc[1], a * tc[2], 1)
