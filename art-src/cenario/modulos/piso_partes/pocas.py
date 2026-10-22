"""Piso da Cripta, parte POCAS E MUSGO: poças rasas, anéis de umidade, tufos de musgo e raízes finas.
Materiais: M_Piso_Agua, M_Piso_Umido, M_Piso_Musgo, M_Piso_Musgo_Claro, M_Piso_Raiz.
Periodicidade de 8 m: nada fica a menos de 0,3 m da borda do módulo (poças e musgo); raízes idem."""
import bpy, bmesh, math, os, random, sys
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum

SEED_P = 5207
BORDA = 0.30
Z_AGUA = 0.0026      # topo da água (+2,6 mm)
Z_UMIDO = 0.0010


def _mat_agua():
    m = comum.material("M_Piso_Agua", (0.008, 0.020, 0.040), rough=0.03)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Alpha"].default_value = 0.82
    for attr, val in (("blend_method", 'BLEND'), ("surface_render_method", 'BLENDED')):
        try: setattr(m, attr, val)
        except Exception: pass
    try: b.inputs["Specular IOR Level"].default_value = 0.8
    except Exception: pass
    return m

def _mats():
    return dict(
        agua=_mat_agua(),
        umido=comum.material("M_Piso_Umido", (0.013, 0.018, 0.028), rough=0.18),
        musgo=comum.material("M_Piso_Musgo", (0.016, 0.048, 0.030), rough=0.95),
        musgo2=comum.material("M_Piso_Musgo_Claro", (0.030, 0.075, 0.032), rough=0.95),
        raiz=comum.material("M_Piso_Raiz", (0.060, 0.042, 0.032), rough=0.90),
    )


# ---------------------------------------------------------------- blobs
def _blob(r, raio):
    """Contorno orgânico em coordenadas polares: elipse + harmônicos. Retorna f(theta)->raio."""
    el = r.uniform(1.0, 1.5); rot = r.uniform(0, math.pi)
    har = [(k, r.uniform(0.04, 0.16) / (k * 0.6), r.uniform(0, 6.28)) for k in (2, 3, 4, 5, 7)]
    def f(t):
        a = t - rot
        e = 1.0 / math.sqrt((math.cos(a) / el) ** 2 + (math.sin(a) * el) ** 2 + 1e-9) * 1.0
        k = 1.0 + sum(A * math.cos(n * t + p) for n, A, p in har)
        return raio * min(e, 1.6) * k * 0.85
    return f


def _anel(bm, cx, cy, f_in, f_out, z_in, z_out, n=64, passos=3, ruido=None):
    """Faixa entre dois contornos polares (f_in..f_out), com 'passos' anéis intermediários; z interpolado."""
    linhas = []
    for i in range(passos + 1):
        u = i / passos
        v = []
        for k in range(n):
            t = 2 * math.pi * k / n
            ri = f_in(t); ro = f_out(t); rr = ri + (ro - ri) * u
            z = z_in + (z_out - z_in) * u
            if ruido: z += ruido.uniform(-0.0002, 0.0002)
            v.append(bm.verts.new((cx + rr * math.cos(t), cy + rr * math.sin(t), z)))
        linhas.append(v)
    for i in range(passos):
        for k in range(n):
            k2 = (k + 1) % n
            bm.faces.new((linhas[i][k], linhas[i][k2], linhas[i + 1][k2], linhas[i + 1][k]))
    return linhas


