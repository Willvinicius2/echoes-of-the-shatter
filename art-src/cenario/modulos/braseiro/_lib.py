"""Biblioteca comum das partes do braseiro: materiais, helpers de forma e acabamento (chanfro, lascas, desgaste)."""
import bpy, bmesh, math, random
from mathutils import Vector, noise

objs = []

def mat(name, color, metal=0.7, rough=0.5, emit=None, strength=3.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metal; b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = strength
    return m

def make_materials():
    global IRON, TRIM, WORN, ASH, EMBER
    IRON = mat("M_Braseiro_Ferro", (0.075, 0.07, 0.08), 0.7, 0.5)
    TRIM = mat("M_Braseiro_Cinta", (0.16, 0.12, 0.09), 0.6, 0.4)       # cintas e rebites: ferro mais quente
    WORN = mat("M_Braseiro_Gasto", (0.27, 0.21, 0.15), 0.8, 0.32)      # arestas lascadas, metal vivo
    ASH = mat("M_Braseiro_Cinza", (0.05, 0.045, 0.045), 0.0, 1.0)
    EMBER = mat("M_Braseiro_Brasa", (0.35, 0.05, 0.01), 0.0, 0.8, emit=(1.0, 0.22, 0.03), strength=1.6)

bpy.ops.wm.read_factory_settings(use_empty=True)
make_materials()


def finish(o, material, bev=0.0, wear=0.0, cut=0.0, seed=0, smooth=False, chip=0.0):
    """Chanfro de 2 segmentos, subdivisão leve e desgaste por ruído (mais forte perto das arestas)."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    if bev:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bev, segments=2, profile=0.55, affect='EDGES')
    if cut:
        long_edges = [e for e in bm.edges if e.calc_length() > cut]
        bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=1, use_grid_fill=True)
    if wear:
        bm.verts.ensure_lookup_table(); bm.normal_update()
        for v in bm.verts:
            edge_k = 1.0 - min(1.0, sum(f.normal.dot(v.normal) for f in v.link_faces) / max(1, len(v.link_faces)))
            n = noise.noise(v.co * 9.0 + Vector((seed, seed * 0.7, 0)))
            v.co += v.normal * n * wear * (0.35 + 2.5 * edge_k)
    if chip:                                          # lascas: cantos escolhidos puxados para dentro, quebrando a silhueta
        c = sum((v.co for v in bm.verts), Vector()) / max(1, len(bm.verts))
        for v in bm.verts:
            if len(v.link_edges) >= 3 and random.random() < chip:
                v.co += (c - v.co).normalized() * random.uniform(0.012, 0.03)
    bm.to_mesh(o.data); bm.free()
    o.data.materials.append(material)
    for p in o.data.polygons: p.use_smooth = smooth
    objs.append(o); return o

def box(loc, size, rot=(0, 0, 0), m=IRON, bev=0.014, wear=0.003, cut=0.09, seed=0, chip=0.22):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = size; bpy.ops.object.transform_apply(scale=True)
    return finish(o, m, bev, wear, cut, seed, chip=chip)

def cone(loc, r, h, sides=4, rot=(0, 0, 0), m=IRON, r2=0.0, wear=0.004, seed=0):
    bpy.ops.mesh.primitive_cone_add(vertices=sides, radius1=r, radius2=r2, depth=h, location=(loc[0], loc[1], loc[2] + h / 2), rotation=rot)
    return finish(bpy.context.object, m, 0.008, wear, 0.07, seed)

def rivet(loc, r=0.022, rot=(0, 0, 0), m=WORN):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=4, radius=r, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = (1, 1, 0.55); bpy.ops.object.transform_apply(scale=True)
    return finish(o, m)

def ring(z, R, r, m=TRIM, seg=24):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=seg, minor_segments=8, location=(0, 0, z))
    o = bpy.context.object
    return finish(o, m, 0, 0.004, 0, 3, smooth=False)



def bake_vertex_colors(body):
    """Vertex color multiplicativa: arestas vivas ficam claras, planos e frestas escurecem, fuligem embaixo, ferrugem em manchas."""
    me = body.data
    bm = bmesh.new(); bm.from_mesh(me); bm.normal_update()
    cav = {}
    for v in bm.verts:
        fs = v.link_faces
        cav[v.index] = 1.0 - min(1.0, sum(f.normal.dot(v.normal) for f in fs) / max(1, len(fs)))   # 0 plano .. 1 aresta
    me.color_attributes.new("Col", 'BYTE_COLOR', 'CORNER')
    attr = me.color_attributes["Col"]
    me.color_attributes.active_color = attr
    for poly in me.polygons:
        mname = me.materials[poly.material_index].name
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index; co = me.vertices[vi].co
            if mname in ("M_Braseiro_Brasa", "M_Braseiro_Cinza"):
                attr.data[li].color = (1, 1, 1, 1); continue
            edge = min(1.0, cav[vi] * 2.5)
            g = noise.fractal(co * 6.0, 0.5, 2.0, 3) * 0.5 + 0.5                        # grunge de baixa/média frequência
            soot = max(0.0, 1.0 - co.z / 0.9) * 0.45 + (0.35 if co.z > 1.1 and co.z < 1.45 else 0.0) * max(0.0, 1 - math.hypot(co.x, co.y) / 0.7)
            rust = max(0.0, noise.noise(co * 4.0 + Vector((9, 4, 1)))) * 0.6
            k = 0.62 + 0.38 * edge - 0.3 * (1 - g) * (1 - edge) - soot * (1 - edge)
            k = max(0.18, min(1.0, k))
            attr.data[li].color = (min(1, k * (1 + rust * 0.35)), k * (1 - rust * 0.05), k * (1 - rust * 0.45), 1)
    bm.free()
