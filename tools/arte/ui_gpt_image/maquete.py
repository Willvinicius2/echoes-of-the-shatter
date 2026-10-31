from PIL import Image,ImageDraw,ImageFont
L=lambda n:Image.open(f"final/{n}.png").convert("RGBA")
S=3
def liquido(base,cx,cy,r,cor,nivel):
    big=Image.new("RGBA",(int(2*r*S),int(2*r*S)),(0,0,0,0)); d=ImageDraw.Draw(big)
    top=int(2*r*S*(1-nivel)); d.rectangle((0,top,big.size[0],big.size[1]),fill=cor)
    # gradiente simples de brilho
    for k in range(int(r*S*0.9)):
        pass
    mask=Image.new("L",big.size,0); ImageDraw.Draw(mask).ellipse((0,0,big.size[0]-1,big.size[1]-1),fill=255)
    big.putalpha(Image.composite(big.split()[3],Image.new("L",big.size,0),mask))
    s=big.resize((int(2*r),int(2*r)),Image.LANCZOS); base.alpha_composite(s,(int(cx-r),int(cy-r)))
def hud(sala,chefe=False):
    bg=Image.open(f"../arte-ui/docs/arte/sprites2d/capturas_cripta/{sala}.png").convert("RGBA").resize((1280,720))
    faixa=L("hud_faixa_pedra").resize((560,75),Image.LANCZOS); bg.alpha_composite(faixa,(360,720-75))
    ids=["tiro","esquiva","multishot","pierce","evasion","bloqueado"]; sl=L("hud_slot_moldura").resize((60,60),Image.LANCZOS)
    tot=6*60+5*8; x0=640-tot//2
    for k,i in enumerate(ids):
        x=x0+k*68; y=720-75+8
        ic=L("icone_"+i).resize((54,54),Image.LANCZOS); bg.alpha_composite(ic,(x+3,y+3)); bg.alpha_composite(sl,(x,y))
    D=135; ri=D/2*0.859
    for cx,cor in ((D//2,(176,28,28,255)),(1280-D//2,(40,70,150,255))):
        cy=720-D//2
        liquido(bg,cx,cy,ri-1,cor,0.8)
        bg.alpha_composite(L("hud_globo_moldura").resize((D,D),Image.LANCZOS),(cx-D//2,cy-D//2))
    if chefe:
        b=L("hud_barra_chefe_moldura").resize((620,73),Image.LANCZOS)
        d0=ImageDraw.Draw(bg); d0.rectangle((362,41,918,57),fill=(18,10,24,255)); d0.rectangle((364,43,780,55),fill=(120,50,160,255))
        bg.alpha_composite(b,(330,6))
        d=ImageDraw.Draw(bg); d.text((640,100),"GUARDIAO DA CRIPTA",fill=(230,225,210,255),anchor="mm")
    return bg.convert("RGB")
hud("sala1").save("maquete_sala1.png"); hud("sala4",True).save("maquete_chefe.png")
