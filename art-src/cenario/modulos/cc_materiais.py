"""Materiais procedurais, bake e prévia da coluna com corrente (Cripta).

Uso (dentro do Blender / bpy):
    import cc_materiais as cm
    mats = cm.criar_materiais()      # M_Pedra, M_PedraEscura, M_Musgo, M_Ferro, M_FerroEscuro
    ... atribui aos objetos, junta tudo num objeto só ...
    info = cm.bake(obj)              # UV + bake Diffuse(cor) e Normal(tangente) + material único M_ColunaCorrente
    cm.render_preview(obj, "prev.png", "tres_quartos", (800, 800), 64, material="baked")

Os materiais usam coordenadas de objeto (metros) e a "Random Per Island" para variar a cor por bloco,
então funcionam em qualquer tamanho de objeto desde que a escala esteja em metros.
"""
import bpy, math, os
from mathutils import Vector

PASTA_PADRAO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "previas")
_ORIG = {}  # nome do objeto -> lista de materiais procedurais antes do bake


# ---------------------------------------------------------------- utilidades de nós
class _B:
    """Construtor enxuto de nós."""
    def __init__(self, nt):
        self.nt = nt
        self.x = -1400
        self.y = 0

    def n(self, tipo, **kw):
        nd = self.nt.nodes.new(tipo)
        for k, v in kw.items():
            if k == "inp":
                for nome, val in v.items():
                    self.set(nd, nome, val)
            else:
                setattr(nd, k, v)
        self.y -= 40
        nd.location = (self.x + (len(self.nt.nodes) % 9) * 150, self.y)
        return nd

    def set(self, nd, nome, val):
        s = nd.inputs[nome]
        if hasattr(val, "outputs"):
            self.nt.links.new(val.outputs[0], s)
        elif hasattr(val, "node"):
            self.nt.links.new(val, s)
        else:
            s.default_value = val

    def link(self, out, nd, nome):
        if hasattr(out, "outputs"):
            out = out.outputs[0]
        self.nt.links.new(out, nd.inputs[nome] if isinstance(nome, str) else nd.inputs[nome])

    # --- atalhos
    def noise(self, vec, scale, detail=6.0, rough=0.55, dist=0.0):
        nd = self.n("ShaderNodeTexNoise", noise_dimensions='3D',
                    inp={"Scale": scale, "Detail": detail, "Roughness": rough, "Distortion": dist})
        self.nt.links.new(vec, nd.inputs["Vector"])
        return nd.outputs["Fac"]

    def voro(self, vec, scale, feature='F1', rand=1.0, smooth=0.0):
        nd = self.n("ShaderNodeTexVoronoi", voronoi_dimensions='3D', feature=feature,
                    inp={"Scale": scale, "Randomness": rand})
        if feature in ('F1', 'F2') and smooth:
            pass
        self.nt.links.new(vec, nd.inputs["Vector"])
        return nd

    def math(self, op, a, b=None, c=None, clamp=False):
        nd = self.n("ShaderNodeMath", operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                nd.inputs[i].default_value = v
            else:
                self.nt.links.new(v, nd.inputs[i])
        return nd.outputs[0]

    def mapr(self, v, a, b, c=0.0, d=1.0, clamp=True, interp='LINEAR'):
        nd = self.n("ShaderNodeMapRange", clamp=clamp, interpolation_type=interp)
        for nome, val in (("Value", v), ("From Min", a), ("From Max", b), ("To Min", c), ("To Max", d)):
            if isinstance(val, (int, float)):
                nd.inputs[nome].default_value = val
            else:
                self.nt.links.new(val, nd.inputs[nome])
        return nd.outputs["Result"]

    def mixc(self, fac, a, b, blend='MIX'):
        nd = self.n("ShaderNodeMix", data_type='RGBA', blend_type=blend, clamp_factor=True)
        for idx, val in ((0, fac), (6, a), (7, b)):
            if isinstance(val, (int, float)):
                nd.inputs[idx].default_value = val if idx == 0 else (val, val, val, 1.0)
            elif isinstance(val, tuple):
                nd.inputs[idx].default_value = (*val, 1.0) if len(val) == 3 else val
            else:
                self.nt.links.new(val, nd.inputs[idx])
        return nd.outputs[2]

    def mulc(self, a, b, fac=1.0):
        return self.mixc(fac, a, b, 'MULTIPLY')

    def ramp(self, fac, stops):
        nd = self.n("ShaderNodeValToRGB")
        cr = nd.color_ramp
        while len(cr.elements) < len(stops):
            cr.elements.new(0.5)
        for e, (p, col) in zip(cr.elements, stops):
            e.position = p
            e.color = (*col, 1.0)
        self.nt.links.new(fac, nd.inputs["Fac"])
        return nd.outputs["Color"]

    def sep_xyz(self, vec):
        nd = self.n("ShaderNodeSeparateXYZ")
        self.nt.links.new(vec, nd.inputs["Vector"])
        return nd.outputs


def _smooth(b, v, a, c):
    return b.mapr(v, a, c, 0.0, 1.0, True, 'SMOOTHSTEP')


def _comuns(b):
    """Entradas geométricas compartilhadas: coordenada de objeto, variação por bloco, desgaste, AO, 'cima'."""
    tc = b.n("ShaderNodeTexCoord")
    geo = b.n("ShaderNodeNewGeometry")
    oi = b.n("ShaderNodeObjectInfo")
    obj = tc.outputs["Object"]
    # --- aleatório por ilha (bloco) com 3 variantes, e por objeto
    isl = geo.outputs["Random Per Island"]
    r1 = isl
    r2 = b.math('FRACT', b.math('MULTIPLY', isl, 7.31))
    r3 = b.math('FRACT', b.math('MULTIPLY', isl, 23.17))
    r1 = b.math('ADD', r1, b.math('MULTIPLY', oi.outputs["Random"], 0.37))
    r1 = b.math('FRACT', r1)
    return {"obj": obj, "geo": geo, "r1": r1, "r2": r2, "r3": r3}


def _bevel_wear(b, geo, raio, amostras=6):
    """Máscara 0..1 de quina (normal chanfrada diverge da normal real)."""
    bv = b.n("ShaderNodeBevel", samples=amostras, inp={"Radius": raio})
    dot = b.n("ShaderNodeVectorMath", operation='DOT_PRODUCT')
    b.nt.links.new(bv.outputs["Normal"], dot.inputs[0])
    b.nt.links.new(geo.outputs["Normal"], dot.inputs[1])
    x = b.math('SUBTRACT', 1.0, dot.outputs["Value"])
    return b.mapr(x, 0.004, 0.16, 0.0, 1.0), bv.outputs["Normal"]


def _ao(b, dist, amostras=10, inside=False):
    nd = b.n("ShaderNodeAmbientOcclusion", samples=amostras, inside=inside, only_local=False,
             inp={"Distance": dist})
    return nd.outputs["AO"]


# ---------------------------------------------------------------- pedra
def _montar_pedra(m, p):
    nt = m.node_tree
    nt.nodes.clear()
    b = _B(nt)
    out = b.n("ShaderNodeOutputMaterial")
    bsdf = b.n("ShaderNodeBsdfPrincipled")
    c = _comuns(b)
    obj, geo = c["obj"], c["geo"]
    sz = p.get("escala", 1.0)

    # vetor com leve distorção (veios tortos)
    wob = b.n("ShaderNodeVectorMath", operation='ADD')
    b.nt.links.new(obj, wob.inputs[0])
    nz = b.n("ShaderNodeTexNoise", noise_dimensions='3D', inp={"Scale": 2.2 * sz, "Detail": 3, "Roughness": 0.5})
    nzv = b.n("ShaderNodeVectorMath", operation='SCALE', inp={"Scale": 0.05 / sz})
    b.nt.links.new(nz.outputs["Color"], nzv.inputs[0])
    b.nt.links.new(nzv.outputs[0], wob.inputs[1])
    pv = wob.outputs[0]

    # ---- tom da pedra: manchas grandes + facetas cinzeladas + grão fino
    grande = b.noise(pv, 1.3 * sz, 5, 0.6)
    media = b.noise(pv, 5.5 * sz, 7, 0.55)
    fino = b.noise(pv, 38 * sz, 4, 0.6)
    facet = b.voro(pv, 13 * sz)                         # facetas de cinzel
    facet_cor = b.n("ShaderNodeRGBToBW")
    b.nt.links.new(facet.outputs["Color"], facet_cor.inputs["Color"])
    facet_edge = b.voro(pv, 8.5 * sz, 'DISTANCE_TO_EDGE')
    facet_e = b.mapr(facet_edge.outputs["Distance"], 0.0, 0.07, 0.0, 1.0)
    # facetas planas inclinadas por célula: altura = dot(inclinação aleatória, P - centro)
    fct = b.voro(pv, 8.5 * sz)
    dif = b.n("ShaderNodeVectorMath", operation='SUBTRACT')
    b.nt.links.new(pv, dif.inputs[0]); b.nt.links.new(fct.outputs["Position"], dif.inputs[1])
    cc = b.n("ShaderNodeVectorMath", operation='SUBTRACT', inp={1: (0.5, 0.5, 0.5)}) if False else None
    inc = b.n("ShaderNodeVectorMath", operation='SUBTRACT')
    b.nt.links.new(fct.outputs["Color"], inc.inputs[0]); inc.inputs[1].default_value = (0.5, 0.5, 0.5)
    dt = b.n("ShaderNodeVectorMath", operation='DOT_PRODUCT')
    b.nt.links.new(dif.outputs[0], dt.inputs[0]); b.nt.links.new(inc.outputs[0], dt.inputs[1])
    plano = b.math('MULTIPLY', dt.outputs["Value"], 8.5 * sz * 1.4)
    tom = b.math('ADD', b.math('MULTIPLY', grande, 0.42),
                 b.math('MULTIPLY', media, 0.25))
    tom = b.math('ADD', tom, b.math('ADD', b.math('MULTIPLY', facet_cor.outputs[0], 0.10), b.math('MULTIPLY', plano, 0.12)))
    tom = b.math('ADD', tom, b.math('MULTIPLY', fino, 0.2))
    tom = b.mapr(tom, 0.28, 0.85, 0.0, 1.0)
    base = b.ramp(tom, [(0.0, p["c0"]), (0.45, p["c1"]), (0.78, p["c2"]), (1.0, p["c3"])])

    # ---- variação por bloco: matiz (quente/frio) e valor
    tint = b.mixc(c["r2"], p["quente"], p["frio"])
    base = b.mulc(base, tint)
    val = b.mapr(c["r1"], 0.0, 1.0, p["v_min"], p["v_max"])
    vcol = b.n("ShaderNodeCombineColor")
    for k in ("Red", "Green", "Blue"):
        b.nt.links.new(val, vcol.inputs[k])
    base = b.mulc(base, vcol.outputs[0])

    contorno = b.math('MULTIPLY', b.mapr(facet_edge.outputs['Distance'], 0.0, 0.035, 1.0, 0.0), b.mapr(facet_cor.outputs[0], 0.35, 0.65, 0.0, 1.0))
    base = b.mulc(base, b.mixc(contorno, (1, 1, 1), (0.76, 0.76, 0.80)))

    # ---- veios de rachadura finos (Voronoi distância à aresta) + máscara para não cobrir tudo
    crk = b.voro(pv, 3.2 * sz, 'DISTANCE_TO_EDGE')
    crk_m = b.mapr(crk.outputs["Distance"], 0.0, 0.014, 1.0, 0.0)
    crk_gate = b.mapr(b.noise(obj, 1.8 * sz, 3, 0.5), 0.42, 0.55, 0.0, 1.0)
    crk_m = b.math('MULTIPLY', crk_m, crk_gate)
    crk2 = b.voro(pv, 11 * sz, 'DISTANCE_TO_EDGE')
    crk2_m = b.mapr(crk2.outputs["Distance"], 0.0, 0.010, 1.0, 0.0)
    crk2_gate = b.mapr(b.noise(obj, 4.0 * sz, 3, 0.5), 0.50, 0.62, 0.0, 1.0)
    crk2_m = b.math('MULTIPLY', crk2_m, crk2_gate)
    rach = b.math('MAXIMUM', crk_m, b.math('MULTIPLY', crk2_m, 0.7))
    base = b.mixc(b.math('MULTIPLY', rach, 0.85), base, p["fenda"])

    # ---- desgaste de quina e cavidades
    desg, bev_n = _bevel_wear(b, geo, p.get("bevel", 0.03) * sz, 6)
    ruido_q = b.mapr(b.noise(obj, 22 * sz, 5, 0.6), 0.3, 0.75, 0.25, 1.0)
    quina = b.math('MULTIPLY', desg, ruido_q)
    quina = b.mapr(quina, 0.02, 0.30, 0.0, 1.0)
    clara = b.mulc(base, (p["quina_mult"],) * 3)
    clara = b.mixc(0.5, clara, p["quina_cor"])
    base = b.mixc(quina, base, clara)

    ao_p = _ao(b, 0.28 * sz, 10)
    ao_g = _ao(b, 0.9 * sz, 6)
    cav = b.mapr(ao_p, 0.25, 1.0, 0.0, 1.0)
    cav = b.math('POWER', cav, 1.4)
    cav2 = b.mapr(ao_g, 0.2, 1.0, 0.0, 1.0)
    escur = b.math('MULTIPLY', b.mapr(cav, 0.0, 1.0, 0.18, 1.0), b.mapr(cav2, 0.0, 1.0, p.get("ao_g_min", 0.45), 1.0))
    esc3 = b.n("ShaderNodeCombineColor")
    for k in ("Red", "Green", "Blue"):
        b.nt.links.new(escur, esc3.inputs[k])
    base = b.mulc(base, esc3.outputs[0])

    # ---- musgo: faces para cima + fresta (AO baixo) + topo das quinas
    nrm = b.sep_xyz(geo.outputs["Normal"])
    cima = b.mapr(nrm["Z"], 0.25, 0.9, 0.0, 1.0)
    pat = b.noise(obj, 4.5 * sz, 8, 0.6, 0.4)
    pat2 = b.noise(obj, 16 * sz, 5, 0.6)
    m1 = b.math('MULTIPLY', cima, b.mapr(pat, 0.42, 0.58, 0.0, 1.0))
    fre = b.math('MULTIPLY', b.mapr(ao_p, 0.0, 0.7, 1.0, 0.0), b.mapr(pat, 0.3, 0.5, 0.0, 1.0))
    fre = b.math('MULTIPLY', fre, b.mapr(nrm["Z"], -0.6, 0.6, 0.15, 1.0))
    musgo = b.math('MAXIMUM', m1, b.math('MULTIPLY', fre, p.get("musgo_fresta", 0.9)))
    musgo = b.math('MULTIPLY', musgo, p.get("musgo_qtd", 1.0))
    musgo = b.math('ADD', musgo, b.math('MULTIPLY', b.math('SUBTRACT', pat2, 0.5), 0.25))
    if p.get("musgo_h"):   # musgo cresce para baixo: (z de cima, z de baixo, peso em cima)
        zalto, zbaixo, wtopo = p["musgo_h"]
        musgo = b.math('MULTIPLY', musgo, b.mapr(b.sep_xyz(obj)["Z"], zalto, zbaixo, wtopo, 1.0))
    lim = p.get("musgo_lim", (0.34, 0.52))
    musgo = b.mapr(musgo, lim[0], lim[1], 0.0, 1.0)
    mus_cor = b.ramp(b.mapr(b.noise(obj, 9 * sz, 5, 0.6), 0.3, 0.7, 0.0, 1.0),
                     [(0.0, tuple(c * p.get("musgo_k", 1.0) for c in (0.030, 0.050, 0.012))), (0.5, tuple(c * p.get("musgo_k", 1.0) for c in (0.075, 0.105, 0.024))), (1.0, tuple(c * p.get("musgo_k", 1.0) for c in (0.135, 0.165, 0.040)))])
    base = b.mixc(musgo, base, mus_cor)

    # ---- sujeira escura de chuva embaixo de saliências (pouca) em tons frios
    suj = b.mapr(b.noise(obj, 3.0 * sz, 6, 0.55), 0.45, 0.70, 0.0, 0.62)
    suj = b.math('MULTIPLY', suj, b.mapr(nrm["Z"], 0.4, -0.5, 0.0, 1.0))
    base = b.mixc(suj, base, p["suja"])
    if p.get("escorre"):   # umidade escorrendo de cima em faixas verticais, e sujeira que sobe do pé
        ov = b.n("ShaderNodeVectorMath", operation='MULTIPLY'); ov.inputs[1].default_value = (3.0, 6.0, 0.8)
        b.nt.links.new(obj, ov.inputs[0])
        fx = b.mapr(b.noise(ov.outputs[0], 2.2 * sz, 4, 0.55), 0.42, 0.66, 0.0, 1.0)
        lateral = b.mapr(nrm["Z"], 0.6, 0.1, 0.0, 1.0)
        base = b.mixc(b.math('MULTIPLY', b.math('MULTIPLY', fx, lateral), p["escorre"]), base, p["suja"])
        zb = p.get("sujo_base", (0.0, 1.2))
        pe = b.mapr(b.sep_xyz(obj)["Z"], zb[1], zb[0], 0.0, 1.0)
        base = b.mixc(b.math('MULTIPLY', pe, b.mapr(b.noise(obj, 3.5 * sz, 4, 0.6), 0.3, 0.7, 0.2, 0.7)), base, p["suja"])

    # ---- relevo: facetas + grão + rachaduras
    alt = b.math('ADD', b.math('MULTIPLY', facet_e, 0.16), b.math('MULTIPLY', fino, 0.12))
    alt = b.math('SUBTRACT', alt, b.math('MULTIPLY', rach, 0.35))
    alt = b.math('ADD', alt, b.math('MULTIPLY', plano, 0.9))
    alt = b.math('ADD', alt, b.math('MULTIPLY', musgo, 0.25))
    alt = b.math('ADD', alt, b.math('MULTIPLY', media, 0.25))
    bump = b.n("ShaderNodeBump", inp={"Strength": p.get("bump", 0.7), "Distance": 0.03 * sz, "Height": alt})
    b.nt.links.new(bev_n, bump.inputs["Normal"])

    # ---- rugosidade
    rug = b.mapr(fino, 0.3, 0.7, p["rug_min"], p["rug_max"])
    rug = b.math('ADD', rug, b.math('MULTIPLY', musgo, 0.25), clamp=True)
    rug = b.math('SUBTRACT', rug, b.math('MULTIPLY', quina, 0.12), clamp=True)

    bsdf.inputs["Metallic"].default_value = 0.0
    b.link(base, bsdf, "Base Color")
    b.link(rug, bsdf, "Roughness")
    b.link(bump.outputs["Normal"], bsdf, "Normal")
    b.link(bsdf.outputs["BSDF"], out, "Surface")


# ---------------------------------------------------------------- musgo isolado (tufos)
def _montar_musgo(m):
    nt = m.node_tree
    nt.nodes.clear()
    b = _B(nt)
    out = b.n("ShaderNodeOutputMaterial")
    bsdf = b.n("ShaderNodeBsdfPrincipled")
    c = _comuns(b)
    obj, geo = c["obj"], c["geo"]
    v = b.noise(obj, 11.0, 6, 0.6)
    v2 = b.noise(obj, 40.0, 4, 0.6)
    voro = b.voro(obj, 26.0)
    vb = b.n("ShaderNodeRGBToBW")
    b.nt.links.new(voro.outputs["Color"], vb.inputs["Color"])
    t = b.math('ADD', b.math('MULTIPLY', v, 0.5), b.math('MULTIPLY', vb.outputs[0], 0.3))
    t = b.math('ADD', t, b.math('MULTIPLY', v2, 0.2))
    t = b.mapr(t, 0.25, 0.85)
    base = b.ramp(t, [(0.0, (0.028, 0.046, 0.010)), (0.45, (0.075, 0.115, 0.026)),
                      (0.8, (0.16, 0.20, 0.040)), (1.0, (0.24, 0.26, 0.06))])
    desg, bev_n = _bevel_wear(b, geo, 0.01, 4)
    base = b.mixc(b.mapr(desg, 0.1, 0.8, 0, 0.5), base, (0.30, 0.31, 0.08))
    ao = _ao(b, 0.2, 8)
    base = b.mulc(base, b.mixc(b.mapr(ao, 0.2, 1.0, 1.0, 0.0), (1, 1, 1), (0.25, 0.3, 0.2)))
    bump = b.n("ShaderNodeBump", inp={"Strength": 0.8, "Distance": 0.02, "Height": t})
    b.nt.links.new(bev_n, bump.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.95
    bsdf.inputs["Metallic"].default_value = 0.0
    b.link(base, bsdf, "Base Color")
    b.link(bump.outputs["Normal"], bsdf, "Normal")
    b.link(bsdf.outputs["BSDF"], out, "Surface")


# ---------------------------------------------------------------- ferro
def _montar_ferro(m, p):
    nt = m.node_tree
    nt.nodes.clear()
    b = _B(nt)
    out = b.n("ShaderNodeOutputMaterial")
    bsdf = b.n("ShaderNodeBsdfPrincipled")
    c = _comuns(b)
    obj, geo = c["obj"], c["geo"]
    sz = p.get("escala", 1.0)

    big = b.noise(obj, 2.6 * sz, 6, 0.6, 0.3)
    mid = b.noise(obj, 9.0 * sz, 8, 0.6)
    fine = b.noise(obj, 55 * sz, 4, 0.6)
    pit = b.voro(obj, 60 * sz)
    pit_bw = b.n("ShaderNodeRGBToBW")
    b.nt.links.new(pit.outputs["Color"], pit_bw.inputs["Color"])

    # metal escuro base com variação por elo
    var = b.mapr(c["r1"], 0.0, 1.0, p["v_min"], p["v_max"])
    vc = b.n("ShaderNodeCombineColor")
    for k in ("Red", "Green", "Blue"):
        b.nt.links.new(var, vc.inputs[k])
    base = b.ramp(b.mapr(mid, 0.3, 0.7), [(0.0, p["b0"]), (1.0, p["b1"])])
    base = b.mulc(base, vc.outputs[0])

    # ferrugem: manchas grandes limiarizadas + salpicado fino
    ferr = b.math('ADD', b.math('MULTIPLY', big, 0.55), b.math('MULTIPLY', mid, 0.30))
    ferr = b.math('ADD', ferr, b.math('MULTIPLY', pit_bw.outputs[0], 0.15))
    ferr = b.math('ADD', ferr, b.math('MULTIPLY', c["r2"], 0.12))
    ferr = b.mapr(ferr, p["lim"], p["lim"] + 0.2, 0.0, 1.0)
    ferr_cor = b.ramp(b.mapr(b.noise(obj, 30 * sz, 5, 0.6), 0.25, 0.75),
                      [(0.0, p["r0"]), (0.5, p["r1"]), (1.0, p["r2"])])
    base = b.mixc(ferr, base, ferr_cor)
    # grão escuro dentro da ferrugem (poros)
    poro = b.mapr(fine, 0.35, 0.7, 0.55, 1.0)
    pv3 = b.n("ShaderNodeCombineColor")
    for k in ("Red", "Green", "Blue"):
        b.nt.links.new(poro, pv3.inputs[k])
    base = b.mulc(base, pv3.outputs[0])

    # desgaste metálico nas quinas (aço polido)
    desg, bev_n = _bevel_wear(b, geo, p.get("bevel", 0.006) * sz, 6)
    quina = b.math('MULTIPLY', desg, b.mapr(b.noise(obj, 40 * sz, 4, 0.6), 0.25, 0.7, 0.4, 1.0))
    quina = b.mapr(quina, 0.04, 0.5)
    base = b.mixc(b.math('MULTIPLY', quina, 0.9), base, p["polido"])

    # cavidades escuras
    ao = _ao(b, 0.12 * sz, 10)
    escur = b.mapr(ao, 0.2, 1.0, 0.15, 1.0)
    ec = b.n("ShaderNodeCombineColor")
    for k in ("Red", "Green", "Blue"):
        b.nt.links.new(escur, ec.inputs[k])
    base = b.mulc(base, ec.outputs[0])

    # depósito de pó/sujeira clara em quinas de cima pouco
    nrm = b.sep_xyz(geo.outputs["Normal"])
    pat = b.mapr(nrm["Z"], 0.5, 1.0, 0.0, 0.25)
    base = b.mixc(b.math('MULTIPLY', pat, b.mapr(mid, 0.4, 0.7)), base, (0.20, 0.10, 0.05))

    alt = b.math('ADD', b.math('MULTIPLY', mid, 0.5), b.math('MULTIPLY', fine, 0.25))
    alt = b.math('ADD', alt, b.math('MULTIPLY', ferr, 0.35))
    alt = b.math('SUBTRACT', alt, b.math('MULTIPLY', pit_bw.outputs[0], 0.15))
    bump = b.n("ShaderNodeBump", inp={"Strength": 0.9, "Distance": 0.006 * sz, "Height": alt})
    b.nt.links.new(bev_n, bump.inputs["Normal"])

    rug_s = b.math('ADD', p["rug_base"], b.math('MULTIPLY', ferr, 0.35))
    rug_s = b.math('ADD', rug_s, b.math('MULTIPLY', b.math('SUBTRACT', fine, 0.5), 0.2))
    rug_s = b.math('MULTIPLY', rug_s, b.mapr(quina, 0.0, 1.0, 1.0, 0.45), clamp=True)
    metal = b.math('ADD', b.math('MULTIPLY', quina, 0.95), p["metal_base"])
    metal = b.math('MULTIPLY', metal, b.mapr(ferr, 0.0, 1.0, 1.0, 0.55), clamp=True)

    b.link(base, bsdf, "Base Color")
    b.link(rug_s, bsdf, "Roughness")
    b.link(metal, bsdf, "Metallic")
    b.link(bump.outputs["Normal"], bsdf, "Normal")
    b.link(bsdf.outputs["BSDF"], out, "Surface")


# ---------------------------------------------------------------- API pública
_PEDRA = dict(
    nome="M_Pedra",
    c0=(0.030, 0.026, 0.021), c1=(0.115, 0.098, 0.076), c2=(0.225, 0.196, 0.152), c3=(0.400, 0.355, 0.285),
    quente=(1.08, 1.0, 0.86), frio=(0.97, 0.97, 0.95), v_min=0.66, v_max=1.30,
    fenda=(0.010, 0.008, 0.008), quina_mult=2.6, quina_cor=(0.55, 0.52, 0.45),
    suja=(0.035, 0.030, 0.024), rug_min=0.72, rug_max=0.95, bump=0.8, musgo_qtd=2.0,
)
_ESCURA = dict(
    nome="M_PedraEscura",
    c0=(0.024, 0.022, 0.022), c1=(0.075, 0.068, 0.062), c2=(0.140, 0.128, 0.115), c3=(0.235, 0.215, 0.190),
    quente=(1.06, 1.0, 0.92), frio=(0.92, 0.96, 1.02), v_min=0.82, v_max=1.15,
    fenda=(0.004, 0.004, 0.007), quina_mult=2.1, quina_cor=(0.34, 0.37, 0.46),
    suja=(0.01, 0.012, 0.02), rug_min=0.65, rug_max=0.9, bump=0.7, musgo_qtd=1.0,
)
_FERRO = dict(
    nome="M_Ferro", b0=(0.018, 0.012, 0.010), b1=(0.055, 0.032, 0.024), v_min=0.7, v_max=1.25,
    r0=(0.10, 0.034, 0.014), r1=(0.22, 0.072, 0.022), r2=(0.52, 0.19, 0.05), lim=0.46,
    polido=(0.42, 0.34, 0.30), rug_base=0.50, metal_base=0.15, bevel=0.005,
)
_FERRO_ESC = dict(
    nome="M_FerroEscuro", b0=(0.012, 0.012, 0.015), b1=(0.040, 0.038, 0.045), v_min=0.75, v_max=1.2,
    r0=(0.10, 0.035, 0.014), r1=(0.22, 0.075, 0.025), r2=(0.34, 0.12, 0.035), lim=0.62,
    polido=(0.38, 0.38, 0.42), rug_base=0.42, metal_base=0.35, bevel=0.005,
)


def criar_materiais() -> dict:
    """Cria (ou recria) os 5 materiais procedurais e devolve {'pedra','escura','musgo','ferro','ferro_escuro'}."""
    def novo(nome):
        antigo = bpy.data.materials.get(nome)
        if antigo:
            antigo.name = nome + ".old"
            antigo.use_fake_user = False
        m = bpy.data.materials.new(nome)
        m.use_nodes = True
        return m
    res = {}
    res["pedra"] = novo("M_Pedra"); _montar_pedra(res["pedra"], _PEDRA)
    res["escura"] = novo("M_PedraEscura"); _montar_pedra(res["escura"], _ESCURA)
    res["musgo"] = novo("M_Musgo"); _montar_musgo(res["musgo"])
    res["ferro"] = novo("M_Ferro"); _montar_ferro(res["ferro"], _FERRO)
    res["ferro_escuro"] = novo("M_FerroEscuro"); _montar_ferro(res["ferro_escuro"], _FERRO_ESC)
    for m in res.values():
        m.use_fake_user = True
    return res


def _cycles_1thread(sc, samples):
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.render.threads_mode = 'AUTO'
    sc.render.threads = 1
    try:
        sc.cycles.use_adaptive_sampling = False
    except Exception:
        pass


def _uv_bake(obj, margem_ilha=0.002):
    me = obj.data
    for l in list(me.uv_layers):  # fica só UV_Bake: o glTF/Godot lê um conjunto de UV só (TEXCOORD_0)
        me.uv_layers.remove(l)
    uv = me.uv_layers.new(name="UV_Bake")
    me.uv_layers.active = uv
    uv.active_render = True
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=margem_ilha,
                             area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=margem_ilha, rotate=True)  # escala uniforme: densidade de texel constante
    bpy.ops.object.mode_set(mode='OBJECT')


def densidade_texel(obj, tamanho):
    """Texels por metro (média): sqrt(área UV * tamanho² / área 3D)."""
    me = obj.data
    uv = me.uv_layers.active.data
    a3 = sum(p.area for p in me.polygons)
    a2 = 0.0
    for p in me.polygons:
        pts = [uv[i].uv for i in p.loop_indices]
        a2 += abs(sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y
                      for i in range(len(pts)))) / 2
    return math.sqrt(a2 * tamanho * tamanho / max(a3, 1e-9))


