"""Piso da Cripta, parte POCAS E MUSGO: poças rasas com ondas, anéis de umidade em gradiente, pedrinhas,
manchas planas de musgo com tufos, umidade nas juntas e raízes finas.
Materiais: M_Piso_Agua, M_Piso_Umido, M_Piso_Musgo, M_Piso_Musgo_Claro, M_Piso_Pedra, M_Piso_Raiz.
Cor por vértice (atributo "Col"; alfa = gradiente da umidade/água) nos materiais com vértice-cor; base branca no glb.
Periodicidade de 8 m: nada fica a menos de 0,3 m da borda do módulo."""
import bpy, bmesh, math, os, random, sys
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum

SEED_P = 5207
BORDA = 0.30
Z_AGUA = 0.0026
Z_UMIDO = 0.0010


def _blend(m):
    for attr, val in (("blend_method", 'BLEND'), ("surface_render_method", 'BLENDED')):
        try: setattr(m, attr, val)
        except Exception: pass
    try: m.use_backface_culling = False
    except Exception: pass


def _mat_vc(nome, cor, rough, alpha=False, metal=0.0):
    """Material cujo Base Color (e, se alpha, o Alpha) vêm do atributo de cor por vértice 'Col'."""
    m = comum.material(nome, cor, rough=rough, metal=metal)
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    vc = nt.nodes.new("ShaderNodeVertexColor"); vc.layer_name = "Col"
    nt.links.new(vc.outputs["Color"], b.inputs["Base Color"])
    if alpha:
        nt.links.new(vc.outputs["Alpha"], b.inputs["Alpha"]); _blend(m)
    return m


def _mats():
    agua = _mat_vc("M_Piso_Agua", (0.04, 0.09, 0.15), rough=0.02, alpha=True)   # metallic 0, rough 0.02, alfa ~0.7 por vértice
    try: agua.node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0.9
    except Exception: pass
    return dict(
        agua=agua,
        umido=_mat_vc("M_Piso_Umido", (0.01, 0.014, 0.022), rough=0.12, alpha=True),
        musgo=_mat_vc("M_Piso_Musgo", (0.020, 0.030, 0.013), rough=0.95),
        musgo2=_mat_vc("M_Piso_Musgo_Claro", (0.046, 0.055, 0.020), rough=0.95),
        pedra=_mat_vc("M_Piso_Pedra", (0.085, 0.078, 0.066), rough=0.7),
        raiz=comum.material("M_Piso_Raiz", (0.060, 0.042, 0.032), rough=0.90),
    )


def _obj(nome, bm, vc, mat, suave=False):
    lay = bm.loops.layers.color.new("Col")
    for f in bm.faces:
        for l in f.loops:
            c = vc.get(l.vert, (1, 1, 1, 1))
            l[lay] = (min(1.0, c[0]) ** 0.4545, min(1.0, c[1]) ** 0.4545, min(1.0, c[2]) ** 0.4545, c[3])   # camada byte é sRGB
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = comum.novo_objeto(nome, bm, [mat])
    if suave:
        for p in o.data.polygons: p.use_smooth = True
    return o


def _sm(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)


def _mix(a, b, t): return tuple(a[i] + (b[i] - a[i]) * t for i in range(len(a)))


# ---------------------------------------------------------------- poças
def _blob(r, raio):
    """Contorno bem irregular: elipse alongada + harmônicos 2..9 + línguas (lóbulos) e reentrâncias gaussianas."""
    el = r.uniform(1.05, 1.4); rot = r.uniform(0, math.pi)
    har = [(k, r.uniform(0.08, 0.26) / max(k * 0.42, 1.0), r.uniform(0, 6.28)) for k in range(2, 10)]
    gau = [(r.uniform(0, 6.28), r.uniform(0.22, 0.45), r.uniform(0.25, 0.6)) for _ in range(r.randint(3, 4))]       # línguas
    gau += [(r.uniform(0, 6.28), r.uniform(0.15, 0.3), -r.uniform(0.2, 0.34)) for _ in range(r.randint(2, 3))]     # reentrâncias
    def f(t):
        a = t - rot
        e = 1.0 / math.sqrt((math.cos(a) / el) ** 2 + (math.sin(a) * el) ** 2 + 1e-9)
        k = 1.0 + sum(A * math.cos(n * t + p) for n, A, p in har)
        for (c, w, L) in gau:
            d = math.atan2(math.sin(t - c), math.cos(t - c)); k += L * math.exp(-(d / w) ** 2)
        return raio * min(e, 1.6) * max(k, 0.35) * 0.8
    return f


