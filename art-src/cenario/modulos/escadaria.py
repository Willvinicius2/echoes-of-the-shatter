"""Módulo 3D da Cripta: escadaria de pedra com corrimão de ferro forjado (objeto separado).
Partes (um arquivo cada, em escadaria_partes/):
  esc_degraus.py   degraus gastos e lascados, avental do pé, patamar
  esc_laterais.py  paredes laterais acompanhando a rampa, capeamento, pilares de ponta, entulho
  esc_corrimao.py  corrimão martelado, balaústres torcidos, barra baixa, cintas, ponteiras, volutas
  esc_musgo.py     musgo e sujeira
Materiais, bake e prévias: cc_materiais.py (mesma régua da coluna com corrente).
python3 escadaria.py <pasta_glb> [pasta_previas] [--sem-bake] [--tam 2048] [--degraus 22] [--pivo-pe] [--colisao] [--largura 4.0] [--altura 0.18] [--piso 0.32]
Parametrico em número de degraus e largura. Metros; pivô no meio da corrida, z=0 no piso do pé; o pé da escada
fica em +Y do Blender (-Z do Godot), a escada sobe para -Y (+Z do Godot)."""
import sys, os, math
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI); sys.path.insert(0, os.path.join(AQUI, "escadaria_partes"))
import bpy
import cc_materiais
import esc_lib as L
import esc_degraus, esc_laterais, esc_corrimao, esc_musgo

args = [a for a in sys.argv[1:] if not a.startswith("--")]
def opt(nome, padrao, tipo=float):
    return tipo(sys.argv[sys.argv.index(nome) + 1]) if nome in sys.argv else padrao
N, LARG, TAM = opt("--degraus", 22, int), opt("--largura", 4.0), opt("--tam", 2048, int)
ALT, PISO = opt("--altura", 0.18), opt("--piso", 0.32)
OUT = args[0] if args else "."
PREV = args[1] if len(args) > 1 else None
SEM_BAKE = "--sem-bake" in sys.argv
NOME = "SM_Cripta_Escadaria"


def juntar(objs, nome):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.object; o.name = nome
    return o


def montar():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    L.configurar(N, LARG, ALT, PISO)
    M = cc_materiais.criar_materiais()
    zt = N * ALT   # altura total da rampa: musgo e umidade dependem dela
    # degraus: musgo escuro nas juntas e cantos, cresce para baixo; sombra suave
    for nome, ps in (("pedra", cc_materiais._PEDRA),):
        ps.update(c1=(0.095, 0.092, 0.120), c2=(0.19, 0.185, 0.235), c3=(0.34, 0.335, 0.42), quente=(1.04, 0.98, 1.0), frio=(0.90, 0.93, 1.10), musgo_qtd=0.95, musgo_lim=(0.40, 0.54), musgo_k=0.42, musgo_h=(zt + 0.5, 0.0, 0.08), ao_g_min=0.78)
        cc_materiais._montar_pedra(M[nome], ps)
    # paredes: pedra maior, cor por bloco bem variada (violeta frio e alguns quentes), umidade escorrendo e sujeira no pé
    par = dict(cc_materiais._ESCURA, nome="M_PedraParede", c1=(0.050, 0.048, 0.075), c2=(0.100, 0.096, 0.150), c3=(0.18, 0.175, 0.25), musgo_qtd=0.85, escala=0.6, v_min=0.6, v_max=1.38,
               quente=(1.16, 1.0, 0.88), frio=(0.86, 0.90, 1.14), ao_g_min=0.8,
               musgo_lim=(0.42, 0.56), musgo_k=0.42, musgo_h=(zt + 0.5, 0.0, 0.05), escorre=0.4, sujo_base=(0.0, 1.4))
    M['parede'] = bpy.data.materials.new("M_PedraParede"); M['parede'].use_nodes = True
    cc_materiais._montar_pedra(M['parede'], par)
    M['parede'].use_fake_user = True
    for parte in (esc_degraus, esc_laterais, esc_corrimao, esc_musgo):
        parte.build(M)
    ferro_m = {M['ferro'], M['ferro_escuro']}
    ferro = [o for o in L.objs if o.data.materials[0] in ferro_m]
    pedra = [o for o in L.objs if o not in ferro]
    op = juntar(pedra, NOME)
    of = juntar(ferro, NOME + "_Ferro")
    for o in (op, of):
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        d = o.modifiers.new("plano", 'DECIMATE'); d.decimate_type = 'DISSOLVE'; d.angle_limit = math.radians(1.5)
        d.delimit = {'MATERIAL'}
        bpy.ops.object.modifier_apply(modifier=d.name)
    # ferro fica fora do bake (barras finas dão ruído na textura): material liso, só pedra e musgo viram textura
    mf = bpy.data.materials.new("M_FerroForjado"); mf.use_nodes = True
    bs = mf.node_tree.nodes["Principled BSDF"]
    bs.inputs["Base Color"].default_value = (0.030, 0.030, 0.040, 1); bs.inputs["Metallic"].default_value = 0.25; bs.inputs["Roughness"].default_value = 0.62
    return M, op, of, mf


