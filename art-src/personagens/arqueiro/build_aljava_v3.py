"""Arqueiro_Aljava*.glb v3: reaproveita corpo e flechas de build_aljava_v2.py e troca:
- alca (bandoleira): curva suave com 8 subdivisoes por trecho, secao arredondada (bisel), mais larga e grossa,
  caindo do ombro ao quadril, com duas fivelas biseladas em latao e rebites nas pontas;
- variante rara (ARQ_ALJ_RAR=2): couro escuro, detalhes dourados, runas luminosas (mapa de emissao) e penas
  violeta e grafite; o incomum (1) tem cintas de latao; o comum (0) e a base.
Saidas: Arqueiro_Aljava.glb (comum), Arqueiro_Aljava_incomum.glb, Arqueiro_Aljava_rara.glb.
Rodar: blender -b --factory-startup -P build_aljava_v3.py   (TEMP/TMP no disco D; ARQ_SAIDA para testes)
"""
import os, sys, math
import bpy
import numpy as np
from mathutils import Vector, Matrix

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import build_aljava as B
import build_aljava_v2 as V2

RAR = int(os.environ.get("ARQ_ALJ_RAR", "0"))
NOME = {0: "Arqueiro_Aljava.glb", 1: "Arqueiro_Aljava_incomum.glb", 2: "Arqueiro_Aljava_rara.glb"}[RAR]
SUB = 8                       # subdivisoes por trecho da curva da alca
HW, HT, RB = 0.026, 0.0055, 0.0030   # meia largura, meia espessura e raio do bisel da fita
FIVELAS = (0.35, 0.80)        # posicao (fracao da curva) das duas fivelas


def cr(p0, p1, p2, p3, t):
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                  + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)


def curva_alca():
    pts = [Vector(p) for p in B.STRAP]
    P = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        for s in range(SUB):
            out.append(cr(P[i - 1], P[i], P[i + 1], P[i + 2], s / SUB))
    out.append(pts[-1])
    return out


def referencial(curve, i):
    a = curve[max(0, i - 1)]; b = curve[min(len(curve) - 1, i + 1)]
    t = (b - a).normalized()
    side = t.cross(Vector((0, 0, 1)))
    if side.length < 0.2:
        side = t.cross(Vector((1, 0, 0)))
    side = side.normalized()
    up = side.cross(t).normalized()
    return t, side, up


def perfil(p, side, up):
    """secao da fita: retangulo com cantos arredondados (8 vertices)."""
    out = []
    for sx, sy, angs in ((1, 1, (0, 90)), (-1, 1, (90, 180)), (-1, -1, (180, 270)), (1, -1, (270, 360))):
        for ang in angs:
            c = math.radians(ang)
            out.append(p + side * (sx * (HW - RB) + RB * math.cos(c)) + up * (sy * (HT - RB) + RB * math.sin(c)))
    return out


def alca(M):
    curve = curva_alca()
    rings = []
    for i, p in enumerate(curve):
        t, side, up = referencial(curve, i)
        rings.append(perfil(p, side, up))
    M.ring_tube(rings, "B", smooth=True, cap_top=True, cap_bot=True)
    # fivelas biseladas: placa em latao com barra de pino
    for f in FIVELAS:
        i = int(f * (len(curve) - 1))
        t, side, up = referencial(curve, i)
        rot = Matrix([side, up, t]).transposed()
        p = curve[i]
        M.box(p + up * (HT + 0.0014), (0.032, 0.0028, 0.024), "Dl", rot=rot, bevel=0.0019)
        M.box(p + up * (HT + 0.0032), (0.036, 0.0020, 0.0022), "Dl", rot=rot, bevel=0.0008)
    # rebites nas pontas da alca
    if RAR >= 1:
        for j in (0, len(curve) - 1):
            t, side, up = referencial(curve, j)
            M.cone(curve[j] - t * 0.001, curve[j] + t * 0.0045, 0.0052, 0.0052, 8, "Dl", cap0=True, cap1=True)


# ------------------------------------------------------------------ variante rara
def regiao(reg):
    u0, u1, v0, v1 = B.REG[reg]
    N = B.N
    return slice(int(v0 * N), int(v1 * N)), slice(int(u0 * N), int(u1 * N))


def pintar_rara(img_bc):
    N = B.N
    buf = np.array(img_bc.pixels[:], dtype=np.float32).reshape(N, N, 4)
    for reg in ("A", "B"):                       # couro escuro
        rs, cs = regiao(reg)
        buf[rs, cs, :3] *= 0.55
    rs, cs = regiao("Dl"); buf[rs, cs, :3] = (0.86, 0.64, 0.24)   # latao dourado
    rs, cs = regiao("Cg"); buf[rs, cs, :3] = (0.36, 0.14, 0.52)   # penas violeta
    rs, cs = regiao("Cm"); buf[rs, cs, :3] = (0.16, 0.17, 0.21)   # penas grafite
    img_bc.pixels.foreach_set(buf.ravel())
    img_bc.update()


def _linha(img, x0, y0, x1, y1, cor):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for k in range(n):
        x = int(round(x0 + (x1 - x0) * k / max(1, n - 1))); y = int(round(y0 + (y1 - y0) * k / max(1, n - 1)))
        img[y, x, :3] = cor


def emissao_rara():
    """mapa de emissao: runas douradas na aba de couro (regiao A)."""
    N = B.N
    em = np.zeros((N, N, 4), np.float32); em[..., 3] = 1.0
    rs, cs = regiao("A")
    cor = (1.0, 0.72, 0.28)
    r0, r1 = rs.start, rs.stop; c0, c1 = cs.start, cs.stop
    gl = 26
    for k in range(5):
        cx = int(c0 + (c1 - c0) * (k + 0.5) / 5)
        cy = int(r0 + (r1 - r0) * 0.5)
        _linha(em, cx, cy - gl // 2, cx, cy + gl // 2, cor)
        _linha(em, cx - gl // 4, cy + gl // 4, cx, cy - gl // 4, cor)
        _linha(em, cx + gl // 4, cy + gl // 4, cx, cy - gl // 4, cor)
        if k % 2 == 0:
            _linha(em, cx - gl // 3, cy, cx + gl // 3, cy, cor)
    img = bpy.data.images.new("M_Arqueiro_Aljava_runas", N, N, alpha=True)
    img.pixels.foreach_set(em.ravel()); img.update()
    return img


# ------------------------------------------------------------------ montagem
def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    img_bc, img_n = B.make_images()
    mat = B.A.mk_mat("M_Arqueiro_Aljava", img_bc, img_n, rough=0.78)
    mat.use_backface_culling = False
    if RAR == 2:
        pintar_rara(img_bc)
        nt = mat.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = emissao_rara()
        nt.links.new(t.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.0
    M = B.Mesh()
    V2.body(M)
    B.build_pouch(M)
    alca(M)
    V2.arrows(M)
    return B.finalize(M, mat)


def exportar(ob):
    os.makedirs(B.SAIDA, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    caminho = os.path.join(B.SAIDA, NOME)
    bpy.ops.export_scene.gltf(filepath=caminho, export_format="GLB", use_selection=True, export_animations=False,
                              export_yup=True, export_apply=True, export_materials="EXPORT", export_image_format="AUTO")
    print("EXPORTADO", caminho)


if __name__ == "__main__":
    ob = build()
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    print("TRIS", tris, "dim", tuple(round(d, 3) for d in ob.dimensions), "RAR", RAR)
    exportar(ob)
