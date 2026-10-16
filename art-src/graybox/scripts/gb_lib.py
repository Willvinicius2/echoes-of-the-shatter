"""Biblioteca graybox: construtor de malhas por primitivas, paleta de cores planas, exportacao FBX e previa.

Convencoes (docs/04_arquitetura.md secoes 3.1, 4.4 e 17):
- 1 unidade = 1 m, cena do Blender em metros (escala 1.0).
- Os scripts descrevem personagens em "espaco do personagem": frente +Y, esquerda -X, pes em z = 0.
  Builder.build(turn=True) e o esqueleto giram 180 graus em Z, e o asset fica de frente para -Y no Blender.
- Exportacao FBX com eixos canonicos (frente -Z, cima Y, Apply Transform, FBX Units Scale): o FBX declara
  o sistema Y-up padrao, entao o Unity nao precisa girar a raiz. Mapeamento Blender -> Unity:
  Unity (x, y, z) = (-x_b, z_b, -y_b); frente -Y no Blender = +Z no Unity.
- Um unico material por malha (M_Graybox_Palette) com textura de paleta 256x256 (16 x 16 amostras de 16 px):
  cada primitiva recebe UV no centro da amostra da sua cor e cor de vertice igual (fallback). Cores emissivas
  tambem aparecem no mapa de emissao (T_Graybox_Palette_E).
"""
import bpy, bmesh, math, os, struct, sys, zlib
from mathutils import Vector, Matrix, Euler

