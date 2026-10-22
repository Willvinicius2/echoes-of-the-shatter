"""Parte 2 (composição): decide quantas peças, em que tamanhos e onde caem. Poucas lajes grandes, várias médias,
muitas lascas e pó de pedra, soltos em camadas para a simulação montar um monte (silhueta de monte, não de grade)."""
import math, bpy, os, json
from mathutils import Vector, Matrix
from comum import rnd
import forma, assentar

def construir(M):
    pecas = []
    def solta(bm, nome, mat, r, z):
        a = rnd.uniform(0, 6.283); rr = rnd.uniform(0, r)
        o = forma.para_objeto(bm, nome, mat, (math.cos(a) * rr, math.sin(a) * rr * 0.8, z), (rnd.uniform(0, 6.28), rnd.uniform(0, 6.28), rnd.uniform(0, 6.28)))
        pecas.append(o); return o
    mats = lambda: M["pedra"] if rnd.random() > 0.35 else M["escura"]
    # camada 1: núcleo de blocos grandes
    for i in range(4):
        s = (rnd.uniform(0.5, 0.75), rnd.uniform(0.4, 0.55), rnd.uniform(0.26, 0.38))
        solta(forma.laje(s, fraturas=rnd.randint(2, 3), sub=1), f"laje{i}", mats(), 0.1, 0.4 + i * 0.5)
    # camada 2: médias lascadas e médias arredondadas
    for i in range(8):
        s = (rnd.uniform(0.24, 0.42), rnd.uniform(0.2, 0.34), rnd.uniform(0.14, 0.26))
        solta(forma.laje(s, fraturas=rnd.randint(2, 3), sub=0), f"media{i}", mats(), 0.28, 3.0 + i * 0.4)
    for i in range(8):
        solta(forma.redonda(rnd.uniform(0.11, 0.2), rnd.uniform(0.6, 0.85)), f"redonda{i}", mats(), 0.3, 6.5 + i * 0.35)
    # camada 3: lascas e pó de pedra
    for i in range(30):
        solta(forma.cascalho(rnd.uniform(0.07, 0.15), 0.55, 10, sub=0), f"lasca{i}", mats(), 0.33, 9.8 + i * 0.2)
    for i in range(36):
        solta(forma.cascalho(rnd.uniform(0.025, 0.055), 0.6, 8), f"po{i}", mats(), 0.4, 16.5 + i * 0.15)
    poses = os.path.join(os.path.dirname(os.path.abspath(__file__)), "poses.json")
    if os.path.exists(poses) and not os.environ.get("ENTULHO_SIMULAR"):
        # pose já assentada e aprovada (a física do Blender não é determinística): reaplica por nome
        gravado = json.load(open(poses))
        mantidas = []
        for o in pecas:
            if o.name in gravado:
                o.matrix_world = Matrix(gravado[o.name]); mantidas.append(o)
            else: bpy.data.objects.remove(o, do_unlink=True)
        pecas = mantidas
        bpy.context.view_layer.update()
        return pecas
    assentar.simular(pecas)
    # descarta peças arremessadas para longe pela simulação
    ficam = []
    for o in pecas:
        c = o.matrix_world @ (sum((v.co for v in o.data.vertices), Vector()) / len(o.data.vertices))
        zs = [(o.matrix_world @ v.co).z for v in o.data.vertices]
        if max(zs) > 1.4 or min(zs) < -0.08 or math.hypot(c.x, c.y) > 1.1: bpy.data.objects.remove(o, do_unlink=True)
        else: ficam.append(o)
    if os.environ.get("ENTULHO_SALVAR"):
        json.dump({o.name: [list(r) for r in o.matrix_world] for o in ficam}, open(os.environ["ENTULHO_SALVAR"], "w"))
    return ficam
