import bpy, sys, numpy as np
OUT=sys.argv[sys.argv.index('--')+1]
S=1024
for mat,tag in (('M_Warrior_Body','body'),('M_Warrior_Starter','starter')):
    pos=np.zeros((S,S,3),np.float32); nrm=np.zeros((S,S,3),np.float32); ok=np.zeros((S,S),bool); oid=np.zeros((S,S),np.int8)
    names=[]
    for o in bpy.data.objects:
        if o.type!='MESH' or not o.data.materials or o.data.materials[0].name!=mat: continue
        names.append(o.name); k=len(names)
        me=o.data; me.calc_loop_triangles(); uv=me.uv_layers.active.data
        for t in me.loop_triangles:
            U=np.array([uv[l].uv for l in t.loops]); U[:,1]=1-U[:,1]; U=U*S
            P=np.array([me.vertices[v].co for v in t.vertices]); N=np.array([me.vertices[v].normal for v in t.vertices])
            x0,y0=np.floor(U.min(0)).astype(int); x1,y1=np.ceil(U.max(0)).astype(int)
            xs,ys=np.meshgrid(np.arange(max(x0,0),min(x1+1,S)),np.arange(max(y0,0),min(y1+1,S)))
            if xs.size==0: continue
            px=xs+0.5; py=ys+0.5
            d=(U[1,1]-U[2,1])*(U[0,0]-U[2,0])+(U[2,0]-U[1,0])*(U[0,1]-U[2,1])
            if abs(d)<1e-9: continue
            a=((U[1,1]-U[2,1])*(px-U[2,0])+(U[2,0]-U[1,0])*(py-U[2,1]))/d
            b=((U[2,1]-U[0,1])*(px-U[2,0])+(U[0,0]-U[2,0])*(py-U[2,1]))/d
            c=1-a-b; m=(a>=-0.02)&(b>=-0.02)&(c>=-0.02)
            yy,xx=ys[m],xs[m]
            pos[yy,xx]=a[m,None]*P[0]+b[m,None]*P[1]+c[m,None]*P[2]
            nrm[yy,xx]=a[m,None]*N[0]+b[m,None]*N[1]+c[m,None]*N[2]
            ok[yy,xx]=True; oid[yy,xx]=k
    np.savez_compressed(f'{OUT}_{tag}.npz',pos=pos,nrm=nrm,ok=ok,oid=oid,names=np.array(names))
    print(tag,names,ok.mean())
