import numpy as np, json
from PIL import Image, ImageDraw
import key as K
from exporta import limpa
def sai(n,saida,w=None,h=None):
    im=limpa(K.trim(K.key(f"hud_v2/{n}.png")))
    if w and not h: h=round(im.size[1]*w/im.size[0])
    im=im.resize((w,h),Image.LANCZOS); im.save(f"final/{saida}.png"); print(saida,im.size); return im
g=sai("hud_globo_moldura","hud_globo_moldura",270,270)
sai("hud_faixa_pedra","hud_faixa_pedra",1120,150)
b=sai("hud_barra_chefe_moldura","hud_barra_chefe_moldura",1240)
# raio interno do vidro (fração do raio externo), pela linha central
a=np.asarray(g)[...,3]; row=a[135]; solid=np.where(row>128)[0]
# primeiro trecho opaco da esquerda e onde acaba
i=solid[0]; j=i
while row[j]>128: j+=1
inner=(135-j)/135; print("raio_interno_frac",round(inner,3))
# icones: reduz brilho/contraste da luz (12%)
def suave(im):
    x=np.asarray(im).astype(float)/255; rgb=x[...,:3]
    lum=rgb.max(axis=2,keepdims=True)
    w=np.clip((lum-0.45)/0.55,0,1)           # só realces
    f=1-0.14*w                                 # corta até 14% nas luzes
    mean=rgb.mean(axis=(0,1),keepdims=True)
    rgb2=(rgb*f)
    rgb2=rgb2+(mean-rgb2)*0.04*w              # contraste da luz um pouco menor
    out=np.dstack([np.clip(rgb2,0,1),x[...,3]])
    return Image.fromarray((out*255).astype(np.uint8),"RGBA")
for i in ["tiro","esquiva","bloqueado","multishot","pierce","evasion","power","haste","swift","vitality"]:
    im=Image.open(f"final/icone_{i}.png").convert("RGBA"); suave(im).save(f"final/icone_{i}.png")
json.dump({"raio_interno_frac":inner},open("globo_info.json","w"))
