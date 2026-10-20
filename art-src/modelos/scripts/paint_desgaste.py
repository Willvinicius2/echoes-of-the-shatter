import numpy as np, sys
from PIL import Image
src,dump,out=sys.argv[1:4]
tex=np.asarray(Image.open(src).convert('RGB')).astype(np.float32)
d=np.load(dump); pos,ok=d['pos'],d['ok']
X,Y,Z=pos[...,0],pos[...,1],pos[...,2]
def vnoise(p,f,seed):
    rng=np.random.default_rng(seed); g=rng.random((33,33,33)).astype(np.float32)
    q=(p*f)%32; i=np.floor(q).astype(int); fr=q-i; fr=fr*fr*(3-2*fr); i1=(i+1)%33
    def G(a,b,c): return g[a[...,0] if False else i[...,0]+a,i[...,1]+b,i[...,2]+c]
    c=0
    for a in (0,1):
        for b in (0,1):
            for e in (0,1):
                w=(fr[...,0] if a else 1-fr[...,0])*(fr[...,1] if b else 1-fr[...,1])*(fr[...,2] if e else 1-fr[...,2])
                c=c+w*g[(i[...,0]+a)%33,(i[...,1]+b)%33,(i[...,2]+e)%33]
    return c
P=np.stack([X,Y,Z],-1)
R,G,B=tex[...,0],tex[...,1],tex[...,2]
mx=tex.max(-1); mn=tex.min(-1); sat=(mx-mn)/(mx+1)
steel=ok&(sat<0.28)&(mx>85)
cloth=ok&(R>G*1.6)&(R>110)
n1=vnoise(P+1.7,9,1); n2=vnoise(P,34,2); n3=vnoise(P+5,14,3)
res=tex.copy()
# riscos finos no aco: linhas onde o ruido fino cruza 0.5
scr=(np.abs(n2-0.5)<0.022)&(n1>0.45)
res[steel&scr]*=0.62
res[steel&scr&(n3>0.6)]+=38
# manchas de ferrugem so do lado +X (assimetria) e amassados escuros do lado -X
rust=steel&(n3>0.66)&(X>-0.05)
res[rust]=res[rust]*0.55+np.array([150,84,40.])*0.45
dent=steel&(n1>0.72)&(X<0.05)
res[dent]*=0.78
# lama nas pernas/botas, mais forte atras
mud=ok&(Z<0.42)
f=np.clip((0.42-Z)/0.42,0,1)[...,None]*(0.35+0.5*n1[...,None])
res=np.where(mud[...,None],res*(1-f*0.6)+np.array([78,56,38.])*f*0.6,res)
# tecido: desbotado e manchado na barra, sem simetria
hem=cloth&(Z<0.75)
res[hem]=res[hem]*0.82+np.array([92,40,36.])*0.18
res[cloth&(n3>0.7)]*=0.78
# variacao geral entre pecas (desgaste por posicao)
res[ok]*=(0.93+0.14*n1[ok][:,None])
Image.fromarray(np.clip(res,0,255).astype(np.uint8)).save(out)
print('steel',int(steel.sum()),'cloth',int(cloth.sum()))
