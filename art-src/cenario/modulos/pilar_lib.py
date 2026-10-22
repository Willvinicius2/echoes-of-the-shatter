"""Biblioteca compartilhada do pilar da Cripta (blocos lascados, arco ogival, loft, render de conferência).
Cada parte do pilar (pilar_base.py, pilar_fuste.py, pilar_nicho.py) importa isto e só chama funções daqui."""
import bpy, bmesh, math, sys, os, random
from mathutils import Vector, Matrix, noise

rnd = random.Random(11)
objs = []
MAT = {}


def mat(name, color, metal=0.0, rough=0.85):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metal; b.inputs["Roughness"].default_value = rough
    return m


def reset(seed=11):
    """Limpa a cena e cria os materiais (mesmos nomes dos outros módulos da Cripta: o Godot remapeia M_Pedra/M_PedraEscura)."""
    bpy.ops.wm.read_factory_settings(use_empty=True); objs.clear(); rnd.seed(seed)
    MAT["pedra"] = mat("M_Pedra", (0.42, 0.42, 0.46))
    MAT["escura"] = mat("M_PedraEscura", (0.16, 0.16, 0.19))
    MAT["estatua"] = mat("M_Estatua", (0.22, 0.21, 0.20), rough=0.9)
    MAT["musgo"] = mat("M_Musgo", (0.16, 0.19, 0.08), rough=1.0)
    MAT["ferro"] = mat("M_Ferro", (0.075, 0.07, 0.08), metal=0.7, rough=0.5)


def from_bm(bm, m, name="p"):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    me.materials.append(m); objs.append(o)
    return o


def bevel_bm(bm, off, seg=2, angle=0.5):
    edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > angle]
    bmesh.ops.bevel(bm, geom=edges, offset=off, segments=seg, affect='EDGES', profile=0.5)


