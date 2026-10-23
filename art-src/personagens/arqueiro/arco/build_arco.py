"""Arco do Arqueiro (v2), reconstruído do zero a partir da folha aprovada
(docs/arte/referencias-geracao/aprovadas/03_arqueiro.png + arco_folha_cartoon_8vistas).

Uso:  python build_arco.py [--variantes comum,incomum,...] [--render]
Saída: godot/art/models/personagens/arqueiro/Arqueiro_Arco[_<raridade>].glb
Eixos (iguais ao GLB antigo): comprimento em Z, centrado na empunhadura; corda em +Y; frente do arco em -Y.
Peça trocável por raridade: só mudam as cores/materiais (VARIANTES); a malha é a mesma.
"""
import bpy, bmesh, sys, os, math
import numpy as np
from mathutils import Vector, Matrix
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '../../../..'))
OUT_MODELS = os.environ.get('ARCO_OUT') or os.path.join(REPO, 'godot/art/models/personagens/arqueiro')
TMP = os.environ.get('ARCO_TMP', '/tmp/arco_tex')
os.makedirs(TMP, exist_ok=True)

# cores em sRGB 0-255
VARIANTES = {
    'comum':     dict(madeira=(112, 78, 48),  metal=(120, 120, 124), corda=(214, 200, 168), gema=None,            emis=0.0),
    'incomum':   dict(madeira=(58, 38, 30),   metal=(196, 142, 84),  corda=(206, 40, 66),   gema=(120, 220, 90),  emis=1.5),
    'raro':      dict(madeira=(36, 44, 62),   metal=(150, 176, 204), corda=(70, 160, 255),  gema=(80, 190, 255),  emis=2.5),
    'epico':     dict(madeira=(48, 30, 66),   metal=(176, 140, 210), corda=(200, 90, 255),  gema=(220, 110, 255), emis=3.0),
    'lendario':  dict(madeira=(40, 26, 22),   metal=(238, 190, 76),  corda=(255, 140, 40),  gema=(255, 170, 50),  emis=4.0),
}

# ---------- utilidades de malha ----------
def catmull(pts, n):
    pts = [np.array(p, float) for p in pts]
    P = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        for k in range(n):
            t = k / n
            p0, p1, p2, p3 = P[i-1], P[i], P[i+1], P[i+2]
            out.append(0.5 * ((2*p1) + (-p0+p2)*t + (2*p0-5*p1+4*p2-p3)*t*t + (-p0+3*p1-3*p2+p3)*t**3))
    out.append(pts[-1])
    return out

def sweep(bm, path, prof, sides, uv_scale=(1, 1), cap_start=True, cap_end=True, twist=0.0):
    """path: pontos no plano YZ (x=0). prof(s)->(rx,ry). Anel de 'sides' lados; X fixo, N = X x T."""
    uvl = bm.loops.layers.uv.verify()
    X = Vector((1, 0, 0))
    path = [(0, float(p[0]), float(p[1])) for p in path]
    rings = []
    L = [0.0]
    for i in range(1, len(path)):
        L.append(L[-1] + (Vector(path[i]) - Vector(path[i-1])).length)
    for i, p in enumerate(path):
        p = Vector(p)
        a = Vector(path[min(i+1, len(path)-1)]) - Vector(path[max(i-1, 0)])
        T = a.normalized()
        N = X.cross(T).normalized()
        s = i / (len(path)-1)
        rx, ry = prof(s)
        ring = []
        for k in range(sides):
            ang = 2*math.pi*k/sides + twist*s
            ring.append(bm.verts.new(p + X*math.cos(ang)*rx + N*math.sin(ang)*ry))
        rings.append(ring)
    faces = []
    for i in range(len(rings)-1):
        for k in range(sides):
            k2 = (k+1) % sides
            f = bm.faces.new((rings[i][k], rings[i][k2], rings[i+1][k2], rings[i+1][k]))
            for lp, (u, v) in zip(f.loops, ((k, i), (k+1, i), (k+1, i+1), (k, i+1))):
                lp[uvl].uv = (u/sides*uv_scale[0], L[v]*uv_scale[1])
            faces.append(f)
    for ring, flag, rev in ((rings[0], cap_start, True), (rings[-1], cap_end, False)):
        if flag:
            f = bm.faces.new(ring[::-1] if rev else ring)
            for lp in f.loops: lp[uvl].uv = (0.5, 0.5)
            faces.append(f)
    return faces

def new_obj(name, bm, mat):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    return o

def bevel_hard(o, width=0.0015, angle=35):
    bpy.context.view_layer.objects.active = o
    m = o.modifiers.new('bv', 'BEVEL'); m.width = width; m.segments = 2
    m.limit_method = 'ANGLE'; m.angle_limit = math.radians(angle)
    bpy.ops.object.modifier_apply(modifier='bv')

