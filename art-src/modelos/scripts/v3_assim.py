import bpy, sys, os, math
from mathutils import Vector
a=sys.argv[sys.argv.index('--')+1:]; OUT=a[0]; TB=a[1]; TS=a[2]; EXPORT=len(a)>3
os.makedirs(OUT,exist_ok=True)
for im in bpy.data.images:
    if 'Warrior_Body_BC' in im.name: im.filepath=TB; im.reload()
    if 'Warrior_Starter_BC' in im.name: im.filepath=TS; im.reload()
def render(tag, cams):
    sc=bpy.context.scene; sc.render.engine='BLENDER_WORKBENCH'; sc.render.resolution_x=sc.render.resolution_y=900
    sh=sc.display.shading; sh.light='STUDIO'; sh.color_type='TEXTURE'
    w=sc.world or bpy.data.worlds.new('w'); sc.world=w; w.color=(0.6,0.6,0.6)
    cam=bpy.data.objects.get('cam') or bpy.data.objects.new('cam',bpy.data.cameras.new('cam'))
    if cam.name not in sc.collection.objects: sc.collection.objects.link(cam)
    sc.camera=cam; cam.data.type='ORTHO'; cam.data.ortho_scale=1.9
    for n,(loc,rot) in cams.items():
        cam.location=loc; cam.rotation_euler=[math.radians(r) for r in rot]
        sc.render.filepath=os.path.join(OUT,f'{tag}_{n}.png'); bpy.ops.render.render(write_still=True)
CAMS=dict(front=((0,-4,0.78),(90,0,0)),q34=((2.6,-3.0,1.0),(80,0,40)))
for o in bpy.data.objects:
    if o.name.startswith('Body_') and o.name!='Body_Head': o.hide_render=True
render('antes',CAMS)
ch=bpy.data.objects['SK_Warrior_Chest_Starter']
c=Vector((0,0.03,0.93))
for v in ch.data.vertices:
    p=v.co
    if p.z>0.80 and abs(p.x)>0.2:
        s=1.13 if p.x>0 else 0.95
        ctr=Vector((0.31 if p.x>0 else -0.31,0.03,0.96)); v.co=ctr+(p-ctr)*s
        if p.x>0: v.co.z+=0.012
ch.data.update()
render('depois',CAMS)
if EXPORT:
    sys.path.insert(0,'D:/openclaude/EchoesOfTheShatter/art-src/graybox/scripts'); os.environ.setdefault('GB_ROOT','D:/openclaude/_trabalho-claude/tmp/gb_root')
    import gb_rig
    arm=bpy.data.objects['Rig_Humanoid_Chibi']
    for o in bpy.data.objects: o.hide_render=False
    gb_rig.export_fbx_rigged(arm,[ch],os.path.join(OUT,'SK_Warrior_Chest_Starter.fbx'))
    body=[bpy.data.objects[n] for n in ('Body_Arms','Body_Feet','Body_Hands','Body_Head','Body_Legs','Body_Torso')]
    gb_rig.export_fbx_rigged(arm,body,os.path.join(OUT,'SK_Warrior_Body.fbx'))
