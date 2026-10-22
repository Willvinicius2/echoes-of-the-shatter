"""Arqueiro_Arco.glb: arco de osso modelado do zero (estatico, sem armature).
Rodar: blender -b --factory-startup -P build_arco.py   (TEMP/TMP no disco D)

ORIENTACAO (convencao do corpo: personagem olha para -Y do Blender = +Z do glTF/Godot):
  Blender (Z-up)          glTF/Godot (Y-up)
  arco vertical em +Z  -> +Y
  CORDA para tras +Y   -> -Z   (lado do arqueiro; "para tras" do personagem)
  barriga/frente -Y    -> +Z   (o arco aponta/e mirado ao longo de +Z do personagem)
  largura (X)          -> X
Origem = centro do cabo (0,0,0). Altura total 1,0 m (de -0,5 a +0,5 em Z). Em BoneAttachment3D de
socket_weapon_l entra sem rotacao extra (mesma convencao usada por previas.py/montar()).

Partes (malha unica SM_Archer_Bow, 3 materiais):
  M_Arqueiro_Arco       atlas 512 pintado (albedo + normal): osso (coluna esq., limb de cima v0.5-1, de baixo v0-0.5),
                        couro (dir. cima), corda trancada (dir. baixo)
  M_Arqueiro_Arco_Gema  pedra verde emissiva
  M_Arqueiro_Arco_Corda corda fina (geometria real) entre os nocks
Desgaste assimetrico: limb de baixo mais sujo/lascado e com rachadura, ponta de cima mais clara.
"""
import os, sys, math, random
import bpy, bmesh
import numpy as np
from mathutils import Vector

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
SAIDA = os.environ.get("ARQ_SAIDA", os.path.join(REPO, "godot", "art", "models", "personagens", "arqueiro"))
TEX = os.path.join(AQUI, "tex_arco")
random.seed(7)
np.random.seed(7)

# ---------------------------------------------------------------- texturas
N = 512


def noise(h, w, scale_y, scale_x, seed):
    rng = np.random.RandomState(seed)
    gy, gx = max(2, int(h / scale_y)), max(2, int(w / scale_x))
    g = rng.rand(gy + 1, gx + 1)
    ys = np.linspace(0, gy, h, endpoint=False); xs = np.linspace(0, gx, w, endpoint=False)
    y0 = ys.astype(int); x0 = xs.astype(int); fy = (ys - y0)[:, None]; fx = (xs - x0)[None, :]
    fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
    a = g[y0][:, x0]; b = g[y0][:, x0 + 1]; c = g[y0 + 1][:, x0]; d = g[y0 + 1][:, x0 + 1]
    return a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy


