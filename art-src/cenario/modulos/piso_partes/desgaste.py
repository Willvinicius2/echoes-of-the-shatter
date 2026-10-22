"""Piso da Cripta - parte DESGASTE: rachaduras, lascas nas quinas, arranhoes, escombros e sujeira nas juntas.
Tudo fica sobre o topo das lajotas (z=0) com offset >= 1,5 mm em camadas (sem z-fighting).
Camadas (z): sujeira 1.6 mm, arranhao 2.0 mm, lasca-sombra 2.4 mm, lasca-miolo 2.9 mm, rachadura 3.5 mm.
Periodico em 8 m: sujeira e arranhoes sao recortados na borda e repetidos do outro lado; rachaduras ficam a > 0,3 m dela;
lascas ficam so em quinas internas; escombros a > 7 cm da borda."""
import os, sys, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from mathutils import Vector
import comum

Z_SUJEIRA, Z_ARRANHAO, Z_LASCA_S, Z_LASCA_M, Z_RACHA = 0.0016, 0.0020, 0.0024, 0.0029, 0.0035
T = comum.TILE
NOMES = dict(rachadura="M_Piso_Rachadura", lasca="M_Piso_Lasca", cascalho="M_Piso_Cascalho", sujeira="M_Piso_Sujeira")


def _mats():
    def get(nome, cor, rough):
        return bpy.data.materials.get(nome) or comum.material(nome, cor, rough)
    return dict(
        rachadura=get(NOMES["rachadura"], (0.010, 0.011, 0.016), 0.9),
        lasca=get(NOMES["lasca"], (0.155, 0.175, 0.235), 0.75),
        cascalho=get(NOMES["cascalho"], (0.115, 0.125, 0.165), 0.85),
        sujeira=get(NOMES["sujeira"], (0.030, 0.033, 0.040), 0.95),
    )


def _in_tile(p, lajes, folga=0.0):
    for l in lajes:
        if l["x0"] - folga <= p[0] <= l["x1"] + folga and l["y0"] - folga <= p[1] <= l["y1"] + folga:
            return l["id"]
    return None


def _tri_fan(bm, pts, z):
    """poligono (convexo ou quase) como leque a partir do centroide, com Z levemente variavel (z pode ser float)."""
    if len(pts) < 3: return
    cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
    c = bm.verts.new((cx, cy, z)); vs = [bm.verts.new((p[0], p[1], z)) for p in pts]
    for i in range(len(vs)):
        try: bm.faces.new((c, vs[i], vs[(i + 1) % len(vs)]))
        except ValueError: pass


def _fita(bm, pts, larg, z, alt=0.0015):
    """fita (polilinha com larguras) com topo em z+alt e paredes ate z; pts = [(x,y)], larg = [w]. Salta segmentos degenerados."""
    n = len(pts)
    if n < 2: return
    L, R = [], []
    for i in range(n):
        a = Vector(pts[max(i - 1, 0)]); b = Vector(pts[min(i + 1, n - 1)])
        d = (b - a)
        if d.length < 1e-6: d = Vector((1, 0))
        d.normalize(); nx, ny = -d.y, d.x
        w = larg[i] / 2
        L.append((pts[i][0] + nx * w, pts[i][1] + ny * w)); R.append((pts[i][0] - nx * w, pts[i][1] - ny * w))
    def v(p, zz): return bm.verts.new((p[0], p[1], zz))
    zt = z + alt
    Lt = [v(p, zt) for p in L]; Rt = [v(p, zt) for p in R]
    Lb = [v(p, z) for p in L]; Rb = [v(p, z) for p in R]
    for i in range(n - 1):
        for f in ((Lt[i], Lt[i + 1], Rt[i + 1], Rt[i]), (Lb[i], Lb[i + 1], Lt[i + 1], Lt[i]), (Rt[i], Rt[i + 1], Rb[i + 1], Rb[i])):
            try: bm.faces.new(f)
            except ValueError: pass
    for a, b, c, d in ((Lt[0], Rt[0], Rb[0], Lb[0]), (Lt[-1], Lb[-1], Rb[-1], Rt[-1])):
        try: bm.faces.new((a, b, c, d))
        except ValueError: pass


def _clip(pts):
    return [(min(max(x, 0.0), T), min(max(y, 0.0), T)) for x, y in pts]


