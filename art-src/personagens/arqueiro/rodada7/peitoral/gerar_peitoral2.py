"""Peitoral v2 (lapidacao): regera folhas do manto, ombreiras, braceletes, placa de osso, correias, a partir do GLB original do repo.
Uso: via regenerar_rodada7.py (a textura e feita por peitoral_textura2.py, que precisa de PIL)
Mantem ossos, pesos (copiados do vertice original mais proximo), UV (mesmas celulas), material, nomes. Teto 2200 tris."""
import bpy, bmesh, sys, os, math, collections, shutil, json, struct, random
import numpy as np
from mathutils import Vector, kdtree
import os as _os
_AQUI = _os.path.dirname(_os.path.abspath(__file__))
_R7 = _os.path.dirname(_AQUI)
_RAIZ = _os.path.abspath(_os.path.join(_R7, "..", "..", "..", ".."))
FONTE = _os.environ.get("ARQ_FONTE_ORIG", _os.path.join(_R7, "_fonte_original"))   # GLBs/texturas pre-polida (somente leitura)
SAIDA = _os.environ.get("ARQ_SAIDA", _os.path.join(_RAIZ, "godot", "art", "models", "personagens", "arqueiro"))
SRC=FONTE+_os.sep
OUT=_os.environ.get("ARQ_OUT", _os.path.join(SAIDA,"Arqueiro_Peitoral.glb"))
_os.makedirs(_os.path.dirname(OUT),exist_ok=True)
CY=0.07
random.seed(7); rnd=random.Random(7)
NT10=int(os.environ.get("NT10",12)); NT6=int(os.environ.get("NT6",32))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC+"Arqueiro_Peitoral.glb")
arm=next(o for o in bpy.data.objects if o.type=="ARMATURE")
ob=bpy.data.objects["SK_Archer_Peitoral"]; me=ob.data
bm=bmesh.new(); bm.from_mesh(me)
uvl=bm.loops.layers.uv.active; dl=bm.verts.layers.deform.active
TRIS0=sum(len(p.vertices)-2 for p in me.polygons)
key=lambda v:tuple(round(c,4) for c in v.co)
par={}
def f(x):
    par.setdefault(x,x)
    while par[x]!=x: par[x]=par[par[x]]; x=par[x]
    return x
for fc in bm.faces:
    ks=[key(v) for v in fc.verts]
    for a in ks[1:]: par[f(a)]=f(ks[0])
isl=collections.defaultdict(list)
for fc in bm.faces: isl[f(key(fc.verts[0]))].append(fc)
def sig(fs): return (sum(len(fc.verts)-2 for fc in fs), len({key(v) for fc in fs for v in fc.verts}))
groups=collections.defaultdict(list)
for k,fs in isl.items(): groups[sig(fs)].append(fs)
print({k:len(v) for k,v in groups.items()})
# KD de pesos: todos os vertices originais
kd=kdtree.KDTree(len(bm.verts)); allv=list(bm.verts)
for i,v in enumerate(allv): kd.insert(v.co,i)
kd.balance()
W={}  # index->dict de pesos (copia, pois os vertices serao removidos)
for v in allv: W[v.index]={k:x for k,x in v[dl].items()}
def wnear(p): return W[allv[kd.find(p)[1]].index]
def setw(v,w):
    for k,x in w.items(): v[dl][k]=x
def Fnew(vs,uvs,nref,smooth=False,away=None):
    fc=bm.faces.new(vs)
    for l,u in zip(fc.loops,uvs): l[uvl].uv=u
    fc.normal_update()
    ref=nref if nref is not None else None
    if ref is not None and fc.normal.dot(ref)<0: fc.normal_flip()
    fc.smooth=smooth
    return fc