def aliviar(o, graus=6.0):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    n0 = len(o.data.polygons)
    d = o.modifiers.new("alivio", 'DECIMATE'); d.decimate_type = 'DISSOLVE'; d.angle_limit = math.radians(graus)
    d.delimit = {'MATERIAL', 'UV'}
    bpy.ops.object.modifier_apply(modifier=d.name)
    print("dissolve", graus, "graus:", n0, "->", len(o.data.polygons), "faces")


def fundir(op, of, mf):
    of.data.materials.clear(); of.data.materials.append(mf)
    for p in of.data.polygons: p.material_index = 0
    bpy.ops.object.select_all(action='DESELECT'); op.select_set(True); of.select_set(True)
    bpy.context.view_layer.objects.active = op
    bpy.ops.object.join()
    o = bpy.context.object; o.name = NOME
    if "--pivo-pe" not in sys.argv:   # pivô no topo da rampa, no nível do patamar: encaixa na âncora Ancora_Escadaria_* do terreno
        o.location = (0.0, -L.YT, -L.N * L.R)
        bpy.ops.object.transform_apply(location=True)
    return o


def colisao(dy, dz):
    """Colisão simples (Godot cria um StaticBody3D com trimesh nos nós *-colonly): rampa contínua pelo meio dos pisos,
    para o herói subir sem trancos nem afundar, paredes e pilares. dy, dz = deslocamento do pivô."""
    n0 = len(L.objs)
    hw = L.W / 2
    y0, y1 = L.YF + 0.62, L.YT - L.LAND
    topo = [(y0, 0.045), (L.YF, 0.045), (L.YF - L.T / 2, L.R), (L.YT + L.T / 2, L.N * L.R), (y1, L.N * L.R)]
    perfil = [(y - dy, z - dz) for y, z in topo + [(y1, L.BAIXO), (y0, L.BAIXO)]]
    L.prisma("rampa", -hw, hw, perfil, None, 1, jit=0, lascas=0, bis=0)
    for lado in (-1, 1):
        xa, xb = (hw, hw + L.WT) if lado > 0 else (-hw - L.WT, -hw)
        zt = lambda y: L.linha(y) + L.H0 + L.COPE
        pf = [(L.YF, L.BAIXO), (L.YF, zt(L.YF)), (L.YT, zt(L.YT)), (y1, zt(L.YT)), (y1, L.BAIXO)]
        L.prisma("parede", xa, xb, [(y - dy, z - dz) for y, z in pf], None, 2, jit=0, lascas=0, bis=0)
        xc = (xa + xb) / 2; ph = L.POST / 2 + 0.05
        for yc, zb, zt2 in ((L.YF + 0.24, L.BAIXO, zt(L.YF) + 0.9), (y1 + 0.24, zt(L.YT), zt(L.YT) + 1.2)):
            L.bloco("pilar", xc - ph, xc + ph, yc - ph - dy, yc + ph - dy, zb - dz, zt2 - dz, None, 3, lascas=0, bis=0, jit=0)
    novos = L.objs[n0:]
    for o in novos: o.data.materials.clear()
    bpy.ops.object.select_all(action='DESELECT')
    for o in novos: o.select_set(True)
    bpy.context.view_layer.objects.active = novos[0]
    bpy.ops.object.join()
    c = bpy.context.object; c.name = NOME + "_Colisao-colonly"
    return c


def exportar(o, col=None):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    if col is not None: col.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, NOME + ".glb"), use_selection=True, export_format='GLB',
                              export_yup=True, export_image_format='JPEG', export_jpeg_quality=88)
    print("exportado", len(o.data.polygons), "faces", tuple(round(d, 2) for d in o.dimensions))


if __name__ == "__main__":
    M, op, of, mf = montar()
    if PREV: os.makedirs(PREV, exist_ok=True)
    if not SEM_BAKE:
        print(cc_materiais.bake(op, tamanho=TAM, samples=12, pasta=PREV or OUT, nome="Escadaria"))
    if not SEM_BAKE: aliviar(op)
    o = fundir(op, of, mf)
    pivo = "--pivo-pe" not in sys.argv
    col = colisao(L.YT if pivo else 0.0, L.N * L.R if pivo else 0.0) if "--colisao" in sys.argv else None
    print("triângulos:", sum(len(p.vertices) - 2 for p in o.data.polygons), "dim", tuple(round(d, 2) for d in o.dimensions))
    exportar(o, col)
    if col is not None: col.hide_render = True; col.hide_viewport = True
    if PREV:
        yp = L.YF - L.YT   # pé fica a esta distância do pivô (topo)
        extras = {   # closes de revisão: topo do pilar de cima e degraus junto ao pilar do pé
            "pilar_topo": ((-2.17, -0.71, 1.55), (0.75, 0.55, 0.30), 2.3),
            "degraus_pilar_pe": ((-1.7, yp - 0.2, -L.N * L.R + 0.9), (0.45, 0.85, 0.55), 3.6),
            "jogo": ((0, yp / 2, -L.N * L.R / 2), (0.55, 0.9, 0.95), 15.0, 35),
        }
        for v in [x for x in os.environ.get("VISTAS", "tres_quartos,lado,pilar_topo,degraus_pilar_pe,jogo").split(",") if x]:
            cc_materiais.render_preview(o, os.path.join(PREV, f"escadaria_{v}.png"), extras.get(v, v), (900, 900), int(os.environ.get("AMOSTRAS", 24)), "auto")
