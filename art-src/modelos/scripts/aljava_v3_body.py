"""Aljava v3, passo 1 (Blender -b, Cycles CPU): recorta o corpo TripoSG (como na v2), alisa facetas, deixa a boca com borda limpa
e assa o normal map do high.ply. Saida: body.blend (corpo no referencial do mundo, UV da v2) e bake_normal.png.
uso: blender -b -P aljava_v3_body.py -- <blend_v1> <high.ply> <out_dir> <tex_dir_v2> [tex=2048]"""
import bpy, bmesh, sys, math, os, json
from mathutils import Vector, Matrix
a = sys.argv[sys.argv.index("--") + 1:]
glb_in, high_ply, out, tex = a[:4]; TEX = int(a[4]) if len(a) > 4 else 2048
THETA = math.radians(9.9); ORG = Vector((0, 0, -0.1))
M = Matrix.Translation(ORG) @ Matrix.Rotation(THETA, 4, 'Y'); Mi = M.inverted()
S_TOP = 0.178; R_TUBE = 0.042
bpy.ops.wm.open_mainfile(filepath=glb_in)   # blend da v1 (corpo TripoSG com UV), no referencial do mundo
body = [o for o in bpy.data.objects if o.type == 'MESH'][0]
body.data.transform(body.matrix_world); body.matrix_world.identity(); body.parent = None
bm = bmesh.new(); bm.from_mesh(body.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
for v in bm.verts: v.co = Mi @ v.co
def in_zone(c): return c.y < 0.01 and 0.012 < c.z < 0.122 and abs(c.x) < 0.047
for v in bm.verts:
    if v.co.y < 0.012 and 0.012 < v.co.z < 0.122 and abs(v.co.x) < 0.047:
        w = min(1.0, (0.047 - abs(v.co.x)) / 0.012, (v.co.z - 0.012) / 0.012, (0.122 - v.co.z) / 0.008)
        r = math.hypot(v.co.x, v.co.y)
        if r > 0.0415 and r > 1e-6:
            k = 0.0415 / r; k = 1 + (k - 1) * w; v.co.x *= k; v.co.y *= k
dele = [f for f in bm.faces if (lambda c: c.z > S_TOP or c.x < -0.05 or (c.x < -0.043 and c.z < 0.135) or (c.x > 0.044 and c.z < 0.125))(f.calc_center_median())]
bmesh.ops.delete(bm, geom=dele, context='FACES')
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
bm.faces.ensure_lookup_table()
seen = set(); islands = []
for f in bm.faces:
    if f in seen: continue
    st = [f]; seen.add(f); isl = []
    while st:
        x = st.pop(); isl.append(x)
        for e in x.edges:
            for g in e.link_faces:
                if g not in seen: seen.add(g); st.append(g)
    islands.append(isl)
islands.sort(key=len, reverse=True)
bmesh.ops.delete(bm, geom=[f for isl in islands[1:] for f in isl], context='FACES')
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
for v in bm.verts:
    if v.co.x < -0.03 and 0.0 < v.co.z < 0.135:
        r = math.hypot(v.co.x, v.co.y)
        if r > 0.0415: k = 0.0415 / r; v.co.x *= k; v.co.y *= k
Z_CUT = 0.125     # acima disso o corpo fica escondido pela cinta da boca (v3_build); corta limpo em vez de remendar o aro rasgado
bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().z > Z_CUT], context='FACES')
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
bm.faces.ensure_lookup_table()


def boundary_loops():
    bset = set(e for e in bm.edges if e.is_boundary); out = []
    while bset:
        e0 = bset.pop(); comp = [e0]; st = [e0]
        while st:
            x = st.pop()
            for v in x.verts:
                for e in v.link_edges:
                    if e in bset: bset.remove(e); comp.append(e); st.append(e)
        out.append(comp)
    return out


sectors = []; small = []; hv = []
for comp in boundary_loops():
    vs = {v for e in comp for v in e.verts}
    if len(comp) <= 10 and max(v.co.z for v in vs) < Z_CUT - 0.01: small.append(comp); continue
    hv += [v for v in vs if v.co.z < Z_CUT - 0.005]            # bordas de buraco (o aro do corte fica de fora)
for left in (True, False):
    side = sorted([v for v in hv if (v.co.x < 0) == left], key=lambda v: v.co.z)
    cl = []
    for v in side:
        if cl and v.co.z - cl[-1][-1].co.z < 0.02: cl[-1].append(v)
        else: cl.append([v])
    for c in cl:
        if len(c) < 4: continue
        ph = [math.atan2(v.co.y, -v.co.x if left else v.co.x) for v in c]; zs = [v.co.z for v in c]
        sectors.append((left, min(ph) - 0.15, max(ph) + 0.15, min(zs) - 0.004, Z_CUT + 0.003 if max(zs) > Z_CUT - 0.03 else max(zs) + 0.004))
print("SECTORS", sectors, "small", len(small))
for comp in small:
    for ff in bmesh.ops.holes_fill(bm, edges=comp, sides=len(comp) + 2)['faces']: ff.material_index = 3
bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])


