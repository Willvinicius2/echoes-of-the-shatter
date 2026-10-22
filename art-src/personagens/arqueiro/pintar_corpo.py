"""Repinta a textura do corpo base do Arqueiro (roupa basica: tunica de linho, calca de pano, botinas).

Mantem o rosto e o cabelo da textura original (malha Body_Head) e reescreve so os texels de
Body_Arms, Body_Hands, Body_Torso, Body_Legs e Body_Feet, pintando por posicao 3D (rasteriza cada triangulo no UV).
Uso: blender -b -P pintar_corpo.py -- <SK_Archer_Body.fbx> <T_Archer_Body_BC.png (original)> <saida.png>
Semente fixa: mesma entrada, mesma saida.
"""
import bpy, sys, numpy as np
from PIL import Image

fbx, tex_in, tex_out = sys.argv[sys.argv.index("--") + 1:][:3]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx)
S = 512
img = np.asarray(Image.open(tex_in).convert("RGB").resize((S, S), Image.BICUBIC), dtype=np.float32) / 255.0
out = img.copy()
rng = np.random.default_rng(7)


def ruido(sc, n=S):
    g = rng.random((n // sc + 2, n // sc + 2)).astype(np.float32)
    im = Image.fromarray((g * 255).astype(np.uint8)).resize((n, n), Image.BICUBIC)
    return np.asarray(im, dtype=np.float32) / 255.0


N1, N2, N3 = ruido(4), ruido(16), ruido(64)
yy, xx = np.mgrid[0:S, 0:S]
trama = 0.5 + 0.25 * np.sin(xx * 1.9) * np.sin(yy * 1.9)  # tecido
PELE = np.array([0.89, 0.69, 0.55], np.float32)
LINHO = np.array([0.74, 0.69, 0.56], np.float32)
LINHO_ESC = np.array([0.50, 0.45, 0.36], np.float32)
PANO = np.array([0.33, 0.31, 0.27], np.float32)      # calca
COURO = np.array([0.30, 0.19, 0.11], np.float32)
COURO_CL = np.array([0.45, 0.30, 0.18], np.float32)
FAIXA = np.array([0.52, 0.40, 0.25], np.float32)     # ataduras / punhos


def cor(nome, p, ty, tx):
    """p = (x, y, z) mundo do ponto; devolve rgb. ty, tx = indices do texel (para ruido)."""
    x, y, z = p
    n = N1[ty, tx] * 0.5 + N2[ty, tx] * 0.3 + N3[ty, tx] * 0.2
    t = trama[ty, tx]
    if nome in ("Body_Arms", "Body_Hands"):
        ax = abs(x)
        if ax < (0.355 if nome == "Body_Hands" else 9):      # manga ate o antebraco
            base = LINHO.copy()
            if ax > 0.325:                                     # punho dobrado
                base = FAIXA * (0.85 + 0.3 * n)
            else:
                base = base * (0.82 + 0.22 * n) * (0.9 + 0.2 * t)
            return base
        return PELE * (0.9 + 0.18 * n)
    if nome == "Body_Torso":
        if z > 1.075:
            return PELE * (0.92 + 0.12 * n)                    # pescoco
        base = LINHO * (0.8 + 0.25 * n) * (0.9 + 0.2 * t)
        if z < 0.745:                                          # barra
            base = LINHO_ESC * (0.85 + 0.25 * n)
        if 1.04 < z <= 1.075:
            base = LINHO_ESC * (0.9 + 0.2 * n)                 # gola
        return base
    if nome == "Body_Legs":
        base = PANO * (0.8 + 0.3 * n) * (0.9 + 0.2 * t)
        if z < 0.34:                                           # ataduras da canela
            base = FAIXA * (0.7 + 0.4 * n) * (0.85 + 0.3 * (0.5 + 0.5 * np.sin(z * 120)))
        if z > 0.70:
            base = PANO * 0.8 * (0.85 + 0.2 * n)
        return base
    if nome == "Body_Feet":
        base = COURO * (0.8 + 0.4 * n)
        if z < 0.035:
            base = COURO_CL * 0.55
        elif z > 0.19:
            base = FAIXA * (0.6 + 0.3 * n)
        return base
    return None


for ob in bpy.data.objects:
    if ob.type != "MESH" or ob.name == "Body_Head":
        continue
    me = ob.data
    uv = me.uv_layers.active.data
    mw = ob.matrix_world
    me.calc_loop_triangles()
    for tri in me.loop_triangles:
        uvs = np.array([[uv[l].uv[0] * S, (1 - uv[l].uv[1]) * S] for l in tri.loops])
        ps = np.array([tuple(mw @ me.vertices[v].co) for v in tri.vertices])
        x0, y0 = np.floor(uvs.min(0)).astype(int); x1, y1 = np.ceil(uvs.max(0)).astype(int)
        x0 = max(x0 - 1, 0); y0 = max(y0 - 1, 0); x1 = min(x1 + 1, S - 1); y1 = min(y1 + 1, S - 1)
        a, b, c = uvs
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-9:
            continue
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                px, py = tx + 0.5, ty + 0.5
                w0 = ((b[1] - c[1]) * (px - c[0]) + (c[0] - b[0]) * (py - c[1])) / den
                w1 = ((c[1] - a[1]) * (px - c[0]) + (a[0] - c[0]) * (py - c[1])) / den
                w2 = 1 - w0 - w1
                if min(w0, w1, w2) < -0.08:                     # margem contra costura
                    continue
                w = np.clip([w0, w1, w2], 0, 1); w /= w.sum()
                p = w @ ps
                r = cor(ob.name, p, ty, tx)
                if r is not None:
                    out[ty, tx] = np.clip(r, 0, 1)
Image.fromarray((out * 255).astype(np.uint8)).save(tex_out)
print("salvo", tex_out)