def _wrapped(pts):
    """copias deslocadas por +-T que tocam o modulo, recortadas em [0,T]; garante emenda periodica."""
    out = []
    for ox in (-T, 0.0, T):
        for oy in (-T, 0.0, T):
            q = [(x + ox, y + oy) for x, y in pts]
            xs = [p[0] for p in q]; ys = [p[1] for p in q]
            if max(xs) < 0 or min(xs) > T or max(ys) < 0 or min(ys) > T: continue
            out.append(_clip(q))
    return out


# ---------------------------------------------------------------- rachaduras
def _caminho(r, p0, ang, comp, larg0, lajes, passo=(0.07, 0.17), margem=0.3):
    pts = [p0]; ws = [larg0]; a = ang; s = 0.0; p = p0
    while s < comp:
        d = r.uniform(*passo)
        a += r.gauss(0, 0.30)
        if r.random() < 0.12: a += r.choice([-1, 1]) * r.uniform(0.5, 0.9)   # quebra brusca de zigue-zague
        q = (p[0] + math.cos(a) * d, p[1] + math.sin(a) * d)
        if not (margem < q[0] < T - margem and margem < q[1] < T - margem): break
        p = q; s += d; pts.append(p)
        ws.append(max(0.004, larg0 * (1 - 0.8 * s / comp) * r.uniform(0.7, 1.15)))
    return pts, ws


