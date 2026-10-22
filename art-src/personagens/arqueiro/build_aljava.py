"""Arqueiro_Aljava.glb: aljava de couro modelada do zero (estatica, sem armature) com bandoleira, bolsa, fivelas e 7 flechas.
Rodar: blender -b --factory-startup -P build_aljava.py   (TEMP/TMP no disco D)

Frame de saida (Blender Z-up; glTF Y-up): origem no meio do tubo; eixo do tubo = Z (boca em +Z); costas do personagem = +Y
(rosto em -Y), esquerda do personagem = +X. A inclinacao de ~20 graus (topo para o ombro direito, -X) JA esta assada na malha,
entao no Godot basta parentar a um BoneAttachment3D em Chest com o offset do equipamento.csv (sem rotacao extra).
Material unico M_Arqueiro_Aljava (atlas 512 pintado em numpy + normal):
  A (u0-.5, v.5-1) couro do tubo | B (u.5-1, v.5-1) couro escuro com costura (cintas, bolsa)
  C (u0-.5, v0-.5) penas: verde (u0-.25) e marfim (u.25-.5) | D (u.5-1, v0-.5) haste (u.5-.7), osso (.7-.9), latao (.9-1)
"""
import os, sys, math
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import build_arco as A  # reaproveita noise() e mk_mat()

REPO = A.REPO
SAIDA = A.SAIDA
TEX = os.path.join(AQUI, "tex_aljava")
N = 512
TILT = math.radians(-20)          # topo para -X (ombro direito do personagem)
TILTX = math.radians(10)         # topo um pouco para o corpo (a capa se alarga para baixo)
ROT = Matrix.Rotation(TILT, 3, "Y") @ Matrix.Rotation(TILTX, 3, "X")
ESC = 1.2                          # escala assada (aljava maior, legivel no chibi)
NT = 10                            # lados do tubo
ZB, ZT = -0.20, 0.20               # base e boca do tubo
# bandoleira: pontos em coordenadas do frame da aljava ANTES da inclinacao (ajustados com o corpo nas previas)
# offset da aljava no osso Chest (Blender, m; costas=+Y) e bandoleira em coordenadas RELATIVAS AO CHEST (mundo, antes da inclinacao)
QOFF = Vector((-0.08, 0.47, -0.08))
STRAP_W = [(-0.10, 0.36, 0.05), (-0.20, 0.12, 0.27), (-0.18, -0.20, 0.21), (-0.02, -0.225, 0.06),
           (0.14, -0.225, -0.10), (0.31, -0.08, -0.15), (0.29, 0.22, -0.13), (0.10, 0.38, -0.19), (-0.05, 0.43, -0.26)]
STRAP = [tuple(ROT.inverted() @ (Vector(p) - QOFF) / ESC) for p in STRAP_W]
STRAP[0] = (-0.012, -0.066, 0.150)   # nasce na cinta da boca, rente a parede (lado do peito)
if os.environ.get("ALJ_STRAP_JSON"):
    import json
    STRAP = [tuple(p) for p in json.loads(os.environ["ALJ_STRAP_JSON"])]


# ------------------------------------------------------------------ texturas
def wrapnoise(h, w, sy, sx, seed):
    return A.noise(h, w, sy, sx, seed)


