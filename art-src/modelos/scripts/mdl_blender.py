"""Auxiliares de Blender do pipeline de modelos: cena limpa, camera ortografica, mascara de UV e arrays de malha."""
import bpy, math, numpy as np
from mathutils import Vector

# camera ortografica de cada vista: (direcao da camera a partir do alvo, rotacao). Personagem de frente para -Y.
VIEWS = {
    "front": (Vector((0, -1, 0)), (math.pi / 2, 0, 0)),
    "back": (Vector((0, 1, 0)), (math.pi / 2, 0, math.pi)),
    "right": (Vector((-1, 0, 0)), (math.pi / 2, 0, -math.pi / 2)),   # camera em -X ve o lado direito do personagem
    "left": (Vector((1, 0, 0)), (math.pi / 2, 0, math.pi / 2)),
}


def clean_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def load_ply_obj(path, name):
    bpy.ops.wm.ply_import(filepath=path)
    ob = bpy.context.selected_objects[0]
    ob.name = name
    ob.data.name = name
    bpy.context.view_layer.objects.active = ob
    return ob


def mesh_arrays(ob):
    me = ob.data
    v = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', v)
    f = np.empty(len(me.polygons) * 3, dtype=np.int64); me.polygons.foreach_get('vertices', f)
    return v.reshape(-1, 3), f.reshape(-1, 3)


def raster_tris(tris2d, size, count=None):
    """Rasteriza triangulos 2D (n,3,2 em pixels) em size x size. Devolve (indice do triangulo ou -1, baricentricas)."""
    idx = -np.ones((size, size), np.int64)
    bary = np.zeros((size, size, 3), np.float32)
    for k, t in enumerate(tris2d):
        x0, y0 = np.floor(t.min(0)).astype(int); x1, y1 = np.ceil(t.max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, size - 1), min(y1, size - 1)
        if x1 < x0 or y1 < y0:
            continue
        a, b, c = t
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w0 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / d
        w1 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / d
        w2 = 1 - w0 - w1
        eps = 1e-6
        inside = (w0 >= eps) & (w1 >= eps) & (w2 >= eps)
        sub = idx[y0:y1 + 1, x0:x1 + 1]
        sub[inside] = k
        if count is not None:
            count[y0:y1 + 1, x0:x1 + 1] += inside
        bsub = bary[y0:y1 + 1, x0:x1 + 1]
        bsub[inside] = np.stack([w0, w1, w2], -1)[inside]
    return idx, bary


def uv_triangles(ob):
    """UV por triangulo (n,3,2) e vertices por triangulo (n,3) da malha de jogo triangulada."""
    me = ob.data
    me.calc_loop_triangles()
    uv = np.empty(len(me.loops) * 2); me.uv_layers[0].data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
    tl = np.array([t.loops[:] for t in me.loop_triangles], dtype=np.int64)
    tv = np.array([t.vertices[:] for t in me.loop_triangles], dtype=np.int64)
    return uv[tl], tv


def rasterize_uv_mask(ob, size=1024):
    uvt, _ = uv_triangles(ob)
    idx, _ = raster_tris(uvt * size, size)
    return idx >= 0


def make_camera(scale=2.2):
    cam = bpy.data.cameras.new('cam'); cam.type = 'ORTHO'; cam.ortho_scale = scale
    cam.clip_start, cam.clip_end = 0.01, 50
    co = bpy.data.objects.new('cam', cam)
    bpy.context.scene.collection.objects.link(co)
    bpy.context.scene.camera = co
    return co


def place_camera(co, view, center=Vector((0, 0, 0.8)), dist=5.0, scale=2.2):
    d, rot = VIEWS[view]
    co.location = center + d * dist
    co.rotation_euler = rot
    co.data.ortho_scale = scale
    bpy.context.view_layer.update()


def save_png(arr, path, name="tmp_img"):
    """Grava um array (h, w, 3|4) float 0..1 (linha 0 em cima) como PNG 8 bits."""
    h, w = arr.shape[:2]
    if arr.shape[2] == 3:
        arr = np.concatenate([arr, np.ones((h, w, 1), arr.dtype)], -1)
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(arr[::-1]).astype(np.float32).ravel())
    img.file_format = 'PNG'
    img.filepath_raw = path
    img.save()
    bpy.data.images.remove(img)


def load_png(path):
    """Le um PNG como array (h, w, 4) float 0..1 com a linha 0 em cima (sRGB como gravado)."""
    img = bpy.data.images.load(path)
    w, h = img.size
    a = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)[::-1].copy()
    bpy.data.images.remove(img)
    return a