def rock(loc, size, m=None, rot=(0, 0, 0), jit=0.0, bev=0.03, cuts=0, seg=2, chip=0.0, rough=0.0, cuts_pre=None):
    """Bloco de pedra com arestas vivas. chip = profundidade (m) das quinas lascadas (0 = sem lascas),
    rough = amplitude (m) do relevo facetado nas faces, jit = deslocamento aleatório dos cantos (fração do tamanho)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    sx, sy, sz = size
    if chip or rough:
        n = cuts_pre if cuts_pre is not None else 3
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=n, use_grid_fill=True)
    elif cuts:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    seed = Vector((rnd.uniform(0, 100), rnd.uniform(0, 100), rnd.uniform(0, 100)))
    for v in bm.verts:
        p = v.co.copy()
        co = Vector((p.x * sx, p.y * sy, p.z * sz))
        if chip:
            # quinas: quanto mais perto de um canto/aresta, mais a lasca puxa o vértice para dentro, em facetas
            ex = abs(p.x) * 2; ey = abs(p.y) * 2; ez = abs(p.z) * 2
            near = sorted([ex, ey, ez])
            corner = near[1] * near[2]            # alto só em arestas/cantos
            k = noise.noise(Vector((p.x * 3, p.y * 3, p.z * 3)) + seed)
            if corner > 0.7 and k > -0.1:
                d = chip * (corner - 0.7) / 0.3 * (0.5 + 0.5 * k + 0.3)
                co -= Vector((math.copysign(1, p.x) * (ex > 0.99) * d * 1.0 if ex >= 0.99 else 0,
                              math.copysign(1, p.y) * (ey > 0.99) * d * 1.0 if ey >= 0.99 else 0,
                              math.copysign(1, p.z) * (ez > 0.99) * d * 1.0 if ez >= 0.99 else 0))
        if rough:
            # relevo facetado: ruído quantizado (patamares) em vez de ondas suaves
            q = noise.noise(Vector((co.x, co.y, co.z)) * 7.0 + seed)
            q = round(q * 3) / 3
            nrm = Vector((p.x * 2 if abs(p.x) > 0.49 else 0, p.y * 2 if abs(p.y) > 0.49 else 0, p.z * 2 if abs(p.z) > 0.49 else 0))
            co += nrm.normalized() * q * rough if nrm.length else Vector()
        if jit:
            co += Vector((rnd.uniform(-1, 1) * jit * sx, rnd.uniform(-1, 1) * jit * sy, rnd.uniform(-1, 1) * jit * sz))
        v.co = co
    if bev:
        bevel_bm(bm, min(bev, 0.3 * min(size)), seg)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.transform(bm, matrix=Matrix.Translation(loc) @ Matrix.Rotation(rot[2], 4, 'Z') @ Matrix.Rotation(rot[1], 4, 'Y') @ Matrix.Rotation(rot[0], 4, 'X'), verts=bm.verts)
    return from_bm(bm, m or MAT["pedra"], "rock")


def prism(poly, y0, y1, m=None):
    """Extrusão em Y de um polígono 2D (x, z)."""
    bm = bmesh.new()
    a = [bm.verts.new((x, y0, z)) for x, z in poly]
    b = [bm.verts.new((x, y1, z)) for x, z in poly]
    bm.faces.new(a[::-1]); bm.faces.new(b)
    n = len(poly)
    for i in range(n):
        bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return from_bm(bm, m or MAT["escura"], "prism")


def boolean(o, cutters, op='DIFFERENCE'):
    for c in cutters:
        md = o.modifiers.new("b", 'BOOLEAN'); md.operation = op; md.object = c; md.solver = 'EXACT'
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=md.name)
        bpy.data.objects.remove(c, do_unlink=True)
        if c in objs: objs.remove(c)


def ogive(w, h_side, rise, n=8):
    """Polígono (x, z) de um arco ogival de largura 2w: lados até h_side e duas curvas de raio 2w até a ponta."""
    r = 2 * w
    a_tip = math.acos((r - w) / r)
    right = [((w - r) + r * math.cos(a_tip * i / n), h_side + r * math.sin(a_tip * i / n)) for i in range(1, n + 1)]
    left = [(-x, z) for x, z in reversed(right[:-1])]
    return [(-w, 0), (w, 0), (w, h_side)] + right + left + [(-w, h_side)]


def ring(c, rx, ry, n=16, z=0.0, fold=0.0, ph=0.0):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        k = 1 + fold * math.sin(a * 4 + ph) * math.cos(z * 9 + ph)
        pts.append(Vector((c[0] + rx * k * math.cos(a), c[1] + ry * k * math.sin(a), z)))
    return pts


def loft(rings, m, cap_top=True, cap_bot=True):
    bm = bmesh.new()
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    n = len(vs[0])
    for j in range(len(vs) - 1):
        for i in range(n):
            bm.faces.new((vs[j][i], vs[j][(i + 1) % n], vs[j + 1][(i + 1) % n], vs[j + 1][i]))
    if cap_bot: bm.faces.new(vs[0][::-1])
    if cap_top: bm.faces.new(vs[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    o = from_bm(bm, m, "loft"); o["liso"] = 1
    md = o.modifiers.new("ss", 'SUBSURF'); md.levels = 1; md.render_levels = 1
    return o


def tube(p0, p1, r0, r1, m, n=10, fold=0.0):
    p0, p1 = Vector(p0), Vector(p1)
    d = (p1 - p0); L = d.length
    q = d.to_track_quat('Z', 'Y')
    rings = []
    for k in range(5):
        t = k / 4
        r = r0 + (r1 - r0) * t
        pts = []
        for i in range(n):
            a = 2 * math.pi * i / n
            pts.append(p0 + d * t + q @ Vector((r * math.cos(a) * (1 + fold * math.sin(a * 3 + t * 6)), r * math.sin(a), 0)))
        rings.append(pts)
    return loft(rings, m)


def stone_preview():
    """Só para a prévia: troca a cor lisa por pedra procedural (manchas, grão e relevo). Não vai para o glb."""
    for m in bpy.data.materials:
        if m.name not in ("M_Pedra", "M_PedraEscura", "M_Estatua"): continue
        base = tuple(m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value)[:3]
        nt = m.node_tree; N = nt.nodes; L = nt.links
        b = N["Principled BSDF"]
        tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (2.2, 2.2, 2.2)
        L.new(tc.outputs["Object"], mp.inputs["Vector"])
        n1 = N.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 3.0; n1.inputs["Detail"].default_value = 6
        n2 = N.new("ShaderNodeTexVoronoi"); n2.inputs["Scale"].default_value = 6.0
        L.new(mp.outputs[0], n1.inputs["Vector"]); L.new(mp.outputs[0], n2.inputs["Vector"])
        ramp = N.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (base[0] * 0.55, base[1] * 0.52, base[2] * 0.5, 1)
        ramp.color_ramp.elements[1].color = (base[0] * 1.25, base[1] * 1.2, base[2] * 1.15, 1)
        L.new(n1.outputs["Fac"], ramp.inputs["Fac"])
        mix = N.new("ShaderNodeMixRGB"); mix.blend_type = 'MULTIPLY'; mix.inputs["Fac"].default_value = 0.2
        L.new(ramp.outputs["Color"], mix.inputs[1]); L.new(n2.outputs["Distance"], mix.inputs[2])
        ca = N.new("ShaderNodeAttribute"); ca.attribute_name = "Color"
        mv = N.new("ShaderNodeMixRGB"); mv.blend_type = 'MULTIPLY'; mv.inputs["Fac"].default_value = 1.0
        L.new(mix.outputs["Color"], mv.inputs[1]); L.new(ca.outputs["Color"], mv.inputs[2])
        L.new(mv.outputs["Color"], b.inputs["Base Color"])
        bump = N.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25; bump.inputs["Distance"].default_value = 0.03
        L.new(n2.outputs["Distance"], bump.inputs["Height"]); L.new(bump.outputs["Normal"], b.inputs["Normal"])


def render(o, prev, nome, view, res=720, samples=40):
    stone_preview()
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        if ob.type in ('CAMERA', 'LIGHT'): bpy.data.objects.remove(ob, do_unlink=True)
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); bpy.context.collection.objects.link(cam)
    h = o.dimensions.z
    target = Vector((0, 0, h * 0.5))
    views = {"frente": (0, 1, 0.25), "tres_quartos": (0.8, 1, 0.55), "costas": (0.5, -1, 0.3), "topo": (0.4, 0.6, 1.6),
             "nicho": (0.0, 1, 0.05), "baixo": (0.6, 1, 0.1)}
    dx, dy, dz = views[view]
    d = max(o.dimensions) * 2.4
    cam.location = target + Vector((dx, dy, dz)).normalized() * d
    if view == "nicho":
        target = Vector((0, 0.7, 2.1)); cam.location = target + Vector((0.25, 1.0, 0.15)).normalized() * 3.2
        cam.data.lens = 85
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    if view != "nicho": cam.data.lens = 60
    sun = bpy.data.objects.new("s", bpy.data.lights.new("s", 'SUN')); sun.data.energy = 4.0; sun.rotation_euler = (0.9, 0.25, 0.7)
    bpy.context.collection.objects.link(sun)
    fill = bpy.data.objects.new("f", bpy.data.lights.new("f", 'SUN')); fill.data.energy = 0.8; fill.rotation_euler = (1.2, 0, -2.2)
    bpy.context.collection.objects.link(fill)
    w = bpy.data.worlds.new("w"); w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.12, 0.13, 0.17, 1); sc.world = w
    sc.render.engine = 'CYCLES'; sc.cycles.samples = samples; sc.cycles.device = 'CPU'; sc.cycles.use_denoising = True
    sc.render.resolution_x = res; sc.render.resolution_y = res
    sc.render.filepath = os.path.join(prev, f"{nome}_{view}.png")
    bpy.ops.render.render(write_still=True)




def juntar(nome):
    for o in objs:
        if o.modifiers:
            bpy.context.view_layer.objects.active = o
            for md in list(o.modifiers): bpy.ops.object.modifier_apply(modifier=md.name)
        o.data.update()
        _tom_peca(o)
        for p in o.data.polygons: p.use_smooth = bool(o.get("liso"))
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.object; o.name = nome
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return o


def boulder(loc, size, m=None, rot=(0, 0, 0), pts=14, bev=0.012, flat=0.35):
    """Pedaço de pedra caído: casco convexo de pontos aleatórios (facetas planas e quinas vivas, formato irregular).
    flat = achatamento do eixo Z (blocos quebrados ficam deitados)."""
    bm = bmesh.new()
    sx, sy, sz = size
    for _ in range(pts):
        d = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1) * (1 - flat)))
        if d.length < 1e-4: continue
        d.normalize(); r = rnd.uniform(0.55, 1.0) * 0.5
        bm.verts.new(Vector((d.x * sx, d.y * sy, d.z * sz)) * r * 2)
    bmesh.ops.convex_hull(bm, input=bm.verts[:], use_existing_faces=False)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(8), verts=bm.verts[:], edges=bm.edges[:])
    # lascas: corta 2-3 cantos com planos aleatórios (faces quebradas menores sobre a forma maior)
    for _ in range(rnd.randint(2, 3)):
        n = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))).normalized()
        if len(bm.verts) < 6: break
        proj = [v.co.dot(n) for v in bm.verts]
        d = max(proj) - rnd.uniform(0.08, 0.25) * (max(proj) - min(proj))
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=n * d, plane_no=n, clear_outer=True, use_snap_center=False)
        cap = [e for e in bm.edges if e.is_boundary]
        if cap: bmesh.ops.holes_fill(bm, edges=cap, sides=0)
    if bev:
        bevel_bm(bm, bev, 1, angle=0.4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.transform(bm, matrix=Matrix.Translation(loc) @ Matrix.Rotation(rot[2], 4, 'Z') @ Matrix.Rotation(rot[1], 4, 'Y') @ Matrix.Rotation(rot[0], 4, 'X'), verts=bm.verts)
    return from_bm(bm, m or MAT["pedra"], "boulder")


def pintar_vertices(o, raios=14, alcance=0.7, seed=5):
    """Pinta o atributo de cor 'Color' (sem luz): oclusão por raios (cantos e juntas escuros), sujeira que escorre
    para baixo, variação de cor por região e desgaste assimétrico por face. No Godot o shader multiplica o albedo por COLOR."""
    from mathutils.bvhtree import BVHTree
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    bvh = BVHTree.FromBMesh(bm)
    bm.verts.ensure_lookup_table()
    r = random.Random(seed)
    off = Vector((r.uniform(0, 50), r.uniform(0, 50), r.uniform(0, 50)))
    cols = {}
    for v in bm.verts:
        n = v.normal if v.normal.length > 0 else Vector((0, 0, 1))
        t = n.cross(Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))).normalized(); b = n.cross(t)
        o_ = v.co + n * 0.01; hit = 0
        for _ in range(raios):
            u1, u2 = r.random(), r.random(); rr = math.sqrt(u1); ph = 2 * math.pi * u2
            d = (t * (rr * math.cos(ph)) + b * (rr * math.sin(ph)) + n * math.sqrt(max(0.0, 1 - u1))).normalized()
            if bvh.ray_cast(o_, d, alcance)[0] is not None: hit += 1
        ao = 1.0 - hit / raios
        p = v.co
        reg = noise.noise(p * 0.9 + off) * 0.5 + 0.5                    # manchas grandes de cor
        fin = noise.noise(p * 6.0 + off) * 0.5 + 0.5                    # grão fino
        face = (math.sin(p.x * 1.7 + p.y * 2.3) + 1) * 0.5              # lados com desgaste diferente
        sujo = max(0.0, 1.0 - (p.z / 6.5)) ** 2 * 0.35 + (1 - ao) * 0.3  # sujeira embaixo e nas juntas
        k = (0.55 + 0.45 * ao ** 1.2) * (0.8 + 0.25 * reg) * (0.92 + 0.12 * fin) * (1 - sujo * (0.5 + 0.5 * face))
        warm = 0.12 * (reg - 0.5)
        cols[v.index] = (min(1, k * (1 + warm)), min(1, k), min(1, k * (1 - warm)), 1.0)
    bm.free()
    tom = me.color_attributes.get("Tom")
    if tom:
        for i in cols:
            t = tom.data[i].color; c = cols[i]; cols[i] = (c[0] * t[0], c[1] * t[1], c[2] * t[2], 1.0)
        me.color_attributes.remove(tom)
    if "Color" in me.color_attributes: me.color_attributes.remove(me.color_attributes["Color"])
    ca = me.color_attributes.new("Color", 'FLOAT_COLOR', 'POINT')
    for v in me.vertices:
        ca.data[v.index].color = cols[v.index]


def _tom_peca(o):
    """Cor própria de cada bloco antes de juntar: marrom-acinzentado quente com variação (a folha tem pedra quente)."""
    t = rnd.random()
    if o.data.materials and o.data.materials[0].name == "M_Musgo":
        c = (1, 1, 1, 1)
    else:
        base = (1.0, 0.86, 0.72) if t < 0.55 else (0.9, 0.88, 0.86)
        k = rnd.uniform(0.78, 1.08)
        c = (base[0] * k, base[1] * k, base[2] * k, 1)
    ca = o.data.color_attributes.new("Tom", 'FLOAT_COLOR', 'POINT')
    for d in ca.data: d.color = c