def paint():
    alb = np.zeros((N, N, 3), np.float32)
    hgt = np.zeros((N, N), np.float32)
    H = W = N // 2
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # ---- A: couro marrom do tubo (grao vertical, desgaste assimetrico, costura nas bordas esquerda/direita)
    g1 = wrapnoise(H, W, 80, 2, 3); g2 = wrapnoise(H, W, 90, 70, 4); g3 = wrapnoise(H, W, 3, 3, 5)
    base = np.array([0.52, 0.31, 0.16])
    col = base * (0.88 + 0.22 * g2[..., None]) * (0.90 + 0.20 * g1[..., None]) * (0.97 + 0.06 * g3[..., None])
    wear = np.clip(wrapnoise(H, W, 40, 40, 6) - 0.55, 0, 1) * 2.2           # manchas claras de uso, so num lado
    wear *= np.clip((xx / W - 0.25) * 1.5, 0, 1)
    col = col * (1 - 0.35 * wear[..., None]) + np.array([0.66, 0.44, 0.26]) * 0.35 * wear[..., None]
    dirt = np.clip(1 - yy / H * 1.2, 0, 1) ** 2                              # base (linha alta = v baixo?) mais suja
    col = col * (1 - 0.40 * dirt[..., None])
    h = g1 * 0.3 + g3 * 0.25
    # paineis: faixa clara de realce nas bordas dos reforcos e veios longitudinais
    for y0 in (int(H * 0.02), int(H * 0.5)):
        col[y0:y0 + 3] *= 0.55
    for cx in (6, W - 7):                                                    # costura nitida
        col[:, cx - 1:cx + 1] *= 0.55
        for y0 in range(2, H, 9):
            col[y0:y0 + 5, cx + 3:cx + 5] = (0.80, 0.68, 0.46)
            h[y0:y0 + 5, cx + 3:cx + 5] += 1.2
        h[:, cx - 1:cx + 1] -= 0.8
    # vincos horizontais de couro (dobras) e riscos
    rng = np.random.RandomState(8)
    for _ in range(14):
        y0 = rng.randint(0, H); x0 = rng.randint(10, W - 10); l = rng.randint(8, 40)
        col[y0, x0:x0 + l] *= 0.62; h[y0, x0:x0 + l] -= 0.9
    # vincos verticais escuros nos cantos para fechar a silhueta
    ed = np.clip(np.abs(xx / W - 0.5) * 2, 0, 1) ** 6
    col *= (1 - 0.25 * ed[..., None])
    alb[0:H, 0:W] = np.clip(col, 0, 1); hgt[0:H, 0:W] = h
    # ---- B: couro escuro das cintas (costura central), bolsa
    g1 = wrapnoise(H, W, 30, 3, 13); g2 = wrapnoise(H, W, 10, 10, 14)
    base = np.array([0.30, 0.17, 0.085])
    col = base * (0.80 + 0.30 * g2[..., None]) * (0.9 + 0.2 * g1[..., None])
    h = g2 * 0.4
    ed = np.clip(np.abs(xx / W - 0.5) * 2, 0, 1) ** 4                        # bordas claras (couro gasto)
    col = col * (1 - 0.2 * ed[..., None]) + np.array([0.52, 0.34, 0.19]) * 0.30 * ed[..., None]
    cx = W // 2
    for sx in (-14, 14):                                                     # duas fileiras de costura
        col[:, cx + sx - 1:cx + sx + 1] *= 0.5
        for y0 in range(0, H, 8):
            col[y0:y0 + 4, cx + sx - 1:cx + sx + 1] = (0.78, 0.66, 0.44)
            h[y0:y0 + 4, cx + sx - 1:cx + sx + 1] += 1.2
    rub = np.clip(wrapnoise(H, W, 30, 30, 15) - 0.6, 0, 1) * 2
    col = col * (1 - 0.3 * rub[..., None]) + np.array([0.5, 0.33, 0.19]) * 0.3 * rub[..., None]
    alb[0:H, W:N] = np.clip(col, 0, 1); hgt[0:H, W:N] = h
    # ---- C: penas (verde e marfim): cor por u, raque central + barbas diagonais, topo (v alto) mais claro
    for half, c0, c1 in ((0, (0.16, 0.36, 0.12), (0.42, 0.66, 0.22)), (1, (0.80, 0.74, 0.58), (0.97, 0.94, 0.84))):
        w = W // 2
        yy2, xx2 = np.mgrid[0:H, 0:w].astype(np.float32)
        t = xx2 / w
        bar = (np.sin((yy2 * 0.9 + np.abs(t - 0.2) * 70) * 0.5) * 0.5 + 0.5)
        grad = np.clip(yy2 / H, 0, 1)[..., None]
        col = np.array(c1) * grad + np.array(c0) * (1 - grad)
        col = col * (0.78 + 0.35 * bar[..., None]) * (0.92 + 0.16 * wrapnoise(H, w, 6, 6, 21 + half)[..., None])
        rach = np.exp(-((t - 0.2) / 0.025) ** 2)[..., None]
        col = col * (1 - rach) + np.array([0.86, 0.80, 0.64]) * rach
        hh = bar * 0.6 - rach[..., 0] * 0
        alb[H:N, half * w:(half + 1) * w] = np.clip(col, 0, 1)
        hgt[H:N, half * w:(half + 1) * w] = hh
    # ---- D: haste (madeira clara), osso, latao
    w = 51
    yy2, xx2 = np.mgrid[0:H, 0:w * 2].astype(np.float32)
    wood = np.array([0.56, 0.40, 0.22]) * (0.8 + 0.3 * wrapnoise(H, w * 2, 40, 2, 31)[..., None])
    wood *= (0.9 + 0.15 * np.sin(yy2 * 0.15)[..., None])
    alb[H:N, W:W + w * 2] = np.clip(wood, 0, 1)
    bone = np.array([0.90, 0.84, 0.70]) * (0.82 + 0.25 * wrapnoise(H, w * 2, 8, 8, 32)[..., None])
    pit = np.clip(wrapnoise(H, w * 2, 4, 4, 33) - 0.62, 0, 1) * 3
    bone *= (1 - 0.35 * pit[..., None])
    alb[H:N, W + w * 2:W + w * 4] = np.clip(bone, 0, 1)
    brass = np.array([0.72, 0.52, 0.20]) * (0.75 + 0.35 * wrapnoise(H, 52, 5, 5, 34)[..., None])
    alb[H:N, W + w * 4:N] = np.clip(brass, 0, 1)
    hgt[H:N, W:W + w * 2] = wrapnoise(H, w * 2, 40, 2, 31) * 0.4
    hgt[H:N, W + w * 2:W + w * 4] = wrapnoise(H, w * 2, 8, 8, 32) * 0.3 - pit * 0.5
    hgt[H:N, W + w * 4:N] = 0.0
    return alb, hgt


