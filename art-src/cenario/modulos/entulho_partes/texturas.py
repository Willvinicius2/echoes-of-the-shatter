"""Parte 4: texturas. Materiais procedurais (pedra com veios, fissuras irregulares, musgo) cozidos em albedo + normal no UV único
e trocados por um material M_Entulho com imagens embutidas no .glb."""
import bpy, os

def _proc(m, base, musgo=False):
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], out.inputs[0])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    warp = nt.nodes.new("ShaderNodeTexNoise"); warp.inputs["Scale"].default_value = 3.0; warp.inputs["Detail"].default_value = 2
    wv = nt.nodes.new("ShaderNodeVectorMath"); wv.operation = 'ADD'
    nt.links.new(tc.outputs["Object"], wv.inputs[0]); nt.links.new(warp.outputs["Color"], wv.inputs[1])
    wv2 = nt.nodes.new("ShaderNodeVectorMath"); wv2.operation = 'SCALE'; wv2.inputs["Scale"].default_value = 0.35
    nt.links.new(warp.outputs["Color"], wv2.inputs[0]); nt.links.new(wv2.outputs[0], wv.inputs[1])
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 16 if not musgo else 40; n.inputs["Detail"].default_value = 14; n.inputs["Roughness"].default_value = 0.75
    veio = nt.nodes.new("ShaderNodeTexNoise"); veio.inputs["Scale"].default_value = 2.2; veio.inputs["Detail"].default_value = 3
    v = nt.nodes.new("ShaderNodeTexVoronoi"); v.feature = 'DISTANCE_TO_EDGE'; v.inputs["Scale"].default_value = 9.0
    for nd in (n, veio): nt.links.new(wv.outputs[0], nd.inputs["Vector"])
    nt.links.new(wv.outputs[0], v.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (*[c * 0.55 for c in base], 1); cr.color_ramp.elements[1].color = (*[min(1, c * 1.35) for c in base], 1)
    nt.links.new(n.outputs["Fac"], cr.inputs["Fac"])
    # fissuras: linhas finas só onde o ruído de veio passa de um limiar (irregulares, não uma grade de células)
    fis = nt.nodes.new("ShaderNodeMapRange"); fis.inputs[1].default_value = 0.0; fis.inputs[2].default_value = 0.035; fis.inputs[3].default_value = 0.1; fis.inputs[4].default_value = 1.0
    nt.links.new(v.outputs["Distance"], fis.inputs[0])
    msk = nt.nodes.new("ShaderNodeMapRange"); msk.inputs[1].default_value = 0.52; msk.inputs[2].default_value = 0.6
    nt.links.new(veio.outputs["Fac"], msk.inputs[0])
    mi = nt.nodes.new("ShaderNodeMix"); mi.inputs[0].default_value = 1.0
    nt.links.new(msk.outputs[0], mi.inputs[0]); mi.inputs[2].default_value = 1.0; nt.links.new(fis.outputs[0], mi.inputs[3])
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0
    cb = nt.nodes.new("ShaderNodeCombineColor")
    for i in range(3): nt.links.new(mi.outputs[0], cb.inputs[i])
    nt.links.new(cr.outputs[0], mx.inputs[6]); nt.links.new(cb.outputs[0], mx.inputs[7]); nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.9
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 1.4; bump.inputs["Distance"].default_value = 0.04
    h = nt.nodes.new("ShaderNodeMath"); h.operation = 'MULTIPLY'
    nt.links.new(n.outputs["Fac"], h.inputs[0]); nt.links.new(mi.outputs[0], h.inputs[1])
    nt.links.new(h.outputs[0], bump.inputs["Height"]); nt.links.new(bump.outputs[0], b.inputs["Normal"])

def cozer(o, M, pasta_prev=None, tam=1024):
    """Cozinha albedo + normal para o objeto único `o` (materiais em M) e troca por M_Entulho."""
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 16; sc.cycles.use_denoising = False
    _proc(M["pedra"], (0.21, 0.19, 0.16)); _proc(M["escura"], (0.11, 0.10, 0.10)); _proc(M["musgo"], (0.08, 0.10, 0.02), True)
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.004); bpy.ops.object.mode_set(mode='OBJECT')
    ia = bpy.data.images.new("entulho_albedo", tam, tam); inn = bpy.data.images.new("entulho_normal", tam, tam, is_data=True)
    def alvo(img):
        for m in o.data.materials:
            nd = m.node_tree.nodes.new("ShaderNodeTexImage"); nd.image = img; m.node_tree.nodes.active = nd; nd.name = "alvo"
    alvo(ia); bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, margin=6)
    alvo(inn); bpy.ops.object.bake(type='NORMAL', margin=6)
    # material final com as imagens embutidas
    f = bpy.data.materials.new("M_Entulho"); f.use_nodes = True; nt = f.node_tree; b = nt.nodes["Principled BSDF"]
    ta = nt.nodes.new("ShaderNodeTexImage"); ta.image = ia; tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = inn
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(ta.outputs[0], b.inputs["Base Color"]); nt.links.new(tn.outputs[0], nm.inputs["Color"]); nt.links.new(nm.outputs[0], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.9
    for p in o.data.polygons: p.material_index = 0
    o.data.materials.clear(); o.data.materials.append(f)
    if pasta_prev:
        ia.filepath_raw = os.path.join(pasta_prev, "entulho_albedo.png"); ia.file_format = 'PNG'; ia.save()
    return ia, inn