def paint_atlas():
    """Retorna (albedo HxWx3, altura HxW). Linha 0 do array = v=1 (topo da imagem), convertido depois."""
    alb = np.zeros((N, N, 3), np.float32)
    hgt = np.zeros((N, N), np.float32)
    H = N // 2
    W = N // 2
    # --- osso: dois limbs 256x256 (u em volta, v ao longo: v=0 no cabo, v=1 na ponta)
    for limb, y0 in (("cima", 0), ("baixo", H)):  # y0 em linhas do array (topo=0): cima = v 0.5..1
        sub = np.zeros((H, W, 3), np.float32)
        v = np.linspace(1, 0, H)[:, None] if limb == "cima" else np.linspace(1, 0, H)[:, None]
        # v aqui = posicao ao longo do limb (0 cabo .. 1 ponta); no array a linha 0 e o topo da imagem = v maior
        base = np.array([0.86, 0.80, 0.66])
        tip = np.array([0.96, 0.93, 0.82])
        # corpo do limb em madeira/couro escuro, ponta (esporao) em osso claro
        wood = np.array([0.30, 0.19, 0.105])
        t0 = np.clip((v - 0.80) / 0.05, 0, 1)
        t1 = np.clip((v - 0.88) / 0.12, 0, 1)
        col = wood[None, None, :] * (1 - t0[..., None]) + base[None, None, :] * t0[..., None]
        col = col * (1 - t1[..., None]) + tip[None, None, :] * t1[..., None]
        fib = noise(H, W, 40, 3, 11 if limb == "cima" else 23)  # fibras longitudinais
        mot = noise(H, W, 14, 14, 5 if limb == "cima" else 9)
        col = col * (0.86 + 0.22 * fib[..., None]) * (0.93 + 0.12 * mot[..., None])
        # sujeira perto do cabo (mais no limb de baixo) e manchas ocre
        suj = np.clip(1 - v / (0.38 if limb == "cima" else 0.62), 0, 1) ** 1.4
        grime = np.array([0.45, 0.34, 0.20])
        col = col * (1 - 0.55 * suj[..., None]) + grime * 0.55 * suj[..., None] * 0.6
        stain = np.clip(noise(H, W, 30, 30, 41 if limb == "baixo" else 42) - (0.55 if limb == "baixo" else 0.72), 0, 1) * 3
        col = col * (1 - stain[..., None] * 0.5) + np.array([0.42, 0.33, 0.18]) * stain[..., None] * 0.5
        # aneis (juntas/ossos) em v = 0.28, 0.55 e marcas
        hh = np.zeros((H, W), np.float32)
        for vv in (0.16, 0.44, 0.62, 0.79):
            band = np.exp(-((v - vv) / 0.018) ** 2)
            col = col * (1 - 0.8 * band[..., None]) + np.array([0.80, 0.72, 0.55]) * 0.8 * band[..., None]
            hh += band * 0.5
            edge = np.exp(-((np.abs(v - vv) - 0.022) / 0.006) ** 2)
            col = col * (1 - 0.45 * edge[..., None])
        # poros e veios do osso (garra) + sujeira nas ranhuras
        pit = np.clip(noise(H, W, 5, 5, 61 + y0) - 0.62, 0, 1) * 3
        boneZ = np.clip((v - 0.82) / 0.05, 0, 1)
        col = col * (1 - 0.5 * pit[..., None] * boneZ[..., None])
        hh -= pit * boneZ * 0.6
        # lascas e riscos
        rng = np.random.RandomState(3 if limb == "cima" else 4)
        for _ in range(26 if limb == "baixo" else 10):
            yy, xx = rng.randint(0, H), rng.randint(0, W)
            l = rng.randint(4, 26)
            for k in range(l):
                yk = min(H - 1, yy + k)
                col[yk, xx] *= 0.7
                hh[yk, xx] -= 0.6
        if limb == "baixo":  # rachadura longa
            xx = 120
            for yy in range(60, 200):
                xx += rng.randint(-1, 2)
                col[yy, xx % W] *= 0.45; hh[yy, xx % W] -= 1.0
        hh += fib * 0.35 + mot * 0.25
        alb[y0:y0 + H, 0:W] = np.clip(col, 0, 1)
        hgt[y0:y0 + H, 0:W] = hh
    # --- couro: canto sup-dir
    ly, lx = 0, W
    gr = noise(H, W, 5, 5, 77); gr2 = noise(H, W, 18, 18, 78)
    base = np.array([0.34, 0.20, 0.11])
    col = base[None, None, :] * (0.78 + 0.35 * gr2[..., None]) * (0.9 + 0.2 * gr[..., None])
    u = np.linspace(0, 1, W)[None, :]
    vv = np.linspace(1, 0, H)[:, None]
    edge = np.exp(-((vv - 0.5) / 0.5) ** 8) * 0 + np.clip(np.abs(vv - 0.5) * 2, 0, 1) ** 4
    col = col * (1 - 0.35 * edge[..., None]) + np.array([0.55, 0.36, 0.2]) * 0.25 * edge[..., None] * gr[..., None]
    # costura (linha tracejada) ao longo
    for yy in range(0, H, 8):
        col[yy:yy + 4, int(W * 0.5):int(W * 0.5) + 2] = (0.78, 0.66, 0.45)
    rubbed = np.clip(noise(H, W, 25, 25, 79) - 0.6, 0, 1) * 2
    col = col * (1 - 0.4 * rubbed[..., None]) + np.array([0.62, 0.42, 0.26]) * 0.4 * rubbed[..., None]
    alb[ly:ly + H, lx:lx + W] = np.clip(col, 0, 1)
    hgt[ly:ly + H, lx:lx + W] = gr * 0.6 + gr2 * 0.3
    # --- corda trancada: canto inf-dir. Torcao diagonal.
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    tw = np.sin((xx * 0.5 + yy * 0.5) * 2 * math.pi / 14.0) * 0.5 + 0.5
    base = np.array([0.74, 0.62, 0.42])
    col = base[None, None, :] * (0.65 + 0.4 * tw[..., None]) * (0.9 + 0.2 * noise(H, W, 6, 6, 91)[..., None])
    dirt = np.clip(noise(H, W, 30, 30, 92) - 0.45, 0, 1)
    col = col * (1 - 0.35 * dirt[..., None])
    alb[H:H + H, W:W + W] = np.clip(col, 0, 1)
    hgt[H:H + H, W:W + W] = tw * 1.2
    return alb, hgt


