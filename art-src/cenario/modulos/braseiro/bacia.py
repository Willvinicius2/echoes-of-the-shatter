"""Parte do braseiro: bacia. build() acrescenta as malhas a _lib.objs."""
from ._lib import *


def build():
    random.seed(11)
    # ---- bacia martelada (hemisfério subdividido, com amassados) e lábio
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=9, radius=0.68, location=(0, 0, 1.12))
    bowl = bpy.context.object
    bm = bmesh.new(); bm.from_mesh(bowl.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > 1.121 - 1.12 + 0.02], context='VERTS')
    bm.to_mesh(bowl.data); bm.free()
    bowl.scale = (1, 1, 0.55); bpy.ops.object.transform_apply(scale=True)
    bm = bmesh.new(); bm.from_mesh(bowl.data); bm.normal_update()
    for v in bm.verts:                                   # marteladas: ruído de baixa e de alta frequência
        v.co += v.normal * random.uniform(-0.014, 0.014)   # facetas marteladas, sem suavizar
    bm.to_mesh(bowl.data); bm.free()
    bowl.data.materials.append(IRON)
    for p in bowl.data.polygons: p.use_smooth = False
    objs.append(bowl)
    for a in range(4):                                   # cintas meridianas sob a bacia
        box((0, 0, 0.97), (0.06, 1.32, 0.05), rot=(0, 0, a * math.pi / 4), m=TRIM, bev=0.01, wear=0.004, seed=40 + a, cut=0.12)