# ---------- texturas pintadas (numpy) ----------
def _noise(h, w, sc, rng):
    g = rng.random((h//sc+2, w//sc+2))
    im = Image.fromarray((g*255).astype('uint8')).resize((w, h), Image.BICUBIC)
    return np.asarray(im, float)/255

def tex_madeira(cor, rng, name):
    h, w = 1024, 512
    base = np.array(cor, float)/255
    grain = _noise(h, w, 4, rng)*0.5 + _noise(h, w, 16, rng)*0.3 + _noise(h//1, w, 64, rng)*0.2
    # veio ao longo do comprimento (V): ruído esticado em V
    g2 = np.asarray(Image.fromarray((rng.random((h//96+2, w//3+2))*255).astype('uint8')).resize((w, h), Image.BICUBIC), float)/255
    t = 0.55*grain + 0.45*g2
    img = base[None, None, :] * (0.55 + 0.9*t[..., None])
    # nós e manchas escuras
    for _ in range(14):
        cx, cy = rng.integers(0, w), rng.integers(0, h); r = rng.integers(8, 26)
        yy, xx = np.ogrid[:h, :w]
        m = np.exp(-(((xx-cx)/(r*0.5))**2 + ((yy-cy)/r)**2))
        img *= (1 - 0.4*m[..., None])
    # pintura à mão: pinceladas claras nas bordas do cilindro
    u = np.linspace(0, 1, w)[None, :, None]
    img *= 0.8 + 0.35*np.sin(u*math.pi)**1.5
    Image.fromarray((np.clip(img, 0, 1)*255).astype('uint8')).save(f'{TMP}/{name}_BC.png')
    # normal a partir do veio
    hm = t
    gx = np.gradient(hm, axis=1); gy = np.gradient(hm, axis=0)
    n = np.stack([-gx*6, gy*6, np.ones_like(hm)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    Image.fromarray(((n*0.5+0.5)*255).astype('uint8')).save(f'{TMP}/{name}_N.png')

def tex_metal(cor, rng, name):
    h = w = 512
    base = np.array(cor, float)/255
    n = _noise(h, w, 4, rng)*0.15 + _noise(h, w, 32, rng)*0.45 + _noise(h, w, 128, rng)*0.4
    img = base[None, None, :]*(0.72 + 0.55*n[..., None])
    # riscos finos
    for _ in range(25):
        x0, y0 = rng.integers(0, w), rng.integers(0, h); ln = rng.integers(20, 90)
        ang = rng.random()*math.pi
        for s in range(ln):
            x = int(x0 + s*math.cos(ang)) % w; y = int(y0 + s*math.sin(ang)) % h
            img[y, x] *= 0.65
    Image.fromarray((np.clip(img, 0, 1)*255).astype('uint8')).save(f'{TMP}/{name}_BC.png')
    gx = np.gradient(n, axis=1); gy = np.gradient(n, axis=0)
    nn = np.stack([-gx*5, gy*5, np.ones_like(n)], -1); nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
    Image.fromarray(((nn*0.5+0.5)*255).astype('uint8')).save(f'{TMP}/{name}_N.png')

def tex_couro(rng, name):
    h = w = 256
    base = np.array((52, 34, 26), float)/255
    n = _noise(h, w, 2, rng)*0.4 + _noise(h, w, 8, rng)*0.6
    img = base[None, None, :]*(0.6 + 0.9*n[..., None])
    Image.fromarray((np.clip(img, 0, 1)*255).astype('uint8')).save(f'{TMP}/{name}_BC.png')

# ---------- materiais ----------
def mat_img(name, bc, nrm=None, rough=0.55, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(bc); t.image.pack()
    nt.links.new(t.outputs['Color'], bsdf.inputs['Base Color'])
    if nrm:
        nm = nt.nodes.new('ShaderNodeNormalMap'); ti = nt.nodes.new('ShaderNodeTexImage')
        ti.image = bpy.data.images.load(nrm); ti.image.colorspace_settings.name = 'Non-Color'; ti.image.pack()
        nt.links.new(ti.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    bsdf.inputs['Roughness'].default_value = rough; bsdf.inputs['Metallic'].default_value = metal
    return m

def mat_flat(name, rgb, rough=0.4, emis=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    lin = [(c/255)**2.2 for c in rgb]
    b.inputs['Base Color'].default_value = (*lin, 1); b.inputs['Roughness'].default_value = rough
    if emis > 0:
        b.inputs['Emission Color'].default_value = (*lin, 1); b.inputs['Emission Strength'].default_value = emis
    return m

# ---------- geometria ----------
ESCALA = 0.86       # comprimento final ~1,15 m
HALF = 0.5          # meia-altura até a ancoragem da corda
ANCORA_Y = 0.150    # corda em +Y (igual ao GLB antigo)

def limb_path(sign):
    # (y, z) do grão da empunhadura até a ponta; sign=+1 braço de cima, -1 de baixo
    base = [(0.000, 0.060), (-0.012, 0.130), (-0.022, 0.230), (-0.006, 0.320),
            (0.040, 0.400), (0.100, 0.465), (0.146, 0.500), (0.136, 0.545), (0.108, 0.585)]
    pts = [(y, z*sign) for y, z in base]
    return catmull(pts, 8)

def limb_radius(s):
    # engrossa no meio do braço (madeira laminada), afina até a ponta
    return 0.027*(1-0.42*s) + 0.004*math.sin(s*math.pi*3)**2*(1-s)

def build_mesh_parts(mats, rng):
    parts = []
    # ---- braços (madeira) ----
    for sign in (1, -1):
        bm = bmesh.new()
        path = limb_path(sign)
        sweep(bm, path, lambda s: (0.0135*(1-0.5*s)+0.004, limb_radius(s)*0.95), 10, uv_scale=(1, 6))
        parts.append(new_obj(f'braco{sign}', bm, mats['madeira']))
    # ---- empunhadura central (madeira + couro + riser metálico) ----
    bm = bmesh.new()
    sweep(bm, [(0, -0.075), (0, -0.04), (0, 0.0), (0, 0.04), (0, 0.075)],
          lambda s: (0.019 + 0.005*math.sin(s*math.pi), 0.024 + 0.006*math.sin(s*math.pi)), 12)
    parts.append(new_obj('riser', bm, mats['madeira']))
    # couro: cinco voltas de cordão (toros achatados)
    bm = bmesh.new()
    for i in range(7):
        z = -0.032 + i*0.0107
        sweep(bm, [(0, z-0.0045), (0, z), (0, z+0.0045)],
              lambda s: (0.0235 + 0.003*math.sin(s*math.pi), 0.0285 + 0.003*math.sin(s*math.pi)), 12)
    g = new_obj('couro', bm, mats['couro']); parts.append(g)
    # cordão enrolado nos braços (como na folha)
    bm = bmesh.new()
    for sign in (1, -1):
        path = limb_path(sign)
        for s in (0.36, 0.40, 0.44, 0.48, 0.52, 0.56):
            i = s*(len(path)-1); i0 = int(i); f = i-i0
            y = path[i0][0]*(1-f)+path[i0+1][0]*f; z = path[i0][1]*(1-f)+path[i0+1][1]*f
            pr = limb_radius(s)*0.95
            sweep(bm, [(y, z-0.003*sign), (y, z), (y, z+0.003*sign)], lambda t: (0.0135*(1-0.5*s)+0.0095, pr+0.0035+0.0015*math.sin(t*math.pi)), 12)
    parts.append(new_obj('cordao', bm, mats['couro']))
    # ---- ferragens (metal) ----
    bm = bmesh.new()
    def spike(base_pt, tip_pt, w, t, bow=0.0):
        from mathutils import Vector as V2
        a, b = V2(base_pt), V2(tip_pt)
        d = (b-a); nrm = V2((-d.y, d.x)).normalized()
        mid = (a+b)/2 + nrm*bow
        path = catmull([tuple(a), tuple(mid), tuple(b)], 6)
        sweep(bm, path, lambda s: (t*(1-s**1.4)+0.0004, w*(1-s**0.85)+0.0003), 4, uv_scale=(1, 1))
    for sign in (1, -1):
        path = limb_path(sign)
        def pt(s):
            i = s*(len(path)-1); i0 = int(i); i1 = min(i0+1, len(path)-1); f = i-i0
            return ((path[i0][0]*(1-f)+path[i1][0]*f), (path[i0][1]*(1-f)+path[i1][1]*f))
        # luva metálica na raiz de cada braço
        sweep(bm, [pt(0.02), pt(0.10)], lambda s: (0.0255, 0.0285), 12)
        for s, direc, ln, w, out in ((0.34, -1, 0.150, 0.058, 0.55), (0.66, +1, 0.135, 0.050, 0.55)):
            y, z = pt(s)
            # direção do espinho: para fora do eixo (z cresce) e lateral em Y
            tip = (y + direc*ln*0.75, z + sign*ln*0.62)
            spike((y, z - sign*0.02), tip, w, 0.0085, bow=direc*0.018)
            # cinta metálica que prende a aleta
            sweep(bm, [pt(s-0.028), pt(s+0.028)], lambda t: (0.0215, 0.0255), 10)
        # ponta: chifre curvo + capa
        sweep(bm, [pt(0.90), pt(0.97), pt(1.0)], lambda s: (0.0125-0.004*s, 0.0145-0.004*s), 10)
        y, z = pt(1.0)
        horn = catmull([(y, z-sign*0.025), (y+0.004, z+sign*0.015), (y-0.010, z+sign*0.052), (y-0.040, z+sign*0.085)], 6)
        sweep(bm, horn, lambda s: (0.0105*(1-s**1.3)+0.0004, 0.0150*(1-s**1.05)+0.0003), 6)
        # nó da corda (anel de metal onde a corda prende)
        sweep(bm, [(y-0.0005, z-sign*0.012), (y-0.0005, z-sign*0.002)], lambda s: (0.0105, 0.0105), 10)
    mt = new_obj('metal', bm, mats['metal'])
    bevel_hard(mt, 0.0012)
    parts.append(mt)
    # ---- gema na empunhadura (frente, -Y) ----
    if mats.get('gema'):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.019)
        for v in bm.verts: v.co.z *= 1.6; v.co.x *= 0.85; v.co.y *= 0.75
        for v in bm.verts: v.co.y -= 0.036
        gm = new_obj('gema', bm, mats['gema'])
        for p in gm.data.polygons: p.use_smooth = False
        parts.append(gm)
        # engaste metálico
        bm = bmesh.new()
        r = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.032, radius2=0.022, depth=0.012)
        for v in bm.verts: v.co.z *= 1.0
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi/2, 3, 'X'))
        for v in bm.verts: v.co.y -= 0.0335; v.co.z *= 1.5
        parts.append(new_obj('engaste', bm, mats['metal']))
    # ---- corda (espessura visível) ----
    bm = bmesh.new()
    zt = 0.512
    cordas = []
    pts = [(ANCORA_Y-0.0, -zt), (ANCORA_Y-0.0, -zt*0.5), (ANCORA_Y-0.0, 0.0), (ANCORA_Y-0.0, zt*0.5), (ANCORA_Y-0.0, zt)]
    # ancoragem exata nos anéis de metal
    pts = [(0.1455, -0.4965)] + [(0.1455, -0.4965 + (0.9930)*k/12) for k in range(1, 12)] + [(0.1455, 0.4965)]
    sweep(bm, pts, lambda s: (0.0058, 0.0058), 8)
    # ponto de nock (engrossamento) no centro
    sweep(bm, [(0.1455, -0.018), (0.1455, 0.018)], lambda s: (0.0085, 0.0085), 8)
    parts.append(new_obj('corda', bm, mats['corda']))
    return parts

def build(var_name, var):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rng = np.random.default_rng(7)
    tex_madeira(var['madeira'], rng, f'arco_madeira_{var_name}')
    tex_metal(var['metal'], rng, f'arco_metal_{var_name}')
    tex_couro(rng, f'arco_couro_{var_name}')
    mats = dict(
        madeira=mat_img('M_Arqueiro_Arco', f'{TMP}/arco_madeira_{var_name}_BC.png', f'{TMP}/arco_madeira_{var_name}_N.png', rough=0.62),
        metal=mat_img('M_Arqueiro_Arco_Metal', f'{TMP}/arco_metal_{var_name}_BC.png', f'{TMP}/arco_metal_{var_name}_N.png', rough=0.38, metal=0.85),
        couro=mat_img('M_Arqueiro_Arco_Couro', f'{TMP}/arco_couro_{var_name}_BC.png', None, rough=0.8),
        corda=mat_flat('M_Arqueiro_Arco_Corda', var['corda'], rough=0.45, emis=0.4 if var['gema'] else 0.0),
    )
    if var['gema']:
        mats['gema'] = mat_flat('M_Arqueiro_Arco_Gema', var['gema'], rough=0.15, emis=var['emis'])
    parts = build_mesh_parts(mats, rng)
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts: p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    o = bpy.context.active_object; o.name = 'SM_Archer_Bow'; o.data.name = 'SM_Archer_Bow'
    o.scale = (ESCALA,)*3; bpy.ops.object.transform_apply(scale=True)
    # flat shading só no que é facetado fica por material; aplicar auto-smooth por ângulo
    bpy.ops.object.shade_smooth()
    return o

def export(var_name, o):
    suf = '' if var_name == 'incomum' else f'_{var_name}'
    os.makedirs(OUT_MODELS, exist_ok=True)
    path = os.path.join(OUT_MODELS, f'Arqueiro_Arco{suf}.glb')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_image_format='JPEG', export_jpeg_quality=90,
                              export_apply=True, use_selection=False)
    print('exportado', path, len(o.data.polygons), 'faces')

if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    vs = ['incomum']
    if '--variantes' in args:
        vs = args[args.index('--variantes')+1].split(',')
    for v in vs:
        o = build(v, VARIANTES[v])
        export(v, o)