def make_images():
    os.makedirs(TEX, exist_ok=True)
    alb, hgt = paint()
    nrm = np.zeros((N, N, 3), np.float32)
    dx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)) * 1.1
    dy = (np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)) * 1.1
    nrm[..., 0] = -dx; nrm[..., 1] = dy; nrm[..., 2] = 1.0
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    nrm = nrm * 0.5 + 0.5
    imgs = []
    for nome, arr in (("T_Aljava_BC", alb), ("T_Aljava_N", nrm)):
        img = bpy.data.images.new(nome, N, N, alpha=True)
        rgba = np.ones((N, N, 4), np.float32); rgba[..., :3] = arr[::-1]
        img.pixels.foreach_set(rgba.ravel())
        img.filepath_raw = os.path.join(TEX, nome + ".png"); img.file_format = "PNG"; img.save()
        imgs.append(img)
    return imgs


# ------------------------------------------------------------------ geometria
REG = {"A": (0.0, 0.5, 0.5, 1.0), "B": (0.5, 1.0, 0.5, 1.0), "Cg": (0.0, 0.25, 0.0, 0.5), "Cm": (0.25, 0.5, 0.0, 0.5),
       "Dw": (0.5, 0.7, 0.0, 0.5), "Db": (0.7, 0.9, 0.0, 0.5), "Dl": (0.9, 1.0, 0.0, 0.5)}


def uvr(reg, fu, fv):
    u0, u1, v0, v1 = REG[reg]
    return (u0 + (u1 - u0) * fu, v0 + (v1 - v0) * fv)