def _forma(r, raio):
    f = _blob(r, raio)
    h = [(k, r.uniform(0.05, 0.14), r.uniform(0, 6.28)) for k in (2, 3, 5, 6)]
    ex = r.uniform(1.15, 1.35)
    def f_halo(t): return f(t) * (ex + sum(A * math.cos(n_ * t + p) for n_, A, p in h))
    rmax = max(f_halo(2 * math.pi * i / 90) for i in range(90))
    return f, f_halo, rmax


def _dentro(f, cx, cy, x, y, k=0.88):
    dx, dy = x - cx, y - cy
    return math.hypot(dx, dy) < f(math.atan2(dy, dx)) * k


def _agua(idx, cx, cy, f, r, M):
    bm = bmesh.new(); vc = {}; n = 72; Z = Z_AGUA
    fundo = (0.018, 0.026, 0.036); raso = (0.045, 0.058, 0.070)
    def col(t): return (*_mix(fundo, raso, _sm(0.2, 1.0, t)), 0.72 * (1 - _sm(0.45, 1.0, t)) ** 1.1)
    c = bm.verts.new((cx, cy, Z)); vc[c] = col(0)
    aneis = []; J = 7
    for j in range(1, J + 1):
        t_ = j / J; v = []
        for k in range(n):
            t = 2 * math.pi * k / n
            vv = bm.verts.new((cx + f(t) * t_ * math.cos(t), cy + f(t) * t_ * math.sin(t), Z - 0.0003 * t_ ** 4))
            vc[vv] = col(t_); v.append(vv)
        aneis.append(v)
    for k in range(n): bm.faces.new((c, aneis[0][k], aneis[0][(k + 1) % n]))
    for j in range(J - 1):
        for k in range(n):
            k2 = (k + 1) % n; bm.faces.new((aneis[j][k], aneis[j + 1][k], aneis[j + 1][k2], aneis[j][k2]))
    return _obj(f"Poca_{idx}", bm, vc, M["agua"], suave=True)


def _faixa(bm, vc, cx, cy, f_in, f_out, z_in, z_out, n, passos, perfil, rgb, ruido=None):
    linhas = []
    for i in range(passos + 1):
        u = i / passos; v = []
        for k in range(n):
            t = 2 * math.pi * k / n; rr = f_in(t) + (f_out(t) - f_in(t)) * u
            z = z_in + (z_out - z_in) * u + (ruido.uniform(-0.0001, 0.0001) if ruido else 0)
            vv = bm.verts.new((cx + rr * math.cos(t), cy + rr * math.sin(t), z))
            vc[vv] = (*rgb, perfil(u) * (ruido.uniform(0.85, 1.0) if ruido else 1)); v.append(vv)
        linhas.append(v)
    for i in range(passos):
        for k in range(n):
            k2 = (k + 1) % n; bm.faces.new((linhas[i][k], linhas[i][k2], linhas[i + 1][k2], linhas[i + 1][k]))


def _umido(idx, cx, cy, f, f_halo, r, M):
    """Borda molhada escura fina + anel de umidade largo com alfa em gradiente suave (sem degrau)."""
    bm = bmesh.new(); vc = {}; n = 72
    _faixa(bm, vc, cx, cy, lambda t: f(t) * 0.99, f_halo, Z_AGUA - 0.0005, Z_UMIDO - 0.0002, n, 9,
           lambda u: 0.5 * (1 - u) ** 1.8, (0.008, 0.012, 0.02), ruido=r)
    return _obj(f"Umido_{idx}", bm, vc, M["umido"], suave=True)


