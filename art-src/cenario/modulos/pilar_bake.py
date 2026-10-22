"""Bake de albedo e normal do pilar (poros, rachaduras finas, lascas, desgaste de aresta, juntas escuras) em PNG, embutidos no glb.
Método do estandarte (METODO_MODELAGEM_3D.md): dissolve coplanar, UV, materiais procedurais assados em 2 imagens, 1 material final.
Funciona no Blender/bpy sem GPU (Cycles CPU). Albedo sem luz; normal tangente OpenGL (+Y)."""
import bpy, bmesh, math, os

# tom único cinza-bege quente por classe de material do pilar (cor base já multiplica a cor de vértice: AO e sujeira)
TINTA = {
    "M_Pedra": (0.60, 0.545, 0.47),
    "M_PedraEscura": (0.30, 0.27, 0.235),
    "M_Estatua": (0.62, 0.565, 0.49),
    "M_Musgo": (0.20, 0.25, 0.085),
    "M_Ferro": (0.14, 0.125, 0.115),
    "M_Sombra": (0.20, 0.18, 0.16),
}


def _dissolver(o, graus=6):
    md = o.modifiers.new("d", 'DECIMATE'); md.decimate_type = 'DISSOLVE'
    md.angle_limit = math.radians(graus); md.delimit = {'MATERIAL'}
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=md.name)


def _uv(o):
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(88), island_margin=0.003, area_weight=0.6)
    bpy.ops.object.mode_set(mode='OBJECT')


