"""Contrato de medidas e utilitários da estátua encapuzada da Cripta (compartilhado pelas partes).
Metros, +Z para cima no Blender, frente da estátua = +Y. Pivô no centro da base do plinto (origem do mundo).
Cada parte (corpo, capuz, maos, plinto) é um módulo com build(L) que cria objetos já com material, via L.new_obj."""
import bpy, bmesh, math, os, random
from mathutils import Vector

# ---- contrato de medidas (todas as partes usam estes valores)
ZP = 0.90          # topo do plinto = chão da figura
Z_HEM = ZP         # barra do manto
Z_WAIST = 1.55     # cintura (corda)
Z_HANDS = 1.85     # altura das mãos juntas (punhos), y ≈ +0.30
Z_SH = 2.45        # linha dos ombros
Z_NECK = 2.58      # base do capuz
Z_TOP = 3.12       # topo do capuz (ponta quebrada por volta de 3.0)
HEM_RX, HEM_RY = 0.50, 0.38   # semieixos da barra do manto (x largura, y profundidade)
SH_RX, SH_RY = 0.44, 0.24     # semieixos nos ombros
PLINTO_W = 1.30    # largura do degrau de baixo
TEX_DIR = os.environ.get("ESTATUA_TEX", "/tmp/estatua_tex"); os.makedirs(TEX_DIR, exist_ok=True)
objs = []          # objetos criados (a main junta e exporta)
M = {}             # materiais: M['pedra'], M['ouro'], M['vazio'] (criados em init_materiais)

def rng(seed): return random.Random(seed)
def lerp(a, b, t): return a + (b - a) * t
def prof(tab, z):
    """Interpola linearmente uma tabela [(z, valor), ...]."""
    if z <= tab[0][0]: return tab[0][1]
    for (z0, v0), (z1, v1) in zip(tab, tab[1:]):
        if z <= z1: return lerp(v0, v1, (z - z0) / (z1 - z0))
    return tab[-1][1]

def init_materiais(com_textura=True):
    import texturas
    alb, nor = texturas.pedra(TEX_DIR) if com_textura else (None, None)
    M['pedra'] = _mat("M_PedraEscura", (0.45, 0.43, 0.50), rough=0.88, image=alb, normal=nor)
    M['ouro'] = _mat("M_Ouro", (0.72, 0.52, 0.16), metal=0.85, rough=0.45)
    M['vazio'] = _mat("M_Vazio", (0.02, 0.02, 0.03), rough=1.0)

def _mat(name, color, metal=0.0, rough=0.85, image=None, normal=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Metallic"].default_value = metal; b.inputs["Roughness"].default_value = rough
    col = None
    if image:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(image); t.image.pack(); col = t.outputs["Color"]
    # a cor de vértice (pintada no fim) multiplica a cor base: manchas, líquen, sujeira
    va = nt.nodes.new("ShaderNodeVertexColor"); va.layer_name = "Color"
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0
    if col: nt.links.new(col, mx.inputs[6])
    else: mx.inputs[6].default_value = (*color, 1)
    nt.links.new(va.outputs["Color"], mx.inputs[7]); nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    if normal:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(normal); t.image.pack(); t.image.colorspace_settings.name = 'Non-Color'
        n = nt.nodes.new("ShaderNodeNormalMap"); n.inputs["Strength"].default_value = 1.0
        nt.links.new(t.outputs["Color"], n.inputs["Color"]); nt.links.new(n.outputs["Normal"], b.inputs["Normal"])
    return m

def new_obj(name, bm_or_mesh, mat="pedra"):
    """Cria o objeto, liga o material (chave de M) e registra para a junção final."""
    if isinstance(bm_or_mesh, bmesh.types.BMesh):
        me = bpy.data.meshes.new(name); bm_or_mesh.to_mesh(me); bm_or_mesh.free()
    else: me = bm_or_mesh
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    if mat: o.data.materials.append(M[mat])
    objs.append(o); return o

def bevel_obj(o, width=0.01, segments=2, angle=30):
    """Bevel real só nas arestas vivas (ângulo), aplicado."""
    mod = o.modifiers.new("bev", 'BEVEL'); mod.width = width; mod.segments = segments
    mod.limit_method = 'ANGLE'; mod.angle_limit = math.radians(angle)
    bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier="bev")

def loft(rings, cap_bottom=True, cap_top=True):
    """rings: lista de anéis (listas de Vector de mesmo tamanho), de baixo para cima. Devolve bmesh."""
    bm = bmesh.new(); n = len(rings[0]); vs = [[bm.verts.new(p) for p in r] for r in rings]
    for a, b in zip(vs, vs[1:]):
        for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    if cap_bottom: bm.faces.new(vs[0][::-1])
    if cap_top: bm.faces.new(vs[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); return bm

def uv_triplanar(o, tile=1.2):
    """UV por projeção de caixa em espaço de mundo (densidade de texel uniforme): cada face usa o eixo dominante da normal."""
    me = o.data; uvl = me.uv_layers.new(name="UVMap") if not me.uv_layers else me.uv_layers[0]
    mw = o.matrix_world
    for p in me.polygons:
        n = mw.to_3x3() @ p.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            v = mw @ me.vertices[me.loops[li].vertex_index].co
            u, w = ((v.y, v.z), (v.x, v.z), (v.x, v.y))[ax]
            uvl.data[li].uv = (u / tile, w / tile)

def stats(o):
    return f"{len(o.data.polygons)} faces, dim " + str(tuple(round(d, 2) for d in o.dimensions))