class Mesh:
    def __init__(self):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")

    def face(self, vs, uvs, smooth=False):
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.smooth = smooth
        for lp, uv in zip(f.loops, uvs):
            lp[self.uv].uv = uv
        return f

    def ring_tube(self, rings, reg, smooth=True, cap_top=False, cap_bot=False, u_scale=1.0, vspan=(0.0, 1.0)):
        """rings: lista de listas de Vector (mesma contagem). UV: u=circunferencia, v=ao longo."""
        n = len(rings[0]); R = [[self.bm.verts.new(p) for p in r] for r in rings]
        m = len(R) - 1
        for i in range(m):
            va = vspan[0] + (vspan[1] - vspan[0]) * i / m; vb = vspan[0] + (vspan[1] - vspan[0]) * (i + 1) / m
            for k in range(n):
                k2 = (k + 1) % n
                ua, ub = k / n * u_scale, (k + 1) / n * u_scale
                self.face([R[i][k], R[i][k2], R[i + 1][k2], R[i + 1][k]],
                          [uvr(reg, ua, va), uvr(reg, ub, va), uvr(reg, ub, vb), uvr(reg, ua, vb)], smooth)
        if cap_top:
            self.face(list(R[-1]), [uvr(reg, 0.5, 0.5)] * n)
        if cap_bot:
            self.face(list(reversed(R[0])), [uvr(reg, 0.5, 0.5)] * n)
        return R

    def poly(self, pts, reg, fu=0.5, fv=0.5):
        vs = [self.bm.verts.new(p) for p in pts]
        return self.face(vs, [uvr(reg, fu, fv)] * len(vs))

    def cone(self, p0, p1, r0, r1, n, reg, fu=0.5, fv=0.5, cap0=True, cap1=True, smooth=False):
        a, b = Vector(p0), Vector(p1)
        ax = (b - a).normalized(); t = Vector((1, 0, 0)) if abs(ax.x) < 0.9 else Vector((0, 1, 0))
        u = ax.cross(t).normalized(); w = ax.cross(u).normalized()
        rs = [[self.bm.verts.new(c + (u * math.cos(2 * math.pi * k / n) + w * math.sin(2 * math.pi * k / n)) * r)
               for k in range(n)] for c, r in ((a, r0), (b, r1))]
        uv = uvr(reg, fu, fv)
        for k in range(n):
            self.face([rs[0][k], rs[0][(k + 1) % n], rs[1][(k + 1) % n], rs[1][k]], [uv] * 4, smooth)
        if cap0 and r0 > 0.0004:
            self.face(list(reversed(rs[0])), [uv] * n)
        if cap1 and r1 > 0.0004:
            self.face(list(rs[1]), [uv] * n)

    def box(self, c, size, reg, rot=None, bevel=0.0035):
        m = bmesh.new()
        bmesh.ops.create_cube(m, size=1.0)
        for v in m.verts:
            v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
        if bevel:
            bmesh.ops.bevel(m, geom=list(m.edges), offset=bevel, segments=1, affect="EDGES")
        mat = Matrix.Translation(c) @ (rot.to_4x4() if rot is not None else Matrix.Identity(4))
        mp = {}
        for v in m.verts:
            mp[v] = self.bm.verts.new(mat @ v.co)
        # UV planar pela normal dominante, centrado na regiao
        for f in m.faces:
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            a1, a2 = [i for i in range(3) if i != ax]
            uvs = [uvr(reg, 0.5 + (v.co[a1]) * 2.0, 0.5 + (v.co[a2]) * 2.0) for v in f.verts]
            self.face([mp[v] for v in f.verts], uvs)
        m.free()


def tube_ring(z, rx, ry, n=NT, cx=0.0, cy=0.0):
    # k=0 no lado +X (costura da aljava fica no flanco externo)
    return [Vector((cx + math.cos(2 * math.pi * k / n) * rx, cy + math.sin(2 * math.pi * k / n) * ry, z)) for k in range(n)]


def radius_at(z):
    t = (z - ZB) / (ZT - ZB)
    return 0.046 + (0.064 - 0.046) * t, 0.040 + (0.054 - 0.040) * t


