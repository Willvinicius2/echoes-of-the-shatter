"""Parte do braseiro: brasas. build() acrescenta as malhas a _lib.objs."""
from ._lib import *


def build():
    random.seed(11)
    # ---- cinza no fundo e brasas irregulares
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.60, depth=0.05, location=(0, 0, 1.17))
    finish(bpy.context.object, ASH, 0, 0.012, 0.1, 7)
    for i in range(11):
        r = 0.36 * math.sqrt(random.random()); a = random.random() * 2 * math.pi
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.09 + random.random() * 0.07, location=(r * math.cos(a), r * math.sin(a), 1.22 + random.random() * 0.08))
        o = bpy.context.object; o.scale = (1, 1, 0.65); o.rotation_euler = (random.random() * 3, random.random() * 3, random.random() * 3)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        finish(o, EMBER, 0, 0.03, 0, i)

