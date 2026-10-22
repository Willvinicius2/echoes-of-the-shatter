"""Helpers locais de pedra (usados por pilastra.py e pedestal.py; build.py só importa lib/modulo)."""
import bpy, bmesh, math
from mathutils import Vector

def poly_loft(L, name, pts, z0, z1, sx=1.0, sy=1.0, m=None, c=(0, 0), bev=0.008, seg=2, offs=(0, 0), cap=True):
    """Prisma/tronco de polígono (pts em XY, anti-horário) entre z0 e z1; topo escalado por sx,sy ao redor de c.
    Origem do objeto no centro do bbox (para chip_corners)."""
    bm = bmesh.new()
    lo = [bm.verts.new((x, y, z0)) for x, y in pts]
    hi = [bm.verts.new((c[0] + (x - c[0]) * sx + offs[0], c[1] + (y - c[1]) * sy + offs[1], z1)) for x, y in pts]
    n = len(pts)
    bm.faces.new(lo[::-1]); bm.faces.new(hi)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return finish(L, name, bm, m, bev, seg)

def finish(L, name, bm, m, bev=0.008, seg=2):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    mn = Vector((min(v.co.x for v in me.vertices), min(v.co.y for v in me.vertices), min(v.co.z for v in me.vertices)))
    mx = Vector((max(v.co.x for v in me.vertices), max(v.co.y for v in me.vertices), max(v.co.z for v in me.vertices)))
    ctr = (mn + mx) / 2
    for v in me.vertices: v.co -= ctr
    o.location = ctr
    L.add(o, m)
    if bev: L.bevel_obj(o, bev, seg)
    return o

def rect(w, d, ch=0.0):
    """Retângulo w x d centrado, com cantos chanfrados (ch)."""
    x, y = w / 2, d / 2
    if ch <= 0: return [(-x, -y), (x, -y), (x, y), (-x, y)]
    return [(-x + ch, -y), (x - ch, -y), (x, -y + ch), (x, y - ch), (x - ch, y), (-x + ch, y), (-x, y - ch), (-x, -y + ch)]

