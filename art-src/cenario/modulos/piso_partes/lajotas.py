"""Piso da Cripta, parte LAJOTAS E JUNTAS.
Cada lajota do comum.layout() vira uma malha real: topo ondulado com altura propria, chanfro irregular e desigual
por aresta (largura e profundidade variam ao longo da aresta), lascas/dentes, cantos arredondados e gastos, laterais
verticais ruidosas. A junta e uma placa de argamassa/terra afundada ~3 cm, com ruido de altura periodico (emenda sem costura).
Materiais: M_Piso_Laje_A..D (azul-ardosia escuro) + M_Piso_Junta. Determinístico (seed fixo)."""
import bpy, bmesh, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum
from comum import TILE

SEED = 20261022
PROF_JUNTA = 0.045         # topo da junta abaixo do topo das lajotas
CORES = {                  # azul-ardosia escuro, linear sRGB; tons diferentes por lajota
    "A": (0.052, 0.068, 0.100),
    "B": (0.040, 0.054, 0.082),
    "C": (0.068, 0.082, 0.115),
    "D": (0.058, 0.066, 0.084),
}
COR_JUNTA = (0.011, 0.010, 0.010)

# ---------------------------------------------------------------- utilidades de ruido
class Onda:
    """Ruido suave 1D/2D como soma de senos com fases aleatorias (barato e deterministico)."""
    def __init__(self, r, n=4, f0=1.0, f1=9.0):
        self.t = [(r.uniform(f0, f1), r.uniform(0, 6.283), r.uniform(0.4, 1.0), r.uniform(0, 6.283), r.uniform(-1, 1)) for _ in range(n)]
        self.norm = sum(a for _, _, a, _, _ in self.t)
    def v1(self, t):
        return sum(a * math.sin(f * t + p) for f, p, a, _, _ in self.t) / self.norm
    def v2(self, x, y):
        return sum(a * math.sin(f * (x * math.cos(q) + y * math.sin(q)) + p) for f, p, a, q, _ in self.t) / self.norm