def bake(obj, tamanho=2048, samples=12, pasta=PASTA_PADRAO, nome="ColunaCorrente", margem=16) -> dict:
    """UV Smart Project + bake de cor (sem luz) e normal tangente; troca os slots por um material único."""
    import time
    t0 = time.time()
    os.makedirs(pasta, exist_ok=True)
    sc = bpy.context.scene
    _cycles_1thread(sc, samples)
    sc.cycles.bake_type = 'DIFFUSE'
    sc.render.bake.margin = margem
    sc.render.bake.margin_type = 'EXTEND'

    _ORIG[obj.name] = ([s.material for s in obj.material_slots], [p.material_index for p in obj.data.polygons])
    mats_orig = [m for m in _ORIG[obj.name][0] if m]
    for m in mats_orig:
        m.use_fake_user = True

    _uv_bake(obj)
    t_uv = time.time() - t0

    def imagem(sufixo, nao_cor):
        nm = f"T_{nome}_{sufixo}"
        if nm in bpy.data.images:
            bpy.data.images.remove(bpy.data.images[nm])
        im = bpy.data.images.new(nm, tamanho, tamanho, alpha=False, float_buffer=False)
        im.colorspace_settings.name = 'Non-Color' if nao_cor else 'sRGB'
        im.filepath_raw = os.path.join(pasta, nm + ".png")
        im.file_format = 'PNG'
        return im

    im_c = imagem("BaseColor", False)
    im_n = imagem("Normal", True)

    # metallic zerado durante o bake de cor (o Diffuse some com metal)
    guardado = []
    for m in mats_orig:
        for nd in m.node_tree.nodes:
            if nd.type == 'BSDF_PRINCIPLED':
                s = nd.inputs["Metallic"]
                lig = [l.from_socket for l in s.links]
                guardado.append((s, s.default_value, lig))
                for l in list(s.links):
                    m.node_tree.links.remove(l)
                s.default_value = 0.0

    def alvo(im):
        for m in mats_orig:
            nt = m.node_tree
            n = nt.nodes.get("_BAKE")
            if n is None:
                n = nt.nodes.new("ShaderNodeTexImage"); n.name = "_BAKE"
            n.image = im
            nt.nodes.active = n
            n.select = True

    alvo(im_c)
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, margin=margem, margin_type='EXTEND',
                        use_clear=True, use_selected_to_active=False, target='IMAGE_TEXTURES')
    im_c.save()
    t_cor = time.time() - t0

    for s, v, lig in guardado:
        s.default_value = v
        for fs in lig:
            s.id_data.links.new(fs, s)

    sc.cycles.samples = max(4, samples // 3)  # normal é quase determinístico
    alvo(im_n)
    bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', margin=margem, margin_type='EXTEND',
                        use_clear=True, use_selected_to_active=False, target='IMAGE_TEXTURES')
    im_n.save()
    t_nor = time.time() - t0
    for m in mats_orig:
        n = m.node_tree.nodes.get("_BAKE")
        if n:
            m.node_tree.nodes.remove(n)

    mb = _material_baked(im_c, im_n, nome)
    obj.data.materials.clear()
    obj.data.materials.append(mb)
    for pl in obj.data.polygons:
        pl.material_index = 0
    for im in (im_c, im_n):
        im.pack()
    return {"texels_por_metro": round(densidade_texel(obj, tamanho)),
            "cor": im_c.filepath_raw, "normal": im_n.filepath_raw, "material": mb,
            "segundos": {"uv": round(t_uv, 1), "cor": round(t_cor - t_uv, 1),
                         "normal": round(t_nor - t_cor, 1), "total": round(time.time() - t0, 1)}}


