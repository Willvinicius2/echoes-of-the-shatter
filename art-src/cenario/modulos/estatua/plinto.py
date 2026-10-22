"""PARTE plinto (pilar de base + entulho). Provisório: o agente do plinto reescreve este arquivo."""
import bmesh
def build(L):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co.x *= L.PLINTO_W; v.co.y *= L.PLINTO_W; v.co.z = (v.co.z + 0.5) * L.ZP
    L.new_obj("plinto", bm)