def _umido_juntas(r, lajes, pocas, M):
    """Faixas escuras de umidade ao longo das juntas perto das poças (alfa cai nas pontas e para os lados)."""
    bm = bmesh.new(); vc = {}; j = comum.JUNTA / 2
    for l in lajes:
        for (xa, ya, xb, yb, nx, ny) in ((l["x0"], l["y0"], l["x1"], l["y0"], 0, -1), (l["x1"], l["y0"], l["x1"], l["y1"], 1, 0),
                                         (l["x1"], l["y1"], l["x0"], l["y1"], 0, 1), (l["x0"], l["y1"], l["x0"], l["y0"], -1, 0)):
            mx, my = (xa + xb) / 2, (ya + yb) / 2
            d = _dist_pocas(mx, my, pocas); p = 0.9 if d < 0.9 else (0.45 if d < 1.8 else 0.1)
            if r.random() > p: continue
            comp = math.hypot(xb - xa, yb - ya); t0 = r.uniform(0.0, 0.3); t1 = r.uniform(0.7, 1.0)
            m = max(4, int(comp * (t1 - t0) / 0.2)); larg = r.uniform(0.05, 0.11) * (1.3 if d < 0.9 else 1.0)
            rows = []
            for i in range(m + 1):
                u = i / m; t = t0 + (t1 - t0) * u
                x = xa + (xb - xa) * t + nx * j; y = ya + (yb - ya) * t + ny * j
                if not _livre(x, y, 0.35): rows = None; break
                w = larg * (0.7 + 0.5 * math.sin(i * 1.7 + t0 * 9)); a = 0.62 * math.sin(math.pi * u) ** 0.7
                z = 0.0006 + r.uniform(0, 0.0002)
                rows.append((x, y, z, w, a))
            if not rows: continue
            horiz = (ya == yb); lin = []
            for (x, y, z, w, a) in rows:
                if horiz: pts = ((x, y - w), (x, y), (x, y + w))
                else: pts = ((x - w, y), (x, y), (x + w, y))
                row = []
                for (px, py), al in zip(pts, (0.0, a, 0.0)):
                    vv = bm.verts.new((px, py, z)); vc[vv] = (0.008, 0.012, 0.02, al); row.append(vv)
                lin.append(row)
            for i in range(len(lin) - 1):
                for q in range(2): bm.faces.new((lin[i][q], lin[i][q + 1], lin[i + 1][q + 1], lin[i + 1][q]))
    return _obj("Umido_juntas", bm, vc, M["umido"], suave=True)


def _dist_pocas(x, y, pocas):
    return min((math.hypot(x - cx, y - cy) - f(math.atan2(y - cy, x - cx)) for (cx, cy, f) in pocas), default=9.0)


# ---------------------------------------------------------------- pedrinhas
def _pedra(bm, vc, x, y, rad, r, z0, tom):
    g = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    ach = r.uniform(0.35, 0.6); el = r.uniform(0.8, 1.3); rot = r.uniform(0, 3.14)
    for v in g["verts"]:
        s = r.uniform(0.75, 1.15); px, py, pz = v.co.x * s * el, v.co.y * s / el, v.co.z * s * ach
        v.co = Vector((x + (px * math.cos(rot) - py * math.sin(rot)) * rad, y + (px * math.sin(rot) + py * math.cos(rot)) * rad, z0 + pz * rad))
        v.co.z = max(v.co.z, z0 - 0.004)
        k = 0.8 + 0.4 * (pz > 0) * r.random()
        vc[v] = (tom[0] * k, tom[1] * k, tom[2] * k, 1.0)


def _pedrinhas(r, pocas, M):
    bm = bmesh.new(); vc = {}
    for (cx, cy, f) in pocas:
        for i in range(r.randint(13, 20)):
            if i < 4:    # dentro da água, quase submersas
                a = r.uniform(0, 6.28); d = r.uniform(0.15, 0.8) * f(a)
            else:        # na borda, dentro e fora
                a = r.uniform(0, 6.28); d = f(a) * r.uniform(0.84, 1.18)
            x, y = cx + d * math.cos(a), cy + d * math.sin(a)
            if not _livre(x, y): continue
            rad = r.choice([0.012, 0.018, 0.026, 0.035, 0.048, 0.065]) * r.uniform(0.85, 1.2)
            t = r.uniform(0.3, 0.75)
            _pedra(bm, vc, x, y, rad, r, 0.0016 if i < 4 else 0.0006, (0.085 * t, 0.078 * t, 0.066 * t))
    return _obj("Pedrinhas", bm, vc, M["pedra"])


