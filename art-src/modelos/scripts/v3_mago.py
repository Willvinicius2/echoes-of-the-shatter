"""Guerreiro v3: aplica a regua de proporcao (ombros/tronco mais largos, cabeca menor, pernas mais grossas) nas malhas E no esqueleto,
renderiza antes/depois e exporta os 6 FBX. Uso: blender -b SRC.blend --python v3_forma.py -- OUTDIR [export]"""
import bpy, sys, os, math, json
from mathutils import Vector
argv = sys.argv[sys.argv.index('--')+1:]
OUT = argv[0]; DO_EXPORT = len(argv) > 1 and argv[1] == 'export'
P = dict(head=1.0, torso_x=1.0, torso_y=1.0, arm_s=1.0, arm_dx=0.0, leg_s=1.0, leg_spread=0.0, crown=1.50, hood_z=1.28, hood_k=1.35, hood_taper=0.5, hood_back=0.10)
P.update(json.loads(os.environ.get('V3_P', '{}')))
os.makedirs(OUT, exist_ok=True)
arm = bpy.data.objects['Rig_Humanoid_Chibi']

def grp(n):
    if n in ('Head', 'Neck', 'socket_head'): return 'head'
    if 'Arm' in n or 'Shoulder' in n or 'Hand' in n or n.startswith('socket_weapon') or n == 'socket_cast':
        return 'armL' if (n.startswith('Left') or n.endswith('_l')) else ('armR' if (n.startswith('Right') or n.endswith('_r')) else 'armL')
    if 'Leg' in n or 'Foot' in n or 'Toes' in n: return 'legL' if n.startswith('Left') else 'legR'
    return 'torso'

def T(g, p):
    x, y, z = p
    if g == 'head':
        z0 = P['hood_z']
        if z <= z0: return Vector(p)
        t = min(1.0, (z - z0) / 0.24)
        tp = 1 - (1 - P['hood_taper']) * t
        return Vector((x * tp, 0.03 + (y - 0.03) * tp + P['hood_back'] * t * t, z0 + (z - z0) * P['hood_k']))
    if g == 'torso':
        return Vector((x * P['torso_x'], 0.03 + (y - 0.03) * P['torso_y'], z))
    if g in ('armL', 'armR'):
        sg = 1 if g == 'armL' else -1
        c = Vector((sg * 0.27, 0.03, 0.93)); q = c + (Vector(p) - c) * P['arm_s']; q.x += sg * P['arm_dx']; return q
    if g in ('legL', 'legR'):
        sg = 1 if g == 'legL' else -1
        xc = sg * 0.16; yc = 0.02
        return Vector((xc + (x - xc) * P['leg_s'] + sg * P['leg_spread'], yc + (y - yc) * P['leg_s'], z))
    return Vector(p)

def final(p, k):  # escala global p/ altura
    return p * k

def render(tag):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.render.resolution_x = sc.render.resolution_y = 800
    sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'TEXTURE'; sh.show_cavity = False
    sc.render.film_transparent = False
    w = bpy.data.worlds.new('w') if not sc.world else sc.world
    sc.world = w; w.color = (0.62, 0.62, 0.62)
    cam = bpy.data.objects.get('cam') or bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    if cam.name not in sc.collection.objects: sc.collection.objects.link(cam)
    sc.camera = cam; cam.data.type = 'ORTHO'; cam.data.ortho_scale = 1.9
    for name, (loc, rot) in dict(front=((0, -4, 0.78), (90, 0, 0)), q34=((2.6, -3.0, 1.2), (80, 0, 40)), side=((4, 0, 0.78), (90, 0, 90))).items():
        cam.location = loc; cam.rotation_euler = [math.radians(a) for a in rot]
        sc.render.filepath = os.path.join(OUT, f'{tag}_{name}.png'); bpy.ops.render.render(write_still=True)

render('antes')
def add_bevel(o):
    if any(m.type=='BEVEL' for m in o.modifiers): return
    b=o.modifiers.new('Bevel','BEVEL'); b.limit_method='ANGLE'; b.angle_limit=math.radians(40); b.width=0.0035; b.segments=2
    w=o.modifiers.new('WN','WEIGHTED_NORMAL'); w.keep_sharp=True
    # ordem: bevel, armature, wn
    while o.modifiers[0].type!='BEVEL': bpy.ops.object.modifier_move_up(modifier=o.modifiers[0].name) if False else None; break
    for i,m in enumerate(list(o.modifiers)):
        pass
    names=[m.name for m in o.modifiers]
    bpy.context.view_layer.objects.active=o
    bpy.ops.object.modifier_move_to_index(modifier=b.name,index=0)
    bpy.ops.object.modifier_move_to_index(modifier=w.name,index=len(o.modifiers)-1)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
for o in meshes:
    if o.name.startswith('SK_'): add_bevel(o)
# 1) malhas: mistura por pesos
for o in meshes:
    names = {vg.index: vg.name for vg in o.vertex_groups}
    for v in o.data.vertices:
        acc = Vector((0, 0, 0)); wsum = 0.0
        src = tuple(v.co)
        for ge in v.groups:
            w = ge.weight; n = names[ge.group]
            acc += T(grp(n), src) * w; wsum += w
        v.co = acc / wsum if wsum > 0 else Vector(src)
# 2) esqueleto: mesma funcao nos ossos
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
for eb in arm.data.edit_bones:
    g = grp(eb.name)
    h, t = T(g, tuple(eb.head)), T(g, tuple(eb.tail))
    eb.head, eb.tail = h, t
bpy.ops.object.mode_set(mode='OBJECT')
# 3) escala global p/ coroa = crown (sem a pluma: osso Head tail original 1.5)
k = 1.0
for o in meshes:
    for v in o.data.vertices: v.co = v.co * k
bpy.ops.object.mode_set(mode='EDIT') if False else None
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
for eb in arm.data.edit_bones:
    eb.head, eb.tail = eb.head * k, eb.tail * k
bpy.ops.object.mode_set(mode='OBJECT')
for o in meshes: o.data.update()
bpy.context.view_layer.update()
render('depois')
print('K', k, 'dims', [(o.name, tuple(round(d, 3) for d in o.dimensions)) for o in meshes])
if DO_EXPORT:
    gb = os.environ['GB_SCRIPTS']; sys.path.insert(0, gb)
    os.environ.setdefault('GB_ROOT', 'D:/openclaude/_trabalho-claude/tmp/gb_root')
    import gb_rig
    for o in meshes:
        if o.name.startswith('SK_'):
            gb_rig.export_fbx_rigged(arm, [o], os.path.join(OUT, o.name + '.fbx'))
    if len(argv)>2 and argv[2]=='nobody': sys.exit(0)
    body = [bpy.data.objects[n] for n in ('Body_Arms', 'Body_Feet', 'Body_Hands', 'Body_Head', 'Body_Legs', 'Body_Torso')]
    gb_rig.export_fbx_rigged(arm, body, os.path.join(OUT, 'SK_Mage_Body.fbx'))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'SK_Warrior_Modular_v3.blend'), compress=True)