def rot_bone_world(arm, name, axis, deg):
    """Gira o osso em torno do eixo do mundo, pelo pivo na cabeca do osso (filhos acompanham). Osso ausente: ignora."""
    import mathutils
    if name not in arm.pose.bones:
        return
    pb = arm.pose.bones[name]
    h = arm.matrix_world @ pb.head
    R = mathutils.Matrix.Translation(h) @ mathutils.Matrix.Rotation(math.radians(deg), 4, Vector(axis)) \
        @ mathutils.Matrix.Translation(-h)
    pb.matrix = arm.matrix_world.inverted() @ (R @ (arm.matrix_world @ pb.matrix))
    bpy.context.view_layer.update()


def apply_test_pose(arm):
    """Pose de teste: bracos para baixo, cabeca virada, passo (perna esquerda a frente, direita atras, joelho dobrado).
    Eixos do mundo do Blender: frente -Y, esquerda do personagem +X."""
    X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
    rot_bone_world(arm, "LeftUpperArm", Y, 28)
    rot_bone_world(arm, "RightUpperArm", Y, -28)
    rot_bone_world(arm, "Neck", Z, 15)
    rot_bone_world(arm, "Head", Z, 25)
    rot_bone_world(arm, "Spine", Z, -8)
    rot_bone_world(arm, "LeftUpperLeg", X, -30)
    rot_bone_world(arm, "LeftLowerLeg", X, 20)
    rot_bone_world(arm, "LeftFoot", X, 10)
    rot_bone_world(arm, "RightUpperLeg", X, 22)
    rot_bone_world(arm, "RightLowerLeg", X, 35)
    rot_bone_world(arm, "RightFoot", X, -20)


def apply_test_pose_quad(arm):
    """Pose de teste do quadrupede: cabeca virada e abaixada, rabo para o lado, passo (perna da frente esquerda e traseira direita avancam)."""
    X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
    rot_bone_world(arm, "Neck", Z, 20)
    rot_bone_world(arm, "Head", Z, 20)
    rot_bone_world(arm, "Head", X, 15)
    rot_bone_world(arm, "Tail1", Z, 30)
    rot_bone_world(arm, "Tail2", Z, 25)
    rot_bone_world(arm, "Spine", Z, -6)
    rot_bone_world(arm, "LeftFrontUpperLeg", X, -28)
    rot_bone_world(arm, "LeftFrontLowerLeg", X, 20)
    rot_bone_world(arm, "RightFrontUpperLeg", X, 22)
    rot_bone_world(arm, "RightHindUpperLeg", X, -25)
    rot_bone_world(arm, "RightHindLowerLeg", X, 20)
    rot_bone_world(arm, "LeftHindUpperLeg", X, 22)
    rot_bone_world(arm, "LeftHindLowerLeg", X, -15)


def test_pose(arm, kind):
    (apply_test_pose_quad if kind == "quadruped" else apply_test_pose)(arm)


def clear_pose(arm):
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()


def evaluated_coords(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    v = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', v)
    ev.to_mesh_clear()
    return v.reshape(-1, 3)


def texel_geometry(ob, size=1024):
    """Para cada texel da UV0: posicao e normal (de canto, respeita arestas vivas) na malha, e mascara de cobertura."""
    me = ob.data
    me.calc_loop_triangles()
    uv = np.empty(len(me.loops) * 2); me.uv_layers[0].data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
    tl = np.array([t.loops[:] for t in me.loop_triangles], dtype=np.int64)
    tv = np.array([t.vertices[:] for t in me.loop_triangles], dtype=np.int64)
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    cn = np.array([c.vector[:] for c in me.corner_normals]).reshape(-1, 3)
    uvt = uv[tl]
    uvt = uvt * size
    uvt[..., 1] = size - uvt[..., 1]          # linha 0 em cima
    idx, bary = raster_tris(uvt, size)
    ok = idx >= 0
    ii = np.maximum(idx, 0)
    pos = (co[tv[ii]] * bary[..., None]).sum(2)
    nrm = (cn[tl[ii]] * bary[..., None]).sum(2)
    nrm /= np.maximum(np.linalg.norm(nrm, axis=-1, keepdims=True), 1e-9)
    return dict(valid=ok, pos=pos, nrm=nrm, tri=idx, bary=bary)


def dilate(img, valid, iters=16):
    """Estende o conteudo dos texels validos para o vazio vizinho (gutter), ate iters pixels."""
    img = img.copy(); valid = valid.copy()
    for _ in range(iters):
        if valid.all():
            break
        acc = np.zeros_like(img); cnt = np.zeros(valid.shape, np.float32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                sv = np.roll(valid, (dy, dx), (0, 1)); si = np.roll(img, (dy, dx), (0, 1))
                acc += si * sv[..., None]; cnt += sv
        new = (~valid) & (cnt > 0)
        img[new] = acc[new] / cnt[new][:, None]
        valid |= new
    return img, valid