# ======================= FOLHAS =======================
leaves=[]
for fs in groups[(10,10)]:
    pts={}
    for fc in fs:
        for l in fc.loops: pts[l.vert.index]=(l.vert.co.copy(),Vector(l[uvl].uv))
    root=[p for p,u in pts.values() if u.y<0.6]; tipp=[p for p,u in pts.values() if u.y>0.95]
    mid=[(p,u) for p,u in pts.values() if abs(u.y-0.673)<0.02]
    P0=sum(root,Vector())/len(root); T0=tipp[0]
    wid=max((a[0]-b[0]).length for a in mid for b in mid)
    cell=int(sum(u.x for p,u in pts.values())/len(pts)/0.125)
    nref=sum((fc.normal for fc in fs),Vector()).normalized()
    leaves.append(dict(P0=P0,T0=T0,w=wid,cell=min(cell,7),n=nref,fs=fs))
print("folhas",len(leaves))
for d in leaves:
    for fc in d["fs"]: bm.faces.remove(fc)
# camadas por altura da raiz
leaves.sort(key=lambda d:d["P0"].z)
NL=6
def back_of(P): 
    ang=math.atan2(P.x,-(P.y-CY)); return (1-math.cos(ang))/2, ang   # 0 frente .. 1 costas
# extras no manto de costas (densidade)
base=[d for d in leaves if back_of(d["P0"])[0]>0.55 and d["P0"].z<0.82]
extras=[]
EXTRA=int(os.environ.get("EXTRA",36))
for i in range(EXTRA):
    a=rnd.choice(base); 
    near=sorted(base,key=lambda d:(d["P0"]-a["P0"]).length)[1:4]; b=rnd.choice(near)
    t=rnd.uniform(.35,.65)
    P0=a["P0"].lerp(b["P0"],t)+Vector((0,rnd.uniform(.0,.02),rnd.uniform(-.05,.0)))
    T0=a["T0"].lerp(b["T0"],t)+Vector((0,0,rnd.uniform(-.03,0)))
    extras.append(dict(P0=P0,T0=T0,w=(a["w"]+b["w"])/2,cell=rnd.choice([0,1,2,3,4]),n=(a["n"]+b["n"]).normalized(),fs=[]))
leaves+=extras
leaves.sort(key=lambda d:d["P0"].z)
for i,d in enumerate(leaves): d["layer"]=min(NL-1,int(i/len(leaves)*NL))
# camada -> escala e paleta (celulas: 0 verde,1 oliva,2 verde-escuro,3 verde+ponta amarela,4 oliva+amarelo,5 branca,6 branca+amarelo,7 listrada)
SZ=[1.25,1.35,1.5,1.6,1.7,1.8]          # largura por camada (cima -> barra)
LM=[0.85,0.9,0.95,1.05,1.15,1.25]            # comprimento por camada
PAL=[[1,1,4,0,1,0],[1,0,4,1,0,6],[0,1,3,0,2],[0,2,3,0,3,5],[2,3,2,0,6,3],[2,3,2,5,6,3,7]]
cvec=Vector((0,CY,0))
for d in leaves:
    P0,T0=d["P0"],d["T0"]; L0=(T0-P0).length; dir0=(T0-P0).normalized()
    b,ang=back_of(P0); L=d["layer"]
    outh=Vector((P0.x,P0.y-CY,0)).normalized()
    depth=L/(NL-1)
    # direcao: cai, abre para fora conforme desce (silhueta de capa), mais atras e nos lados
    flare=0.03+0.17*depth*(0.5+0.8*b)
    dr=Vector((dir0.x*0.4,dir0.y*0.4,-1.0))+outh*flare; dr.normalize()
    side=math.sin(ang)**2
    m=LM[L]*(0.80+0.45*b+0.20*side)*rnd.uniform(0.75,1.2)*(0.62 if rnd.random()<0.33 else (1.28 if rnd.random()<0.18 else 1.0))
    Ln=max(L0,0.07)*m
    tipz=P0.z+dr.z*Ln
    if tipz<0.24: Ln*=(P0.z-0.24)/max(1e-3,(P0.z-tipz))
    d.update(dir=dr,L=Ln,w=d["w"]*SZ[L]*rnd.uniform(0.9,1.12),b=b,layerid=L)
    pal=PAL[L]; d["cell"]=rnd.choice(pal)
    d["wn"]=wnear(P0)
    d["score"]=Ln*3+d["w"]*8+b*0.15+depth*0.15
