import numpy as np
from PIL import Image
import key as K
def limpa(im):
    a=np.asarray(im).astype(float); al=a[...,3]/255
    semi=(al<0.98)&(al>0)
    g=a[...,1]
    for c in (0,2):
        a[...,c]=np.where(semi,np.minimum(a[...,c],g*1.05+8),a[...,c])
    return Image.fromarray(a.clip(0,255).astype(np.uint8),"RGBA")
def sai(n,saida,size):
    im=limpa(K.trim(K.key(f"hud/{n}.png")))
    im=im.resize(size,Image.LANCZOS); im.save(f"final/{saida}.png"); print(saida,im.size)
sai("hud_globo_moldura","hud_globo_moldura",(256,256))
sai("hud_slot_moldura","hud_slot_moldura",(96,96))
sai("hud_faixa_pedra","hud_faixa_pedra",(1280,147))
sai("hud_barra_chefe_moldura","hud_barra_chefe_moldura",(1024,199))
