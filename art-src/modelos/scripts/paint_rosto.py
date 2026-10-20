"""Rosto do Guerreiro menos 'de IA': pele em 2 tons (luz alto-esquerda), olhos assimetricos, cicatriz, sobrancelha pesada, boca de lado.
Projeta uma folha 2D (espaco do rosto, camera frontal ortografica 0,55 m centrada em x=0,z=1,25) nos texels do Body_Head."""
import numpy as np, sys
from PIL import Image, ImageDraw, ImageFilter
src,dump,out=sys.argv[1:4]
tex=np.asarray(Image.open(src).convert('RGB')).astype(np.float32)
d=np.load(dump); pos,nrm,ok,oid=d['pos'],d['nrm'],d['ok'],d['oid']
head=ok&(oid==4)
X=pos[...,0]; Z=pos[...,2]; Y=pos[...,1]
SC=0.55/900
px=X/SC+450; py=(1.25-Z)/SC+450
R,G,B=tex[...,0],tex[...,1],tex[...,2]
skin=head&(R>70)&(G/(R+1)>0.55)&(R-B>20)&(Y<0.1)&(nrm[...,1]<0.35)
face=skin&(py>270)&(py<720)&(px>200)&(px<690)
# 1) pele chapada 2 tons por luz (alto-esquerda-frente)
L=np.array([-0.45,-0.7,0.55]); L/=np.linalg.norm(L)
nd=np.clip((nrm*L).sum(-1),-1,1)
base=np.array([222,158,108.]); sh=np.array([168,104,76.]); hi=np.array([238,180,128.])
t=np.clip((nd-0.10)/0.45,0,1)[...,None]
col=np.where(t<0.5, sh+(base-sh)*np.clip(t*2,0,1), base+(hi-base)*np.clip(t*2-1,0,1))
step=np.round(t*3)/3; col=sh+(hi-sh)*step*0.85+ (base-sh)*0.1
# 2) folha de detalhes (900x900 RGBA, 4x supersample)
SS=4; W=900*SS
ov=Image.new('RGBA',(W,W),(0,0,0,0)); dr=ImageDraw.Draw(ov)
def E(cx,cy,rx,ry,fill,ang=0):
    dr.ellipse([(cx-rx)*SS,(cy-ry)*SS,(cx+rx)*SS,(cy+ry)*SS],fill=fill)
ink=(52,30,24,255)
def eye(cx,cy,rx,ry,tilt,iris=(122,78,46,255),hl=(-0.25,-0.25),open_=1.0):
    E(cx,cy,rx,ry*open_,(236,224,204,255))
    E(cx+rx*0.05,cy+ry*0.05,rx*0.62,ry*0.88*open_,iris)
    E(cx+rx*0.05,cy+ry*0.05,rx*0.30,ry*0.45*open_,(28,18,14,255))
    E(cx+rx*hl[0]*1.4,cy+ry*hl[1]*1.5,rx*0.16,ry*0.2,(255,255,255,255))
    # palpebra superior + contorno
    dr.arc([(cx-rx)*SS,(cy-ry*open_)*SS,(cx+rx)*SS,(cy+ry*open_)*SS],200,340,fill=ink,width=int(7*SS))
    dr.arc([(cx-rx)*SS,(cy-ry*open_)*SS,(cx+rx)*SS,(cy+ry*open_)*SS],20,160,fill=(96,56,44,255),width=int(3*SS))
# olho esquerdo (do personagem = direita da imagem) mais aberto, direito semicerrado e mais baixo
eye(352,447,40,31,0,open_=0.82,hl=(0.3,-0.3))
eye(548,438,43,36,0,open_=1.0,hl=(-0.3,-0.25))
def brow(pts,w):
    dr.line([(x*SS,y*SS) for x,y in pts],fill=(70,34,28,255),width=int(w*SS),joint='curve')
brow([(292,398),(330,384),(380,392)],18)      # esquerda da imagem: grossa e baixa, franzida
brow([(500,376),(552,360),(606,366)],14)      # outra: mais alta, arqueada
# cicatriz na sobrancelha da imagem-esquerda
dr.line([(548*SS,338*SS),(584*SS,412*SS)],fill=(206,128,112,255),width=int(8*SS))
dr.line([(548*SS,338*SS),(584*SS,412*SS)],fill=(128,64,60,255),width=int(3*SS))
for k in range(3): dr.line([((545+k*13)*SS,(352+k*22)*SS),((565+k*13)*SS,(346+k*22)*SS)],fill=(128,64,60,255),width=int(2.5*SS))
# nariz: sombra lateral + ponta
dr.line([(437*SS,452*SS),(428*SS,505*SS),(452*SS,520*SS)],fill=(150,92,66,255),width=int(5*SS),joint='curve')
E(455,512,13,8,(244,196,150,255))
# boca: meio sorriso de lado
dr.line([(402*SS,586*SS),(446*SS,596*SS),(502*SS,576*SS)],fill=ink,width=int(6*SS),joint='curve')
dr.line([(502*SS,576*SS),(514*SS,566*SS)],fill=ink,width=int(5*SS))
dr.line([(420*SS,606*SS),(470*SS,612*SS)],fill=(190,120,92,255),width=int(5*SS))
# barba rala + sujeira so de um lado
rng=np.random.default_rng(7)
for _ in range(260):
    x=rng.uniform(300,600); y=rng.uniform(630,690)
    if (x-450)**2/190**2+(y-520)**2/200**2<1.0: dr.ellipse([x*SS,y*SS,(x+2.6)*SS,(y+2.6)*SS],fill=(96,62,46,200))
E(300,520,34,20,(190,122,92,120)); E(590,500,26,16,(176,110,84,90))
ov=ov.filter(ImageFilter.GaussianBlur(SS*0.45)).resize((900,900),Image.LANCZOS)
ova=np.asarray(ov).astype(np.float32)
ix=np.clip(px.astype(int),0,899); iy=np.clip(py.astype(int),0,899)
O=ova[iy,ix]; a=(O[...,3]/255)[...,None]
res=tex.copy()
fm=face[...,None]
# mistura da pele nova: suave nas bordas da mascara
edge=np.clip(np.minimum(np.minimum(px-200,690-px),np.minimum(py-270,720-py))/25,0,1)[...,None]
res=np.where(fm,res*(1-edge*0.92)+col*edge*0.92,res)
det=(face|(head&(px>470)&(px<640)&(py>330)&(py<420)))&(nrm[...,1]<0.05)&(Y<0.1)
res=np.where(det[...,None],res*(1-a)+O[...,:3]*a,res)
Image.fromarray(np.clip(res,0,255).astype(np.uint8)).save(out)
print('face texels',int(face.sum()))