def _poca(idx, cx, cy, raio, r, M):
    f = _blob(r, raio)
    # água: leque de anéis do centro até o contorno, com leve queda na borda (menisco)
    bm = bmesh.new(); n = 72
    c = bm.verts.new((cx, cy, Z_AGUA))
    aneis = []
    for j in range(1, 6):
        t_ = j / 5.0
        v = []
        for k in range(n):
            t = 2 * math.pi * k / n
            rr = f(t) * (t_ if j < 5 else 1.0)
            z = Z_AGUA - (0.0006 * t_ ** 6)         # menisco: cai de leve na beirada
            v.append(bm.verts.new((cx + rr * math.cos(t), cy + rr * math.sin(t), z)))
        aneis.append(v)
    for k in range(n):
        bm.faces.new((c, aneis[0][k], aneis[0][(k + 1) % n]))
    for j in range(4):
        for k in range(n):
            k2 = (k + 1) % n
            bm.faces.new((aneis[j][k], aneis[j + 1][k], aneis[j + 1][k2], aneis[j][k2]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o_agua = comum.novo_objeto(f"Poca_{idx}", bm, [M["agua"]])

    # umidade: borda molhada fina e escura (menisco) + halo largo irregular
    h = [(k, r.uniform(0.05, 0.14), r.uniform(0, 6.28)) for k in (2, 3, 5, 6)]
    ex = r.uniform(1.12, 1.35)
    def f_halo(t): return f(t) * (ex + sum(A * math.cos(n_ * t + p) for n_, A, p in h))
    def f_borda(t): return f(t) * 1.05 + 0.012
    bm = bmesh.new()
    _anel(bm, cx, cy, lambda t: f(t) * 0.995, f_borda, Z_AGUA - 0.0006, Z_UMIDO + 0.0004, n=n, passos=1)
    _anel(bm, cx, cy, f_borda, f_halo, Z_UMIDO + 0.0004, Z_UMIDO - 0.0004, n=n, passos=3, ruido=r)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o_um = comum.novo_objeto(f"Umido_{idx}", bm, [M["umido"]])
    return [o_agua, o_um], f


# ---------------------------------------------------------------- musgo
def _lamina(bm, base, r, altura, larg, inclina):
    """Lâmina fina de musgo/líquen: base triangular, um anel intermediário curvado e ponta. ~9 triângulos."""
    ang = r.uniform(0, 6.28)
    dirv = Vector((math.cos(ang), math.sin(ang), 0))
    curva = inclina * altura
    def anel(t, w):
        cen = Vector(base) + dirv * (curva * t * t) + Vector((0, 0, altura * t))
        vs = []
        for k in range(3):
            a = ang + 2.094 * k + r.uniform(-0.3, 0.3)
            vs.append(bm.verts.new(cen + Vector((math.cos(a), math.sin(a), 0)) * w * r.uniform(0.8, 1.2)))
        return vs
    a0 = anel(0.0, larg); a1 = anel(0.55, larg * 0.6)
    tip = bm.verts.new(Vector(base) + dirv * curva * 1.1 + Vector((0, 0, altura)))
    for k in range(3):
        k2 = (k + 1) % 3
        bm.faces.new((a0[k], a0[k2], a1[k2], a1[k]))
        bm.faces.new((a1[k], a1[k2], tip))
    bm.faces.new(a0[::-1])


def _monte(bm, cx, cy, raio, alt, r):
    """Montinho irregular achatado (icosfera deformada por ruído e esmagada), sem cara de esfera lisa."""
    g = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    vs = g["verts"]
    for v in vs:
        s = r.uniform(0.55, 1.15)
        v.co = Vector((v.co.x * raio * s * r.uniform(0.8, 1.25), v.co.y * raio * s * r.uniform(0.8, 1.25),
                       v.co.z * alt * r.uniform(0.6, 1.2)))
        v.co.x += cx; v.co.y += cy
        v.co.z = max(v.co.z, -0.002) + alt * 0.1
    # recorta o fundo: tudo abaixo de -2 mm vira -2 mm (assenta no piso)
    for v in vs:
        if v.co.z < 0.0: v.co.z = -0.002


def _tufo(bm, bm2, x, y, r, escala=1.0):
    n = r.randint(11, 19)
    raio = r.uniform(0.030, 0.065) * escala
    _monte(bm2, x, y, raio * 1.2, r.uniform(0.012, 0.024) * escala, r)
    for _ in range(n):
        a = r.uniform(0, 6.28); d = abs(r.gauss(0, raio))
        px, py = x + d * math.cos(a), y + d * math.sin(a)
        alt = r.uniform(0.012, 0.032) * escala * (1.0 - 0.5 * d / (raio * 2.5 + 1e-6))
        _lamina(bm, (px, py, 0.0), r, max(alt, 0.010), r.uniform(0.0035, 0.0070), r.uniform(0.0, 0.6))


def _livre(x, y, margem=BORDA):
    return margem <= x <= comum.TILE - margem and margem <= y <= comum.TILE - margem


def _musgo(r, lajes, pocas, M):
    bm1 = bmesh.new(); bm2 = bmesh.new(); bm_m = bmesh.new()   # lâminas escuras, lâminas claras, montinhos
    pontos = []
    for l in lajes:
        # quinas: quase sempre, com probabilidade; bordas: pontos ao longo da junta
        for (x, y) in ((l["x0"], l["y0"]), (l["x1"], l["y0"]), (l["x1"], l["y1"]), (l["x0"], l["y1"])):
            if r.random() < 0.32: pontos.append((x, y, 1.0))
        for (xa, ya, xb, yb) in ((l["x0"], l["y0"], l["x1"], l["y0"]), (l["x1"], l["y0"], l["x1"], l["y1"]),
                                 (l["x1"], l["y1"], l["x0"], l["y1"]), (l["x0"], l["y1"], l["x0"], l["y0"])):
            comp = math.hypot(xb - xa, yb - ya)
            if r.random() < 0.32:
                # trecho contínuo de musgo ao longo da junta
                t0 = r.uniform(0.05, 0.6); t1 = min(0.97, t0 + r.uniform(0.15, 0.35))
                m = max(2, int(comp * (t1 - t0) / 0.12))
                for i in range(m):
                    t = t0 + (t1 - t0) * (i + r.random()) / m
                    pontos.append((xa + (xb - xa) * t, ya + (yb - ya) * t, 0.8))
    # musgo extra perto das poças (mais umidade)
    for (cx, cy, f) in pocas:
        for _ in range(26):
            t = r.uniform(0, 6.28); rr = f(t) * r.uniform(1.15, 1.9)
            pontos.append((cx + rr * math.cos(t), cy + rr * math.sin(t), 0.7))
    cont = 0
    for (x, y, e) in pontos:
        # puxa o ponto para a junta mais próxima? Já está nas arestas; só um desvio mínimo para dentro da junta
        x += r.uniform(-0.012, 0.012); y += r.uniform(-0.012, 0.012)
        if not _livre(x, y): continue
        alvo = bm2 if r.random() < 0.3 else bm1
        _tufo(alvo, bm_m, x, y, r, escala=e * r.uniform(0.8, 1.5))
        cont += 1
    for b in (bm1, bm2, bm_m):
        bmesh.ops.recalc_face_normals(b, faces=b.faces)
    # montinhos usam o material escuro
    objs = [comum.novo_objeto("Musgo_laminas", bm1, [M["musgo"]]),
            comum.novo_objeto("Musgo_claro", bm2, [M["musgo2"]]),
            comum.novo_objeto("Musgo_montes", bm_m, [M["musgo"]])]
    return objs


# ---------------------------------------------------------------- raízes
def _tubo(bm, pts, raios, lados=4):
    aneis = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        u = t.cross(Vector((0, 0, 1)))
        if u.length < 1e-4: u = Vector((1, 0, 0))
        u.normalize(); w = t.cross(u).normalized()
        aneis.append([bm.verts.new(p + (u * math.cos(2 * math.pi * k / lados) + w * math.sin(2 * math.pi * k / lados)) * raios[i])
                      for k in range(lados)])
    for i in range(len(aneis) - 1):
        for k in range(lados):
            k2 = (k + 1) % lados
            bm.faces.new((aneis[i][k], aneis[i][k2], aneis[i + 1][k2], aneis[i + 1][k]))
    return


def _raizes(r, lajes, M):
    bm = bmesh.new(); feitas = 0
    cand = list(lajes); r.shuffle(cand)
    for l in cand:
        if feitas >= 9: break
        # raiz que corre ao longo de uma junta (borda horizontal ou vertical da lajota), com ondulação
        if r.random() < 0.5:
            y = l["y0"] if r.random() < 0.5 else l["y1"]; a = r.uniform(l["x0"], l["x1"] - 0.2); b = min(l["x1"], a + r.uniform(0.25, 0.7))
            ini, fim = Vector((a, y, 0.0)), Vector((b, y, 0.0))
        else:
            x = l["x0"] if r.random() < 0.5 else l["x1"]; a = r.uniform(l["y0"], l["y1"] - 0.2); b = min(l["y1"], a + r.uniform(0.25, 0.7))
            ini, fim = Vector((x, a, 0.0)), Vector((x, b, 0.0))
        if not (_livre(ini.x, ini.y) and _livre(fim.x, fim.y)): continue
        m = 9; lat = (fim - ini).cross(Vector((0, 0, 1))).normalized(); fase = r.uniform(0, 6.28)
        pts = []; rad = []
        for i in range(m + 1):
            t = i / m
            p = ini + (fim - ini) * t + lat * 0.012 * math.sin(fase + t * 9) + Vector((0, 0, 0.004 + 0.003 * math.sin(fase + t * 5)))
            pts.append(p); rad.append(0.0035 * (1.0 - 0.7 * t) + 0.0008)
        _tubo(bm, pts, rad)
        # ramificações finas
        for _ in range(r.randint(1, 3)):
            i = r.randint(2, m - 2); d = lat * r.choice([-1, 1]) + (fim - ini).normalized() * r.uniform(-0.3, 0.8)
            d.normalize(); q = [pts[i] + d * 0.04 * j + Vector((0, 0, 0.001 * j)) for j in range(5)]
            _tubo(bm, q, [0.0016 * (1 - j / 5) + 0.0004 for j in range(5)], lados=3)
        feitas += 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return [comum.novo_objeto("Raizes", bm, [M["raiz"]])]


# ---------------------------------------------------------------- API
def construir():
    r = random.Random(SEED_P)
    M = _mats()
    lajes = comum.layout()
    # centros das poças: preferencialmente em cruzamentos de juntas (quinas de lajotas), longe da borda
    cantos = [(l["x1"] + comum.JUNTA / 2, l["y1"] + comum.JUNTA / 2) for l in lajes]
    cantos = [c for c in cantos if 1.3 <= c[0] <= 6.7 and 1.3 <= c[1] <= 6.7]
    r.shuffle(cantos)
    alvo = [(1.0, 1.0)]  # raios nominais
    raios = [0.95, 0.70, 0.55, 0.80, 0.50]
    escolhidos = []
    for c in cantos:
        rad = raios[len(escolhidos)]
        if all(math.hypot(c[0] - e[0], c[1] - e[1]) > 1.9 for e in escolhidos):
            escolhidos.append((c[0] + r.uniform(-0.15, 0.15), c[1] + r.uniform(-0.15, 0.15), rad))
        if len(escolhidos) == len(raios): break
    objs = []; pocas = []
    for i, (cx, cy, rad) in enumerate(escolhidos):
        o, f = _poca(i, cx, cy, rad, r, M)
        objs += o; pocas.append((cx, cy, f))
    objs += _musgo(r, lajes, pocas, M)
    objs += _raizes(r, lajes, M)
    return objs


# ---------------------------------------------------------------- prévia
def _lajotas_previa():
    """Só para a prévia: caixas simples (topo z=0) a partir do layout; NÃO faz parte de construir()."""
    r = random.Random(11)
    m = comum.material("M_Previa_Laje", (0.07, 0.09, 0.13), rough=0.7)
    for l in comum.layout():
        bm = bmesh.new()
        v = [bm.verts.new((x, y, z)) for z in (0.0, -comum.ESPESSURA) for (x, y) in ((l["x0"], l["y0"]), (l["x1"], l["y0"]), (l["x1"], l["y1"]), (l["x0"], l["y1"]))]
        for q in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            bm.faces.new([v[i] for i in q])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        for vv in bm.verts: vv.co.z += 0 if vv.co.z == 0 else 0
        o = comum.novo_objeto(f"laje{l['id']}", bm, [m])
    # base escura sob as juntas
    bm = bmesh.new(); z = -comum.ESPESSURA - 0.001
    vs = [bm.verts.new((x, y, z)) for (x, y) in ((-1, -1), (9, -1), (9, 9), (-1, 9))]
    bm.faces.new(vs); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    comum.novo_objeto("fundo", bm, [comum.material("M_Previa_Fundo", (0.01, 0.01, 0.015), rough=1.0)])


def _tris(objs):
    return sum(len(o.data.polygons) if False else sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)


if __name__ == "__main__":
    comum.limpar_cena()
    objs = construir()
    print("TRIANGULOS", _tris(objs), {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs})
    _lajotas_previa()
    saida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "previas", "piso")
    saida = os.path.normpath(saida)
    p0 = objs[0].location
    # centro da primeira poça para close
    ce = None
    for o in objs:
        if o.name == "Poca_0":
            vs = [v.co for v in o.data.vertices]; ce = sum(vs, Vector()) / len(vs)
    ce = ce or Vector((4, 4, 0))
    def _lp():
        for o in [o for o in bpy.data.objects if o.name.startswith(("lua", "tocha", "cam"))]: bpy.data.objects.remove(o)
    comum.previa(os.path.join(saida, "pocas_3q.png"), olhar=(4, 4, 0), cam=(4 + 5.5, 4 - 7.5, 8.5), amostras=32)
    _lp()
    comum.previa(os.path.join(saida, "pocas_rasante.png"), olhar=(ce.x, ce.y, 0), cam=(ce.x + 1.2, ce.y - 2.6, 0.35), amostras=32, lente=35)
    _lp()
    comum.previa(os.path.join(saida, "pocas_close.png"), olhar=(ce.x, ce.y, 0), cam=(ce.x + 0.9, ce.y - 1.5, 1.1), amostras=48, lente=40)
