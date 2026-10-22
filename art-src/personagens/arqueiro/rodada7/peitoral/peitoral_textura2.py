"""Textura do Peitoral v2 (numpy + PIL): le a textura original (pre-polida) e grava a nova ao lado do GLB."""
import os
import numpy as np
from PIL import Image, ImageFilter
import os as _os
_AQUI = _os.path.dirname(_os.path.abspath(__file__))
_R7 = _os.path.dirname(_AQUI)
_RAIZ = _os.path.abspath(_os.path.join(_R7, "..", "..", "..", ".."))
FONTE = _os.environ.get("ARQ_FONTE_ORIG", _os.path.join(_R7, "_fonte_original"))   # GLBs/texturas pre-polida (somente leitura)
SAIDA = _os.environ.get("ARQ_SAIDA", _os.path.join(_RAIZ, "godot", "art", "models", "personagens", "arqueiro"))
SRC=FONTE+os.sep
OUT=os.path.join(SAIDA,"Arqueiro_Peitoral.glb")
# ---- textura: tecido mais claro/oliva (forro nao some no escuro), osso com vinheta/desgaste, couro com realce de borda
im=Image.open(SRC+"T_Arqueiro_Peitoral_BC.png").convert("RGB"); A=np.asarray(im).astype(np.float32)/255
def cell(x0,y0,x1,y1): return A[y0:y1,x0:x1]
cl=cell(0,256,128,512); cl[:]=np.clip(cl*np.array([1.30,1.38,1.0]),0,1)
bn=cell(256,256,384,512)   # osso: vinheta ocre + riscas de desgaste
H,Wd=bn.shape[:2]; yy,xx=np.mgrid[0:H,0:Wd]; r=np.sqrt(((xx-Wd/2)/(Wd/2))**2+((yy-H/2)/(H/2))**2)
vig=np.clip((r-0.55)/0.6,0,1)**1.5
bn[:]=bn*(1-0.42*vig[...,None])+np.array([0.42,0.30,0.16])*0.25*vig[...,None]
lt=cell(128,256,256,512); H,Wd=lt.shape[:2]; yy,xx=np.mgrid[0:H,0:Wd]
ed=np.minimum(np.minimum(xx,Wd-1-xx),np.minimum(yy,H-1-yy))/20.0
lt[:]=np.clip(lt*(0.82+0.3*np.clip(ed,0,1)[...,None]+0.0),0,1)
mt=cell(384,256,512,512); H,Wd=mt.shape[:2]; yy,xx=np.mgrid[0:H,0:Wd]
r=np.sqrt(((xx-Wd/2)/(Wd/2))**2+((yy-H/2)/(H/2))**2); mt[:]=np.clip(mt*(1.12-0.3*np.clip(r-.5,0,1)[...,None]),0,1)
Image.fromarray((A*255).astype(np.uint8)).save(os.path.join(os.path.dirname(OUT),"T_Arqueiro_Peitoral_BC.png"))