def build_body(M):
    zs = [ZB + (ZT - ZB) * i / 4 for i in range(5)]
    M.ring_tube([tube_ring(z, *radius_at(z)) for z in zs], "A", smooth=True, cap_bot=True, u_scale=1.0)
    # forro escuro da boca (disco abaixo da boca; as flechas atravessam)
    zi = ZT - 0.012
    M.poly(list(reversed(tube_ring(zi, *[r - 0.004 for r in radius_at(zi)]))), "B", 0.2, 0.2)
    # cintas (reforcos) com perfil em degrau: rim da boca, cinta do meio, cinta baixa, fundo
    def band(z0, z1, grow):
        rr = []
        for z, g in ((z0, 0.0), (z0 + 0.0025, grow), (z1 - 0.0025, grow), (z1, 0.0)):
            rx, ry = radius_at(z)
            rr.append(tube_ring(z, rx + g, ry + g))
        M.ring_tube(rr, "B", smooth=False, u_scale=0.9)
    band(ZT - 0.040, ZT + 0.004, 0.0075)
    band(-0.012, 0.016, 0.0055)
    band(ZB - 0.004, ZB + 0.030, 0.0075)
    # fundo: tampa em cupula de couro escuro com rebite de latao
    rb = radius_at(ZB)
    M.ring_tube([tube_ring(ZB - 0.004, rb[0] + 0.007, rb[1] + 0.007), tube_ring(ZB - 0.020, rb[0] * 0.78, rb[1] * 0.78),
                 tube_ring(ZB - 0.030, rb[0] * 0.40, rb[1] * 0.40)], "B", smooth=False, cap_bot=False, cap_top=True)
    M.cone((0, 0, ZB - 0.030), (0, 0, ZB - 0.040), 0.009, 0.006, 6, "Dl")
    # tira da costura (vertical, no flanco +X), com borda levantada
    rx0, ry0 = radius_at(ZB); rx1, ry1 = radius_at(ZT)
    M.box(Vector(((rx0 + rx1) / 2 + 0.004, 0, (ZB + ZT) / 2)), (0.009, 0.026, ZT - ZB - 0.05), "B", bevel=0)
    for z in (-0.17, -0.06, 0.06, 0.15):  # rebites de latao na tira
        rx, _ = radius_at(z)
        M.cone((rx + 0.0075, 0, z), (rx + 0.0105, 0, z), 0.0055, 0.0036, 6, "Dl", cap0=False)


def build_pouch(M):
    # bolsa pequena no flanco de fora (+Y), tampa com aba inclinada, botao/fivela de latao
    zc = -0.075
    _, ry = radius_at(zc)
    yb = ry + 0.0135
    M.box(Vector((0.0, yb, zc - 0.006)), (0.074, 0.030, 0.070), "A", bevel=0.0045)
    rot = Matrix.Rotation(math.radians(-5), 3, "X")
    M.box(Vector((0.0, yb + 0.0165, zc + 0.026)), (0.080, 0.0075, 0.050), "B", rot=rot, bevel=0.0032)
    M.cone((0, yb + 0.021, zc + 0.010), (0, yb + 0.0265, zc + 0.010), 0.0075, 0.0055, 8, "Dl")
    # correias de fixacao da bolsa ao tubo
    for x in (-0.027, 0.027):
        M.box(Vector((x, ry + 0.003, zc + 0.012)), (0.012, 0.007, 0.115), "B", bevel=0.002)