# ---------------------------------------------------------------- musgo
TONS = [((0.040, 0.070, 0.026), 0.45), ((0.075, 0.100, 0.032), 0.35), ((0.028, 0.052, 0.030), 0.20)]   # verde-escuro, oliva, verde-musgo apagado


def _livre(x, y, margem=BORDA):
    return margem <= x <= comum.TILE - margem and margem <= y <= comum.TILE - margem


def _base(bm, vc, cx, cy, ra, r, tom):
    """Base minúscula e escura sob o tufo (só para não aparecer pedra nua entre as lâminas)."""
    n = 8; c = bm.verts.new((cx, cy, 0.0026)); vc[c] = (tom[0] * 0.7, tom[1] * 0.7, tom[2] * 0.7, 1.0); v = []
    for k in range(n):
        t = 2 * math.pi * k / n; rr = ra * r.uniform(0.7, 1.2)
        vv = bm.verts.new((cx + rr * math.cos(t), cy + rr * math.sin(t), 0.0008)); vc[vv] = (tom[0] * 0.45, tom[1] * 0.45, tom[2] * 0.45, 1.0); v.append(vv)
    for k in range(n): bm.faces.new((c, v[k], v[(k + 1) % n]))


def _lamina(bm, vc, px, py, h, b, ang, dir_, inc, tom, kk, z0=0.0012):
    """Lâmina fina curva: base triangular, anel intermediário e ponta inclinada (9 tris)."""
    bs = [bm.verts.new((px + b * math.cos(ang + 2.094 * k), py + b * math.sin(ang + 2.094 * k), z0)) for k in range(3)]
    mid = [bm.verts.new((px + b * 0.7 * math.cos(ang + 2.094 * k) + inc * 0.35 * math.cos(dir_), py + b * 0.7 * math.sin(ang + 2.094 * k) + inc * 0.35 * math.sin(dir_), z0 + h * 0.55)) for k in range(3)]
    tip = bm.verts.new((px + inc * math.cos(dir_), py + inc * math.sin(dir_), z0 + h))
    for v in bs: vc[v] = (tom[0] * kk * 0.6, tom[1] * kk * 0.6, tom[2] * kk * 0.6, 1.0)
    for v in mid: vc[v] = (tom[0] * kk * 1.2, tom[1] * kk * 1.2, tom[2] * kk * 1.1, 1.0)
    vc[tip] = (min(1, tom[0] * kk * 2.6 + 0.01), min(1, tom[1] * kk * 2.3 + 0.015), min(1, tom[2] * kk * 1.5), 1.0)
    for k in range(3):
        k2 = (k + 1) % 3; bm.faces.new((bs[k], bs[k2], mid[k2], mid[k])); bm.faces.new((mid[k], mid[k2], tip))


def _tufo_vol(bm, vc, x, y, rad, r, tom):
    """Aglomerado volumétrico: montículo irregular + 10-16 lâminas curvas radiais, mais altas no centro."""
    g = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    for v in g["verts"]:
        s_ = r.uniform(0.6, 1.1); v.co = Vector((x + v.co.x * rad * 0.8 * s_, y + v.co.y * rad * 0.8 * s_, max(v.co.z, -0.1) * rad * 0.45 * s_ + 0.0012))
        k = r.uniform(0.7, 1.4) * (1.0 if v.co.z > 0.0016 else 0.6); vc[v] = (tom[0] * k, tom[1] * k, tom[2] * k, 1.0)
    for _ in range(r.randint(7, 9)):
        a = r.uniform(0, 6.28); d = abs(r.gauss(0, rad * 0.55)); px, py = x + d * math.cos(a), y + d * math.sin(a)
        h = r.uniform(0.014, 0.038) * (1.25 - min(1.0, d / (rad * 1.4)) * 0.6) * (rad / 0.03) ** 0.5
        _lamina(bm, vc, px, py, h, r.uniform(0.0016, 0.0030), r.uniform(0, 6.28), a + r.uniform(-0.5, 0.5), r.uniform(0.15, 0.9) * h, tom, r.uniform(0.8, 1.35))


