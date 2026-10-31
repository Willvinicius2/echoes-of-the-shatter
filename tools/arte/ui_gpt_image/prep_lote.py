import json,sys,os,numpy as np
from PIL import Image,ImageDraw
prompts,indir,outdir,previa,cols=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],int(sys.argv[5])
ids=[i["id"] for i in json.load(open(prompts,encoding="utf-8"))]
os.makedirs(outdir,exist_ok=True)
def suave(im):
    x=np.asarray(im).astype(float)/255; rgb=x[...,:3]
    lum=rgb.max(axis=2,keepdims=True); w=np.clip((lum-0.45)/0.55,0,1)
    mean=rgb.mean(axis=(0,1),keepdims=True); r2=rgb*(1-0.14*w); r2=r2+(mean-r2)*0.04*w
    return Image.fromarray((np.dstack([np.clip(r2,0,1),x[...,3]])*255).astype(np.uint8),"RGBA")
rows=(len(ids)+cols-1)//cols
sheet=Image.new("RGB",(cols*140+10,rows*140+10),(20,20,24))
for n,i in enumerate(ids):
    im=Image.open(f"{indir}/{i}.png").convert("RGBA")
    w,h=im.size; m=int(w*0.012); im=im.crop((m,m,w-m,h-m)).resize((128,128),Image.LANCZOS)
    mask=Image.new("L",(512,512),0); ImageDraw.Draw(mask).rounded_rectangle((0,0,511,511),radius=44,fill=255)
    im.putalpha(mask.resize((128,128),Image.LANCZOS)); im=suave(im); im.save(f"{outdir}/{i}.png")
    sheet.paste(im,(10+(n%cols)*140,10+(n//cols)*140),im)
sheet.save(previa); print(len(ids))
