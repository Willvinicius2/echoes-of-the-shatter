"""Peças comuns do entulho: materiais, gerador de bloco lascado e mapa de altura para assentar as pedras."""
import bpy, bmesh, math, random
from mathutils import Vector

import os
rnd = random.Random(int(os.environ.get("ENTULHO_SEED", "7")))

def mat(name, color, rough=0.9):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    return m

def criar_materiais():
    return dict(pedra=mat("M_Pedra", (0.42, 0.40, 0.38)), escura=mat("M_PedraEscura", (0.20, 0.19, 0.19)), musgo=mat("M_Musgo", (0.12, 0.17, 0.05), 1.0), terra=mat("M_Terra", (0.07, 0.055, 0.045), 1.0))

class Altura:
    """Assentamento por raio: cada pedra nova desce até o primeiro contato com o que já está na pilha (sem flutuar nem afundar)."""
    def __init__(self):
        self.placed = []
    def _bvh(self):
        from mathutils.bvhtree import BVHTree
        vs, ps = [], []
        for o in self.placed:
            base = len(vs); vs += [o.matrix_world @ v.co for v in o.data.vertices]
            ps += [tuple(base + i for i in p.vertices) for p in o.data.polygons]
        return BVHTree.FromPolygons(vs, ps) if ps else None
    def assentar(self, o, folga=0.004):
        bpy.context.view_layer.update()
        ws = [o.matrix_world @ v.co for v in o.data.vertices]
        bvh = self._bvh(); sobe = -min(w.z for w in ws)      # base no chão
        if bvh:
            for w in ws:
                hit = bvh.ray_cast(Vector((w.x, w.y, 5.0)), Vector((0, 0, -1)))
                if hit[0] is not None: sobe = max(sobe, hit[0].z - w.z)
        o.location.z += sobe + folga
        bpy.context.view_layer.update(); self.placed.append(o)

def bloco(loc, size, rot, m, lascas=3, relevo=True, bev=0.02, mat_musgo=None):
    """Bloco cortado: cubo lascado por planos de corte (facetas retas), relevo de pedra grosseira, chanfro fino, sombreamento chapado."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    mn = min(size)
    for _ in range(lascas):
        n = Vector([rnd.choice((-1, 1)) * rnd.uniform(0.2, 1) for _ in range(3)])
        if rnd.random() < 0.5: n[rnd.randrange(3)] = 0
        if n.length < 0.1: continue
        n.normalize()
        corner = Vector((n.x * size[0] / 2, n.y * size[1] / 2, n.z * size[2] / 2))
        pt = corner - n * rnd.uniform(0.04, 0.17) * mn
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=pt, plane_no=n, clear_outer=True, clear_inner=False)
        bord = [e for e in bm.edges if e.is_boundary]
        if bord: bmesh.ops.holes_fill(bm, edges=bord)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if relevo:
        for f in bm.faces[:]:
            if f.calc_area() < 0.04: continue
            r = bmesh.ops.inset_individual(bm, faces=[f], thickness=0.07 * mn, use_even_offset=True)
            d = rnd.uniform(-0.06, 0.02) * mn      # painel recuado ou saliente: pedra de talhe grosseiro
            for v in f.verts: v.co += f.normal * d
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bev * mn, segments=1, affect='EDGES')
    me = bpy.data.meshes.new("b"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("b", me); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot
    me.materials.append(m)
    for p in me.polygons: p.use_smooth = False
    bpy.context.view_layer.update()
    return o
