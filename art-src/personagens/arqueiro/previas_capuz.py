"""Renders de revisao SO do capuz (EEVEE 1024, um por vez, cena limpa a cada render).
Rodar: blender -b -P previas_capuz.py        (saida em previas/capuz_*.png; o conjunto vem de previas.py)
Vistas: frente, 3q, lado, costas, close (rosto), wire. capuz_vs_folha.png e montado por montar_vs_folha() com PIL fora do Blender.
"""
import os, sys, math
import bpy
from mathutils import Vector

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import previas as p   # reaproveita nova_cena/importar_glb/render (o bloco __main__ de previas.py nao roda no import)

OUT = os.path.join(AQUI, "previas")
p.OUT = OUT


def malhas():
    return [o for o in bpy.data.objects if o.type == "MESH"]


def box_de(nomes):
    pts = []
    for o in malhas():
        if any(n in o.name for n in nomes):
            pts += [o.matrix_world @ v.co for v in o.data.vertices]
    lo = Vector((min(q.x for q in pts), min(q.y for q in pts), min(q.z for q in pts)))
    hi = Vector((max(q.x for q in pts), max(q.y for q in pts), max(q.z for q in pts)))
    return lo, hi


def wire_real(sc):
    """copia avaliada (ja skinada) de cada malha + modifier Wireframe: sem os espetos do modifier sobre armature."""
    dg = bpy.context.evaluated_depsgraph_get()
    mat = bpy.data.materials.new("wire"); mat.use_nodes = True
    nt = mat.node_tree; nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission"); o = nt.nodes.new("ShaderNodeOutputMaterial")
    e.inputs["Color"].default_value = (0.85, 0.95, 1, 1); e.inputs["Strength"].default_value = 2.0
    nt.links.new(e.outputs[0], o.inputs[0])
    for ob in malhas():
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        me.materials.clear(); me.materials.append(mat)
        for q in me.polygons:
            q.material_index = 0
        n = bpy.data.objects.new("w_" + ob.name, me)
        sc.collection.objects.link(n)
        n.matrix_world = ob.matrix_world.copy()
        m = n.modifiers.new("wf", "WIREFRAME"); m.thickness = 0.0016; m.use_replace = True; m.use_even_offset = False
        ob.hide_render = True
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.04, 0.04, 0.05, 1)


def um(nome, az, el, ortho=None, so_rosto=False, wire=False):
    sc = p.nova_cena()
    p.importar_glb("Capuz")
    lo, hi = p.limites(malhas())
    if so_rosto:
        a, b = box_de(["Mascara", "Rosto"])
        centro = (a + b) / 2 + Vector((0, 0, 0.01))
        escala = ortho or 0.42
    else:
        centro = (lo + hi) / 2
        escala = ortho or max(hi.z - lo.z, hi.x - lo.x, hi.y - lo.y) * 1.15
    if wire:
        wire_real(sc)
    p.render(sc, nome, centro, escala, az, el)


def conjunto(nome, az, el, escala):
    """capuz no traje completo (todas as pecas modulares), close na cabeca; escala 1.0 mostra busto."""
    sc = p.nova_cena()
    p.montar(p.PECAS)
    a, b = box_de(["Capuz", "Mascara"])
    centro = (a + b) / 2 + Vector((0, 0, -0.10))
    p.render(sc, nome, centro, escala, az, el)


if __name__ == "__main__":
    if "conjunto" in sys.argv:
        conjunto("capuz_no_conjunto", 25, 8, 0.9)
        sys.exit(0)
    um("capuz_frente", 0, 5)
    um("capuz_3q", 35, 15)
    um("capuz_lado", 90, 5)
    um("capuz_costas", 180, 5)
    um("capuz_close", 12, 4, ortho=0.42, so_rosto=True)
    um("capuz_wire", 35, 15, wire=True)