def in_sector(c):
    for (left, p0, p1, z0, z1) in sectors:
        if (c.x < 0) != left: continue
        p = math.atan2(c.y, -c.x if left else c.x)
        if p0 + 0.13 <= p <= p1 - 0.13 and z0 + 0.008 <= c.z <= z1 - 0.004: return True
    return False


bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != 3 and in_sector(f.calc_center_median())], context='FACES')
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
# fragmentos da alca da v1 que sobram: prende no raio do tubo
for v in bm.verts:
    if 0.0 < v.co.z < 0.16:
        r = math.hypot(v.co.x, v.co.y)
        if r > 0.0425: v.co.x *= 0.0415 / r; v.co.y *= 0.0415 / r
pv = {v for f in bm.faces if f.material_index == 3 for v in f.verts}
for v in pv:
    r = math.hypot(v.co.x, v.co.y)
    if r > 1e-6: v.co.x *= 0.0415 / r; v.co.y *= 0.0415 / r
# alisa facetas (Laplaciano leve, sem mexer nas bordas)
inner = [v for v in bm.verts if not v.is_boundary and v.co.z < Z_CUT - 0.01 and v not in pv]
bmesh.ops.smooth_vert(bm, verts=inner, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
bmesh.ops.smooth_vert(bm, verts=inner, factor=0.35, use_axis_x=True, use_axis_y=True, use_axis_z=True)
# casca cilindrica limpa por cima dos buracos da alca da v1 (grade regular, margem de 1,5 mm de sobreposicao)
RP = 0.0418; CELL = 0.009
uvl = bm.loops.layers.uv.active
for (left, p0, p1, z0, z1) in sectors:
    nph = max(2, int(math.ceil((p1 - p0) * RP / CELL))); nz = max(2, int(math.ceil((z1 - z0) / CELL)))
    g = []
    for i in range(nz + 1):
        row = []
        for j in range(nph + 1):
            p = p0 + (p1 - p0) * j / nph; z = z0 + (z1 - z0) * i / nz
            x = RP * math.cos(p) * (-1 if left else 1); y = RP * math.sin(p)
            row.append(bm.verts.new((x, y, z)))
        g.append(row)
    for i in range(nz):
        for j in range(nph):
            f = bm.faces.new((g[i][j], g[i][j + 1], g[i + 1][j + 1], g[i + 1][j])); f.material_index = 3
            for lp, (uj, ui) in zip(f.loops, ((j, i), (j + 1, i), (j + 1, i + 1), (j, i + 1))): lp[uvl].uv = (0.2 + 0.5 * uj / nph, 0.2 + 0.5 * ui / nz)
bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.normal_update()
bm.normal_update()
for f in bm.faces:
    if f.material_index == 3:
        c = f.calc_center_median()
        if f.normal.dot(Vector((c.x, c.y, 0))) < 0: f.normal_flip()
bm.normal_update()
print("ZMAX", max(v.co.z for v in bm.verts), "zmin", min(v.co.z for v in bm.verts))
bm.to_mesh(body.data); bm.free()
body.data.transform(M)   # mundo
for p in body.data.polygons: p.use_smooth = True
body.name = body.data.name = "SM_ArcherDark_Quiver_Body"
for o in bpy.data.objects:
    if o is not body: bpy.data.objects.remove(o)
# ---- bake do normal ----
idx_save = [p.material_index for p in body.data.polygons]
bpy.ops.wm.ply_import(filepath=high_ply); high = bpy.context.selected_objects[0]; high.name = "high"
hv = [high.matrix_world @ Vector(c) for c in high.bound_box]; bv = [body.matrix_world @ Vector(c) for c in body.bound_box]
print("HIGHBB", [round(min(p[i] for p in hv), 3) for i in range(3)], [round(max(p[i] for p in hv), 3) for i in range(3)])
print("BODYBB", [round(min(p[i] for p in bv), 3) for i in range(3)], [round(max(p[i] for p in bv), 3) for i in range(3)])
for o in (high,):
    bpy.context.view_layer.objects.active = o; o.select_set(True); bpy.ops.object.shade_smooth()
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.use_denoising = False; sc.cycles.samples = 4
mat = bpy.data.materials.new("m"); mat.use_nodes = True; body.data.materials.clear(); body.data.materials.append(mat)
for p in body.data.polygons: p.material_index = 0
img = bpy.data.images.new("bn", TEX, TEX); img.colorspace_settings.name = 'Non-Color'
n = mat.node_tree.nodes.new('ShaderNodeTexImage'); n.image = img; mat.node_tree.nodes.active = n
bpy.ops.object.select_all(action='DESELECT'); high.select_set(True); body.select_set(True); bpy.context.view_layer.objects.active = body
bpy.ops.object.bake(type='NORMAL', margin=14, margin_type='EXTEND', use_selected_to_active=True, cage_extrusion=0.010, max_ray_distance=0.03, normal_space='TANGENT')
img.filepath_raw = os.path.join(out, "bake_normal.png"); img.file_format = 'PNG'; img.save()
body.data.polygons.foreach_set('material_index', idx_save)
bpy.data.objects.remove(high)
for _ in range(3): body.data.materials.append(mat)   # 4 slots: corpo, interior, metal, remendo
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "body.blend"))
print("BODYDONE", len(body.data.polygons))