def save_pngs():
    os.makedirs(TEX, exist_ok=True)
    alb, hgt = paint_atlas()
    nrm = np.zeros((N, N, 3), np.float32)
    dx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)) * 2.2
    dy = (np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)) * 2.2  # linha 0 = topo; +Y OpenGL = para cima
    nrm[..., 0] = -dx; nrm[..., 1] = dy; nrm[..., 2] = 1.0
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    nrm = nrm * 0.5 + 0.5
    paths = []
    for nome, arr in (("T_Arco_BC", alb), ("T_Arco_N", nrm)):
        img = bpy.data.images.new(nome, N, N, alpha=True)
        rgba = np.ones((N, N, 4), np.float32)
        rgba[..., :3] = arr[::-1]  # bpy: linha 0 = base da imagem
        img.pixels.foreach_set(rgba.ravel())
        img.filepath_raw = os.path.join(TEX, nome + ".png")
        img.file_format = "PNG"
        img.save()
        paths.append(img)
    return paths


# ---------------------------------------------------------------- materiais
def mk_mat(nome, img=None, nrm=None, cor=(0.8, 0.8, 0.8, 1), rough=0.7, emis=None, emis_str=0.0):
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = 0.0
    if img is not None:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
        nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
        if nrm is not None:
            nrm.colorspace_settings.name = "Non-Color"
            tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = nrm
            nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = 1.0
            nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    else:
        bsdf.inputs["Base Color"].default_value = cor
    if emis:
        bsdf.inputs["Emission Color"].default_value = emis
        bsdf.inputs["Emission Strength"].default_value = emis_str
    return m


# ---------------------------------------------------------------- geometria
def centerline(s):
    """Ponto (y,z) do eixo do limb para s em [-1,1]. +Y = lado da corda. Altura total 1,1 m (z=0.55*s)."""
    a = abs(s)
    y = 0.17 * a ** 1.8 - 0.026 * math.sin(math.pi * min(max(a - 0.15, 0.0) / 0.45, 1.0)) ** 1.5   # S: ventre para frente perto do punho
    if a > 0.75:  # recurvo em M: reflexo suave e, na ponta, a garra volta para frente (-Y)
        y -= 0.03 * ((a - 0.75) / 0.25) ** 2
    if a > 0.90:
        y -= 0.115 * ((a - 0.90) / 0.10) ** 1.5
    z = 0.55 * s
    return y, z


