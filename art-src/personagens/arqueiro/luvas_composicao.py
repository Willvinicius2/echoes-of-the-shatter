"""Monta previas/luvas_vs_folha.png e luvas_wire.png (python, PIL) a partir dos renders de luvas_previas.py."""
from PIL import Image, ImageDraw
R = Image.open("ref/arq_ref_angulos.png").convert("RGB"); P = "previas/"
def fit(im, s=512):
    im = im.copy(); im.thumbnail((s, s)); c = Image.new("RGB", (s, s), (60, 60, 66)); c.paste(im, ((s - im.width) // 2, (s - im.height) // 2)); return c
ref_a = R.crop((773, 630, 1150, 1020)); ref_b = R.crop((420, 230, 640, 520))
mine_a = Image.open(P + "luvas_mao_esq_3q.png").convert("RGB").crop((150, 100, 900, 950))
mine_b = Image.open(P + "luvas_dir_3q.png").convert("RGB").crop((200, 150, 800, 950))
W = Image.new("RGB", (1024, 1060), (40, 40, 44)); d = ImageDraw.Draw(W)
for i, (a, b, t) in enumerate(((ref_a, mine_a, "mao esquerda no arco"), (ref_b, mine_b, "antebraco + mao direita"))):
    W.paste(fit(a), (0, i * 530 + 24)); W.paste(fit(b), (512, i * 530 + 24))
    d.text((6, i * 530 + 6), "FOLHA APROVADA - " + t, fill=(255, 255, 255)); d.text((518, i * 530 + 6), "LUVAS (modelo 3D, Blender EEVEE)", fill=(255, 255, 255))
W.save(P + "luvas_vs_folha.png")
a = Image.open(P + "luvas_wire_esq.png").convert("RGB"); b = Image.open(P + "luvas_wire_dir.png").convert("RGB")
w = Image.new("RGB", (1024, 512)); w.paste(a.resize((512, 512)), (0, 0)); w.paste(b.resize((512, 512)), (512, 0)); w.save(P + "luvas_wire.png")
