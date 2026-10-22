"""PARTE corpo (manto, ombros, mangas, cinto, adornos). Provisório: o agente do corpo reescreve este arquivo."""
import bmesh, math
from mathutils import Vector
def build(L):
    rings = [[Vector((L.prof([(L.Z_HEM, L.HEM_RX), (L.Z_NECK, 0.2)], z) * math.cos(t), L.prof([(L.Z_HEM, L.HEM_RY), (L.Z_NECK, 0.18)], z) * math.sin(t), z))
              for t in [i / 48 * math.tau for i in range(48)]] for z in [L.Z_HEM + k / 10 * (L.Z_NECK - L.Z_HEM) for k in range(11)]]
    L.new_obj("corpo", L.loft(rings))