def build_strap(M):
    # bandoleira: fita plana seguindo STRAP (suavizada Catmull-Rom), com costura e duas fivelas de latao
    pts = [Vector(p) for p in STRAP]

    def cr(p0, p1, p2, p3, t):
        return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)
    P = [pts[0]] + pts + [pts[-1]]
    curve = []
    for i in range(1, len(P) - 2):
        for s in range(2):
            curve.append(cr(P[i - 1], P[i], P[i + 1], P[i + 2], s / 2))
    curve.append(pts[-1])
    W_, T_ = 0.040, 0.0065
    rr = []
    total = 0.0
    for i, p in enumerate(curve):
        a = curve[max(0, i - 1)]; b = curve[min(len(curve) - 1, i + 1)]
        tg = (b - a).normalized()
        side = tg.cross(Vector((0, 0, 1)))
        if side.length < 0.2:
            side = tg.cross(Vector((0, 1, 0)))
        side.normalize()
        nrm = side.cross(tg).normalized()
        rr.append([p + side * (W_ / 2) + nrm * (T_ / 2), p - side * (W_ / 2) + nrm * (T_ / 2),
                   p - side * (W_ / 2) - nrm * (T_ / 2), p + side * (W_ / 2) - nrm * (T_ / 2)])
    n = len(rr)
    R = [[M.bm.verts.new(v) for v in r] for r in rr]
    for i in range(n - 1):
        va, vb = i / (n - 1), (i + 1) / (n - 1)
        # face superior (0->1) com a costura central; demais com a mesma regiao
        for k, (ua, ub) in enumerate(((0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0))):
            k2 = (k + 1) % 4
            if k == 0:
                uvs = [uvr("B", 0.0, va), uvr("B", 1.0, va), uvr("B", 1.0, vb), uvr("B", 0.0, vb)]
            else:
                uvs = [uvr("B", 0.02, va), uvr("B", 0.04, va), uvr("B", 0.04, vb), uvr("B", 0.02, vb)]
            M.face([R[i][k], R[i][k2], R[i + 1][k2], R[i + 1][k]], uvs)
    M.face(list(reversed(R[0])), [uvr("B", 0.5, 0.0)] * 4); M.face(list(R[-1]), [uvr("B", 0.5, 1.0)] * 4)
    # fivela de latao na parte da frente (peito) e argola no alto da aljava
    def buckle(p, tg):
        side = tg.cross(Vector((0, 0, 1))).normalized(); nrm = side.cross(tg).normalized()
        out = nrm
        w, hgt = 0.044, 0.030
        for (c, sz) in ((p + side * (w / 2 - 0.003), (0.006, 0.006, hgt)), (p - side * (w / 2 - 0.003), (0.006, 0.006, hgt)),
                        (p + tg * (hgt / 2 - 0.003), (w, 0.006, 0.006)), (p - tg * (hgt / 2 - 0.003), (w, 0.006, 0.006))):
            pass
        # moldura: 4 barras (como caixas alinhadas ao frame da fita)
        rot = Matrix((side, tg, nrm)).transposed()
        for off, size in (((w / 2 - 0.003, 0, 0), (0.006, hgt, 0.006)), ((-(w / 2 - 0.003), 0, 0), (0.006, hgt, 0.006)),
                          ((0, hgt / 2 - 0.003, 0), (w, 0.006, 0.006)), ((0, -(hgt / 2 - 0.003), 0), (w, 0.006, 0.006))):
            M.box(p + side * off[0] + tg * off[1] + nrm * (T_ / 2 + 0.002), size, "Dl", rot=rot, bevel=0)
        M.box(p + nrm * (T_ / 2 + 0.003), (0.004, 0.004, 0.0), "Dl", rot=rot, bevel=0) if False else None
    i1 = int(len(curve) * 0.42); i2 = int(len(curve) * 0.78)
    for i in (i1, i2):
        buckle(curve[i], (curve[i + 1] - curve[i - 1]).normalized())
    return curve