order=sorted(leaves,key=lambda d:-d["score"])
for i,d in enumerate(order): d["kind"]=10 if i<NT10 else (6 if i<NT10+NT6 else 4)
def mkleaf(d):
    P0=d["P0"]; a=d["dir"]; n0=d["n"]; kind=d["kind"]; Ln=d["L"]; w=d["w"]; c=0.0625+0.125*d["cell"]
    outh=Vector((P0.x,P0.y-CY,0)).normalized()
    n=(outh-a*outh.dot(a)).normalized() if abs(outh.dot(a))<0.97 else n0
    s=a.cross(n).normalized()
    curl=0.10+0.16*d["layerid"]/(NL-1)
    def C(t): return P0+a*(Ln*t)+n*(Ln*curl*t*t)+Vector((0,0,-Ln*0.06*t*t))
    ridge=0.20
    def V(p):
        v=bm.verts.new(p); setw(v,d["wn"]); return v
    def ring(t,wf,vv,hw):
        cc=C(t); ww=w*wf*0.5
        return [(V(cc-s*ww),(c-hw,vv)),(V(cc+n*ww*ridge*1.4),(c,vv)),(V(cc+s*ww),(c+hw,vv))]
    tipv=(V(C(1.0)),(c,0.99))
    def Q(r0,r1):
        (l0,m0,rr0),(l1,m1,rr1)=r0,r1
        for q in ([l0,m0,m1,l1],[m0,rr0,rr1,m1]):
            Fnew([x[0] for x in q],[x[1] for x in q],n)
    if kind==10:
        R=[ring(0,.45,.51,.027),ring(.34,1.0,.673,.055),ring(.68,.62,.836,.033)]
        Q(R[0],R[1]);Q(R[1],R[2])
        for (l,m,r) in [R[2]]:
            Fnew([l[0],m[0],tipv[0]],[l[1],m[1],tipv[1]],n);Fnew([m[0],r[0],tipv[0]],[m[1],r[1],tipv[1]],n)
    elif kind==6:
        R=[ring(0,.5,.51,.03),ring(.42,1.0,.72,.055)]
        Q(R[0],R[1])
        l,m,r=R[1]
        Fnew([l[0],m[0],tipv[0]],[l[1],m[1],tipv[1]],n);Fnew([m[0],r[0],tipv[0]],[m[1],r[1],tipv[1]],n)
    else:
        rt=(V(C(0)),(c,0.51)); R=ring(.40,1.0,.72,.055)
        l,m,r=R
        for tri in ([rt,m,l],[rt,r,m],[l,m,tipv],[m,r,tipv]):
            Fnew([x[0] for x in tri],[x[1] for x in tri],n)
for d in leaves: mkleaf(d)

# ======================= PLACAS ARREDONDADAS =======================
def frame(fs,outward_ref=None):
    vs=list({v.index:v for fc in fs for v in fc.verts}.values())
    P=np.array([v.co[:] for v in vs]); c0=P.mean(0)
    u_,s_,vt=np.linalg.svd(P-c0)
    ax=[Vector(vt[i]) for i in range(3)]
    ext=[max(abs(np.dot(P-c0,vt[i]))) for i in range(3)]
    o=sorted(range(3),key=lambda i:-ext[i])
    return vs,Vector(c0),ax[o[0]],ax[o[1]],ax[o[2]],ext[o[0]],ext[o[1]],ext[o[2]]
def uvbox(fs):
    u=np.array([l[uvl].uv[:] for fc in fs for l in fc.loops]); return u.min(0),u.max(0)
