import numpy as np, os
import os as _os
_AQUI = _os.path.dirname(_os.path.abspath(__file__))
_R7 = _os.path.dirname(_AQUI)
_RAIZ = _os.path.abspath(_os.path.join(_R7, "..", "..", "..", ".."))
FONTE = _os.environ.get("ARQ_FONTE_ORIG", _os.path.join(_R7, "_fonte_original"))   # GLBs/texturas pre-polida (somente leitura)
SAIDA = _os.environ.get("ARQ_SAIDA", _os.path.join(_RAIZ, "godot", "art", "models", "personagens", "arqueiro"))
TRAB = _os.environ.get("ARQ_TRAB", _os.path.join(_R7, "_trabalho", "capuz"))   # intermediarios (fora do git)
_os.makedirs(TRAB, exist_ok=True)
from PIL import Image, ImageFilter
rng=np.random.default_rng(7)
def weave(h,w,p=6,amp=0.07):
    y,x=np.mgrid[0:h,0:w].astype(float)
    a=np.sin(2*np.pi*x/p)*np.sin(2*np.pi*y/p)       # tafeta
    th=np.sin(2*np.pi*(x+ (y//p)%2*p/2)/p)         # fio
    n=rng.normal(0,1,(h,w)); n=np.array(Image.fromarray(((n-n.min())/(np.ptp(n))*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)),float)/255-0.5
    return 1+amp*(0.6*a+0.4*th)+0.10*n
# ---- capuz
o=Image.open(os.path.join(TRAB,"orig","T_Capuz_BC.png")).convert("RGB"); A=np.array(o,float)/255; H,W,_=A.shape
band=int(H*0.745)
lum=A[:,:,1]
col=lum[int(H*.08):band].mean(0)
k=np.ones(25)/25; colw=np.convolve(np.r_[col[-12:],col,col[:12]],k,'valid')[:W]
colw=(colw-colw.mean())/colw.std()
# dobras largas suaves em v tambem (caimento): 2 faixas verticais largas + gradiente para o barrado
y,x=np.mgrid[0:H,0:W].astype(float)
base=np.array([0.16,0.31,0.125])
fold=0.9*colw[None,:]*0.16+0.16*np.sin(2*np.pi*(x/W*2+0.1))+0.06*np.sin(2*np.pi*(x/W*5+0.4)+y/H*3)
fv=1-0.18*(np.clip((y-H*0.55)/(H*0.2),0,1))        # escurece perto do barrado
vig=1-0.25*np.clip(1-y/(H*0.08),0,1)*0
G=base[None,None,:]*(1+fold+0.0)[:,:,None]*fv[:,:,None]
# luz suave: topo mais claro
G=G*(1+0.30*np.clip(1-y/H*1.4,0,1)**1.5)[:,:,None]
G[:,:,1]*=1+0.10*np.clip(np.sin(2*np.pi*(x/W*2+0.1)),0,1)
G[:,:,0]*=1+0.18*np.clip(np.sin(2*np.pi*(x/W*2+0.1)),0,1)
G=G*weave(H,W)[:,:,None]
# tom: leve variacao de matiz (verde-oliva) em manchas MUITO suaves
n=rng.normal(0,1,(H//16,W//16)); n=np.array(Image.fromarray(((n-n.min())/np.ptp(n)*255).astype(np.uint8)).resize((W,H),Image.BICUBIC),float)/255-0.5
G[:,:,0]*=1+0.10*n; G[:,:,2]*=1-0.08*n
# faixa superior lisa original (tampa do capuz) = mesma base
# barrado bege: suaviza o ruido, trama e mantem pespontos
T=np.array(o.filter(ImageFilter.GaussianBlur(14)),float)/255
T[:]=np.array([0.66,0.53,0.29])*(1+0.1*np.sin(np.arange(W)/W*2*np.pi*3))[None,:,None]
Tl=np.array(o,float)/255
Tb=np.array(o.filter(ImageFilter.GaussianBlur(3)),float)/255
dash=np.clip((Tb.mean(2)-Tl.mean(2))*6,0,1)[:,:,None]     # pixels mais escuros que a vizinhanca = pesponto
tan=T*weave(H,W,5,0.09)[:,:,None]; tan=tan*(1-dash*0.9)+Tl*dash*0.9*0.8
# transicao capuz -> barrado: usa mascara original (verde vs bege)
r=Tl[:,:,0]-Tl[:,:,1]; m=np.clip((r+0.02)*14,0,1)      # bege: r>g
m=np.array(Image.fromarray((m*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)),float)/255
m[:int(H*0.7)]=0
out=G*(1-m[:,:,None])+tan*m[:,:,None]
# pespontos originais verticais nas bordas laterais (u=0/1)
sd=np.zeros((H,W)); sd[:, :8]=1; sd[:, -8:]=1
edge=np.clip((Tl.mean(2)-A.mean(2).mean()*0)*0,0,1)
ob=np.clip(Tl.mean(2)-G.mean(2),0,1)
out=np.where((sd[:,:,None]>0)&(Tl.mean(2)[:,:,None]>0.5),Tl,out)
# costura continua: linha de pesponto vertical nas bordas (ja) e sombra da dobra
Image.fromarray((np.clip(out,0,1)*255).astype(np.uint8)).save(os.path.join(TRAB,"T_Capuz_BC_new.png"))
# ---- face (CapuzDetalhe): quadrante verde 0..256 x 0..256 (topo-esq)
d=Image.open(os.path.join(TRAB,"orig","T_CapuzDetalhe_BC.png")).convert("RGB"); D=np.array(d,float)/255
Q=256
y,x=np.mgrid[0:Q,0:Q].astype(float)
b=np.array([0.20,0.37,0.15])
# dobras grandes diagonais que convergem ao centro + 2 pregas verticais; nada periodico
f=0.20*np.sin(2*np.pi*(0.9*x/Q+0.45*y/Q)+0.8)+0.16*np.sin(2*np.pi*(1.0*x/Q-0.6*y/Q)+2.1)+0.10*np.sin(2*np.pi*(2.3*x/Q)+0.3)
sh=np.clip(np.sin(2*np.pi*(0.9*x/Q+0.45*y/Q)+0.8),-1,0)*0.30
G2=b[None,None,:]*(1+f+sh)[:,:,None]*weave(Q,Q,5,0.08)[:,:,None]
n=rng.normal(0,1,(Q//16,Q//16)); n=np.array(Image.fromarray(((n-n.min())/np.ptp(n)*255).astype(np.uint8)).resize((Q,Q),Image.BICUBIC),float)/255-0.5
G2[:,:,0]*=1+0.1*n
# costura: pesponto tracejado grosso (3px) em curva, com sombra e furinhos
for xx in range(Q):
    yy=int(Q*0.5+8*np.sin(2*np.pi*xx/Q*1.0))
    if (xx//8)%2==0:
        for dy in (-3,-2,-1,0,1,2,3):
            if abs(dy)<=1: G2[yy+dy,xx]=np.array([0.80,0.72,0.46])*(1-0.12*abs(dy))
            elif abs(dy)==2: G2[yy+dy,xx]=G2[yy+dy,xx]*0.62
            else: G2[yy+dy,xx]=G2[yy+dy,xx]*0.85
D[:Q,:Q]=np.clip(G2,0,1)
Image.fromarray((D*255).astype(np.uint8)).save(os.path.join(TRAB,"T_CapuzDetalhe_BC_new.png"))
