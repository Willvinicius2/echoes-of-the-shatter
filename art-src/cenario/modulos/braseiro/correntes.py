"""Parte do braseiro: correntes. build() acrescenta as malhas a _lib.objs."""
from ._lib import *


def build():
    random.seed(11)
    # ---- correntes penduradas sob a bacia (elos alternados) entre as pernas
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        for j in range(5):
            bpy.ops.mesh.primitive_torus_add(major_radius=0.045, minor_radius=0.012, major_segments=10, minor_segments=5,
                                             location=(0.30 * math.cos(a), 0.30 * math.sin(a), 0.93 - j * 0.075),
                                             rotation=(math.pi / 2, 0, a + (j % 2) * math.pi / 2))
            o = bpy.context.object; o.scale = (1, 1.5, 1); bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
            finish(o, WORN)