def wsrc_of(vs):
    k=kdtree.KDTree(len(vs))
    for i,v in enumerate(vs): k.insert(v.co,i)
    k.balance(); return k,[W[v.index] for v in vs]
def shell(fs,N,rings,bow=0.0,e=2.6,flatten=1.0,thick=1.0,smooth=True,outref=None,apex=1.0):
    """rings: lista de (h,escala) de baixo para cima; fecha com apice. Contorno super-elipse (cantos arredondados)."""
    vs,cen,eu,ev,en,su,sv,sn=frame(fs)
    u0,u1=uvbox(fs); kw,ww=wsrc_of(vs)
    o=outref(cen) if outref else Vector((cen.x,cen.y-CY,0))
    if en.dot(o)<0: en=-en
    for fc in list(fs): bm.faces.remove(fc)
    sn=sn*thick
    def NV(co,a,b):
        v=bm.verts.new(co); setw(v,ww[kw.find(co)[1]]); return v,(u0[0]+(u1[0]-u0[0])*(0.5+0.5*a),u0[1]+(u1[1]-u0[1])*(0.5+0.5*b))
    def sp(t):
        c,s=math.cos(t),math.sin(t)
        return math.copysign(abs(c)**(2/e),c),math.copysign(abs(s)**(2/e),s)
    R=[]
    for h,sc in rings:
        ring=[]
        for i in range(N):
            a,b=sp(2*math.pi*(i+0.5)/N)
            p=cen+eu*(a*su*sc)+ev*(b*sv*sc)+en*(h*sn-bow*(a*sc)**2*su*0.7)
            ring.append(NV(p,a*sc,b*sc))
        R.append(ring)
    ap=NV(cen+en*(rings[-1][0]*sn+sn*0.35*apex-bow*0*su),0,0)
    def Fq(vv): Fnew([x[0] for x in vv],[x[1] for x in vv],None,smooth)
    faces=[]
    for r0,r1 in zip(R,R[1:]):
        for i in range(N):
            j=(i+1)%N; faces.append([r0[i],r0[j],r1[j],r1[i]])
    for i in range(N): faces.append([R[-1][i],R[-1][(i+1)%N],ap])
    for vv in faces:
        fc=bm.faces.new([x[0] for x in vv])
        for l,x in zip(fc.loops,vv): l[uvl].uv=x[1]
        fc.normal_update(); mid=sum((x[0].co for x in vv),Vector())/len(vv)
        if fc.normal.dot(mid-cen)<0: fc.normal_flip()
        fc.smooth=smooth
    return vs
# ombreiras (3 por lado) e braceletes (2 por lado)
for fs in groups[(52,32)]:
    vs,cen,*_=frame(fs)
    if cen.z>0.8:   # ombreira: concha curva sobre o ombro, cai nas pontas
        shell(fs,10,[(-1,1.0),(-0.15,1.1),(0.55,.86)],bow=0.55,thick=1.0)
    else:           # bracelete de osso: placa curva em volta do punho
        shell(fs,8,[(-1,1.0),(-0.1,1.08),(0.6,.80)],bow=0.45,thick=1.0)
for fs in groups[(20,20)]:   # cinta de couro do bracelete
    shell(fs,6,[(-0.6,.95),(0.4,1.0)],bow=0.2,smooth=True)
# caixas -> almofadas (18 tris)
for fs in groups[(12,8)]:
    shell(fs,6,[(-1,.85),(0.15,1.0)],smooth=True,apex=1.0)
# placa de osso do peito (heptagonal): disco chanfrado de 14 lados
for fs in groups[(35,22)]:
    shell(fs,14,[(-0.2,1.3),(0.5,1.25),(1.0,.86)],e=2.0,thick=3.2,smooth=True,apex=0.4,outref=lambda c:Vector((0,-1,0)))