def build_arrows(M):
    # (dx, dy, tilt_x_deg, tilt_y_deg, topo_z, tipo, cor)  tipo: 'pena' (penas pra cima) ou 'ponta' (ponta de osso pra cima)
    ARR = [(-0.020, 0.010, -4, 3, 0.340, "pena", "Cg"), (0.018, -0.008, 5, -2, 0.350, "pena", "Cm"),
           (0.000, 0.022, -2, 6, 0.322, "pena", "Cg"), (-0.012, -0.022, 3, 5, 0.360, "pena", "Cm"),
           (0.028, 0.014, -4, -6, 0.318, "ponta", "Cg"), (-0.030, -0.012, 3, 6, 0.300, "ponta", "Cm"),
           (0.004, -0.004, 1, -3, 0.372, "pena", "Cg")]
    for (dx, dy, tx, ty, ztop, tipo, cor) in ARR:
        zb = -0.14
        base = Vector((dx, dy, zb))
        d = (Matrix.Rotation(math.radians(tx), 3, "X") @ Matrix.Rotation(math.radians(ty), 3, "Y")) @ Vector((0, 0, 1))
        L = (ztop - zb) / d.z
        top = base + d * L
        M.cone(base, top, 0.0048, 0.0048, 5, "Dw", 0.5, 0.5, smooth=False, cap0=False)
        axis = d
        t = Vector((1, 0, 0)); u = axis.cross(t).normalized(); w = axis.cross(u).normalized()
        if tipo == "pena":
            for j, k0 in enumerate((0, 1)):
                s0 = top - axis * (0.012 + 0.048 * 0 + k0 * 0.0)
            for k in range(3):
                ang = 2 * math.pi * k / 3 + 0.4
                rad = u * math.cos(ang) + w * math.sin(ang)
                P = [(0.0035, 0.0), (0.020, 0.011), (0.026, 0.052), (0.010, 0.070), (0.0035, 0.056)]
                vs = [M.bm.verts.new(top - axis * (0.070 - s) + rad * r) for (r, s) in P]
                # UV da pena: u=raio, v=ao longo
                M.face(vs, [uvr(cor, r / 0.028, s / 0.07) for (r, s) in P])
            M.cone(top - axis * 0.074, top - axis * 0.058, 0.0062, 0.0062, 4, "Dl", cap0=False, cap1=False)  # anel de latao
            M.cone(top, top + axis * 0.012, 0.0048, 0.0030, 6, "Dw")
        else:
            # ponta de osso: lamina facetada com colar
            M.cone(top - axis * 0.012, top + axis * 0.008, 0.0075, 0.0075, 6, "Db", cap0=False, cap1=False)
            M.cone(top + axis * 0.008, top + axis * 0.062, 0.0088, 0.0006, 4, "Db")
            M.cone(top + axis * 0.008, top + axis * 0.034, 0.0, 0.0, 3, "Db") if False else None
            # farpas: dois triangulos finos nos lados
            for sgn in (-1, 1):
                a = top + axis * 0.012 + u * (0.0085 * sgn)
                b = top + axis * 0.012 + u * (0.0160 * sgn) - axis * 0.012
                c = top + axis * 0.036 + u * (0.0040 * sgn)
                M.poly([a, b, c], "Db"); M.poly([a, c, b], "Db")


def finalize(M, mat):
    mesh = bpy.data.meshes.new("SM_Archer_Quiver")
    ob = bpy.data.objects.new("SM_Archer_Quiver", mesh)
    bpy.context.scene.collection.objects.link(ob)
    mesh.materials.append(mat)
    bmesh.ops.recalc_face_normals(M.bm, faces=M.bm.faces)
    M.bm.to_mesh(mesh); M.bm.free()
    # inclinacao ~20 graus assada na malha
    mesh.transform(Matrix.Scale(ESC, 4) @ ROT.to_4x4())
    mesh.update()
    return ob


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    img_bc, img_n = make_images()
    mat = A.mk_mat("M_Arqueiro_Aljava", img_bc, img_n, rough=0.78)
    mat.use_backface_culling = False
    M = Mesh()
    build_body(M); build_pouch(M); build_strap(M); build_arrows(M)
    return finalize(M, mat)


def exportar(ob):
    os.makedirs(SAIDA, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    caminho = os.path.join(SAIDA, "Arqueiro_Aljava.glb")
    bpy.ops.export_scene.gltf(filepath=caminho, export_format="GLB", use_selection=True, export_animations=False,
                              export_yup=True, export_apply=True, export_materials="EXPORT", export_image_format="AUTO")
    print("EXPORTADO", caminho)


if __name__ == "__main__":
    ob = build()
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    print("TRIS", tris, "dim", tuple(round(d, 3) for d in ob.dimensions))
    exportar(ob)