def sweep(bm, ss, rx_f, ry_f, nring, uv_layer, u_rng, v_rng, v_of_s, mat_idx, cap_end=True, cap_start=True, twist=None, smooth=True):
    """Varre elipse (rx em X, ry na normal do plano YZ) ao longo de centerline(s). Retorna lista de aneis."""
    pts = [centerline(s) for s in ss]
    rings = []
    for i, s in enumerate(ss):
        y, z = pts[i]
        j0, j1 = max(0, i - 1), min(len(ss) - 1, i + 1)
        ty, tz = pts[j1][0] - pts[j0][0], pts[j1][1] - pts[j0][1]
        L = math.hypot(ty, tz); ty, tz = ty / L, tz / L
        ny, nz = -tz, ty  # normal no plano YZ (aponta para +Y quando T=+Z)
        rx, ry = rx_f(s), ry_f(s)
        ring = []
        for k in range(nring):
            ang = 2 * math.pi * k / nring
            cx, cy = math.cos(ang) * rx, math.sin(ang) * ry
            ring.append(bm.verts.new((cx, y + ny * cy, z + nz * cy)))
        rings.append(ring)
    uvl = bm.loops.layers.uv[uv_layer]

    def face(vs, uvs):
        try:
            f = bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = mat_idx
        for lp, uv in zip(f.loops, uvs):
            lp[uvl].uv = uv
        f.smooth = smooth
        return f
    for i in range(len(rings) - 1):
        va, vb = v_of_s(ss[i]), v_of_s(ss[i + 1])
        va = v_rng[0] + (v_rng[1] - v_rng[0]) * va
        vb = v_rng[0] + (v_rng[1] - v_rng[0]) * vb
        for k in range(nring):
            k2 = (k + 1) % nring
            ua = u_rng[0] + (u_rng[1] - u_rng[0]) * k / nring
            ub = u_rng[0] + (u_rng[1] - u_rng[0]) * (k + 1) / nring
            face([rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]],
                 [(ua, va), (ub, va), (ub, vb), (ua, vb)])
    uc = (u_rng[0] + u_rng[1]) / 2
    for end, cap in ((rings[-1], cap_end), (rings[0], cap_start)):
        if cap:
            vc = v_rng[1] if end is rings[-1] else v_rng[0]
            f = face(list(reversed(end)) if end is rings[-1] else list(end), [(uc, vc)] * nring)
    return rings