def smooth(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

def linhas(L, r):
    """Coordenadas das linhas da grade em [0,L]: densas perto das arestas (onde esta o chanfro), grossas no miolo."""
    borda = [0.0, 0.010, 0.024, 0.044, 0.070, 0.105, 0.150]
    n = max(2, round((L - 2 * 0.150) / 0.20))
    miolo = [0.150 + (L - 0.300) * k / n for k in range(1, n)]
    return borda + miolo + [L - b for b in reversed(borda)]

# ---------------------------------------------------------------- uma lajota
def linhas(L):
    """Grade fina (3-4 cm) para resolver as facetas das lascas; depois os planos coplanares sao dissolvidos."""
    borda = [0.0, 0.010, 0.020]
    n = max(2, round((L - 0.040) / 0.022))
    return borda + [0.020 + (L - 0.040) * k / n for k in range(1, n)] + [L - b for b in reversed(borda)]

def lascas(r, W, H):
    """Quinas quebradas e dentes: cunhas angulosas (plano inclinado + abertura em V). (px,py,nx,ny,tamanho,profundidade,kl)"""
    out = []
    cantos = [(0, 0, 1, 1), (W, 0, -1, 1), (W, H, -1, -1), (0, H, 1, -1)]
    r.shuffle(cantos)
    for px, py, sx, sy in cantos[:r.choice([1, 2, 2, 3, 3])]:
        ang = math.atan2(sy, sx) + r.uniform(-0.35, 0.35)
        out.append((px, py, math.cos(ang), math.sin(ang), r.uniform(0.22, 0.55), r.uniform(0.05, 0.10), r.uniform(0.7, 1.3)))
    def na_borda(medio):
        lado = r.choice("lrbt")
        if lado in "lr":
            py = r.uniform(0.04, H - 0.04); px = 0 if lado == "l" else W; nx0, ny0 = (1, 0) if lado == "l" else (-1, 0)
        else:
            px = r.uniform(0.04, W - 0.04); py = 0 if lado == "b" else H; nx0, ny0 = (0, 1) if lado == "b" else (0, -1)
        ang = math.atan2(ny0, nx0) + r.uniform(-0.5, 0.5)
        if medio: return (px, py, math.cos(ang), math.sin(ang), r.uniform(0.20, 0.40), r.uniform(0.04, 0.08), r.uniform(0.9, 1.6))
        return (px, py, math.cos(ang), math.sin(ang), r.uniform(0.03, 0.08), r.uniform(0.012, 0.03), r.uniform(1.0, 1.8))
    for _ in range(r.choice([1, 2, 2, 3])): out.append(na_borda(True))
    for _ in range(r.randint(5, 9)): out.append(na_borda(False))
    return out

def lajota(bm, l, r):
    W = l["x1"] - l["x0"]; H = l["y1"] - l["y0"]
    xs = linhas(W); ys = linhas(H)
    h0 = -r.uniform(0.0, 0.014)                        # micro-desnivel entre lajotas
    if r.random() < 0.28: tx, ty = r.uniform(-0.009, 0.009) / W, r.uniform(-0.009, 0.009) / H   # algumas levemente inclinadas
    else: tx = ty = 0.0
    cw = {k: r.choice((0.010, 0.020)) for k in "lrbt"}  # chanfro pequeno e nitido, 1-2 cm
    ch = lascas(r, W, H)
    nx, ny = len(xs), len(ys)
    V = [[None] * ny for _ in range(nx)]
    for i, u in enumerate(xs):
        for j, v in enumerate(ys):
            z = h0 + tx * (u - W / 2) + ty * (v - H / 2)
            for k, d in (("l", u), ("r", W - u), ("b", v), ("t", H - v)):
                if d < cw[k]: z -= (cw[k] - d) * 0.9
            for px, py, nxx, nyy, s, dep, kl in ch:
                dx, dy = u - px, v - py
                t = dx * nxx + dy * nyy; lat = abs(-dx * nyy + dy * nxx)
                zc = h0 - dep + (max(t, 0.0) + kl * lat) * dep / s * 1.1
                if zc < z: z = zc
            V[i][j] = bm.verts.new((l["x0"] + u, l["y0"] + v, z))
    faces = [bm.faces.new((V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1])) for i in range(nx - 1) for j in range(ny - 1)]
    bm.normal_update()
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.2), verts=[v for row in V for v in row], edges=list({e for f in faces if f.is_valid for e in f.edges}), use_dissolve_boundaries=False, delimit=set())
    loop = [V[i][0] for i in range(nx)] + [V[nx - 1][j] for j in range(1, ny)] + \
           [V[i][ny - 1] for i in range(nx - 2, -1, -1)] + [V[0][j] for j in range(ny - 2, 0, -1)]
    loop = [v for v in loop if v.is_valid]
    n = len(loop)
    cx = l["x0"] + W / 2; cy = l["y0"] + H / 2
    zb = -0.075
    aneis = [loop]
    for frac, amp in ((0.0, 0.0),):
        pass
    for z_alvo, amp in ((-0.022, 0.0015), (zb, 0.0)):
        aneis.append([bm.verts.new((v.co.x + r.uniform(-amp, amp), v.co.y + r.uniform(-amp, amp), z_alvo)) for v in loop])
    for a in range(2):
        for k in range(n):
            k2 = (k + 1) % n
            try: bm.faces.new((aneis[a][k], aneis[a][k2], aneis[a + 1][k2], aneis[a + 1][k]))
            except ValueError: pass
    try: bm.faces.new(list(reversed(aneis[2])))
    except ValueError: pass

# ---------------------------------------------------------------- junta
def junta(bm):
    r = random.Random(SEED + 99)
    # ondas com numero de ciclos inteiro em TILE => periodico
    ondas = [(r.randint(2, 9), r.randint(2, 9), r.uniform(0, 6.28), r.uniform(0.4, 1)) for _ in range(6)]
    fino = [(r.randint(14, 30), r.randint(14, 30), r.uniform(0, 6.28), r.uniform(0.4, 1)) for _ in range(5)]
    def z(x, y):
        s = sum(a * math.sin(2 * math.pi * (i * x + j * y) / TILE + p) for i, j, p, a in ondas) / 3.2
        t = sum(a * math.sin(2 * math.pi * (i * x + j * y) / TILE + p) for i, j, p, a in fino) / 3.0
        return -PROF_JUNTA + 0.003 * s + 0.002 * t
    n = 64
    V = {}
    for i in range(n):
        for j in range(n):
            V[(i, j)] = bm.verts.new((TILE * i / n, TILE * j / n, z(TILE * i / n, TILE * j / n)))
    # a ultima linha/coluna repete a primeira: valores identicos por periodicidade
    for i in range(n): V[(i, n)] = bm.verts.new((TILE * i / n, TILE, z(TILE * i / n, TILE)))
    for j in range(n + 1): V[(n, j)] = bm.verts.new((TILE, TILE * j / n, z(TILE, TILE * j / n)))
    for i in range(n):
        for j in range(n):
            bm.faces.new((V[(i, j)], V[(i + 1, j)], V[(i + 1, j + 1)], V[(i, j + 1)]))

