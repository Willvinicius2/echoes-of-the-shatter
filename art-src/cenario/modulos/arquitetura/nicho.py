"""SM_Cripta_Nicho: parede de 3,0 x 1,2 x 5,4 m com nicho arqueado (1,7 x 3,4 m, 0,7 m de fundo) na face +Y.
Camada de trás (y -0,6..-0,1) em cantaria corrida; camada da frente (y -0,1..0,6) em blocos cortados pelo vão
(boolean). Arco de aduelas claras, batentes, ressalto de imposta, pedestal em degraus, prateleiras de vela,
rodapé e cornija iguais aos da parede reta.
COLISÃO (decisão): caixas fiéis à escavação: pilar esquerdo, pilar direito, fundo, verga (z>=3,4) e o pedestal
(que já fecha o nicho a partir de y=-0,05). O herói entra no máximo ~0,05 m de forma útil; nada de caixa extra na boca."""
import bpy, bmesh, math
from mathutils import Vector

GLB = "SM_Cripta_Nicho"
HEROI_X, HEROI_Y = -2.0, 1.6
VISTAS = {
    "frente": ((0, 11.5, 2.9), (0, 0, 2.7), 700, 900),
    "tres_quartos": ((-6.2, 7.0, 5.0), (0, 0, 2.3), 800, 900),
    "close": ((-1.6, 3.0, 1.6), (0, 0.2, 1.6), 800, 800),
    "esq": ((-2.6, 2.2, 2.7), (-1.3, 0.3, 2.5), 800, 800),
}

HW = 0.85            # meia largura do vão
SPR = 2.55           # linha de nascença do arco
FY0, FY1 = -0.10, 0.60   # camada da frente
GAP = 0.012

