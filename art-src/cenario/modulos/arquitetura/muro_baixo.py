"""Muro baixo 3,0 x 0,6 x 1,1 m: rodapé escalonado, corpo em fiadas de blocos, cordão moldurado, merlões irregulares lascados e pilaretes de ponta."""
import bpy, math
from _pedra import cut
GLB = 'SM_Cripta_MuroBaixo'
VISTAS = {
    "frente": ((0, 5.2, 0.7), (0, 0, 0.55), 900, 600),
    "tres_quartos": ((-3.0, 3.2, 2.0), (0, 0, 0.5), 900, 700),
    "close_ameias": ((-1.2, 1.7, 1.5), (-0.4, 0, 0.9), 800, 700),
    "close_ponta": ((1.8, -1.6, 1.3), (1.2, 0, 0.6), 800, 700),
}
HEROI_X, HEROI_Y = 1.9, 1.6
W = 3.0; D = 0.6

def _sano(o):
    import bmesh
    bm = bmesh.new(); bm.from_mesh(o.data)
    ok = all(e.is_manifold for e in bm.edges) and bm.calc_volume(signed=True) > 0
    bm.free(); return ok

def cbox(L, loc, size, m, chips=None, rot=(0, 0, 0), bev=0.012):
    """Bloco lascado: cria na origem, corta (boolean EXACT só funciona limpo assim; refaz com outra seed se sair aberto), chanfra, posiciona/gira."""
    for t in range(6):
        o = L.box((0, 0, 0), size, m, bev=0)
        if not chips: break
        L.chip_corners(o, chips[0], chips[1], chips[2] + 1000 * t)
        if _sano(o): break
        L.objs.remove(o); bpy.data.objects.remove(o, do_unlink=True)
    else:
        o = L.box((0, 0, 0), size, m, bev=0)
    if bev: L.bevel_obj(o, bev, 2)
    o.rotation_euler = rot; o.location = loc
    return o

def build(L):
    sd, sc = L.stone('escura'), L.stone('clara')
    r = L.rng(7)
    # rodapé escalonado
    cbox(L, (0, 0, 0.07), (W, D, 0.14), sc, (6, 0.12, 1), bev=0.014)
    cbox(L, (0, 0, 0.19), (W - 0.09, D - 0.06, 0.1), sd, (3, 0.08, 2), bev=0.012)
    # corpo: 3 fiadas (0,24-0,75), juntas deslocadas, recuo e altura levemente variáveis
    z = 0.24; fi = 0
    for h in (0.17, 0.17, 0.17):
        x = -W / 2 + 0.06; i = 0
        while x < W / 2 - 0.09:
            w = r.uniform(0.5, 0.85)
            if fi % 2 and i == 0: w *= 0.55
            w = min(w, W / 2 - 0.06 - x)
            if w < 0.12: break
            depth = D - 0.10 + r.uniform(-0.015, 0.015)
            hh = h - 0.012 + r.uniform(-0.005, 0.005)
            ch = (r.choice((1, 2, 3)), r.uniform(0.07, 0.13), 100 + fi * 10 + i) if r.random() < 0.6 else None
            cbox(L, (x + w / 2, r.uniform(-0.008, 0.008), z + h / 2), (w - 0.014, depth, hh), sd, ch, bev=0.011)
            x += w; i += 1
        z += h; fi += 1
    # cordão (0,75-0,86)
    cbox(L, (0, 0, 0.775), (W, D - 0.02, 0.05), sc, (4, 0.08, 11), bev=0.012)
    cbox(L, (0, 0, 0.83), (W, D + 0.04, 0.06), sc, (7, 0.1, 12), bev=0.013)
    # merlões irregulares (bloco + chapéu), um quebrado
    xs = [-1.0, -0.33, 0.33, 1.0]; alt = [0.15, 0.12, 0.04, 0.16]; wid = [0.48, 0.44, 0.46, 0.44]
    for k, (cx, hh, w) in enumerate(zip(xs, alt, wid)):
        cx += r.uniform(-0.03, 0.03); tilt = r.uniform(-0.04, 0.04)
        z0 = 0.86 + hh / 2
        cbox(L, (cx, r.uniform(-0.01, 0.01), z0), (w, D - 0.14, hh), sd, (5 if k != 2 else 8, 0.14 if k != 2 else 0.2, 30 + k), rot=(0, tilt, 0), bev=0.014)
        if k != 2:
            cbox(L, (cx, 0, 0.86 + hh + 0.025), (w + 0.02, D - 0.1, 0.05), sc, (5, 0.12, 20 + k), rot=(0, tilt, 0), bev=0.014)
        else:   # quebrado: fragmentos caídos sobre o cordão
            cbox(L, (cx + 0.18, 0.07, 0.9), (0.14, 0.12, 0.07), sd, rot=(0.2, 0.3, 0.5), bev=0.012)
            cbox(L, (cx - 0.25, -0.08, 0.895), (0.1, 0.1, 0.06), sd, rot=(0.3, 0.1, 1.2), bev=0.012)
    # pilaretes de ponta
    for sx in (-1, 1):
        px = sx * (W / 2 - 0.12)
        cbox(L, (px, 0, 0.5), (0.20, D, 0.74), sc, (2, 0.06, 60 + sx), bev=0.014)
        for yy in (-1, 1):
            L.box((px, yy * (D / 2 + 0.006), 0.5), (0.1, 0.014, 0.36), sd, bev=0.004, seg=1)
        cbox(L, (px, 0, 0.9), (0.2, D + 0.02, 0.06), sc, (3, 0.08, 70 + sx), bev=0.012)
        cbox(L, (px, 0, 0.96), (0.17, D - 0.08, 0.08), sd, (3, 0.08, 72 + sx), bev=0.012)
    # entulho junto ao pé
    for (x, y, s) in ((-0.62, 0.34, 0.06), (0.75, 0.33, 0.08), (0.2, -0.33, 0.055)):
        cbox(L, (x, y, s / 2), (s * 1.4, s * 1.1, s), sd, rot=(0.1, 0.2, r.uniform(0, 3)), bev=0.01)
    L.col_box((0, 0, 0.55), (W, D, 1.1))