# ---------------------------------------------------------------- API
def _aresta_viva(bm, graus=0):
    """Sombreamento plano: facetas e arestas vivas, sem suavizar normais."""
    for f in bm.faces: f.smooth = False

def construir():
    r = random.Random(SEED)
    mats = {k: comum.material("M_Piso_Laje_" + k, c, rough=0.78) for k, c in CORES.items()}
    mj = comum.material("M_Piso_Junta", COR_JUNTA, rough=1.0)
    bms = {k: bmesh.new() for k in CORES}
    for l in comum.layout():
        rl = random.Random(SEED * 31 + l["id"] * 7 + (1 if l["cortada"] else 0) * 3 + int(l["x0"] * 100) % 97 + int(l["y0"] * 100) * 13)
        k = rl.choice("ABCD")
        # lajotas cortadas pela borda: mesma cor da irma (usa o id) para a emenda parecer uma lajota so
        if l["cortada"]: k = "ABCD"[(l["id"] * 5 + 1) % 4]
        lajota(bms[k], l, rl)
    objs = []
    for k, bm in bms.items():
        _aresta_viva(bm)
        objs.append(comum.novo_objeto("Lajotas_" + k, bm, [mats[k]]))
    bj = bmesh.new(); junta(bj); _aresta_viva(bj)
    objs.append(comum.novo_objeto("Junta", bj, [mj]))
    return objs

# ---------------------------------------------------------------- previa (nos procedurais so aqui)
def _materiais_previa():
    for m in bpy.data.materials:
        if not m.name.startswith("M_Piso_") or not m.use_nodes: continue
        nt = m.node_tree; b = nt.nodes["Principled BSDF"]
        base = tuple(b.inputs["Base Color"].default_value)[:3]
        tc = nt.nodes.new("ShaderNodeTexCoord")
        n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 9 if "Junta" not in m.name else 40
        n1.inputs["Detail"].default_value = 10; n1.inputs["Roughness"].default_value = 0.7
        n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 160; n2.inputs["Detail"].default_value = 6
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (base[0] * 0.55, base[1] * 0.55, base[2] * 0.6, 1)
        ramp.color_ramp.elements[1].color = (base[0] * 1.45, base[1] * 1.45, base[2] * 1.4, 1)
        bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25; bump.inputs["Distance"].default_value = 0.01
        mx = nt.nodes.new("ShaderNodeMath"); mx.operation = 'MULTIPLY_ADD'; mx.inputs[1].default_value = 0.5; mx.inputs[2].default_value = 0.3
        nt.links.new(tc.outputs["Object"], n1.inputs["Vector"]); nt.links.new(tc.outputs["Object"], n2.inputs["Vector"])
        nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
        nt.links.new(n2.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])

def _luz_fria():
    """Luz fria rasante extra (so prévia): realça facetas e chanfros sem a tocha quente."""
    s2 = bpy.data.objects.new("lua_rasante", bpy.data.lights.new("lua_rasante", 'SUN')); s2.data.energy = 3.0; s2.data.color = (0.55, 0.68, 1.0)
    s2.rotation_euler = (math.radians(74), 0, math.radians(-30)); bpy.context.collection.objects.link(s2)

if __name__ == "__main__":
    comum.limpar_cena()
    objs = construir()
    tris = 0
    for o in objs:
        bm = bmesh.new(); bm.from_mesh(o.data); tris += sum(len(f.verts) - 2 for f in bm.faces); bm.free()
    print("TRIANGULOS", tris)
    _materiais_previa()
    bpy.context.scene.view_settings.exposure = 0.0
    saida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "previas", "piso")
    saida = os.path.normpath(saida)
    _luz_fria()
    comum.previa(os.path.join(saida, "lajotas_3q.png"), olhar=(4, 4, 0), cam=(9.5, -3.5, 8.5), luz_quente=False)
    comum.previa(os.path.join(saida, "lajotas_rasante.png"), olhar=(3.5, 3.5, 0), cam=(6.5, 0.2, 0.55), lente=40, luz_quente=False)
    comum.previa(os.path.join(saida, "lajotas_close.png"), olhar=(3, 3, 0), cam=(4.0, 1.6, 1.4), lente=50, luz_quente=False)