def _no_pedra(m, img_bc, img_n, tinta, rugo=1.0):
    """Material procedural de bake: base color e relevo (bump) a partir de ruído, Voronoi e rachaduras; imagem alvo ativa."""
    m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; Lk = nt.links
    N.clear()
    out = N.new("ShaderNodeOutputMaterial"); b = N.new("ShaderNodeBsdfPrincipled")
    Lk.new(b.outputs["BSDF"], out.inputs["Surface"])
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping"); Lk.new(tc.outputs["Object"], mp.inputs["Vector"])
    # grão fino (poros) e manchas médias
    fino = N.new("ShaderNodeTexNoise"); fino.inputs["Scale"].default_value = 45; fino.inputs["Detail"].default_value = 7; fino.inputs["Roughness"].default_value = 0.65
    medio = N.new("ShaderNodeTexNoise"); medio.inputs["Scale"].default_value = 6.0; medio.inputs["Detail"].default_value = 5
    vor = N.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 14
    rach = N.new("ShaderNodeTexVoronoi"); rach.feature = 'DISTANCE_TO_EDGE'; rach.inputs["Scale"].default_value = 3.2
    for t in (fino, medio, vor, rach): Lk.new(mp.outputs["Vector"], t.inputs["Vector"])
    # rachaduras finas: linha escura onde a distância à aresta é pequena
    rr = N.new("ShaderNodeMapRange"); rr.inputs["From Min"].default_value = 0.0; rr.inputs["From Max"].default_value = 0.035
    rr.inputs["To Min"].default_value = 0.0; rr.inputs["To Max"].default_value = 1.0; rr.clamp = True
    Lk.new(rach.outputs["Distance"], rr.inputs["Value"])
    # tom: cor base × variação de mancha × grão
    var = N.new("ShaderNodeMapRange"); var.inputs["From Min"].default_value = 0.3; var.inputs["From Max"].default_value = 0.7
    var.inputs["To Min"].default_value = 0.78; var.inputs["To Max"].default_value = 1.12
    Lk.new(medio.outputs["Fac"], var.inputs["Value"])
    gr = N.new("ShaderNodeMapRange"); gr.inputs["From Min"].default_value = 0.35; gr.inputs["From Max"].default_value = 0.65
    gr.inputs["To Min"].default_value = 0.86; gr.inputs["To Max"].default_value = 1.08
    Lk.new(fino.outputs["Fac"], gr.inputs["Value"])
    # desgaste de aresta (convexo clareia, cavidade escurece) pela pointiness
    geo = N.new("ShaderNodeNewGeometry")
    pt = N.new("ShaderNodeMapRange"); pt.inputs["From Min"].default_value = 0.35; pt.inputs["From Max"].default_value = 0.65
    pt.inputs["To Min"].default_value = 0.78; pt.inputs["To Max"].default_value = 1.22; pt.clamp = True
    Lk.new(geo.outputs["Pointiness"], pt.inputs["Value"])
    cv = N.new("ShaderNodeAttribute"); cv.attribute_name = "Color"
    def mult(a, bsock, fac=1.0):
        x = N.new("ShaderNodeMixRGB"); x.blend_type = 'MULTIPLY'; x.inputs["Fac"].default_value = fac
        Lk.new(a, x.inputs[1]); Lk.new(bsock, x.inputs[2]); return x.outputs["Color"]
    def esc(v):
        x = N.new("ShaderNodeCombineColor");
        for i, n in enumerate(("Red", "Green", "Blue")): x.inputs[n].default_value = v
        return x.outputs["Color"]
    base = N.new("ShaderNodeRGB"); base.outputs[0].default_value = (*tinta, 1)
    c = mult(base.outputs[0], cv.outputs["Color"])
    for sock in (var.outputs["Result"], gr.outputs["Result"], pt.outputs["Result"]):
        # multiplica a cor por um escalar via cinza
        g = N.new("ShaderNodeCombineColor")
        for n in ("Red", "Green", "Blue"): Lk.new(sock, g.inputs[n])
        c = mult(c, g.outputs["Color"])
    # rachadura e junta: escurece (0.45 no centro da linha)
    rg = N.new("ShaderNodeMapRange"); rg.inputs["From Min"].default_value = 0.0; rg.inputs["From Max"].default_value = 1.0
    rg.inputs["To Min"].default_value = 0.42; rg.inputs["To Max"].default_value = 1.0
    Lk.new(rr.outputs["Result"], rg.inputs["Value"])
    g2 = N.new("ShaderNodeCombineColor")
    for n in ("Red", "Green", "Blue"): Lk.new(rg.outputs["Result"], g2.inputs[n])
    c = mult(c, g2.outputs["Color"])
    Lk.new(c, b.inputs["Base Color"])
    # relevo: poros + células + rachadura funda
    h1 = N.new("ShaderNodeMath"); h1.operation = 'MULTIPLY'; h1.inputs[1].default_value = 0.6
    Lk.new(fino.outputs["Fac"], h1.inputs[0])
    h2 = N.new("ShaderNodeMath"); h2.operation = 'MULTIPLY'; h2.inputs[1].default_value = 0.5
    Lk.new(vor.outputs["Distance"], h2.inputs[0])
    h3 = N.new("ShaderNodeMath"); h3.operation = 'ADD'; Lk.new(h1.outputs[0], h3.inputs[0]); Lk.new(h2.outputs[0], h3.inputs[1])
    h4 = N.new("ShaderNodeMath"); h4.operation = 'MULTIPLY'; h4.inputs[1].default_value = 1.6
    Lk.new(rr.outputs["Result"], h4.inputs[0])
    h5 = N.new("ShaderNodeMath"); h5.operation = 'ADD'; Lk.new(h3.outputs[0], h5.inputs[0]); Lk.new(h4.outputs[0], h5.inputs[1])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.9 * rugo; bp.inputs["Distance"].default_value = 0.02
    Lk.new(h5.outputs[0], bp.inputs["Height"])
    Lk.new(bp.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.85
    # imagem alvo do bake (ativa)
    it = N.new("ShaderNodeTexImage"); it.image = img_bc; N.active = it
    return it


def bake(o, out_dir, res=2048, nome="SM_Cripta_Pilar"):
    """Dissolve + UV + bake de albedo e normal + material único. Devolve o objeto pronto para exportar."""
    os.makedirs(out_dir, exist_ok=True)
    _dissolver(o)
    _uv(o)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 4
    img_bc = bpy.data.images.new("T_Pilar_BC", res, res, alpha=False)
    img_n = bpy.data.images.new("T_Pilar_N", res, res, alpha=False); img_n.colorspace_settings.name = 'Non-Color'
    img_bc.generated_color = (0.3, 0.27, 0.23, 1); img_n.generated_color = (0.5, 0.5, 1.0, 1)
    mats = list(o.data.materials)
    nodes_alvo = []
    for m in mats:
        t = TINTA.get(m.name, (0.5, 0.45, 0.4))
        rugo = 0.35 if m.name == "M_Musgo" else (0.5 if m.name == "M_Ferro" else 1.0)
        nodes_alvo.append(_no_pedra(m, img_bc, img_n, t, rugo))
    bk = sc.render.bake; bk.margin = 10; bk.use_clear = True; bk.use_selected_to_active = False
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    # albedo (sem luz)
    bk.use_pass_direct = False; bk.use_pass_indirect = False; bk.use_pass_color = True
    bpy.ops.object.bake(type='DIFFUSE')
    img_bc.filepath_raw = os.path.join(out_dir, "T_Cripta_Pilar_BC.png"); img_bc.file_format = 'PNG'; img_bc.save()
    # normal tangente
    for m, it in zip(mats, nodes_alvo): it.image = img_n; m.node_tree.nodes.active = it
    bk.normal_space = 'TANGENT'
    bpy.ops.object.bake(type='NORMAL')
    img_n.filepath_raw = os.path.join(out_dir, "T_Cripta_Pilar_N.png"); img_n.file_format = 'PNG'; img_n.save()
    # material final único
    fm = bpy.data.materials.new("M_PilarBake"); fm.use_nodes = True
    N = fm.node_tree.nodes; Lk = fm.node_tree.links
    b = N["Principled BSDF"]
    t1 = N.new("ShaderNodeTexImage"); t1.image = img_bc
    t2 = N.new("ShaderNodeTexImage"); t2.image = img_n
    nm = N.new("ShaderNodeNormalMap")
    Lk.new(t1.outputs["Color"], b.inputs["Base Color"]); Lk.new(t2.outputs["Color"], nm.inputs["Color"]); Lk.new(nm.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.85; b.inputs["Metallic"].default_value = 0.0
    o.data.materials.clear(); o.data.materials.append(fm)
    for p in o.data.polygons: p.material_index = 0
    for a in list(o.data.color_attributes): o.data.color_attributes.remove(a)
    return o