def _material_baked(im_c, im_n, nome):
    nm = "M_" + nome
    if nm in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials[nm])
    m = bpy.data.materials.new(nm)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Roughness"].default_value = 0.8
    bs.inputs["Metallic"].default_value = 0.0
    uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = "UV_Bake"
    tc = nt.nodes.new("ShaderNodeTexImage"); tc.image = im_c; tc.interpolation = 'Linear'
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = im_n
    nm_node = nt.nodes.new("ShaderNodeNormalMap"); nm_node.space = 'TANGENT'; nm_node.uv_map = "UV_Bake"
    nt.links.new(uvn.outputs["UV"], tc.inputs["Vector"])
    nt.links.new(uvn.outputs["UV"], tn.inputs["Vector"])
    nt.links.new(tc.outputs["Color"], bs.inputs["Base Color"])
    nt.links.new(tn.outputs["Color"], nm_node.inputs["Color"])
    nt.links.new(nm_node.outputs["Normal"], bs.inputs["Normal"])
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------- prévia
def _bbox_mundo(objs):
    pts = []
    for o in objs:
        for c in o.bound_box:
            pts.append(o.matrix_world @ Vector(c))
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def render_preview(obj_ou_cena, caminho, vista="tres_quartos", res=(800, 800), samples=64, material="auto"):
    """Renderiza em Cycles (1 thread). obj_ou_cena: objeto, lista de objetos ou None (cena inteira).
    vista: 'tres_quartos' | 'frente' | 'close'. material: 'auto' (como está), 'baked' ou 'procedural'
    (só vale para objeto passado a bake())."""
    sc = bpy.context.scene
    if obj_ou_cena is None or not hasattr(obj_ou_cena, "name") and not isinstance(obj_ou_cena, (list, tuple)):
        objs = [o for o in sc.objects if o.type == 'MESH']
    elif isinstance(obj_ou_cena, (list, tuple)):
        objs = list(obj_ou_cena)
    else:
        objs = [obj_ou_cena]
    if isinstance(res, int):
        res = (res, res)

    # troca temporária de material
    trocas = []
    if material == 'procedural':
        for o in objs:
            if o.name in _ORIG:
                trocas.append((o, [s.material for s in o.material_slots]))
                o.data.materials.clear()
                for mm in _ORIG[o.name][0]:
                    o.data.materials.append(mm)
                for pl, i in zip(o.data.polygons, _ORIG[o.name][1]):
                    pl.material_index = i
    mn, mx = _bbox_mundo(objs)
    cen = (mn + mx) / 2
    dim = mx - mn
    mdim = max(dim)

    _cycles_1thread(sc, samples)
    sc.cycles.use_denoising = False
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    try:
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    sc.view_settings.exposure = 0.0

    criados = []
    w = bpy.data.worlds.new("_w"); w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.020, 0.026, 0.045, 1); bg.inputs[1].default_value = 1.0
    sc_w = sc.world
    sc.world = w
    criados.append(w)

    def luz(nome, tipo, loc, energia, cor, tam=1.0, apontar=cen):
        ld = bpy.data.lights.new(nome, tipo)
        ld.energy = energia; ld.color = cor
        if tipo == 'AREA':
            ld.size = tam
        elif tipo == 'POINT':
            ld.shadow_soft_size = tam
        lo = bpy.data.objects.new(nome, ld)
        sc.collection.objects.link(lo)
        lo.location = loc
        d = apontar - Vector(loc)
        lo.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        criados.append(lo); criados.append(ld)
        return lo

    k = mdim
    # tocha quente lateral (esquerda-frente, alta) + preenchimento frio do lado oposto + contraluz fraco
    luz("_tocha", 'AREA', (cen.x - 0.9 * k, cen.y + 0.7 * k, cen.z + 0.8 * k), 110 * k * k, (1.0, 0.70, 0.42), 0.45 * k)
    luz("_fill", 'AREA', (cen.x + 1.1 * k, cen.y + 0.9 * k, cen.z + 0.35 * k), 45 * k * k, (0.45, 0.60, 1.0), 1.4 * k)
    luz("_rim", 'AREA', (cen.x + 0.3 * k, cen.y - 1.1 * k, cen.z + 0.9 * k), 60 * k * k, (0.55, 0.65, 1.0), 0.8 * k)

    cam_d = bpy.data.cameras.new("_cam")
    cam = bpy.data.objects.new("_cam", cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    criados += [cam, cam_d]
    if vista == "frente":
        d = Vector((0.0, 1.0, 0.18)); alvo = cen; dist = 1.55 * k; cam_d.lens = 50
    elif vista == "close":
        d = Vector((0.25, 1.0, 0.30)); alvo = cen + Vector((-0.34 * dim.x, 0, 0.22 * dim.z)); dist = 0.5 * k
        cam_d.lens = 50
    elif vista == "lado":
        d = Vector((1.0, 0.05, 0.12)); alvo = cen; dist = 1.55 * k; cam_d.lens = 50
    elif vista == "topo":
        d = Vector((0.0, 0.35, 1.0)); alvo = cen; dist = 1.5 * k; cam_d.lens = 50
    else:
        d = Vector((0.62, 0.78, 0.42)); alvo = cen; dist = 1.5 * k; cam_d.lens = 50
    d.normalize()
    cam.location = alvo + d * dist
    cam.rotation_euler = (alvo - cam.location).to_track_quat('-Z', 'Y').to_euler()

    os.makedirs(os.path.dirname(os.path.abspath(caminho)), exist_ok=True)
    sc.render.filepath = caminho
    bpy.ops.render.render(write_still=True)

    for o, mats in trocas:
        o.data.materials.clear()
        for mm in mats:
            o.data.materials.append(mm)
        for pl in o.data.polygons:
            pl.material_index = 0
    for it in criados:
        try:
            if isinstance(it, bpy.types.Object):
                bpy.data.objects.remove(it, do_unlink=True)
            elif isinstance(it, bpy.types.Light):
                bpy.data.lights.remove(it)
            elif isinstance(it, bpy.types.Camera):
                bpy.data.cameras.remove(it)
            elif isinstance(it, bpy.types.World):
                bpy.data.worlds.remove(it)
        except Exception:
            pass
    sc.world = sc_w
    return caminho