def cut(o, loc, size, rot=(0, 0, 0)):
    """Entalhe real: boolean DIFFERENCE com caixa girada."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    c = bpy.context.object; c.scale = size; bpy.ops.object.transform_apply(scale=True)
    mod = o.modifiers.new("cut", 'BOOLEAN'); mod.operation = 'DIFFERENCE'; mod.object = c; mod.solver = 'EXACT'
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier="cut")
    bpy.data.objects.remove(c, do_unlink=True)

def crack(o, p0, p1, w=0.018, depth=0.04, seed=1, axis_y=1, n=6):
    """Rachadura em zigue-zague numa face (axis_y=+1 frente +Y, -1 trás, 0 = face X); p0->p1 em (u,z)."""
    import random
    r = random.Random(seed)
    pts = [(p0[0] + (p1[0] - p0[0]) * t / n + (r.uniform(-0.03, 0.03) if 0 < t < n else 0),
            p0[1] + (p1[1] - p0[1]) * t / n) for t in range(n + 1)]
    fy = o.location.y + axis_y * o.dimensions.y / 2
    for a, b in zip(pts, pts[1:]):
        du, dz = b[0] - a[0], b[1] - a[1]; ln = math.hypot(du, dz) + w
        ang = math.atan2(du, dz)
        cut(o, (o.location.x + (a[0] + b[0]) / 2, fy, (a[1] + b[1]) / 2), (w, depth * 2, ln), rot=(0, ang, 0))

def profile_loft(L, name, levels, m=None, bev=0.006, seg=1, offs=(0, 0)):
    """Moldura por perfil: levels = [(z, w, d, ch), ...] (cada anel é um retângulo chanfrado de 8 pontos)."""
    bm = bmesh.new(); rings = []
    for z, w, d, ch in levels:
        rings.append([bm.verts.new((x + offs[0], y + offs[1], z)) for x, y in rect(w, d, ch)])
    n = 8
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return finish(L, name, bm, m, bev, seg)

def curve_levels(z0, z1, a, b, steps=6, kind="ovolo", ch=0.04):
    """a=(w,d) embaixo, b=(w,d) em cima. ovolo = convexo (cresce rápido), cove = côncavo (escócia)."""
    out = []
    for i in range(steps + 1):
        t = i / steps
        s = math.sin(t * math.pi / 2) if kind == "ovolo" else 1 - math.cos(t * math.pi / 2)
        out.append((z0 + (z1 - z0) * t, a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s, ch))
    return out

def diamond(L, name, c, nx, ny, half=0.035, thick=0.012, m=None, bev=0.003):
    """Losango em relevo: centro c, face voltada para (nx,ny) horizontal; vértices explícitos."""
    bm = bmesh.new()
    tx, ty = -ny, nx   # tangente horizontal
    def P(u, v, w): return (c[0] + tx * u + nx * w, c[1] + ty * u + ny * w, c[2] + v)
    base = [(half, 0), (0, half), (-half, 0), (0, -half)]
    back = [bm.verts.new(P(u, v, 0)) for u, v in base]
    front = [bm.verts.new(P(u * 0.7, v * 0.7, thick)) for u, v in base]
    bm.faces.new(back[::-1]); bm.faces.new(front)
    for i in range(4):
        j = (i + 1) % 4; bm.faces.new((back[i], back[j], front[j], front[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return finish(L, name, bm, m, bev, 1)

def fiada(L, hx, hy, z0, h, prof, wmin, wmax, seed, m, mdark=None, bev=0.016, chip=0.45, core=True):
    """Anel de blocos de pedra (frente +Y e laterais; atrás encosta na parede): larguras variadas, desalinho, bisel e lascas."""
    import random
    r = random.Random(seed)
    objs = []
    def bloco(cx, cy, sx, sy, sz):
        sx -= 0.012; sy -= 0.0
        cz = z0 + sz / 2 + r.uniform(0, 0.004)
        o = L.box((cx + r.uniform(-0.004, 0.004), cy + r.uniform(-0.008, 0.008), cz), (sx, sy, sz * r.uniform(0.97, 1.0)),
                  mdark if (mdark and r.random() < 0.15) else m, rot=(0, 0, r.uniform(-0.01, 0.01)), bev=bev, seg=2)
        if r.random() < chip:
            L.chip_corners(o, r.choice((1, 2)), 0.3 * min(sx, sy, sz) * r.uniform(0.7, 1.1), r.randint(0, 9999))
        objs.append(o)
    # frente
    u = -hx
    while u < hx - 0.05:
        w = min(r.uniform(wmin, wmax), hx - u)
        if hx - u - w < wmin * 0.5: w = hx - u
        bloco(u + w / 2, hy - prof / 2, w, prof, h); u += w
    # laterais (da frente até a parede)
    for sx in (-1, 1):
        v = hy - prof
        while v > -hy + 0.05:
            w = min(r.uniform(wmin, wmax), v + hy)
            if v - w < -hy + wmin * 0.5: w = v + hy
            bloco(sx * (hx - prof / 2), v - w / 2, prof, w, h); v -= w
    if core:
        L.box((0, 0, z0 + h / 2), (2 * (hx - prof * 0.6), 2 * (hy - prof * 0.6), h), mdark or m, bev=0)
    return objs

def garantir_material(L, fallback):
    """Boolean/bevel podem perder o slot: todo objeto sai com exatamente 1 material (o que tinha, senão fallback)."""
    for o in L.objs:
        ms = [m for m in o.data.materials if m]
        m = ms[0] if ms else fallback
        o.data.materials.clear(); o.data.materials.append(m)
        for p in o.data.polygons: p.material_index = 0
