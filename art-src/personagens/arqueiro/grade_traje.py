"""Gradacao de cor do traje do Arqueiro (textura compartilhada Peitoral/Calca/Luvas/Botas).

Le a fonte (somente leitura) T_Archer_Starter_BC.png / _M.png em ARQ_FONTE/modular_arqueiro/final,
aplica a gradacao HSV por faixa de matiz e grava em godot/art/models/personagens/arqueiro/:
  T_Archer_Starter_BC.png (512x512) e T_Archer_Starter_M.png (256x256).
Rodar: python grade_traje.py   (reproduzivel: mesma fonte -> mesma saida; semente fixa)
Metas (folha 03): verde-musgo vivo, penas marfim, bordas douradas, couro quente, placas de osso claras.
"""
import os, json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
FONTE = os.environ.get("ARQ_FONTE", "D:/openclaude/_trabalho-claude/modelos3d")
FINAL = FONTE + "/modular_arqueiro/final"
SAIDA = os.environ.get("ARQ_SAIDA", os.path.join(RAIZ, "godot", "art", "models", "personagens", "arqueiro"))
TAM = 512


def ss(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def faixa(h, a, b, borda=12):
    """Peso suave 1 dentro de [a,b] graus, caindo em 'borda' graus."""
    return ss(h, a - borda, a) * (1 - ss(h, b, b + borda))


def rgb_hsv(img):
    a = np.array(img.convert("HSV")).astype(np.float32)
    return a[..., 0] * 360 / 255, a[..., 1] / 255, a[..., 2] / 255


def hsv_rgb(h, s, v):
    a = np.stack([np.mod(h, 360) * 255 / 360, np.clip(s, 0, 1) * 255, np.clip(v, 0, 1) * 255], -1).astype(np.uint8)
    return Image.fromarray(a, "HSV").convert("RGB")


def ruido(n, escala, semente):
    r = np.random.RandomState(semente)
    g = Image.fromarray((r.rand(escala, escala) * 255).astype(np.uint8)).resize((n, n), Image.BICUBIC)
    return np.array(g).astype(np.float32) / 255


def mascara_osso(n):
    """Placas de osso (cano das botas): rasteriza os triangulos UV de mascara_osso_uv.json (gerado por mascara_uv.py)."""
    arq = os.path.join(AQUI, "mascara_osso_uv.json")
    m = Image.new("L", (n, n), 0)
    if os.path.exists(arq):
        d = ImageDraw.Draw(m)
        for tris in json.load(open(arq)).values():
            for t in tris:
                d.polygon([(u * n, (1 - v) * n) for u, v in t], fill=255)
        m = m.filter(ImageFilter.GaussianBlur(n / 300))
    return np.array(m).astype(np.float32) / 255


def graduar(img):
    h, s, v = rgb_hsv(img)
    v0 = v.copy()
    # 1) curva de tons: levanta sombras (modelo estava escuro), preserva contraste
    v = np.clip(v ** 0.78 * 1.12, 0, 1)
    # pesos por faixa de matiz (olival 50-150 = verde; 0-45 = couro; osso = pouco saturado e claro)
    wv = faixa(h, 52, 160, 14) * ss(s, 0.06, 0.20)
    wc = faixa(h, 0, 46, 8) + faixa(h, 340, 360, 10)
    wc = np.clip(wc, 0, 1) * (1 - wv)
    osso = ss(v0, 0.30, 0.50) * (1 - ss(s, 0.28, 0.42)) * faixa(h, 20, 85, 15)
    ouro = ss(v0, 0.34, 0.55) * ss(s, 0.36, 0.52) * faixa(h, 30, 62, 8)
    wc = wc * (1 - osso) * (1 - ouro)
    wv = wv * (1 - osso)
    # 2) verde-musgo vivo
    h = np.where(wv > 0, h + (104 - h) * 0.55 * wv, h)
    s = s + wv * (np.clip(0.20 + s * 1.0, 0, 0.55) - s)
    v = v * (1 - 0.06 * wv)
    # 3) couro marrom quente
    h = h + (27 - h) * 0.6 * wc
    s = s + wc * (np.clip(s * 1.05 + 0.03, 0, 0.55) - s)
    v = v * (1 + 0.0 * wc)
    # 4) osso/marfim e dourado
    h = h + (44 - h) * osso * 0.8
    s = s + osso * (0.16 - s)
    v = v + osso * (np.clip(v * 1.05 + 0.12, 0, 0.97) - v)
    h = h + (46 - h) * ouro
    s = s + ouro * (0.82 - s)
    v = v + ouro * (np.clip(v * 1.25 + 0.2, 0, 0.96) - v)
    # 5) desgaste assimetrico leve: manchas de baixa frequencia clareiam e dessaturam
    n = ruido(img.width, 7, 11) * 0.65 + ruido(img.width, 23, 5) * 0.35
    d = ss(n, 0.55, 0.85)
    v = v * (1 + 0.10 * d - 0.05 * (1 - n))
    s = s * (1 - 0.18 * d)
    # 6) placas de osso claras (cano das botas): preserva o relevo pintado, troca a cor
    mo = mascara_osso(img.width)
    lum = np.clip(v0 / max(np.percentile(v0, 97), 1e-3), 0, 1)
    h = h + (44 - h) * mo * 0.9
    s = s + mo * (0.20 - s)
    v = v + mo * (0.50 + 0.42 * lum ** 0.8 - v)
    return hsv_rgb(h, s, v)


def main():
    os.makedirs(SAIDA, exist_ok=True)
    bc = Image.open(FINAL + "/T_Archer_Starter_BC.png").convert("RGB")
    g = graduar(bc)  # na resolucao da fonte, depois reduz (mais nitido)
    g = g.resize((TAM, TAM), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.0, percent=55, threshold=2))
    g.save(SAIDA + "/T_Archer_Starter_BC.png", optimize=True)
    m = Image.open(FINAL + "/T_Archer_Starter_M.png")
    m.resize((TAM // 2, TAM // 2), Image.NEAREST).save(SAIDA + "/T_Archer_Starter_M.png", optimize=True)
    print("ok", SAIDA)


if __name__ == "__main__":
    main()
