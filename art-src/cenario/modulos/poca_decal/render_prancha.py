"""Prévia no Blender: piso das lajes com a decal aplicada NO material do piso (cor, rugosidade e normal), como o Decal do Godot faz.
/tmp/venv/bin/python render_prancha.py <pasta_saida> [A,B,C]   (AMOSTRAS=24, RAPIDO=1)"""
import bpy, bmesh, math, os, sys
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
TEX = os.path.join(RAIZ, "godot", "art", "textures")
OUT = sys.argv[1]; NOMES = (sys.argv[2] if len(sys.argv) > 2 else "A,B,C").split(","); os.makedirs(OUT, exist_ok=True)

def img(path, nc=False):
    i = bpy.data.images.load(path); i.pack()
    if nc: i.colorspace_settings.name = 'Non-Color'
    return i

def cena(nome):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    w, h, _, _ = lib.VARIANTES[nome]; sc = bpy.context.scene; sc.render.engine = 'CYCLES'
    sc.cycles.samples = int(os.environ.get("AMOSTRAS", 24)); sc.cycles.use_denoising = True
    # ambiente: horizonte claro e frio, topo escuro
    wd = bpy.data.worlds.new("w"); wd.use_nodes = True; nt = wd.node_tree; sc.world = wd; bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); sp = nt.nodes.new("ShaderNodeSeparateXYZ"); rp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sp.inputs[0]); nt.links.new(sp.outputs["Z"], rp.inputs[0]); nt.links.new(rp.outputs[0], bg.inputs[0])
    cr = rp.color_ramp; cr.elements[0].position = 0.45; cr.elements[0].color = (0.02, 0.025, 0.05, 1); cr.elements[1].position = 0.78; cr.elements[1].color = (0.55, 0.7, 1.0, 1)
    e = cr.elements.new(0.58); e.color = (0.5, 0.62, 0.9, 1); bg.inputs[1].default_value = 1.7
    S = max(w, h) * 1.9; side = 14
    for k, (x, y, z) in enumerate(((2.4 * S / 4, -0.6 * S / 4, 1.1), (-1.0 * S / 4, 2.6 * S / 4, 1.3), (2.8 * S / 4, 1.6 * S / 4, 1.0))):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(x, y, z)); t = bpy.context.object
        mm = bpy.data.materials.new(f"tv{k}"); mm.use_nodes = True; n2 = mm.node_tree; n2.nodes.clear(); em = n2.nodes.new("ShaderNodeEmission"); em.inputs[0].default_value = (1.0, 0.5, 0.15, 1); em.inputs[1].default_value = 220
        oo = n2.nodes.new("ShaderNodeOutputMaterial"); n2.links.new(em.outputs[0], oo.inputs[0]); t.data.materials.append(mm); t.visible_camera = False; t.visible_shadow = False
    def luz(nm, e, loc, cor, size):
        d = bpy.data.lights.new(nm, 'AREA'); d.energy = e; d.color = cor; d.size = size; o = bpy.data.objects.new(nm, d); o.location = loc
        bpy.context.collection.objects.link(o); o.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return o
    luz("tocha", 70, (1.7 * S / 2.2, -0.9 * S / 2.2, 1.5), (1.0, 0.55, 0.25), 0.5)
    for l in (luz("frio", 120, (-1.8, 1.4, 2.2), (0.45, 0.6, 1.0), 1.4), luz("topo", 60, (0.2, -0.3, 3.0), (0.8, 0.85, 1.0), 1.5)): l.visible_glossy = False
    # piso: plano com UV em metros (lajes de 16 m por tile como no jogo) + decal projetada por coordenadas de objeto
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=side); uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops: lp[uv].uv = ((lp.vert.co.x + side) / 16.0 * 6.0, (lp.vert.co.y + side) / 16.0 * 6.0)
    me = bpy.data.meshes.new("piso"); bm.to_mesh(me); bm.free(); g = bpy.data.objects.new("piso", me); bpy.context.collection.objects.link(g)
    m = bpy.data.materials.new("piso"); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    t0 = nt.nodes.new("ShaderNodeTexImage"); t0.image = img(os.path.join(TEX, "T_Cripta_Piso.png"))
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = img(os.path.join(TEX, "T_Cripta_Piso_n.png"), True)
    mc = nt.nodes.new("ShaderNodeMix"); mc.data_type = 'RGBA'; mc.blend_type = 'MULTIPLY'; mc.inputs[0].default_value = 1; mc.inputs[7].default_value = (0.62, 0.62, 0.68, 1)
    nt.links.new(t0.outputs["Color"], mc.inputs[6])
    co = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")        # coordenadas da decal: 0..1 sobre w x h metros, centro no (0,0)
    mp.inputs["Scale"].default_value = (1 / w, 1 / h, 1); mp.inputs["Location"].default_value = (0.5, 0.5, 0)
    nt.links.new(co.outputs["Object"], mp.inputs[0])
    da = nt.nodes.new("ShaderNodeTexImage"); da.image = img(os.path.join(TEX, f"T_Poca_{nome}_albedo.png")); da.extension = 'CLIP'; da.interpolation = 'Linear'
    dor = nt.nodes.new("ShaderNodeTexImage"); dor.image = img(os.path.join(TEX, f"T_Poca_{nome}_orm.png"), True); dor.extension = 'CLIP'
    dn = nt.nodes.new("ShaderNodeTexImage"); dn.image = img(os.path.join(TEX, f"T_Poca_{nome}_n.png"), True); dn.extension = 'CLIP'
    for t in (da, dor, dn): nt.links.new(mp.outputs[0], t.inputs[0])
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; nt.links.new(da.outputs["Alpha"], mx.inputs[0]); nt.links.new(mc.outputs[2], mx.inputs[6]); nt.links.new(da.outputs["Color"], mx.inputs[7])
    nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    sep = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(dor.outputs["Color"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMix"); mr.data_type = 'FLOAT'; mr.inputs[2].default_value = 0.55                      # rugosidade: piso -> decal onde há alfa
    gain = nt.nodes.new("ShaderNodeMath"); gain.operation = 'MULTIPLY'; gain.inputs[1].default_value = 2.2; gain.use_clamp = True
    nt.links.new(da.outputs["Alpha"], gain.inputs[0]); nt.links.new(gain.outputs[0], mr.inputs[0]); nt.links.new(sep.outputs["Green"], mr.inputs[3]); nt.links.new(mr.outputs[0], b.inputs["Roughness"])
    mn = nt.nodes.new("ShaderNodeMix"); mn.data_type = 'RGBA'; mn.inputs[6].default_value = (0.5, 0.5, 1.0, 1); nt.links.new(dn.outputs["Alpha"], mn.inputs[0]); nt.links.new(dn.outputs["Color"], mn.inputs[7])
    nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(mn.outputs[2], nm.inputs["Color"]); nm.inputs["Strength"].default_value = 1.0; nt.links.new(nm.outputs[0], b.inputs["Normal"])
    g.data.materials.append(m)
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); bpy.context.collection.objects.link(cam); sc.camera = cam
    return sc, cam, S

def render(sc, cam, loc, alvo, path, lente):
    cam.location = loc; cam.data.lens = lente; cam.rotation_euler = (Vector(alvo) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sc.render.resolution_x, sc.render.resolution_y = 720, 500; sc.render.filepath = path; bpy.ops.render.render(write_still=True)

for nome in NOMES:
    sc, cam, S = cena(nome); k = S / 2.2; w, h, _, _ = lib.VARIANTES[nome]
    vistas = {"tq": ((1.5 * k, -1.5 * k, 0.95 * k), 40), "frente": ((0, -1.7 * k, 0.5 * k), 40), "lado": ((1.9 * k, 0.2 * k, 0.45 * k), 40),
              "topo": ((0.001, -0.2 * k, 2.6 * k), 36), "close": ((0.55 * k, -0.7 * k, 0.16 * k), 38)}
    for a, (loc, lente) in vistas.items():
        if os.environ.get("RAPIDO") and a not in ("tq", "close"): continue
        render(sc, cam, loc, (0, 0, 0), os.path.join(OUT, f"poca_{nome}_{a}.png"), lente)
