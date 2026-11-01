"""Pós-processo das folhas do veneno: tira o magenta (key.py), fatia em N células iguais, centraliza cada quadro e
remonta em linha no tamanho final de efeitos_arqueiro_veneno_2d.gd (FOLHAS). Uso: prep.py <pasta_bruta> <pasta_saida>
Ícones: recorta o conteúdo e redimensiona para 128 px (como tools/arte/ui_gpt_image/prep.py)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ui_gpt_image"))
from key import key, trim
from PIL import Image
FOLHAS = {"fx_veneno_flecha": (64, 64, 6), "fx_veneno_impacto": (96, 96, 8), "fx_veneno_bola": (64, 64, 6),
          "fx_veneno_poca": (192, 192, 8), "fx_veneno_nuvem": (192, 192, 8), "fx_veneno_chuva": (192, 192, 8),
          "fx_veneno_status": (96, 96, 6), "fx_veneno_arauto_aura": (128, 128, 6), "fx_veneno_arauto_gatilho": (128, 128, 8)}
def separa(im, n):
    """Separa n quadros pelos vãos de colunas vazias (os quadros gerados invadem a célula vizinha); se não achar n, cai nas células iguais."""
    al = im.split()[3].point(lambda v: 255 if v > 20 else 0)
    cols = [al.crop((x, 0, x + 1, al.height)).getbbox() is not None for x in range(al.width)]
    runs, x = [], 0
    while x < len(cols):
        if cols[x]:
            y = x
            while y < len(cols) and cols[y]: y += 1
            runs.append([x, y]); x = y
        else: x += 1
    while len(runs) > n:  # junta o menor vão (faíscas soltas)
        g = min(range(len(runs) - 1), key=lambda i: runs[i + 1][0] - runs[i][1]); runs[g][1] = runs[g + 1][1]; del runs[g + 1]
    if len(runs) != n:
        cw = im.width / n; runs = [[round(i * cw), round((i + 1) * cw)] for i in range(n)]
    out = []
    for x0, x1 in runs:
        c = im.crop((x0, 0, x1, im.height)); b = c.split()[3].point(lambda v: 255 if v > 20 else 0).getbbox()
        out.append(c.crop(b) if b else c)
    return out
bruta, saida = sys.argv[1], sys.argv[2]
os.makedirs(saida, exist_ok=True)
for nome, (w, h, n) in FOLHAS.items():
    p = os.path.join(bruta, nome + ".png")
    if not os.path.exists(p):
        continue
    im = key(p); bb = im.split()[3].point(lambda v: 255 if v > 20 else 0).getbbox(); im = im.crop((0, bb[1], im.width, bb[3])) if bb else im
    quadros = separa(im, n)
    sc = min(w / max(q.width for q in quadros), h / max(q.height for q in quadros), 1.0) * 0.96
    folha = Image.new("RGBA", (w * n, h), (0, 0, 0, 0))
    for i, c in enumerate(quadros):
        c = c.resize((max(1, round(c.width * sc)), max(1, round(c.height * sc))), Image.LANCZOS)
        folha.paste(c, (i * w + (w - c.width) // 2, (h - c.height) // 2), c)
    folha.save(os.path.join(saida, nome + ".png")); print(nome, folha.size)
for nome in ("icone_poison_arrow", "icone_venom_orb", "icone_corrosive_rain", "icone_herald_plague"):
    p = os.path.join(bruta, nome + ".png")
    if os.path.exists(p):
        Image.open(p).convert("RGBA").resize((128, 128), Image.LANCZOS).save(os.path.join(saida, nome + ".png")); print(nome)