def build(L):
    r = L.rng(404)
    esc, cla, fer = L.stone("escura"), L.stone("clara"), L.stone("ferro")
    X = L.SEG / 2

    CH = [0, 0]
    def chip_corners(o, n, size, seed):
        """Lascas reais nos cantos da caixa envolvente (centro lido dos vértices: aqui a origem fica em 0)."""
        rr = L.rng(seed)
        vs = [v.co for v in o.data.vertices]
        lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs))); hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
        for i in range(n):
            p = Vector((rr.choice((lo.x, hi.x)), rr.choice((lo.y, hi.y)), rr.choice((lo.z, hi.z))))
            sz = size * rr.uniform(0.6, 1.4)
            bpy.ops.mesh.primitive_cube_add(size=1, location=p, rotation=(rr.uniform(0, 1.5), rr.uniform(0, 1.5), rr.uniform(0, 1.5)))
            c = bpy.context.object; c.scale = (sz, sz * rr.uniform(0.7, 1.3), sz * rr.uniform(0.7, 1.3)); bpy.ops.object.transform_apply(scale=True)
            m = o.modifiers.new("chip", 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = c; m.solver = 'EXACT'
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.modifier_apply(modifier="chip"); bpy.data.objects.remove(c, do_unlink=True)
    def chip(o, n, size, seed):
        """Lasca com checagem de volume: se o boolean estragar o bloco, refaz sem lasca."""
        me0 = o.data.copy()
        bm = bmesh.new(); bm.from_mesh(me0); v0 = bm.calc_volume(); bm.free()
        chip_corners(o, n, size, seed)
        bm = bmesh.new(); bm.from_mesh(o.data); v1 = abs(bm.calc_volume()); manifold = all(e.is_manifold for e in bm.edges); bm.free()
        if not manifold or v1 < v0 * 0.8 or v1 > v0 * 1.02:
            o.data = me0; CH[1] += 1
        else: bpy.data.meshes.remove(me0); CH[0] += 1

    def rough(o, amp, rr, cuts=2):
        """Pedra talhada a mão: subdivide e desloca vértices (faces levemente onduladas), preservando as pontas x=+-X."""
        bm = bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
        for v in bm.verts:
            if abs(abs(v.co.x) - X) < 1e-3: v.co.y += rr.uniform(-amp, amp) * 0.5; continue
            v.co += Vector((rr.uniform(-amp, amp) * 0.4, rr.uniform(-amp, amp), rr.uniform(-amp, amp) * 0.4))
        bm.to_mesh(o.data); bm.free()

    def cut(o, cutters):
        for c in cutters:
            m = o.modifiers.new("cut", 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = c; m.solver = 'EXACT'
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.modifier_apply(modifier="cut")
        if len(o.data.polygons) == 0:
            if o in L.objs: L.objs.remove(o)
            bpy.data.objects.remove(o, do_unlink=True); return None
        return o

    # ---- cortadores do vão (caixa + cilindro, raio um pouco menor que as aduelas para as pedras "entrarem" por baixo)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0.25, SPR / 2 - 0.05)); cbox = bpy.context.object
    cbox.scale = (2 * (HW + 0.25), 1.2, SPR + 0.1); bpy.ops.object.transform_apply(scale=True)
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=HW + 0.25, depth=1.2, location=(0, 0.25, SPR), rotation=(math.pi / 2, 0, 0)); ccyl = bpy.context.object
    cutters = [cbox, ccyl]
    def inside_bbox(x0, x1, z0, z1):
        return not (x1 < -(HW + 0.25) or x0 > HW + 0.25 or z1 < 0 or z0 > SPR + HW + 0.25)
    def fully_inside(x0, x1, z0, z1):
        return x0 >= -(HW + 0.25) and x1 <= HW + 0.25 and z1 <= SPR

    # ---- fiadas
    z_edges = [L.PLINTH]
    for h in (0.60, 0.50, 0.70, 0.55, 0.62, 0.50, 0.78): z_edges.append(z_edges[-1] + h)
    assert abs(z_edges[-1] - L.CORNICE_Z) < 1e-6
    def divisions(rr, lo, hi, a, b):
        xs = [lo]
        while xs[-1] < hi - 0.01:
            xs.append(min(hi, xs[-1] + rr.uniform(a, b)))
        if hi - xs[-2] < 0.3 and len(xs) > 2: xs.pop(-2)
        return xs
    def course_blocks(rr, y0, y1, ybump, front):
        n = 0
        for i in range(len(z_edges) - 1):
            z0, z1 = z_edges[i], z_edges[i + 1]
            xs = divisions(rr, -X, X, 0.55, 1.0) if i % 2 == 0 else divisions(rr, -X + rr.uniform(-0.0, 0.0), X, 0.5, 0.95)
            if i % 2: xs = [-X] + [x for x in divisions(rr, -X + 0.45, X, 0.55, 1.0)][0:] if False else xs
            for j in range(len(xs) - 1):
                a = xs[j] + (GAP / 2 if j > 0 else 0); b = xs[j + 1] - (GAP / 2 if j < len(xs) - 2 else 0)
                za, zb = z0 + GAP / 2, z1 - GAP / 2
                if front and fully_inside(a, b, za, zb): continue
                dy = rr.uniform(-ybump, ybump)
                ya, yb = y0 + (rr.uniform(0, 0.02) if not front else 0), y1 + dy
                sz = (b - a, yb - ya, zb - za)
                o = L.box(((a + b) / 2, (ya + yb) / 2, (za + zb) / 2), sz, esc, rot=(rr.uniform(-.006, .006), rr.uniform(-.006, .006), rr.uniform(-.008, .008)), bev=0)
                rough(o, 0.017 if front else 0.01, rr, 3 if front else 1); L.bevel_obj(o, 0.014, 2, 35)
                if front and inside_bbox(a, b, za, zb): o = cut(o, cutters)
                if o is None: continue
                n += 1
                if front and rr.random() < 0.6: chip(o, rr.choice((1, 2, 3)), rr.choice((0.10, 0.14, 0.2)), rr.randint(0, 99999))
        return n
    # fiadas deslocadas para o fundo ter juntas diferentes da frente
    course_blocks(L.rng(11), -L.WALL_T / 2 + 0.01, FY0 + 0.02, 0.012, False)
    course_blocks(L.rng(23), FY0, FY1 - 0.02, 0.03, True)

    # ---- aduelas do arco (pedra clara)
    n = 11; cz = SPR
    b = [math.pi * k / n + (r.uniform(-0.03, 0.03) if 0 < k < n else 0) for k in range(n + 1)]
    for k in range(n):
        a0, a1 = b[k] + 0.006, b[k + 1] - 0.006
        key = k == n // 2
        ro = 1.40 if key else 1.18 + (0.07 if k % 2 else 0.0) + r.uniform(0, 0.03)
        ri = HW
        yf = 0.69 if key else 0.63 + r.uniform(0, 0.03)
        yb = FY0
        bm = bmesh.new()
        for ang, rad in ((a0, ri), (a1, ri), (a0, ro), (a1, ro)):
            for y in (yb, yf):
                bm.verts.new((rad * math.cos(ang), y, cz + rad * math.sin(ang)))
        bmesh.ops.convex_hull(bm, input=bm.verts[:])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        o = L.new_obj(f"aduela{k}", bm, cla)
        L.bevel_obj(o, 0.016, 2, 30)
        o.location.x = 0   # origem permanece, geometria já em coordenadas de mundo
        chip(o, 2, 0.06, 500 + k)
    # moldura baixa acima do arco (cordão) em pedra clara, partida em pedaços
    for k in range(7):
        a0 = 0.15 + (math.pi - 0.3) * k / 7 + 0.01; a1 = 0.15 + (math.pi - 0.3) * (k + 1) / 7 - 0.01; rm = 1.34
        bm = bmesh.new()
        for ang, rad in ((a0, 1.27), (a1, 1.27), (a0, rm), (a1, rm)):
            for y in (FY1 - 0.02, 0.66):
                bm.verts.new((rad * math.cos(ang), y, cz + rad * math.sin(ang)))
        bmesh.ops.convex_hull(bm, input=bm.verts[:]); bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        if k == 3: pass
        o = L.new_obj(f"cordao{k}", bm, cla); L.bevel_obj(o, 0.012, 2, 30)

    # ---- batentes (pedras claras empilhadas dos dois lados) e imposta
    for side in (-1, 1):
        z = 0.0; i = 0
        while z < SPR - 0.05:
            h = r.choice((0.55, 0.62, 0.48, 0.7)); h = min(h, SPR - z - 0.01) if SPR - z < 0.85 else h
            w = (0.34 if i % 2 == 0 else 0.30) + r.uniform(-0.01, 0.012)
            x0 = HW; x1 = HW + w
            yb = FY0; yf = 0.62 + r.uniform(0, 0.03) + (0.02 if i % 2 == 0 else 0)
            o = L.box((side * (x0 + x1) / 2, (yb + yf) / 2, z + h / 2 - GAP / 2 + (0.0 if z else 0.0)), (w - GAP, yf - yb, h - GAP), cla, bev=0.016, seg=2,
                      rot=(0, 0, r.uniform(-.006, .006)))
            chip(o, 2, 0.06, 700 + i + side * 13)
            z += h; i += 1
        # imposta: ressalto que marca a nascença do arco
        o = L.box((side * (HW + 0.2), 0.27, SPR + 0.05), (0.42, 0.86, 0.1), cla, bev=0.016); chip(o, 2, 0.05, 900 + side)
        L.box((side * (HW + 0.2), 0.27, SPR - 0.025), (0.34, 0.76, 0.05), cla, bev=0.01)
    # ---- piso do nicho, soleira e pedestal em degraus
    L.box((0, 0.25, 0.05), (2 * HW + 0.1, 0.86, 0.1), cla, bev=0.012)
    steps = [((0.0, 0.25, 0.2 / 2 + 0.1), (1.56, 0.80, 0.2)), ((0.0, 0.26, 0.2 + 0.1 + 0.09), (1.30, 0.66, 0.18)), ((0.0, 0.27, 0.38 + 0.1 + 0.035), (1.06, 0.52, 0.07))]
    for i, (loc, sz) in enumerate(steps):
        o = L.box(loc, sz, cla, bev=0.018, rot=(0, 0, r.uniform(-.01, .01))); chip(o, 3, 0.07, 1100 + i)
    # prateleiras de vela: duas mísulas nas laterais interiores do nicho + ressalto no degrau
    for side in (-1, 1):
        for zz, dep in ((1.05, 0.34), (1.55, 0.28)):
            o = L.box((side * (HW - 0.07), 0.38, zz), (0.16, dep, 0.07), cla, bev=0.012); chip(o, 1, 0.04, 1300 + int(zz * 10) + side)
            L.box((side * (HW - 0.06), 0.38, zz - 0.11), (0.10, dep * 0.8, 0.14), cla, bev=0.01, rot=(0, 0, 0))
    # velas: tocos de cera em degraus e mísulas (pedra clara serve de cera; o Godot pode trocar o material)
    rc = L.rng(5)
    for (cx, cy, cz0) in ((-0.62, 0.50, 0.38 + 0.1 + 0.0), (-0.50, 0.55, 0.30), (0.66, 0.52, 0.30), (0.52, 0.58, 0.30), (0.72, 0.44, 0.30), (-0.8, 0.40, 1.085), (0.8, 0.38, 1.585), (0.8, 0.46, 1.085)):
        h = rc.uniform(0.1, 0.26); L.cyl((cx, cy, cz0 + h / 2), 0.028 + rc.uniform(0, .01), h, cla, sides=8, bev=0.004)
        L.cyl((cx, cy, cz0 + h + 0.012), 0.006, 0.03, fer, sides=5)
    # ---- rodapé (igual da parede reta): fora do vão; camadas escalonadas de espessura total
    for (xa, xb) in ((-X, -HW - 0.34), (HW + 0.34, X)):
        parts = divisions(L.rng(77 + int(xa * 10)), xa, xb, 0.5, 0.85)
        for j in range(len(parts) - 1):
            a = parts[j] + (GAP / 2 if j else 0); bb = parts[j + 1] - (GAP / 2 if j < len(parts) - 2 else 0)
            w = bb - a; cx = (a + bb) / 2
            o = L.box((cx, 0, 0.15), (w, L.WALL_T + 0.14 + r.uniform(-.01, .01), 0.3), esc, bev=0.02, seg=2)
            L.box((cx, 0, 0.375), (w, L.WALL_T + 0.07, 0.15), esc, bev=0.016)
            if j % 2 == 0: chip(o, 2, 0.07, 1500 + j + int(xa * 7))
    # entre o rodapé e o batente a base do batente usa pedra clara (pés)
    for side in (-1, 1):
        L.box((side * (HW + 0.2 + 0.07), 0.66, 0.11), (0.62, 0.12, 0.22), cla, bev=0.016)
    # ---- cornija em camadas (z 4,7..5,4), os dois lados
    T = L.WALL_T
    L.box((0, 0, 4.775), (L.SEG, T + 0.08, 0.15), cla, bev=0.015)
    L.box((0, 0, 4.935), (L.SEG, T + 0.18, 0.17), esc, bev=0.015)
    for sy in (1, -1):
        nd = 21
        for k in range(nd):
            xx = -X + (k + 0.5) * L.SEG / nd
            L.box((xx, sy * (T / 2 + 0.08), 5.115), (L.SEG / nd * 0.62, 0.14, 0.13 + r.uniform(-0.01, 0.01)), esc, bev=0.01, seg=1)
    L.box((0, 0, 5.115), (L.SEG, T + 0.1, 0.13), esc, bev=0.01)
    L.box((0, 0, 5.205), (L.SEG, T + 0.28, 0.09), cla, bev=0.012)
    o = L.box((0, 0, 5.325), (L.SEG, T + 0.36, 0.15), cla, bev=0.02); chip(o, 4, 0.08, 31)
    # lajes da cornija partidas por juntas finas
    for k in (-0.55, 0.7):
        for sy in (1, -1):
            L.box((k, sy * (L.WALL_T / 2 + 0.18), 5.35), (0.012, 0.06, 0.16), fer, bev=0)
    # ---- rachaduras (tiras escuras em zigue-zague) e relevos pequenos
    def crack(x, z, ang, ln, seed, y=FY1):
        rr = L.rng(seed); px, pz = x, z
        for i in range(int(ln / 0.1)):
            a = ang + rr.uniform(-0.5, 0.5); l = rr.uniform(0.07, 0.13)
            L.box((px + math.cos(a) * l / 2, y - 0.004, pz + math.sin(a) * l / 2), (l, 0.012, 0.012 + rr.random() * 0.006), fer, rot=(0, -a, 0), bev=0)
            px += math.cos(a) * l; pz += math.sin(a) * l
    crack(-1.40, 3.9, -1.2, 0.6, 1); crack(1.2, 4.1, -1.6, 0.7, 2); crack(-1.25, 1.1, 1.3, 0.5, 3); crack(1.35, 0.9, 1.5, 0.4, 4); crack(-0.45, 4.15, 0.3, 0.4, 5)
    # losango entalhado nos pilares (como no conceito)
    for sx in (-1, 1):
        px = sx * 1.32
        L.box((px, FY1 + 0.012, 3.3), (0.17, 0.03, 0.17), cla, rot=(0, math.radians(45), 0), bev=0.008)
        L.box((px, FY1 + 0.03, 3.3), (0.09, 0.03, 0.09), esc, rot=(0, math.radians(45), 0), bev=0.006)
    # ---- colisão
    L.col_box((-(HW + X) / 2 - 0.0, 0, L.WALL_H / 2), (X - HW, L.WALL_T, L.WALL_H))
    L.col_box(((HW + X) / 2, 0, L.WALL_H / 2), (X - HW, L.WALL_T, L.WALL_H))
    L.col_box((0, (-L.WALL_T / 2 + FY0) / 2, L.WALL_H / 2), (2 * HW, FY0 + L.WALL_T / 2, L.WALL_H))
    L.col_box((0, 0, (3.4 + L.WALL_H) / 2), (2 * HW, L.WALL_T, L.WALL_H - 3.4))
    L.col_box((0, 0.25, 0.275), (1.56, 0.80, 0.55))
    print('lascas ok/falha', CH)
    # encaixe exato: nada passa de x=+-1,5 nem de z=0..5,4 (rotações e lascas podem sobrar milímetros)
    for o in L.objs:
        for v in o.data.vertices:
            v.co.x = max(-X, min(X, v.co.x)); v.co.z = max(0.0, min(L.WALL_H, v.co.z))
    for c in cutters: bpy.data.objects.remove(c, do_unlink=True)