def _musgo(r, lajes, pocas, M):
    bm1 = bmesh.new(); bm2 = bmesh.new(); vc1 = {}; vc2 = {}
    cand = []     # (x, y, nº de tufos no aglomerado, espalhamento)
    for (cx, cy, f) in pocas:        # colado na margem molhada das poças
        for _ in range(r.randint(7, 10)):
            t = r.uniform(0, 6.28); rr = f(t) * r.uniform(1.0, 1.3)
            cand.append((cx + rr * math.cos(t), cy + rr * math.sin(t), r.randint(3, 6), 0.07))
    for l in lajes:                   # juntas e quinas: denso perto das poças, esparso longe
        for (xa, ya, xb, yb, nx, ny) in ((l["x0"], l["y0"], l["x1"], l["y0"], 0, -1), (l["x1"], l["y0"], l["x1"], l["y1"], 1, 0),
                                         (l["x1"], l["y1"], l["x0"], l["y1"], 0, 1), (l["x0"], l["y1"], l["x0"], l["y0"], -1, 0)):
            d = _dist_pocas((xa + xb) / 2, (ya + yb) / 2, pocas); p = 0.33 if d < 1.0 else (0.15 if d < 2.0 else 0.04)
            if r.random() > p: continue
            for _ in range(r.randint(1, 2)):
                t = r.uniform(0.05, 0.95)
                cand.append((xa + (xb - xa) * t + nx * comum.JUNTA / 2, ya + (yb - ya) * t + ny * comum.JUNTA / 2, r.randint(3, 5), 0.06))
        for (x, y) in ((l["x0"], l["y0"]), (l["x1"], l["y0"]), (l["x1"], l["y1"]), (l["x0"], l["y1"])):
            if r.random() < 0.2: cand.append((x, y, r.randint(3, 4), 0.05))
    for (x, y, nt, esp) in cand:
        if not _livre(x, y, 0.4) or _dist_pocas(x, y, pocas) < 0.02: continue
        sorte = r.random(); acc = 0
        for tom, pr in TONS:
            acc += pr
            if sorte <= acc: break
        if r.random() < 0.35: _base(bm1, vc1, x, y, r.uniform(0.02, 0.035), r, tom)
        for _ in range(nt):
            a = r.uniform(0, 6.28); d = r.uniform(0, esp)
            t2 = tom if r.random() < 0.6 else TONS[r.randrange(3)][0]
            _tufo_vol(bm2, vc2, x + d * math.cos(a), y + d * math.sin(a), r.uniform(0.022, 0.05), r, t2)
    return [_obj("Musgo_base", bm1, vc1, M["musgo"]), _obj("Musgo_tufos", bm2, vc2, M["musgo2"], suave=True)]


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
    cantos = [(l["x1"] + comum.JUNTA / 2, l["y1"] + comum.JUNTA / 2) for l in lajes]
    cantos = [c for c in cantos if 0.6 <= c[0] <= 7.4 and 0.6 <= c[1] <= 7.4]
    r.shuffle(cantos)
    raios = [0.95, 0.70, 0.55, 0.80, 0.50]
    escolhidos = []
    for c in cantos:
        if len(escolhidos) == len(raios): break
        rad = raios[len(escolhidos)]
        cx = c[0] + r.uniform(-0.15, 0.15); cy = c[1] + r.uniform(-0.15, 0.15)
        if not all(math.hypot(cx - e[0], cy - e[1]) > 1.9 for e in escolhidos): continue
        est = r.getstate(); f, fh, rmax = _forma(r, rad)
        if not (BORDA + 0.05 <= cx - rmax and cx + rmax <= comum.TILE - BORDA - 0.05 and BORDA + 0.05 <= cy - rmax and cy + rmax <= comum.TILE - BORDA - 0.05):
            r.setstate(est); continue
        escolhidos.append((cx, cy, rad, f, fh))
    objs = []; pocas = []
    for i, (cx, cy, rad, f, fh) in enumerate(escolhidos):
        objs += [_agua(i, cx, cy, f, r, M), _umido(i, cx, cy, f, fh, r, M)]
        pocas.append((cx, cy, f))
    objs.append(_umido_juntas(r, lajes, pocas, M))
    objs.append(_pedrinhas(r, pocas, M))
    objs += _musgo(r, lajes, pocas, M)
    objs += _raizes(r, lajes, M)
    return objs


