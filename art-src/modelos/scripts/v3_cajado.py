import bpy, bmesh, math, sys, os
OUT=sys.argv[sys.argv.index('--')+1]
o=bpy.data.objects['SM_Weapon_Staff']
def render(tag):
    sc=bpy.context.scene; sc.render.engine='BLENDER_WORKBENCH'; sc.render.resolution_x=600; sc.render.resolution_y=900
    sh=sc.display.shading; sh.light='STUDIO'; sh.color_type='TEXTURE'
    w=sc.world or bpy.data.worlds.new('w'); sc.world=w; w.color=(0.55,0.55,0.55)
    cam=bpy.data.objects.get('cam') or bpy.data.objects.new('cam',bpy.data.cameras.new('cam'))
    if cam.name not in sc.collection.objects: sc.collection.objects.link(cam)
    sc.camera=cam; cam.data.type='ORTHO'; cam.data.ortho_scale=1.7
    cam.location=(3,-3,0.15); cam.rotation_euler=(math.radians(90),0,math.radians(45))
    sc.render.filepath=os.path.join(OUT,tag+'.png'); bpy.ops.render.render(write_still=True)
render('antes')
bm=bmesh.new(); bm.from_mesh(o.data)
uvl=bm.loops.layers.uv.active
img=bpy.data.images[[i.name for i in bpy.data.images if 'Staff_BC' in i.name][0]]
W,H=img.size; px=list(img.pixels)
def pix(u,v):
    x=min(W-1,max(0,int(u*W))); y=min(H-1,max(0,int(v*H))); i=(y*W+x)*4; return px[i],px[i+1],px[i+2]
best=None;bs=-9
for f in bm.faces:
    for l in f.loops:
        u,v=l[uvl].uv; r,g,b=pix(u,v); sc=b-(r+g)/2
        if sc>bs: bs=sc;best=(u,v)
print('BLUE',best,bs)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if sum(v.co.z for v in f.verts)/len(f.verts)>0.615],context='FACES')
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
# cristal novo: bipiramide hexagonal alongada, 6 lados
Z0=0.55; n=6; rad=0.10
def ring(z,r,rot=0):
    return [bm.verts.new((r*math.cos(rot+2*math.pi*k/n), r*math.sin(rot+2*math.pi*k/n), z)) for k in range(n)]
bot=bm.verts.new((0,0,Z0+0.015)); r1=ring(Z0+0.07,rad*0.6); r2=ring(Z0+0.17,rad,0.0); r3=ring(Z0+0.31,rad*0.85); top=bm.verts.new((0,0,Z0+0.46))
fs=[]
for k in range(n):
    k2=(k+1)%n
    fs.append(bm.faces.new((bot,r1[k2],r1[k])))
    fs.append(bm.faces.new((r1[k],r1[k2],r2[k2],r2[k])))
    fs.append(bm.faces.new((r2[k],r2[k2],r3[k2],r3[k])))
    fs.append(bm.faces.new((r3[k],r3[k2],top)))
for f in fs:
    for l in f.loops: l[uvl].uv=best
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(o.data); bm.free()
render('depois')
print('FACES',len(o.data.polygons))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'SM_Weapon_Staff_v3.blend'))