ROOT = os.environ.get("GB_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
FBX = ROOT + "/fbx"
PREV = ROOT + "/previews"
for d in (FBX, PREV):
    os.makedirs(d, exist_ok=True)

TURN = Matrix.Rotation(math.pi, 4, 'Z')   # espaco do personagem (frente +Y) -> Blender (frente -Y)

# ---------- paleta ----------
# (hex, emissivo). A ordem fixa o indice da amostra na textura: so acrescentar no fim.
PALETTE = [
    # neutros escuros (sem preto puro, 03 secao 3.4)
    ('#0F0B14', 0), ('#161117', 0), ('#1A1A20', 0), ('#1A1A2A', 0), ('#2A2A32', 0), ('#2A222F', 0),
    ('#3A3640', 0), ('#4A4650', 0), ('#0E2A30', 0),
    # metal
    ('#5A5F6A', 0), ('#9AA0AA', 0), ('#D8DCE4', 0), ('#8E8A96', 0), ('#C8CCD4', 0), ('#4E5360', 0), ('#6E7480', 0),
    # ouro e bronze
    ('#D9A441', 0), ('#A87A2E', 0), ('#7A5A2A', 0),
    # vermelhos
    ('#C02A22', 0), ('#E0301E', 0), ('#8A2A2A', 0), ('#B02A22', 0), ('#C0392B', 0), ('#6A1E22', 0),
    # marrons e couro
    ('#4A3A2E', 0), ('#5A3A24', 0), ('#5A4030', 0), ('#7A5230', 0), ('#6A4A2E', 0), ('#6A4428', 0), ('#3A2E28', 0),
    # verdes
    ('#2F7A32', 0), ('#5FD04A', 0), ('#3E5A2E', 0), ('#5B7A3A', 0), ('#A08A5A', 0), ('#2E4424', 0),
    # azuis
    ('#2E3A8C', 0), ('#3E4FA8', 0), ('#1E2660', 0),
    # pele, osso, tecido claro
    ('#E0B090', 0), ('#C8B890', 0), ('#E8E0D0', 0), ('#D8CCB0', 0), ('#E8DCC0', 0), ('#B8AC90', 0),
    # inimigos: pedra, pelo, espectro
    ('#8A8580', 0), ('#55504C', 0), ('#A89F90', 0), ('#6E675C', 0), ('#4FC8D8', 0), ('#1E5F6B', 0), ('#E8F8FF', 0),
    # cenario da Cripta (saturacao <= 35%, 03 secao 3.4)
    ('#3A3342', 0), ('#4E4858', 0), ('#5E5868', 0), ('#6A6474', 0), ('#7C7684', 0), ('#8A8490', 0), ('#6A5A55', 0),
    ('#4A4038', 0),
    # emissivos (olhos, cristal, fogo, runas)
    ('#FFC040', 1), ('#FF9A2E', 1), ('#FFFFFF', 1), ('#4A9CF0', 1), ('#FF7A1E', 1), ('#FFD27A', 1), ('#9AFF6A', 1),
    ('#3FE0D0', 1),
    # previa do esqueleto (nao entram em asset de jogo)
    ('#3A7AD0', 0), ('#D04A3A', 0), ('#E0C060', 0),
]
PAL_INDEX = {h.upper(): i for i, (h, _) in enumerate(PALETTE)}
assert len(PAL_INDEX) == len(PALETTE) <= 256, "paleta com cor repetida ou maior que 256"
PAL_COLS, PAL_SWATCH = 16, 16
PAL_SIZE = PAL_COLS * PAL_SWATCH
PAL_BC = FBX + "/T_Graybox_Palette_BC.png"
PAL_E = FBX + "/T_Graybox_Palette_E.png"
MAT_NAME = "M_Graybox_Palette"


def hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def pal_index(color):
    i = PAL_INDEX.get(color.upper())
    if i is None:
        raise KeyError(f"cor {color} fora da paleta de gb_lib.PALETTE")
    return i


def pal_uv(i):
    col, row = i % PAL_COLS, i // PAL_COLS
    return ((col + 0.5) / PAL_COLS, 1.0 - (row + 0.5) / PAL_COLS)


def _write_png(path, rows):
    """PNG RGB 8 bits sem dependencias (bytes estaveis entre maquinas)."""
    h, w = len(rows), len(rows[0]) // 3
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    if not os.path.exists(path) or open(path, "rb").read() != png:
        with open(path, "wb") as f:
            f.write(png)


def write_palette():
    for path, emissive_only in ((PAL_BC, False), (PAL_E, True)):
        rows = []
        for y in range(PAL_SIZE):
            r = bytearray()
            for x in range(PAL_SIZE):
                i = (y // PAL_SWATCH) * PAL_COLS + x // PAL_SWATCH
                if i < len(PALETTE) and (not emissive_only or PALETTE[i][1]):
                    r += bytes(hex_rgb(PALETTE[i][0]))
                else:
                    r += b"\x00\x00\x00"
            rows.append(r)
        _write_png(path, rows)


def palette_material():
    m = bpy.data.materials.get(MAT_NAME)
    if m:
        return m
    write_palette()
    m = bpy.data.materials.new(MAT_NAME)
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.85
    bsdf.inputs["Emission Strength"].default_value = 1.0
    nodes = []
    for path, sock, x in ((PAL_E, "Emission Color", -420), (PAL_BC, "Base Color", -420)):
        img = bpy.data.images.load(path, check_existing=True)
        img.colorspace_settings.name = 'sRGB'
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.interpolation = 'Closest'
        tex.location = (x, 300 if sock == "Base Color" else 0)
        nt.links.new(tex.outputs["Color"], bsdf.inputs[sock])
        nodes.append(tex)
    nt.nodes.active = nodes[-1]          # Workbench (cor TEXTURE) mostra a textura ativa
    m.diffuse_color = (0.5, 0.5, 0.5, 1.0)
    return m


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.unit_settings.system = 'METRIC'
    s.unit_settings.scale_length = 1.0


def rotm(rot):
    if rot is None:
        return Matrix.Identity(3)
    if isinstance(rot, Matrix):
        return rot.to_3x3()
    return Euler((math.radians(rot[0]), math.radians(rot[1]), math.radians(rot[2])), 'XYZ').to_matrix()


def aim(a, b):
    """Matriz 3x3 que alinha +Z ao vetor a->b."""
    d = (Vector(b) - Vector(a))
    return d.to_track_quat('Z', 'Y').to_matrix()


class Builder:
    """Acumula primitivas num unico bmesh com indice de paleta por face e grupos de vertices (skinning rigido).

    `xf` (Matrix 4x4) e uma transformacao de grupo aplicada a tudo o que for adicionado enquanto estiver definida.
    """

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.groups = []
        self.deform = self.bm.verts.layers.deform.verify()
        self.pal = self.bm.faces.layers.int.new("pal")
        self.xf = None

    # -- infraestrutura --
    def _finish(self, verts, faces, color, bone, emit):
        i = pal_index(color)
        if emit and not PALETTE[i][1]:
            raise ValueError(f"{color} nao esta marcada como emissiva na paleta")
        if self.xf is not None:
            bmesh.ops.transform(self.bm, matrix=self.xf, verts=list(verts))
        for f in faces:
            f[self.pal] = i
            f.smooth = False
        if bone:
            if bone not in self.groups:
                self.groups.append(bone)
            gi = self.groups.index(bone)
            for v in verts:
                v[self.deform].clear()
                v[self.deform][gi] = 1.0

    def add(self, shape, dim, loc, color, rot=None, bone=None, taper=1.0, seg=8, matname=None, emit=False,
            bev=0.03, tube=0.18):
        """shape: 'box', 'bbox' (caixa chanfrada, chanfro `bev` em metros), 'cyl' (cone se taper != 1),
        'sph' ou 'ring' (toro no plano XY, espessura relativa `tube`). `matname` e ignorado (paleta unica)."""
        bm = self.bm
        S = Matrix.Diagonal(Vector((dim[0], dim[1], dim[2], 1.0)))
        TR = Matrix.Translation(Vector(loc)) @ rotm(rot).to_4x4()
        if shape in ('box', 'bbox'):
            verts = bmesh.ops.create_cube(bm, size=1.0)['verts']
            bmesh.ops.transform(bm, matrix=S, verts=verts)
            faces = {f for v in verts for f in v.link_faces}
            b = min(bev, 0.45 * min(dim))
            if shape == 'bbox' and b > 0.002:
                edges = list({e for v in verts for e in v.link_edges})
                res = bmesh.ops.bevel(bm, geom=list(verts) + edges, offset=b, offset_type='OFFSET', segments=1,
                                      profile=0.5, affect='EDGES', clamp_overlap=True)
                # o chanfro recria as faces da caixa: pegar todas as faces ligadas aos vertices novos
                faces = {f for v in res['verts'] for f in v.link_faces}
            verts = list({v for f in faces for v in f.verts})
            bmesh.ops.transform(bm, matrix=TR, verts=verts)
        elif shape in ('cyl', 'sph', 'ring'):
            if shape == 'cyl':
                verts = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                                              radius1=0.5, radius2=0.5 * taper, depth=1.0)['verts']
            elif shape == 'sph':
                verts = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(2, seg // 2), radius=0.5)['verts']
            else:
                verts = self._ring(seg, max(3, seg // 2), tube)
            bmesh.ops.transform(bm, matrix=TR @ S, verts=verts)
            faces = {f for v in verts for f in v.link_faces}
        else:
            raise ValueError(shape)
        self._finish(verts, faces, color, bone, emit)

    def _ring(self, seg, sides, tube):
        bm = self.bm
        R = 0.5 - tube
        grid = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            c, s = math.cos(a), math.sin(a)
            ring = []
            for j in range(sides):
                b = 2 * math.pi * j / sides
                rr = R + tube * math.cos(b)
                ring.append(bm.verts.new((rr * c, rr * s, tube * math.sin(b))))
            grid.append(ring)
        for i in range(seg):
            for j in range(sides):
                a, b = grid[i][j], grid[(i + 1) % seg][j]
                c, d = grid[(i + 1) % seg][(j + 1) % sides], grid[i][(j + 1) % sides]
                bm.faces.new((a, b, c, d))
        return [v for r in grid for v in r]

    def limb(self, a, b, r0, color, bone=None, taper=1.0, seg=8, **kw):
        a, b = Vector(a), Vector(b)
        self.add('cyl', (r0 * 2, r0 * 2, (b - a).length), (a + b) / 2, color, rot=aim(a, b), bone=bone, taper=taper, seg=seg, **kw)

    def prism(self, profile_xz, y0, y1, color, bone=None):
        """Extruda um poligono simples (lista de (x, z), sentido anti-horario visto de -Y) entre y0 e y1."""
        bm = self.bm
        front = [bm.verts.new((x, y0, z)) for x, z in profile_xz]
        back = [bm.verts.new((x, y1, z)) for x, z in profile_xz]
        faces = [bm.faces.new(front), bm.faces.new(list(reversed(back)))]
        n = len(profile_xz)
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((front[j], front[i], back[i], back[j])))
        tri = bmesh.ops.triangulate(bm, faces=faces[:2], quad_method='BEAUTY', ngon_method='BEAUTY')
        faces = faces[2:] + tri['faces']
        bmesh.ops.recalc_face_normals(bm, faces=faces)
        self._finish(front + back, faces, color, bone, False)

    def arc(self, center, radius, a0, a1, n, radial, thick, color, plane='XY', shape='bbox', bev=0.02, overlap=1.04, **kw):
        """n blocos ao longo de um arco (graus). XY: anel no chao (espessura em Z). XZ: arco de porta (espessura em Y)."""
        cx, cy, cz = center
        step = math.radians(a1 - a0) / n
        tang = 2 * radius * math.sin(abs(step) / 2) * overlap
        for i in range(n):
            t = math.radians(a0) + step * (i + 0.5)
            if plane == 'XY':
                loc = (cx + radius * math.cos(t), cy + radius * math.sin(t), cz)
                self.add(shape, (tang, radial, thick), loc, color, rot=(0, 0, math.degrees(t) - 90), bev=bev, **kw)
            else:
                loc = (cx + radius * math.cos(t), cy, cz + radius * math.sin(t))
                self.add(shape, (tang, thick, radial), loc, color, rot=(0, 90 - math.degrees(t), 0), bev=bev, **kw)

    def build(self, coll=None, mesh_name=None, turn=False):
        if turn:
            bmesh.ops.transform(self.bm, matrix=TURN, verts=self.bm.verts)
        me = bpy.data.meshes.new(mesh_name or self.name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        me.materials.append(palette_material())
        # UV na amostra da paleta + cor de vertice (sRGB) por canto
        uv = me.uv_layers.new(name="UVMap")
        ca = me.color_attributes.new("Col", 'BYTE_COLOR', 'CORNER')
        pal = me.attributes["pal"].data
        for p in me.polygons:
            i = pal[p.index].value
            u = pal_uv(i)
            rgb = [c / 255 for c in hex_rgb(PALETTE[i][0])]
            for li in p.loop_indices:
                uv.data[li].uv = u
                ca.data[li].color_srgb = (rgb[0], rgb[1], rgb[2], 1.0)
        me.color_attributes.active_color = ca
        ob = bpy.data.objects.new(self.name, me)
        (coll or bpy.context.scene.collection).objects.link(ob)
        for g in self.groups:
            ob.vertex_groups.new(name=g)
        return ob


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def bbox(objs):
    pts = []
    for o in objs:
        if o.type != 'MESH':
            continue
        for c in o.bound_box:
            pts.append(o.matrix_world @ Vector(c))
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def to_unity(v):
    """Ponto do Blender -> Unity (x, y, z) com o preset canonico."""
    return (-v[0], v[2], -v[1])


def unity_bounds(mn, mx):
    a, b = to_unity(mn), to_unity(mx)
    lo = [round(min(a[i], b[i]), 3) + 0.0 for i in range(3)]
    hi = [round(max(a[i], b[i]), 3) + 0.0 for i in range(3)]
    return dict(min=lo, max=hi, size=[round(hi[i] - lo[i], 3) for i in range(3)])


def new_coll(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    return c


# Preset de exportacao (docs/04 secao 17.1): FBX Units Scale, transformacoes aplicadas, eixos canonicos.
FBX_PRESET = dict(global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
                  bake_space_transform=True, axis_forward='-Z', axis_up='Y',
                  object_types={'MESH', 'ARMATURE'}, use_mesh_modifiers=True, mesh_smooth_type='FACE',
                  colors_type='SRGB', add_leaf_bones=False, use_armature_deform_only=False,
                  primary_bone_axis='Y', secondary_bone_axis='X', bake_anim=False,
                  path_mode='RELATIVE', embed_textures=False)


def export_fbx(objs, path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, **FBX_PRESET)


def save_blend(path):
    bpy.ops.wm.save_as_mainfile(filepath=path, relative_remap=True, compress=True)


def version_info():
    return dict(blender=bpy.app.version_string, python=sys.version.split()[0])


# ---------- previa ----------
def setup_render(w=1600, h=900, outline=True):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sh = sc.display.shading
    sh.light = 'STUDIO'
    sh.studio_light = 'outdoor.sl'
    sh.color_type = 'TEXTURE'
    sh.show_shadows = True
    sh.shadow_intensity = 0.45
    sh.show_cavity = False
    sh.show_object_outline = outline
    sh.object_outline_color = (0.06, 0.04, 0.08)
    sh.background_type = 'VIEWPORT'
    sh.background_color = (0.035, 0.028, 0.05)
    sc.display.light_direction = (-0.3, 0.3, 0.9)   # sombra curta para baixo e a direita da tela
    if sc.world is None:
        sc.world = bpy.data.worlds.new("W")
    sc.world.color = (0.035, 0.028, 0.05)
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.exposure = 0.8
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.image_settings.compression = 100


def game_camera(center, dist, ortho_scale=None, yaw=45.0, pitch=-55.0, focal=None, fov_v=None):
    """Camera do jogo (docs/04 secao 3.2): rig com pitch 55 graus para baixo e yaw 45 graus.

    Com o preset canonico, o rig do Unity fica no quadrante +X+Y do alvo no Blender, olhando para -X-Y.
    `fov_v` (graus, vertical) reproduz a camera de perspectiva do jogo (14,2 graus a 42 m)."""
    cam = bpy.data.cameras.new("Cam")
    co = bpy.data.objects.new("Cam", cam)
    bpy.context.scene.collection.objects.link(co)
    if ortho_scale:
        cam.type = 'ORTHO'
        cam.ortho_scale = ortho_scale
    else:
        cam.type = 'PERSP'
        if fov_v:
            cam.sensor_fit = 'VERTICAL'
            cam.angle_y = math.radians(fov_v)
        else:
            cam.lens = focal or 85
    cam.clip_start = 0.5
    cam.clip_end = 500
    el = math.radians(-pitch)
    yw = math.radians(yaw)
    d = Vector((math.sin(yw) * math.cos(el), math.cos(yw) * math.cos(el), math.sin(el))) * dist
    co.location = Vector(center) + d
    direction = Vector(center) - co.location
    co.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = co
    return co


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