def torus_band(bm, cx_z, r_major_x, r_major_y, r_minor, tilt, nmaj, nmin, uv_layer, u_rng, v_rng, mat_idx, shift=0.0):
    """Anel de corda em volta do cabo (eixo Z), inclinado em tilt rad (trancado/diagonal)."""
    uvl = bm.loops.layers.uv[uv_layer]
    ring_pts = []
    for a in range(nmaj):
        ang = 2 * math.pi * a / nmaj
        c, s = math.cos(ang), math.sin(ang)
        px, py = c * r_major_x, s * r_major_y
        pz = math.sin(ang) * math.tan(tilt) * r_major_x * 0.0 + (c * 0.0)
        pz = s * r_major_x * math.tan(tilt)
        # normal radial no plano XY
        n = Vector((c * r_major_y, s * r_major_x, 0)).normalized()
        row = []
        for b in range(nmin):
            bb = 2 * math.pi * b / nmin
            off = n * (math.cos(bb) * r_minor) + Vector((0, 0, math.sin(bb) * r_minor * 1.0))
            row.append(bm.verts.new((px + off.x, py + off.y, cx_z + pz + off.z + shift)))
        ring_pts.append(row)
    for a in range(nmaj):
        a2 = (a + 1) % nmaj
        for b in range(nmin):
            b2 = (b + 1) % nmin
            vs = [ring_pts[a][b], ring_pts[a2][b], ring_pts[a2][b2], ring_pts[a][b2]]
            f = bm.faces.new(vs)
            f.material_index = mat_idx; f.smooth = True
            for lp, (uu, vv) in zip(f.loops, [(a / nmaj, b / nmin), ((a + 1) / nmaj, b / nmin), ((a + 1) / nmaj, (b + 1) / nmin), (a / nmaj, (b + 1) / nmin)]):
                lp[uvl].uv = (u_rng[0] + (u_rng[1] - u_rng[0]) * uu, v_rng[0] + (v_rng[1] - v_rng[0]) * vv)
    return ring_pts


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    img_bc, img_n = save_pngs()
    m_atlas = mk_mat("M_Arqueiro_Arco", img_bc, img_n, rough=0.62)
    m_gema = mk_mat("M_Arqueiro_Arco_Gema", cor=(0.05, 0.45, 0.1, 1), rough=0.25, emis=(0.15, 0.9, 0.2, 1), emis_str=0.9)
    m_corda = mk_mat("M_Arqueiro_Arco_Corda", cor=(0.80, 0.74, 0.55, 1), rough=0.8)
    mesh = bpy.data.meshes.new("SM_Archer_Bow")
    ob = bpy.data.objects.new("SM_Archer_Bow", mesh)
    bpy.context.scene.collection.objects.link(ob)
    for m in (m_atlas, m_gema, m_corda):
        mesh.materials.append(m)
    bm = bmesh.new()
    bm.loops.layers.uv.new("UVMap")
    UV = "UVMap"

    # --- limbs: corpo de madeira escura (liso) + garra de osso (facetada, bisel marcado)
    def rx(s):
        a = abs(s)
        base = 0.0165 - 0.0045 * a
        base *= 1 + 0.55 * math.exp(-((a - 0.15) / 0.02) ** 2)         # virola do punho
        base *= 0.78 + 0.22 * min(1.0, max(0.0, (a - 0.12) / 0.2))
        for c0 in (0.44, 0.62):
            base *= 1 + 0.16 * math.exp(-((a - c0) / 0.018) ** 2)       # aneis de osso
        base *= 1 + 0.45 * math.exp(-((a - 0.795) / 0.020) ** 2)        # colar da garra
        if a > 0.80:   # garra: afila em ponta
            t = (a - 0.80) / 0.20
            base *= max(0.03, 1 - t) ** 0.85
        return base

    def ry(s):
        a = abs(s)
        return rx(s) * (1.45 + (0.8 * (a - 0.8) / 0.2 if a > 0.8 else 0.0))  # garra achatada em lamina

    def limb(sign):
        for lo, hi, n, flat, nr in ((0.10, 0.80, 12, False, 8), (0.80, 1.0, 12, True, 6)):
            ss = [sign * (lo + (hi - lo) * (i / (n - 1))) for i in range(n)]
            vr = (0.5, 1.0) if sign > 0 else (0.0, 0.5)
            sweep(bm, ss, rx, ry, nr, UV, (0.0, 0.5), vr, lambda s: min(1.0, (abs(s) - 0.10) / 0.90), 0,
                  cap_end=True, cap_start=True, smooth=not flat)
    limb(+1); limb(-1)

    # --- cabo de couro (straight Z), ligeiramente bojudo, com colares de osso nas pontas
    ssg = [(-0.127 + 0.254 * i / 6) for i in range(7)]
    cabo_pts = ssg
    def grx(s):
        a = abs(s) / 0.127
        return 0.0245 * (1.0 + 0.10 * (1 - a * a)) + (0.003 if a > 0.9 else 0)
    def gry(s):
        return grx(s) * 0.90
    sweep(bm, ssg, grx, gry, 8, UV, (0.5, 1.0), (0.55, 0.95), lambda s: (s + 0.127) / 0.254, 0)

    # --- enrolamento de corda trancada: aneis inclinados em torno do cabo
    zs = [-0.058, -0.045, 0.034, 0.047, 0.060]
    for i, z in enumerate(zs):
        tl = 0.03 if i % 2 == 0 else 0.05
        torus_band(bm, z, 0.0262 + 0.0004 * (i % 3), 0.0240 + 0.0004 * (i % 2), 0.0042 + 0.0002 * (i % 2),
                   tl, 8, 3, UV, (0.5, 1.0), (0.0, 0.5), 0)

    # --- nocks: dente de osso saindo do limb em +Y ate a corda; corda fina reta de ponta a ponta
    SN = 0.905
    yn, zn = {}, {}
    for sign in (+1, -1):
        yn[sign], zn[sign] = centerline(sign * SN)
    ys_ = yn[1] + ry(SN) + 0.006          # corda logo atras da face do limb
    uvl = bm.loops.layers.uv[UV]

    def cone(p0, p1, r0, r1, n, mat, smooth=False):
        a = Vector(p0); b = Vector(p1); ax = (b - a).normalized()
        t = Vector((1, 0, 0)) if abs(ax.x) < 0.9 else Vector((0, 1, 0))
        u = ax.cross(t).normalized(); w = ax.cross(u).normalized()
        rs = []
        for c, r in ((a, r0), (b, r1)):
            rs.append([bm.verts.new(c + (u * math.cos(2 * math.pi * k / n) + w * math.sin(2 * math.pi * k / n)) * r) for k in range(n)])
        fs = []
        for k in range(n):
            k2 = (k + 1) % n
            fs.append(bm.faces.new([rs[0][k], rs[0][k2], rs[1][k2], rs[1][k]]))
        fs.append(bm.faces.new(list(reversed(rs[0]))))
        if r1 > 0.0005:
            fs.append(bm.faces.new(rs[1]))
        for f in fs:
            f.material_index = mat; f.smooth = smooth
            for lp in f.loops:
                lp[uvl].uv = (0.75, 0.25) if mat == 0 else (0.5, 0.5)
    for sign in (+1, -1):
        cone((0, yn[sign], zn[sign]), (0, ys_, zn[sign]), 0.0085, 0.0045, 6, 0)      # dente do nock (osso)
        cone((0, ys_ - 0.002, zn[sign] - sign * 0.0), (0, ys_ + 0.004, zn[sign]), 0.0065, 0.0035, 6, 0)
    cone((0, ys_, zn[-1]), (0, ys_, zn[1]), 0.0028, 0.0028, 4, 2)

    # --- pedra verde emissiva: facetada, engastada na frente do cabo (-Y)
    gz = 0.0
    gy0 = -0.024
    top = bm.verts.new((0, gy0 - 0.016, gz + 0.030)); bot = bm.verts.new((0, gy0 - 0.016, gz - 0.030))
    eq = [bm.verts.new((math.cos(a) * 0.017, gy0 - 0.020 - math.sin(a) * 0.014, gz)) for a in [i * math.pi / 3 + math.pi / 6 for i in range(6)]]
    for i in range(6):
        j = (i + 1) % 6
        for tri in ([top, eq[i], eq[j]], [bot, eq[j], eq[i]]):
            f = bm.faces.new(tri)
            f.material_index = 1
            for lp in f.loops:
                lp[uvl].uv = (0.5, 0.5)
    # engaste de couro/osso em volta da pedra (anel baixo)
    cone((0, gy0 + 0.004, 0.0), (0, gy0 - 0.006, 0.0), 0.027, 0.023, 8, 0)

    # --- toque do cabo: saliencia de couro (dragona) pendente nao incluida (orcamento)
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    return ob


def exportar(ob):
    os.makedirs(SAIDA, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    caminho = os.path.join(SAIDA, "Arqueiro_Arco.glb")
    bpy.ops.export_scene.gltf(filepath=caminho, export_format="GLB", use_selection=True,
                              export_animations=False, export_yup=True, export_apply=True,
                              export_materials="EXPORT", export_image_format="AUTO")
    print("EXPORTADO", caminho)


if __name__ == "__main__":
    ob = build()
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    print("TRIS", tris, "dim", tuple(round(d, 3) for d in ob.dimensions))
    exportar(ob)
