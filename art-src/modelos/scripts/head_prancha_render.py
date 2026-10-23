import bpy, math
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r"D:\openclaude\_trabalho-claude\modelos3d\arqueiro_dark\corpo\final\SK_ArcherDark_Body.blend")
sc=bpy.context.scene; sc.render.resolution_x=sc.render.resolution_y=900; sc.render.engine='BLENDER_EEVEE'
sc.view_settings.view_transform='Standard'
w=bpy.data.worlds.new("w"); w.use_nodes=True; w.node_tree.nodes["Background"].inputs[0].default_value=(0.42,0.42,0.42,1); w.node_tree.nodes["Background"].inputs[1].default_value=0.9; sc.world=w
for n,e,r in (("k",2.6,(50,0,-35)),("f",0.9,(65,0,140))):
    ld=bpy.data.lights.new(n,'SUN'); ld.energy=e; lo=bpy.data.objects.new(n,ld); lo.rotation_euler=[math.radians(a) for a in r]; sc.collection.objects.link(lo)
cam=bpy.data.cameras.new("c"); co=bpy.data.objects.new("c",cam); sc.collection.objects.link(co); sc.camera=co
P=r"D:\openclaude\_trabalho-claude\modelos3d\arqueiro_dark\cabeca\p_"
def shot(name, az, tz, dist, lens=85):
    cam.lens=lens; a=math.radians(az); t=Vector((0,0.0,tz)); co.location=t+Vector((math.sin(a)*dist,-math.cos(a)*dist,0))
    co.rotation_euler=(t-co.location).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=P+name+".png"; bpy.ops.render.render(write_still=True)
shot("f",0,1.62,1.1); shot("q",-35,1.62,1.1); shot("b",180,1.62,1.1)
shot("face",-12,1.66,0.55); shot("hair",-60,1.68,0.62)
hair=bpy.data.objects["SM_ArcherDark_Hair"]; body=bpy.data.objects["SK_ArcherDark_Body"]
g=bpy.data.materials.new("g"); g.use_nodes=True; g.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.78,0.78,0.8,1)
wm=bpy.data.materials.new("wm"); wm.use_nodes=True; wm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.05,0.05,0.08,1)
for o in (body,hair):
    o.data.materials.clear(); o.data.materials.append(g); o.data.materials.append(wm)
    for p in o.data.polygons: p.material_index=0
    m=o.modifiers.new("wf",'WIREFRAME'); m.thickness=0.0010; m.use_replace=False; m.material_offset=1
shot("wire",-25,1.66,0.8)
