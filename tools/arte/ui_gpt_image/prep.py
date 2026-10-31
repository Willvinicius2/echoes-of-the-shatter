import sys,os
from PIL import Image,ImageDraw
ids=["tiro","esquiva","bloqueado","multishot","pierce","evasion","power","haste","swift","vitality"]
os.makedirs("final",exist_ok=True)
sheet=Image.new("RGB",(10*140+10,300),(20,20,24))
for n,i in enumerate(ids):
    im=Image.open(f"icones/icone_{i}.png").convert("RGBA")
    w,h=im.size; m=int(w*0.012); im=im.crop((m,m,w-m,h-m)).resize((128,128),Image.LANCZOS)
    mask=Image.new("L",(512,512),0); ImageDraw.Draw(mask).rounded_rectangle((0,0,511,511),radius=44,fill=255)
    im.putalpha(mask.resize((128,128),Image.LANCZOS)); im.save(f"final/icone_{i}.png")
    sheet.paste(im,(10+n*140,10),im)
    sheet.paste(im.resize((64,64),Image.LANCZOS),(10+n*140,150),im.resize((64,64),Image.LANCZOS))
    sheet.paste(im.resize((48,48),Image.LANCZOS),(10+n*140+70,150),im.resize((48,48),Image.LANCZOS))
sheet.save("contato.png")
