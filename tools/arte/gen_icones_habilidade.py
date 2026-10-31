#!/usr/bin/env python3
"""Gera godot/art2d/ui/icone_<id>.png: ícones de habilidade e carta, pintados e emoldurados.
Uso: python3 tools/arte/gen_icones_habilidade.py [pasta_saida]
Decisão de estilo (Jev, 76% pintado com glifo, brilho colorido e moldura de pedra): docs/arte/28_icones_habilidades.md
"""
import math, random, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageChops

S = 512      # resolução de trabalho
OUT = 128    # resolução final (a tela escala)

# id -> (glifo, cor do brilho)
ICONES = {
    "tiro":      ("flecha",   "#e6e1d6"),
    "esquiva":   ("rolada",   "#4a9fbf"),
    "bloqueado": ("cadeado",  "#6a6878"),
    "power":     ("flecha_pesada", "#e0703a"),
    "haste":     ("raio",     "#e8c840"),
    "swift":     ("bota",     "#6ec06e"),
    "vitality":  ("coracao",  "#b53030"),
    "multishot": ("leque",    "#d9a84c"),
    "pierce":    ("perfura",  "#9ac8ee"),
    "evasion":   ("pegadas",  "#58b8a0"),
}

def hexc(h):
    h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def mix(a, b, t): return tuple(int(a[i]*(1-t)+b[i]*t) for i in range(3))
def shade(c, t): return mix(c, (0, 0, 0), t) if t >= 0 else mix(c, (255, 255, 255), -t)

def vgrad(size, top, bot):
    g = Image.linear_gradient("L").resize(size)  # preto em cima, branco embaixo
    return Image.composite(Image.new("RGB", size, bot), Image.new("RGB", size, top), g)

_RUIDO = {}
def _ruido(s):
    if s not in _RUIDO:
        rnd = random.Random(3)
        n = Image.effect_noise((s, s), 22).filter(ImageFilter.GaussianBlur(0.8))
        _RUIDO[s] = n
    return _RUIDO[s]