# correias: fita com secao arredondada, curvada sobre o torso
def strap(fs,SEG=7):
    vs,cen,eu,ev,en,su,sv,sn=frame(fs); u0,u1=uvbox(fs); kw,ww=wsrc_of(vs)
    P=np.array([v.co[:] for v in vs]); pr=[(Vector(v.co)-cen).dot(eu) for v in vs]
    o=Vector((cen.x,cen.y-CY,0))
    if en.dot(Vector((0,-1,0)))<0: en=-en
    for fc in list(fs): bm.faces.remove(fc)
    sv=max(sv*0.6,0.010); th=0.0065
    sec=[(-1,0.0),(-0.85,0.85),(0.85,0.85),(1,0.0)]
    rows=[]
    for i in range(SEG+1):
        t=i/SEG; u=-1+2*t
        # secao: afunila nas pontas
        tap=1.0-0.35*abs(u)**3
        row=[]
        for (a,h) in sec:
            p=cen+eu*(u*su)+ev*(a*sv*tap)+en*(h*th*tap)+en*(0.010+0.006*(1-u*u))
            v=bm.verts.new(p); setw(v,ww[kw.find(p)[1]])
            row.append((v,(u0[0]+(u1[0]-u0[0])*(0.5+0.5*a),u0[1]+(u1[1]-u0[1])*t)))
        rows.append(row)
    for r0,r1 in zip(rows,rows[1:]):
        for k in range(3):
            vv=[r0[k],r0[k+1],r1[k+1],r1[k]]
            fc=bm.faces.new([x[0] for x in vv])
            for l,x in zip(fc.loops,vv): l[uvl].uv=x[1]
            fc.normal_update()
            if fc.normal.dot(en)<0: fc.normal_flip()
            fc.smooth=True
    for row in (rows[0],rows[-1]):
        vv=[row[0],row[1],row[2],row[3]]
        fc=bm.faces.new([x[0] for x in vv])
        for l,x in zip(fc.loops,vv): l[uvl].uv=x[1]
        fc.normal_update()
        if fc.normal.dot(eu*(1 if row is rows[-1] else -1))<0: fc.normal_flip()
        fc.smooth=True
for fs in groups[(14,16)]: strap(fs)
bm.normal_update()
bm.to_mesh(me); bm.free()
# faces nao marcadas como smooth ficam planas (folhas); as redondas ja foram marcadas
tris=sum(len(p.vertices)-2 for p in me.polygons)
print("TRIS_ANTES",TRIS0,"TRIS_DEPOIS",tris)
bpy.ops.object.select_all(action="DESELECT")
for o in (arm,ob): o.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT,export_format="GLB",use_selection=True,export_animations=False,export_skins=True,export_yup=True,export_apply=False,export_materials="EXPORT",export_image_format="AUTO",export_leaf_bone=False)
# externaliza textura (mesmo uri do original) e pinta a textura nova
b=open(OUT,"rb").read(); n=struct.unpack("<I",b[12:16])[0]; j=json.loads(b[20:20+n]); off=20+n
bl=struct.unpack("<I",b[off:off+4])[0]; binario=bytearray(b[off+8:off+8+bl])
for im in j["images"]:
    bv=j["bufferViews"][im.pop("bufferView")]; im.pop("mimeType",None); im["uri"]="T_Arqueiro_Peitoral_BC.png"
    ini,tam=bv.get("byteOffset",0),bv["byteLength"]; fim=(ini+tam+3)&~3; del binario[ini:fim]; bv["byteLength"]=0
    for o in j["bufferViews"]:
        if o is not bv and o.get("byteOffset",0)>ini: o["byteOffset"]-=fim-ini
j["buffers"][0]["byteLength"]=len(binario)
js=json.dumps(j,separators=(",",":")).encode(); js+=b" "*(-len(js)%4); binario+=b"\0"*(-len(binario)%4)
open(OUT,"wb").write(struct.pack("<III",0x46546C67,2,12+8+len(js)+8+len(binario))+struct.pack("<I",len(js))+b"JSON"+js+struct.pack("<I",len(binario))+b"BIN\0"+bytes(binario))
