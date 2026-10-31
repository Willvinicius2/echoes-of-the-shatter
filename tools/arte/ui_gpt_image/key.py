import numpy as np
from PIL import Image
def key(path):
    a=np.asarray(Image.open(path).convert("RGB")).astype(float)
    r,g,b=a[...,0],a[...,1],a[...,2]
    mag=(np.minimum(r,b)-g)            # magenta-ness
    alpha=np.clip(1-(mag-40)/90,0,1)   # <40 opaque, >130 transparent
    # despill: reduce magenta cast on semi pixels
    spill=np.clip(np.minimum(r,b)-g,0,None)*(alpha<1)
    a[...,0]-=spill*0.6; a[...,2]-=spill*0.6
    out=np.dstack([np.clip(a,0,255),alpha*255]).astype(np.uint8)
    return Image.fromarray(out,"RGBA")
def trim(im):
    bb=im.split()[3].point(lambda v:255 if v>20 else 0).getbbox(); return im.crop(bb)
if __name__=="__main__":
    import sys
    for n,size in [("hud_globo_moldura",(224,224)),("hud_slot_moldura",(72,72)),("hud_faixa_pedra",None),("hud_barra_chefe_moldura",None)]:
        im=trim(key(f"hud/{n}.png")); print(n,im.size)
        im.save(f"hud/{n}_key.png")
