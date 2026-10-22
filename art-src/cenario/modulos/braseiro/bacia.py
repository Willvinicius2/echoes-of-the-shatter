"""Bacia: casco martelado com espessura real, lábio enrolado, forro de fuligem por dentro e cintas meridianas."""
from ._lib import *

def build():
    r = rng(201)
    # casco externo: meia-esfera achatada, subdividida e amassada
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=28, v_segments=14, radius=0.68)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > 0.03], context='VERTS')
    for v in bm.verts:
        v.co.z *= 0.55
        n = v.co.normalized()
        v.co += n * (r.uniform(-0.010, 0.010) + 0.018 * math.sin(v.co.x * 9 + 1.3) * math.sin(v.co.y * 7 - 0.4))
    casco = new("casco", bm, (0, 0, 1.12), (0, 0, 0), FERRO, 0, flat=True)
    mod = casco.modifiers.new("sol", 'SOLIDIFY'); mod.thickness = 0.028; mod.offset = 1.0
    bpy.context.view_layer.objects.active = casco; bpy.ops.object.modifier_apply(modifier="sol")
    # forro de fuligem dentro
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=0.645)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > 0.01], context='VERTS')
    for v in bm.verts: v.co.z *= 0.52
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:]); jitter(bm, 0.006, r)
    new("forro", bm, (0, 0, 1.125), (0, 0, 0), FUL, 0)
    # lábio enrolado irregular
    bpy.ops.mesh.primitive_torus_add(major_radius=0.70, minor_radius=0.032, major_segments=40, minor_segments=8, location=(0, 0, 1.125))
    t = bpy.context.object
    for v in t.data.vertices: v.co += Vector((r.uniform(-.005, .005), r.uniform(-.005, .005), r.uniform(-.005, .005)))
    add(t, ENVELH, PARTE[0])
    # cintas meridianas sob a bacia (seguem a curva do casco)
    for a in range(4):
        ang = a * math.pi / 4
        pts = [(0.70 * math.sin(j / 8 * 1.45), 0, 0) for j in range(-8, 9)]
        bm = bmesh.new()
        prev = None
        for p in pts:
            v1 = bm.verts.new((p[0], -0.035, 1.12 - 0.55 * 0.68 * math.sqrt(max(0, 1 - (p[0] / 0.68) ** 2)) - 0.02))
            v2 = bm.verts.new((p[0], 0.035, v1.co.z))
            if prev: bm.faces.new((prev[0], prev[1], v2, v1))
            prev = (v1, v2)
        o = new("cinta", bm, (0, 0, 0), (0, 0, ang), ENVELH, 0.006)
        mod = o.modifiers.new("sol", 'SOLIDIFY'); mod.thickness = 0.02
        bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier="sol")