def pintar(base, mask, cor, contorno=True, brilho=True):
    """Sombreado em 3 tons com luz vinda de cima à esquerda, ruído de pincel e contorno fino."""
    w, h = base.size
    gh = Image.linear_gradient("L").rotate(90).resize((w, h))          # claro à esquerda->escuro à direita (invertido abaixo)
    gv = Image.linear_gradient("L").resize((w, h))
    luz = ImageChops.add(gh, gv, scale=2)                              # 0 = topo-esquerda, 255 = base-direita
    fill = Image.composite(Image.new("RGB", (w, h), shade(cor, 0.28)), Image.new("RGB", (w, h), shade(cor, -0.42)), luz)
    fill = Image.blend(Image.new("RGB", (w, h), cor), fill, 1.0)
    if brilho:
        # bisel: realce no lado de luz e sombra no oposto, deslocando a máscara
        claro = ImageChops.subtract(mask, ImageChops.offset(mask, 6, 7)).filter(ImageFilter.GaussianBlur(1.5))
        escuro = ImageChops.subtract(mask, ImageChops.offset(mask, -6, -7)).filter(ImageFilter.GaussianBlur(1.5))
        fill = Image.composite(Image.new("RGB", (w, h), shade(cor, 0.6)), fill, escuro.point(lambda v: v//2))
        fill = Image.composite(Image.new("RGB", (w, h), shade(cor, -0.45)), fill, claro.point(lambda v: v//2))
    # ruído de pincel
    r = _ruido(w)
    fill = ImageChops.add(fill, Image.merge("RGB", (r, r, r)), scale=1, offset=-128)
    if contorno:
        grow = mask.filter(ImageFilter.MaxFilter(5))
        base.paste(Image.new("RGB", (w, h), (16, 11, 12)), mask=grow)
    base.paste(fill, mask=mask)

def poli(pts, s=S):
    m = Image.new("L", (s, s), 0)
    ImageDraw.Draw(m).polygon([(x*s, y*s) for x, y in pts], fill=255)
    return m

def linha(p0, p1, larg, s=S):
    m = Image.new("L", (s, s), 0)
    ImageDraw.Draw(m).line([(p0[0]*s, p0[1]*s), (p1[0]*s, p1[1]*s)], fill=255, width=int(larg*s))
    return m

def elipse(c, r, s=S):
    m = Image.new("L", (s, s), 0)
    ImageDraw.Draw(m).ellipse([(c[0]-r[0])*s, (c[1]-r[1])*s, (c[0]+r[0])*s, (c[1]+r[1])*s], fill=255)
    return m

def rot(pts, ang, c=(0.5, 0.5)):
    ca, sa = math.cos(ang), math.sin(ang)
    return [(c[0]+(x-c[0])*ca-(y-c[1])*sa, c[1]+(x-c[0])*sa+(y-c[1])*ca) for x, y in pts]

# ---------- glifos: cada um recebe (img, cor) e desenha no centro ----------
MADEIRA = (150, 108, 66); PENA = (232, 228, 214); FERRO = (176, 184, 196)

def flecha_pts(w=1.0):
    """Flecha apontando para cima, centro em (0.5,0.5): [haste, ponta, penas]."""
    haste = [(0.485, 0.2), (0.515, 0.2), (0.515, 0.86), (0.485, 0.86)]
    ponta = [(0.5, 0.08), (0.575, 0.24), (0.5, 0.21), (0.425, 0.24)]
    penas = [[(0.5, 0.70), (0.585, 0.80), (0.585, 0.93), (0.5, 0.86)], [(0.5, 0.70), (0.415, 0.80), (0.415, 0.93), (0.5, 0.86)]]
    return haste, ponta, penas

def desenha_flecha(img, ang, centro, escala, cor_ponta=FERRO, haste_cor=MADEIRA, grossa=1.0):
    def t(pts):
        p = [((x-0.5)*escala+0.5, (y-0.5)*escala+0.5) for x, y in pts]
        p = rot(p, ang)
        return [(x+centro[0]-0.5, y+centro[1]-0.5) for x, y in p]
    haste, ponta, penas = flecha_pts()
    haste = [(0.5+(x-0.5)*grossa, y) for x, y in haste]
    pintar(img, poli(t(haste)), haste_cor)
    for p in penas: pintar(img, poli(t(p)), PENA)
    pintar(img, poli(t(ponta)), cor_ponta)

def g_flecha(img, cor):
    desenha_flecha(img, math.radians(40), (0.5, 0.5), 1.0)
    # rastro de luz
    for k, a in enumerate((0.5, 0.3, 0.15)):
        pass

def g_flecha_pesada(img, cor):
    desenha_flecha(img, math.radians(40), (0.5, 0.5), 1.05, cor_ponta=(240, 150, 80), grossa=2.4)
    chama = poli(rot([(0.5, 0.0), (0.58, 0.14), (0.54, 0.26), (0.5, 0.2), (0.46, 0.26), (0.42, 0.14)], math.radians(40)))
    pintar(img, chama, (255, 170, 60), contorno=False)

def g_leque(img, cor):
    for ang in (-34, 0, 34):
        desenha_flecha(img, math.radians(ang), (0.5, 0.5 + (0.06 if ang == 0 else 0.1)), 0.86)

def g_perfura(img, cor):
    # escudo trincado + ponta atravessando
    esc = [(0.2, 0.2), (0.8, 0.2), (0.8, 0.52), (0.5, 0.9), (0.2, 0.52)]
    pintar(img, poli(esc), (96, 100, 116))
    pintar(img, poli([(0.27, 0.27), (0.73, 0.27), (0.73, 0.5), (0.5, 0.8), (0.27, 0.5)]), (66, 70, 86), contorno=False)
    desenha_flecha(img, math.radians(0), (0.5, 0.44), 1.15, cor_ponta=(210, 230, 250))

def g_raio(img, cor):
    pintar(img, poli([(0.62, 0.06), (0.24, 0.56), (0.46, 0.56), (0.36, 0.95), (0.78, 0.4), (0.55, 0.4)]), cor)

def g_coracao(img, cor):
    pts = []
    for i in range(240):
        t = i/240*2*math.pi
        x = 16*math.sin(t)**3
        y = 13*math.cos(t)-5*math.cos(2*t)-2*math.cos(3*t)-math.cos(4*t)
        pts.append((0.5+x/40, 0.46-y/40))
    pintar(img, poli(pts), cor)
    # runa gravada no centro (gota de energia dentro do coração)
    pintar(img, poli([(0.5, 0.34), (0.58, 0.5), (0.5, 0.66), (0.42, 0.5)]), (250, 214, 150), contorno=False)
    pintar(img, poli([(0.5, 0.40), (0.54, 0.5), (0.5, 0.60), (0.46, 0.50)]), (120, 30, 28), contorno=False)

def g_bota(img, cor):
    bota = [(0.30, 0.12), (0.58, 0.12), (0.58, 0.5), (0.86, 0.62), (0.88, 0.86), (0.28, 0.86)]
    pintar(img, poli(bota), (120, 84, 52))
    pintar(img, poli([(0.28, 0.76), (0.88, 0.76), (0.88, 0.86), (0.28, 0.86)]), (60, 44, 34), contorno=False)
    pintar(img, poli([(0.30, 0.12), (0.58, 0.12), (0.58, 0.2), (0.30, 0.2)]), (190, 150, 96), contorno=False)
    # asa
    for i, (dx, dy) in enumerate(((0, 0), (-0.03, 0.07), (-0.06, 0.14))):
        pintar(img, poli([(0.30+dx, 0.34+dy), (0.06+dx, 0.28+dy), (0.30+dx, 0.44+dy)]), PENA)

def g_pegadas(img, cor):
    # bota leve com rastro de vento atrás (Passo Rápido)
    for y, x0, x1 in ((0.30, 0.04, 0.34), (0.48, 0.0, 0.30), (0.66, 0.06, 0.34)):
        pintar(img, linha((x0, y), (x1, y), 0.035), (215, 245, 235), contorno=False)
    bota = [(0.42, 0.14), (0.66, 0.14), (0.66, 0.50), (0.92, 0.62), (0.94, 0.82), (0.40, 0.82)]
    pintar(img, poli(bota), (92, 70, 52))
    pintar(img, poli([(0.40, 0.72), (0.94, 0.72), (0.94, 0.82), (0.40, 0.82)]), (46, 36, 30), contorno=False)
    pintar(img, poli([(0.42, 0.14), (0.66, 0.14), (0.66, 0.22), (0.42, 0.22)]), cor, contorno=False)

def g_rolada(img, cor):
    # seta circular robusta com ponta marcada
    m = Image.new("L", (S, S), 0); d = ImageDraw.Draw(m)
    d.arc([0.16*S, 0.16*S, 0.84*S, 0.84*S], 115, 385, fill=255, width=int(0.17*S))
    pintar(img, m, cor)
    th = math.radians(-135)
    tri = [(0.0, -0.20), (0.22, 0.08), (-0.22, 0.08)]
    cx, cy = 0.5+0.34*math.cos(math.radians(25)), 0.5+0.34*math.sin(math.radians(25))
    ponta = [(cx+x*math.cos(th)-y*math.sin(th), cy+x*math.sin(th)+y*math.cos(th)) for x, y in tri]
    pintar(img, poli(ponta), shade(cor, -0.1))
    pintar(img, linha((0.40, 0.50), (0.60, 0.50), 0.03), (225, 242, 250), contorno=False)

def g_cadeado(img, cor):
    arco = Image.new("L", (S, S), 0); d = ImageDraw.Draw(arco)
    d.arc([0.30*S, 0.12*S, 0.70*S, 0.62*S], 180, 360, fill=255, width=int(0.09*S))
    d.line([(0.30*S, 0.37*S), (0.30*S, 0.52*S)], fill=255, width=int(0.09*S))
    d.line([(0.70*S, 0.37*S), (0.70*S, 0.52*S)], fill=255, width=int(0.09*S))
    pintar(img, arco, (140, 140, 150))
    pintar(img, poli([(0.24, 0.46), (0.76, 0.46), (0.76, 0.88), (0.24, 0.88)]), (92, 90, 104))
    pintar(img, elipse((0.5, 0.62), (0.055, 0.055)), (16, 12, 14), contorno=False)
    pintar(img, poli([(0.48, 0.64), (0.52, 0.64), (0.53, 0.76), (0.47, 0.76)]), (16, 12, 14), contorno=False)

GLIFOS = {"flecha": g_flecha, "flecha_pesada": g_flecha_pesada, "leque": g_leque, "perfura": g_perfura, "raio": g_raio,
          "coracao": g_coracao, "bota": g_bota, "pegadas": g_pegadas, "rolada": g_rolada, "cadeado": g_cadeado}

# ---------- fundo e moldura ----------
def pedra(size, cor_base, seed):
    rnd = random.Random(seed)
    img = Image.new("RGB", size, cor_base)
    px = img.load()
    for _ in range(size[0]*size[1]//6):
        x, y = rnd.randrange(size[0]), rnd.randrange(size[1]); v = rnd.randint(-14, 14)
        r, g, b = px[x, y]; px[x, y] = (max(0, r+v), max(0, g+v), max(0, b+v))
    return img.filter(ImageFilter.GaussianBlur(1.2))

def montar(id_, glifo, cor_hex):
    cor = hexc(cor_hex)
    bloq = id_ == "bloqueado"
    suave = mix(cor, (120, 110, 100), 0.35)          # menos saturado, família da paleta da cripta
    fundo = pedra((S, S), (34, 31, 36), hash(id_) & 0xffff)
    g = Image.radial_gradient("L").resize((S, S))
    vig = g.point(lambda v: int(max(0, v-110)*1.7))
    fundo = Image.composite(Image.new("RGB", (S, S), (6, 5, 8)), fundo, vig)
    img = fundo
    if not bloq:
        halo = Image.new("L", (S, S), 0); ImageDraw.Draw(halo).ellipse([0.22*S, 0.22*S, 0.78*S, 0.78*S], fill=95)
        img = Image.composite(Image.new("RGB", (S, S), suave), img, halo.filter(ImageFilter.GaussianBlur(46)))
    GLIFOS[glifo](img, cor)
    # moldura única: ferro biselado com cantos dourados (igual em todos, como o slot da HUD)
    m = int(0.085*S)
    ferro = pedra((S, S), (58, 56, 62), 7)
    dentro = Image.new("L", (S, S), 0); ImageDraw.Draw(dentro).rounded_rectangle([m, m, S-m, S-m], radius=18, fill=255)
    res = Image.composite(img, ferro, dentro)
    d = ImageDraw.Draw(res)
    OURO = (205, 164, 82)
    d.rounded_rectangle([2, 2, S-3, S-3], radius=30, outline=(10, 8, 10), width=6)
    d.rounded_rectangle([9, 9, S-10, S-10], radius=26, outline=(96, 94, 104), width=4)     # bisel claro
    d.rounded_rectangle([m-6, m-6, S-m+6, S-m+6], radius=20, outline=(12, 10, 12), width=7)  # encaixe escuro
    d.line([(16, 16), (S-16, 16)], fill=(130, 128, 138), width=3)
    d.line([(16, 16), (16, S-16)], fill=(118, 116, 126), width=3)
    c = 118
    for (x0, y0, sx, sy) in ((10, 10, 1, 1), (S-11, 10, -1, 1), (10, S-11, 1, -1), (S-11, S-11, -1, -1)):
        d.line([(x0, y0), (x0+sx*c, y0)], fill=OURO, width=9)
        d.line([(x0, y0), (x0, y0+sy*c)], fill=OURO, width=9)
        d.line([(x0+sx*4, y0+sy*4), (x0+sx*(c-14), y0+sy*4)], fill=(240, 208, 130), width=2)
        d.ellipse([x0+sx*20-9, y0+sy*20-9, x0+sx*20+9, y0+sy*20+9], fill=(36, 32, 30), outline=OURO, width=3)
    alfa = Image.new("L", (S, S), 0); ImageDraw.Draw(alfa).rounded_rectangle([0, 0, S-1, S-1], radius=34, fill=255)
    res = res.convert("RGBA"); res.putalpha(alfa)
    return res.resize((OUT, OUT), Image.LANCZOS)

def main():
    pasta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "godot/art2d/ui"
    pasta.mkdir(parents=True, exist_ok=True)
    folha = Image.new("RGBA", (len(ICONES)*(OUT+8)+8, OUT+16), (20, 18, 22, 255))
    for i, (id_, (glifo, cor)) in enumerate(ICONES.items()):
        ic = montar(id_, glifo, cor)
        ic.save(pasta / f"icone_{id_}.png")
        folha.alpha_composite(ic, (8+i*(OUT+8), 8))
    folha.save(pasta.parent.parent.parent / "docs/arte/sprites2d/icones_habilidades_previa.png" if len(sys.argv) < 2 else pasta / "_previa_icones.png")
    print("ok", pasta)

if __name__ == "__main__":
    main()
