"""Parte 2 (composição): decide quantas peças, em que tamanhos e onde caem. Poucas lajes grandes, várias médias,
muitas lascas e pó de pedra, soltos em camadas para a simulação montar um monte (silhueta de monte, não de grade)."""
import math, bpy
from mathutils import Vector
from comum import rnd
import forma, assentar

def construir(M):
    pecas = []
    def solta(bm, nome, mat, r, z):
        a = rnd.uniform(0, 6.283); rr = rnd.uniform(0, r)
        o = forma.para_objeto(bm, nome, mat, (math.cos(a) * rr, math.sin(a) * rr * 0.8, z), (rnd.uniform(0, 6.28), rnd.uniform(0, 6.28), rnd.uniform(0, 6.28)))
        pecas.append(o); return o
    mats = lambda: M["pedra"] if rnd.random() > 0.35 else M["escura"]
    # camada 1: lajes grandes (poucas)
    for i in range(2):
        s = (rnd.uniform(0.6, 0.85), rnd.uniform(0.42, 0.6), rnd.uniform(0.22, 0.32))
        solta(forma.laje(s, fraturas=rnd.randint(2, 3)), f"laje{i}", mats(), 0.12, 0.4 + i * 0.6)
    # camada 2: médias
    for i in range(13):
        s = (rnd.uniform(0.24, 0.44), rnd.uniform(0.2, 0.36), rnd.uniform(0.14, 0.26))
        solta(forma.laje(s, fraturas=rnd.randint(2, 3)), f"media{i}", mats(), 0.3, 2.0 + i * 0.45)
    # camada 3: lascas e cascalho
    for i in range(26):
        solta(forma.cascalho(rnd.uniform(0.07, 0.15), 0.55, 10), f"lasca{i}", mats(), 0.45, 8.2 + i * 0.28)
    # pó de pedra: cascalho miúdo espalhado
    for i in range(36):
        solta(forma.cascalho(rnd.uniform(0.025, 0.055), 0.6, 8), f"po{i}", mats(), 0.5, 16.0 + i * 0.2)
    assentar.simular(pecas)
    # descarta peças arremessadas para longe pela simulação
    ficam = []
    for o in pecas:
        c = o.matrix_world @ (sum((v.co for v in o.data.vertices), Vector()) / len(o.data.vertices))
        zs = [(o.matrix_world @ v.co).z for v in o.data.vertices]
        if max(zs) > 1.1 or min(zs) < -0.08 or math.hypot(c.x, c.y) > 1.2: bpy.data.objects.remove(o, do_unlink=True)
        else: ficam.append(o)
    return ficam