def _rachaduras(bm, lajes, r):
    """3 rachaduras principais + ramais; devolve conjunto de ids de lajotas cruzadas."""
    cruzadas = set(); caminhos = []
    inicios = [((1.0, 2.0), 0.35, 4.8, 0.026), ((4.6, 0.9), 1.9, 4.2, 0.022), ((2.6, 6.9), -0.3, 4.6, 0.022), ((6.6, 4.3), 2.7, 3.2, 0.018)]
    for p0, ang, comp, w0 in inicios:
        pts, ws = _caminho(r, p0, ang, comp, w0, lajes)
        caminhos.append((pts, ws))
        for _ in range(r.randint(1, 3)):                                   # ramais
            k = r.randint(max(1, len(pts) // 5), len(pts) - 2) if len(pts) > 4 else 0
            if k <= 0: continue
            a = math.atan2(pts[k + 1][1] - pts[k][1], pts[k + 1][0] - pts[k][0]) + r.choice([-1, 1]) * r.uniform(0.45, 0.95)
            bp, bw = _caminho(r, pts[k], a, r.uniform(0.7, 1.8), ws[k] * 0.7, lajes)
            if len(bp) > 2: caminhos.append((bp, bw))
    for pts, ws in caminhos:
        # subdivide e quebra a fita nas juntas (a rachadura nao flutua sobre a junta)
        fin, wfin = [], []
        for i in range(len(pts) - 1):
            a, b = Vector(pts[i]), Vector(pts[i + 1]); n = max(1, int((b - a).length / 0.035))
            for k in range(n):
                t = k / n; q = a.lerp(b, t); fin.append((q.x, q.y)); wfin.append(ws[i] + (ws[i + 1] - ws[i]) * t)
        fin.append(pts[-1]); wfin.append(ws[-1])
        run, rw = [], []
        for q, w in zip(fin, wfin):
            idt = _in_tile(q, lajes, folga=-0.004)
            if idt is not None:
                run.append(q); rw.append(w); cruzadas.add(idt)
            else:
                if len(run) > 2: _fita(bm, run, rw, 0.0 + Z_RACHA - 0.0015)
                run, rw = [], []
        if len(run) > 2: _fita(bm, run, rw, Z_RACHA - 0.0015)
    return cruzadas


# ---------------------------------------------------------------- lascas
def _lascas(bm_sombra, bm_miolo, lajes, r):
    n = 0
    for l in lajes:
        cantos = [(l["x0"], l["y0"], 1, 1), (l["x1"], l["y0"], -1, 1), (l["x1"], l["y1"], -1, -1), (l["x0"], l["y1"], 1, -1)]
        for cx, cy, sx, sy in cantos:
            if min(cx, T - cx) < 0.04 or min(cy, T - cy) < 0.04: continue     # canto na borda do modulo: a lajota continua do outro lado
            if r.random() > 0.55: continue
            a = r.uniform(0.04, 0.13) * (1.5 if r.random() < 0.15 else 1.0)    # penetracao na lajota ao longo de x
            b = r.uniform(0.04, 0.13) * (1.5 if r.random() < 0.15 else 1.0)
            a = min(a, (l["x1"] - l["x0"]) * 0.3); b = min(b, (l["y1"] - l["y0"]) * 0.3)
            # contorno irregular: canto -> ao longo de x (com dentes) -> ponto interior irregular -> ao longo de y
            u = lambda t, w: t + r.uniform(-w, w)
            pts = [(0, 0), (a * 0.5, -0.0), (a * u(0.8, 0.1), b * r.uniform(0.15, 0.4)), (a * r.uniform(0.9, 1.0), b * r.uniform(0.3, 0.5)),
                   (a * r.uniform(0.5, 0.75), b * r.uniform(0.55, 0.85)), (a * r.uniform(0.2, 0.4), b * r.uniform(0.7, 1.0)), (0, b * r.uniform(0.9, 1.0)), (0, b * 0.5)]
            pts = [(cx + sx * px, cy + sy * py) for px, py in pts]
            # fatia sombra (escura) e miolo claro encolhido para o canto externo, deixando borda escura na quebra
            _tri_fan(bm_sombra, pts, Z_LASCA_S)
            c0 = Vector((cx + sx * a * 0.25, cy + sy * b * 0.25))
            mio = [tuple(c0 + (Vector(p) - Vector((cx, cy))) * 0.0 + (Vector(p) - c0) * 0.62) for p in pts]
            mio = [(p[0], p[1]) for p in mio]
            _tri_fan(bm_miolo, [(p[0] - sx * 0.0, p[1]) for p in mio], Z_LASCA_M)
            n += 1
    return n


# ---------------------------------------------------------------- arranhoes
def _arranhoes(bm, lajes, r, n=46):
    for _ in range(n):
        l = r.choice(lajes)
        x = r.uniform(l["x0"] + 0.1, l["x1"] - 0.1); y = r.uniform(l["y0"] + 0.1, l["y1"] - 0.1)
        ang = r.uniform(0, math.pi); comp = r.uniform(0.15, 0.55)
        for k in range(r.randint(2, 4)):                                    # feixe de riscos quase paralelos (passos / arrasto)
            off = r.uniform(-0.03, 0.03) * k
            ox, oy = -math.sin(ang) * off, math.cos(ang) * off
            a = ang + r.uniform(-0.08, 0.08); c = comp * r.uniform(0.5, 1.0)
            pts = []; m = 7
            for i in range(m + 1):
                t = i / m - 0.5
                pts.append((x + ox + math.cos(a) * c * t + r.gauss(0, 0.002), y + oy + math.sin(a) * c * t + r.gauss(0, 0.002)))
            pts2 = []; ws = []
            for i, p in enumerate(pts):
                q = _in_tile(p, lajes, folga=-0.008)
                if q is None: continue
                pts2.append(p); ws.append(0.0035 * math.sin(math.pi * (i + 0.5) / (m + 1)) + 0.0012)
            if len(pts2) > 2:
                for w in _wrapped_polilinha(pts2, ws): _fita(bm, w[0], w[1], Z_ARRANHAO - 0.0008, alt=0.0008)


def _wrapped_polilinha(pts, ws):
    out = []
    for ox in (-T, 0.0, T):
        for oy in (-T, 0.0, T):
            q = [(x + ox, y + oy) for x, y in pts]
            if all(0 <= x <= T and 0 <= y <= T for x, y in q): out.append((q, ws))
            elif any(0 <= x <= T and 0 <= y <= T for x, y in q):
                q2 = [(a, w) for a, w in zip(q, ws) if 0 <= a[0] <= T and 0 <= a[1] <= T]
                if len(q2) > 2: out.append(([a for a, _ in q2], [w for _, w in q2]))
    return out


# ---------------------------------------------------------------- sujeira
def _tira(bm, pts, larg, z):
    """tira plana irregular (quads entre bordas esquerda/direita com larguras individuais)."""
    n = len(pts); L, R = [], []
    for i in range(n):
        a = Vector(pts[max(i - 1, 0)]); b = Vector(pts[min(i + 1, n - 1)]); d = (b - a).normalized(); w = larg[i]
        L.append(bm.verts.new((pts[i][0] - d.y * w[0], pts[i][1] + d.x * w[0], z))); R.append(bm.verts.new((pts[i][0] + d.y * w[1], pts[i][1] - d.x * w[1], z)))
    for i in range(n - 1):
        try: bm.faces.new((L[i], L[i + 1], R[i + 1], R[i]))
        except ValueError: pass


def _sujeira(bm, lajes, r, n=150):
    """manchas escuras rasas e geometricas (tiras facetadas, afinando nas pontas) ao longo de juntas reais."""
    J = comum.JUNTA
    for _ in range(n):
        l = r.choice(lajes)
        if r.random() < 0.5:                                  # junta direita da lajota (vertical)
            ax, ay = l["x1"] + J / 2, r.uniform(l["y0"], l["y1"]); d = (0.0, 1.0)
        else:                                                 # junta de cima (horizontal)
            ax, ay = r.uniform(l["x0"], l["x1"]), l["y1"] + J / 2; d = (1.0, 0.0)
        comp = r.uniform(0.12, 0.55); m = max(3, int(comp / 0.06))
        pts = []; ws = []
        for i in range(m + 1):
            t = i / m - 0.5; env = math.sin(math.pi * (i + 0.35) / (m + 0.7))
            lat = r.gauss(0, 0.004)
            pts.append((ax + d[0] * comp * t - d[1] * lat, ay + d[1] * comp * t + d[0] * lat))
            ws.append((J / 2 + env * r.uniform(0.004, 0.032), J / 2 + env * r.uniform(0.004, 0.032)))
        for q in _wrapped_polilinha_w(pts, ws): _tira(bm, q[0], q[1], Z_SUJEIRA)


def _wrapped_polilinha_w(pts, ws):
    out = []
    for ox in (-T, 0.0, T):
        for oy in (-T, 0.0, T):
            q = [(x + ox, y + oy) for x, y in pts]
            if all(-0.05 <= x <= T + 0.05 and -0.05 <= y <= T + 0.05 for x, y in q):
                if all(0 <= x <= T and 0 <= y <= T for x, y in q): out.append((q, ws))
                continue
            if any(0 <= x <= T and 0 <= y <= T for x, y in q) or any(-0.1 < x < T + 0.1 and -0.1 < y < T + 0.1 for x, y in q):
                q2 = [(_clamp(a), w) for a, w in zip(q, ws)]
                if len(q2) > 2: out.append(([a for a, _ in q2], [w for _, w in q2]))
    return out


def _clamp(p): return (min(max(p[0], 0.0), T), min(max(p[1], 0.0), T))


# ---------------------------------------------------------------- escombros
def _pedra(bm, r, x, y, z0, tam, sink=0.0):
    """fragmento de pedra facetado: icosfera de 20 faces achatada/girada com vertices deslocados; apoiada em z0."""
    g = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.5)
    vs = g["verts"]
    sx, sy, sz = tam * r.uniform(0.7, 1.3), tam * r.uniform(0.6, 1.2), tam * r.uniform(0.35, 0.8)
    rot = r.uniform(0, math.pi)
    c, s = math.cos(rot), math.sin(rot)
    for v in vs:
        k = r.uniform(0.75, 1.15)
        px, py, pz = v.co.x * sx * k, v.co.y * sy * k, v.co.z * sz * k
        if pz < 0: pz *= 0.35                                  # base mais chata (assenta no piso)
        v.co = Vector((x + px * c - py * s, y + px * s + py * c, z0 + sz * 0.3 + pz - sink))


def _escombros(bm, lajes, lascas_pos, r):
    ys = sorted({round(l["y1"] + comum.JUNTA / 2, 4) for l in lajes}); xs = sorted({round(l["x1"] + comum.JUNTA / 2, 4) for l in lajes})
    cont = 0
    def ok(x, y): return 0.07 < x < T - 0.07 and 0.07 < y < T - 0.07
    for _ in range(170):                                       # nas juntas
        if r.random() < 0.5: x = r.uniform(0.1, T - 0.1); y = r.choice(ys) + r.uniform(-0.012, 0.012)
        else: x = r.choice(xs) + r.uniform(-0.012, 0.012); y = r.uniform(0.1, T - 0.1)
        if not ok(x, y): continue
        t = r.choice([0.012, 0.015, 0.02, 0.025, 0.03, 0.04, 0.06]) if r.random() < 0.8 else r.uniform(0.05, 0.07)
        _pedra(bm, r, x, y, 0.0, t, sink=t * 0.18); cont += 1
    for (cx, cy, sx, sy) in lascas_pos:                        # em volta das lascas
        for _ in range(r.randint(3, 7)):
            d = r.uniform(0.02, 0.2); a = r.uniform(0, 2 * math.pi)
            x = cx + sx * abs(math.cos(a)) * d + r.uniform(-0.02, 0.02); y = cy + sy * abs(math.sin(a)) * d + r.uniform(-0.02, 0.02)
            if not ok(x, y): continue
            _pedra(bm, r, x, y, 0.0, r.choice([0.01, 0.014, 0.02, 0.028, 0.035, 0.05]), sink=0.002); cont += 1
    for _ in range(30):                                        # alguns pedregulhos soltos no meio de lajotas
        l = r.choice(lajes); x = r.uniform(l["x0"] + 0.08, l["x1"] - 0.08); y = r.uniform(l["y0"] + 0.08, l["y1"] - 0.08)
        if ok(x, y): _pedra(bm, r, x, y, 0.0, r.uniform(0.015, 0.045), sink=0.002); cont += 1
    return cont


def construir():
    r = random.Random(1744 + 17)
    lajes = comum.layout()
    m = _mats()
    bm_rac, bm_ls, bm_lm, bm_arr, bm_casc, bm_suj = [bmesh.new() for _ in range(6)]

    cruzadas = _rachaduras(bm_rac, lajes, r)
    nl = _lascas(bm_ls, bm_lm, lajes, r)
    _arranhoes(bm_arr, lajes, r)
    _sujeira(bm_suj, lajes, r)
    # posicoes de lascas para espalhar cascalho (recalcula de forma deterministica a partir do layout, sem consumir r)
    rp = random.Random(99)
    lpos = []
    for l in lajes:
        for cx, cy, sx, sy in [(l["x0"], l["y0"], 1, 1), (l["x1"], l["y0"], -1, 1), (l["x1"], l["y1"], -1, -1), (l["x0"], l["y1"], 1, -1)]:
            if min(cx, T - cx) < 0.04 or min(cy, T - cy) < 0.04: continue
            if rp.random() < 0.4: lpos.append((cx, cy, sx, sy))
    nc = _escombros(bm_casc, lajes, lpos, r)

    objs = []
    for nome, bm, mat in (("Desgaste_Sujeira", bm_suj, "sujeira"), ("Desgaste_Arranhoes", bm_arr, "lasca"), ("Desgaste_LascaSombra", bm_ls, "rachadura"),
                          ("Desgaste_LascaMiolo", bm_lm, "lasca"), ("Desgaste_Rachaduras", bm_rac, "rachadura"), ("Desgaste_Cascalho", bm_casc, "cascalho")):
        if nome in ("Desgaste_Sujeira", "Desgaste_LascaSombra", "Desgaste_LascaMiolo"):   # folhas planas: normal sempre +Z
            for f in bm.faces:
                f.normal_update()
                if f.normal.z < 0: f.normal_flip()
        else:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        objs.append(comum.novo_objeto(nome, bm, [m[mat]]))
    construir.info = dict(lajotas_com_rachadura=len(cruzadas), lascas=nl, escombros=nc)
    return objs


def _lajotas_previa(lajes):
    r = random.Random(5)
    for l in lajes:
        bm = bmesh.new()
        w, h = l["x1"] - l["x0"], l["y1"] - l["y0"]
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co = Vector((l["x0"] + (v.co.x + 0.5) * w, l["y0"] + (v.co.y + 0.5) * h, (v.co.z - 0.5) * comum.ESPESSURA))
        t = r.uniform(0.7, 1.3)
        mt = comum.material("M_Previa_Lajota", (0.055 * t, 0.075 * t, 0.115 * t), 0.7)
        mt.name = "tmp"; me = bpy.data.meshes.new("l"); bm.to_mesh(me); bm.free(); me.materials.append(mt)
        o = bpy.data.objects.new("lajota_prev", me); bpy.context.collection.objects.link(o)


if __name__ == "__main__":
    comum.limpar_cena()
    _lajotas_previa(comum.layout())
    objs = construir()
    tris = sum(len(o.data.polygons) if all(len(p.vertices) == 3 for p in o.data.polygons) else sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)
    print("TRIANGULOS", tris, construir.info)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "previas", "piso")
    out = os.path.normpath(out)
    comum.previa(os.path.join(out, "desgaste_3q.png"), olhar=(4, 4, 0), cam=(9.5, -3.5, 8.5), res=(1100, 720), amostras=48)
    # remove luzes/camera para as proximas
    for o in [o for o in bpy.data.objects if o.type in ("LIGHT", "CAMERA")]: bpy.data.objects.remove(o)
    comum.previa(os.path.join(out, "desgaste_rasante.png"), olhar=(3.0, 3.5, 0), cam=(6.2, 0.5, 0.9), res=(1100, 640), amostras=48, lente=40)
    for o in [o for o in bpy.data.objects if o.type in ("LIGHT", "CAMERA")]: bpy.data.objects.remove(o)
    comum.previa(os.path.join(out, "desgaste_close.png"), olhar=(2.2, 2.6, 0), cam=(3.4, 1.0, 2.0), res=(1100, 700), amostras=64, lente=40)