# ---------------------------------------------------------------- prévia
def _lajotas_previa():
    """Só para a prévia: caixas simples (topo z=0) a partir do layout; NÃO faz parte de construir()."""
    r = random.Random(11)
    m = comum.material("M_Previa_Laje", (0.055, 0.050, 0.044), rough=0.7)
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
    return sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)


def _previa(png, olhar, cam, res=(960, 640), amostras=32, lente=35):
    """Igual a comum.previa, mas com céu em gradiente no world (SÓ prévia) para o reflexo da água aparecer."""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = amostras; sc.cycles.use_denoising = True
    try: sc.cycles.device = 'CPU'
    except Exception: pass
    sc.render.resolution_x, sc.render.resolution_y = res
    w = bpy.data.worlds.new("ceu"); w.use_nodes = True; nt = w.node_tree; bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); rp = nt.nodes.new("ShaderNodeValToRGB")
    ns = nt.nodes.new("ShaderNodeTexNoise"); ns.inputs["Scale"].default_value = 2.2; ns.inputs["Detail"].default_value = 4
    mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs[0].default_value = 0.3
    nt.links.new(tc.outputs["Generated"], sep.inputs[0]); nt.links.new(sep.outputs["Z"], rp.inputs[0])
    nt.links.new(tc.outputs["Generated"], ns.inputs["Vector"])
    el = rp.color_ramp.elements; el[0].position = 0.35; el[0].color = (0.02, 0.03, 0.06, 1); el[1].position = 1.0; el[1].color = (0.55, 0.7, 1.0, 1)
    e2 = el.new(0.6); e2.color = (0.22, 0.32, 0.52, 1)
    nt.links.new(rp.outputs["Color"], mul.inputs[6]); nt.links.new(ns.outputs["Color"], mul.inputs[7])
    nt.links.new(mul.outputs[2], bg.inputs[0]); bg.inputs[1].default_value = 1.1
    sc.world = w
    sol = bpy.data.objects.new("lua", bpy.data.lights.new("lua", 'SUN')); sol.data.energy = 1.6; sol.data.color = (0.6, 0.7, 1.0)
    sol.rotation_euler = (math.radians(55), 0, math.radians(35)); bpy.context.collection.objects.link(sol)
    t = bpy.data.objects.new("tocha", bpy.data.lights.new("tocha", 'POINT')); t.data.energy = 350; t.data.color = (1.0, 0.6, 0.25); t.data.shadow_soft_size = 0.3
    t.location = (olhar[0] - 1.5, olhar[1] + 1.0, 1.1); bpy.context.collection.objects.link(t)
    c = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); c.data.lens = lente; bpy.context.collection.objects.link(c); sc.camera = c
    c.location = cam; c.rotation_euler = (Vector(olhar) - c.location).to_track_quat('-Z', 'Y').to_euler()
    os.makedirs(os.path.dirname(png), exist_ok=True); sc.render.filepath = png; bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    comum.limpar_cena()
    objs = construir()
    print("TRIANGULOS", _tris(objs), {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs})
    xs = [v.co.x for o in objs for v in o.data.vertices]; ys = [v.co.y for o in objs for v in o.data.vertices]
    print("EXTENSAO x", round(min(xs), 3), round(max(xs), 3), "y", round(min(ys), 3), round(max(ys), 3))
    _lajotas_previa()
    saida = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "previas", "piso"))
    vs = [v.co for o in objs if o.name == "Poca_0" for v in o.data.vertices]
    ce = sum(vs, Vector()) / len(vs) if vs else Vector((4, 4, 0))
    def _lp():
        for o in [o for o in bpy.data.objects if o.name.startswith(("lua", "tocha", "cam"))]: bpy.data.objects.remove(o)
    qual = sys.argv[1:] or ["3q", "rasante", "close"]
    if "3q" in qual: _previa(os.path.join(saida, "pocas_3q.png"), (4, 4, 0), (9.5, -3.5, 8.5)); _lp()
    if "rasante" in qual: _previa(os.path.join(saida, "pocas_rasante.png"), (ce.x, ce.y, 0), (ce.x + 1.2, ce.y - 2.6, 0.35), lente=35); _lp()
    if "close" in qual: _previa(os.path.join(saida, "pocas_close.png"), (ce.x, ce.y, 0), (ce.x + 0.9, ce.y - 1.5, 1.1), amostras=48, lente=40); _lp()
