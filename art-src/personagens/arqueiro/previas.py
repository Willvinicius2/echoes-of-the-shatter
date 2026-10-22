"""Renders de revisao (EEVEE, um por vez, 1024 px) dos GLBs do arqueiro.
Rodar: blender -b -P previas.py   (ARQ_SAIDA aponta para a pasta dos GLBs; saida em previas/_png)
"""
import os, sys, math
import bpy
from mathutils import Vector

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import _comum as c

OUT = os.path.join(AQUI, "previas", "_png")
os.makedirs(OUT, exist_ok=True)
PECAS = ["Capuz", "Peitoral", "Calca", "Luvas", "Botas", "Arco", "Aljava"]


def nova_cena():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x = sc.render.resolution_y = 1024
    sc.view_settings.view_transform = "Standard"
    sc.render.film_transparent = False
    w = bpy.data.worlds.new("w"); w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.32, 0.33, 0.36, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    sc.world = w
    for loc, en in (((-3, -4, 5), 3.0), ((4, 3, 2), 1.2)):
        l = bpy.data.lights.new("s", "SUN"); l.energy = en
        o = bpy.data.objects.new("s", l); sc.collection.objects.link(o)
        o.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return sc


def importar_glb(nome):
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(c.SAIDA, f"Arqueiro_{nome}.glb"))
    novos = [o for o in bpy.data.objects if o not in antes]
    for o in list(novos):  # esferas de forma de osso criadas pelo importador
        if o.name.startswith("Icosphere"):
            bpy.data.objects.remove(o); novos.remove(o)
    return novos


def osso_mundo(arm, nome):
    return arm.matrix_world @ arm.pose.bones[nome].head


def montar(nomes):
    objs = []
    for n in nomes:
        novos = importar_glb(n)
        if n in ("Arco", "Aljava"):
            arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
            raiz = [o for o in novos if o.parent is None][0]
            if n == "Arco" and arm:
                raiz.location = osso_mundo(arm, "socket_weapon_l")
            if n == "Aljava" and arm:
                ch = osso_mundo(arm, "Chest")
                raiz.location = (ch.x - 0.08, 0.27, ch.z + 0.05)  # costas = +Y no Blender (rosto em -Y)
                raiz.rotation_euler = (0, math.radians(20), 0)
        objs += novos
    return objs


def limites(objs):
    pts = []
    for o in objs:
        if o.type == "MESH":
            pts += [o.matrix_world @ v.co for v in o.data.vertices]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


_guard = {}


def wire_on(sc):
    mat = bpy.data.materials.new("wire"); mat.use_nodes = True
    nt = mat.node_tree; nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission"); o = nt.nodes.new("ShaderNodeOutputMaterial")
    e.inputs["Color"].default_value = (0.8, 0.9, 1, 1); e.inputs["Strength"].default_value = 2.0
    nt.links.new(e.outputs[0], o.inputs[0])
    for ob in sc.objects:
        if ob.type == "MESH":
            _guard[ob.name] = list(ob.data.materials)
            ob.data.materials.clear(); ob.data.materials.append(mat)
            m = ob.modifiers.new("wf", "WIREFRAME"); m.thickness = 0.0025; m.use_replace = True
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.04, 0.04, 0.05, 1)


def wire_off(sc):
    for ob in sc.objects:
        if ob.type == "MESH" and ob.name in _guard:
            ob.modifiers.remove(ob.modifiers["wf"]); ob.data.materials.clear()
            for m in _guard[ob.name]: ob.data.materials.append(m)
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.32, 0.33, 0.36, 1)


def render(sc, nome, centro, escala, az, el, wire=False, persp=False):
    cam_d = bpy.data.cameras.new("cam")
    cam_d.type = "PERSP" if persp else "ORTHO"
    cam_d.ortho_scale = escala
    cam_d.clip_end = 100
    cam = bpy.data.objects.new("cam", cam_d); sc.collection.objects.link(cam)
    d = 6.0
    a, e = math.radians(az), math.radians(el)
    cam.location = centro + Vector((math.sin(a) * math.cos(e) * d, -math.cos(a) * math.cos(e) * d, math.sin(e) * d))
    cam.rotation_euler = (centro - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    if wire:
        wire_on(sc)
    if False:
        sc.display.shading.type = "WIREFRAME"
        sc.display.shading.show_object_outline = False
        sc.display.shading.color_type = "SINGLE"
        sc.display.shading.single_color = (1, 1, 1)
        sc.display.shading.background_type = "VIEWPORT"
        sc.display.shading.background_color = (0.1, 0.1, 0.12)
        sc.display.render_aa = "8"
    sc.render.filepath = os.path.join(OUT, nome + ".png")
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    if wire:
        wire_off(sc)


def vistas(prefixo, nomes, rosto=True):
    nova = nova_cena()
    objs = montar(nomes)
    lo, hi = limites(objs)
    centro = (lo + hi) / 2
    escala = max(hi.z - lo.z, hi.x - lo.x, hi.y - lo.y) * 1.15
    lista = [("frente", 0, 5), ("lado", 90, 5), ("tres_quartos", 35, 15), ("costas", 180, 5)]
    for n, az, el in lista:
        render(nova, f"{prefixo}_{n}", centro, escala, az, el)
    render(nova, f"{prefixo}_wire", centro, escala, 35, 15, wire=True)
    if rosto and ("Capuz" in nomes):
        cabeca = Vector((0, 0.0, 1.27))
        render(nova, f"{prefixo}_rosto", cabeca, 0.8, 20, 8)


if __name__ == "__main__":
    alvo = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["conjunto"] + PECAS
    for a in alvo:
        if a == "conjunto":
            vistas("conjunto", PECAS)
        else:
            vistas(a.lower(), [a], rosto=(a == "Capuz"))
