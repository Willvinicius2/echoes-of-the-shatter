"""Parte 3 (assentamento): simulação de corpo rígido do Blender. As pedras caem de um volume pequeno sobre o chão e se apoiam
umas nas outras (gravidade plausível, inclinadas, sem face colada em face). Aplica a pose final e devolve os objetos."""
import bpy, math
from mathutils import Vector

def simular(objs, quadros=360):
    sc = bpy.context.scene
    if sc.rigidbody_world is None: bpy.ops.rigidbody.world_add()
    sc.rigidbody_world.point_cache.frame_end = quadros
    sc.frame_start = 1; sc.frame_end = quadros
    bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0)); chao = bpy.context.object; chao.name = "chao_fisica"
    bpy.ops.rigidbody.object_add(type='PASSIVE'); chao.rigid_body.friction = 0.9
    # funil de paredes: segura a queda num raio pequeno e se afasta (animado) no fim, deixando o monte alto assentar sozinho
    paredes = []
    n = 12; raio = 0.5
    for k in range(n):
        an = k / n * math.tau; px, py = math.cos(an) * raio, math.sin(an) * raio
        bpy.ops.mesh.primitive_cube_add(size=1, location=(px, py, 1.0)); w = bpy.context.object
        w.scale = (0.05, 0.42, 2.0); w.rotation_euler = (0, 0, an); bpy.ops.object.transform_apply(scale=True)
        bpy.ops.rigidbody.object_add(type='PASSIVE'); w.rigid_body.kinematic = True; w.rigid_body.friction = 0.3
        w.keyframe_insert("location", frame=quadros - 80); w.location = (px * 3.5, py * 3.5, 1.0); w.keyframe_insert("location", frame=quadros - 40)
        w.location = (px, py, 1.0); paredes.append(w)
    for o in objs:
        bpy.context.view_layer.objects.active = o; o.select_set(True)
        bpy.ops.rigidbody.object_add(type='ACTIVE')
        rb = o.rigid_body; rb.collision_shape = 'CONVEX_HULL'; rb.friction = 1.0; rb.restitution = 0.0
        rb.linear_damping = 0.35; rb.angular_damping = 0.4; rb.collision_margin = 0.002; rb.use_margin = True
        vol = o.dimensions.x * o.dimensions.y * o.dimensions.z; rb.mass = max(0.05, vol * 2000)
    for f in range(1, quadros + 1): sc.frame_set(f)
    for o in objs:
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.visual_transform_apply()
        bpy.ops.rigidbody.object_remove()
    for w in paredes: bpy.data.objects.remove(w, do_unlink=True)
    bpy.data.objects.remove(chao, do_unlink=True)
    sc.frame_set(1)
    return objs
