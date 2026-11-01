#!/usr/bin/env python3
"""Gera as folhas 2D do Guerreiro (pixel art provisório, formato de docs/arte/25_formato_folhas_sprites_2d.md).

Uso: python3 tools/sprites2d/gerar_guerreiro.py [pasta_saida]
Saída padrão: godot/art2d/sprites/guerreiro/guerreiro_<anim>.png (5 direções x N quadros de 128 px, pivô 64,104).
Desenha em 64x64 sem suavização e amplia 2x (pixel art); o contorno escuro sai da máscara dilatada.
"""
import math
import os
import sys
from PIL import Image, ImageDraw, ImageFilter

L = 64            # tela lógica; a folha final usa 128 (2x)
PX, PY = 32, 52   # pivô (pés) na tela lógica
ANIMS = {"idle": 6, "run": 8, "attack": 6, "dodge": 6, "hit": 3, "death": 8}

OUT = (28, 22, 34, 255)
STEEL = (150, 162, 180, 255)
STEEL_D = (96, 108, 130, 255)
STEEL_L = (205, 215, 232, 255)
GOLD = (212, 170, 72, 255)
RED = (176, 44, 48, 255)
RED_D = (112, 26, 38, 255)
SKIN = (236, 190, 152, 255)
SKIN_D = (196, 146, 112, 255)
BOOT = (92, 62, 42, 255)
LEATHER = (120, 80, 52, 255)
BLADE = (226, 232, 240, 255)
BLADE_D = (150, 160, 178, 255)
SHADOW = (0, 0, 0, 70)


def dir_info(d):
    """d: 0 S, 1 SE, 2 E, 3 NE, 4 N -> (t lateral 0..1, costas?)"""
    return {0: (0.0, False), 1: (0.6, False), 2: (1.0, False), 3: (0.6, True), 4: (0.0, True)}[d]


def disc(dr, cx, cy, r, fill):
    dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)


def sword(dr, hx, hy, ang, comp=21):
    a = math.radians(ang)
    ex, ey = hx + math.cos(a) * comp, hy + math.sin(a) * comp
    gx, gy = hx + math.cos(a) * 3, hy + math.sin(a) * 3
    nx, ny = -math.sin(a), math.cos(a)
    dr.line([(hx, hy), (ex, ey)], fill=BLADE, width=4)
    dr.line([(hx + nx, hy + ny), (ex + nx, ey + ny)], fill=BLADE_D, width=1)
    dr.line([(gx - nx * 4, gy - ny * 4), (gx + nx * 4, gy + ny * 4)], fill=GOLD, width=2)
    dr.line([(hx, hy), (hx - math.cos(a) * 3, hy - math.sin(a) * 3)], fill=LEATHER, width=2)


def pose_frame(anim, q, n):
    """Parâmetros de pose: bob, fase das pernas, ângulo da espada, inclinação, agachamento, giro do golpe."""
    p = dict(bob=0, leg=0.0, sw=-78, lean=0, crouch=0, swing=0.0, flash=False, fall=0.0, stretch=0)
    t = q / n
    if anim == "idle":
        p["bob"] = round(math.sin(t * math.tau) * 1.0)
        p["sw"] = -78 + math.sin(t * math.tau) * 3
    elif anim == "run":
        p["leg"] = math.sin(t * math.tau)
        p["bob"] = -abs(math.sin(t * math.tau * 2)) * 2
        p["lean"] = 2
        p["sw"] = -60 + math.sin(t * math.tau) * 8
    elif anim == "attack":
        # 0-1 preparar, 2 começar, 3 golpe (evento), 4-5 recuperar
        sw = [-130, -150, -110, 10, 35, -20][q]
        p["sw"] = sw
        p["swing"] = [0, 0, 0.3, 1.0, 0.6, 0.2][q]
        p["lean"] = [-2, -3, 0, 4, 3, 1][q]
        p["crouch"] = [0, 1, 0, 1, 1, 0][q]
    elif anim == "dodge":
        p["lean"] = 5
        p["crouch"] = 4
        p["stretch"] = 1
        p["sw"] = -20
        p["leg"] = math.sin(t * math.tau) * 0.6
        p["bob"] = 2 if q in (1, 2, 3, 4) else 0
    elif anim == "hit":
        p["lean"] = [-3, -5, -2][q]
        p["flash"] = q == 0
        p["sw"] = -95
    elif anim == "death":
        p["fall"] = min(1.0, q / (n - 2))
        p["flash"] = q == 0
        p["sw"] = -40 + 60 * p["fall"]
    return p


def desenhar(d, p):
    img = Image.new("RGBA", (L, L), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    t, costas = dir_info(d)
    fall = p["fall"]
    lean = p["lean"] * (1 if d in (1, 2, 3) else 0.4)
    cy = PY - 20 + p["bob"] + p["crouch"] + 6 * fall  # centro do torso
    cx = PX + lean
    w = 14 - 4 * t  # largura do torso

    # sombra suave sob os pés é desenhada pelo motor; aqui só o personagem

    # capa (atrás do corpo; maior de costas)
    cape_w = w + (4 if costas else 1)
    dr.polygon([(cx - cape_w / 2, cy - 4), (cx + cape_w / 2, cy - 4),
                (cx + cape_w / 2 + 2 - lean * 0.5, cy + 15), (cx - cape_w / 2 - 2 - lean * 0.5, cy + 15)], fill=RED_D if costas else RED)
    if costas:
        dr.line([(cx, cy - 2), (cx, cy + 14)], fill=RED, width=1)

    # escudo atrás do corpo (visto de lado)
    sh_x = cx + (-2 if d == 2 else 0)
    if d == 2:
        disc(dr, sh_x - 5, cy + 6, 6, STEEL_D)

    # pernas
    leg = p["leg"]
    sep = 3.2 * (1 - 0.5 * t)
    for side in (-1, 1):
        ph = leg * side
        lx = cx + side * sep + (ph * 3 * t)
        top = cy + 10
        foot_y = PY + p["bob"] * 0 - (max(0, -ph) * 4 if p["leg"] else 0) + p["crouch"] * 0.3
        if fall:
            foot_y = PY + 4 * fall
            lx = cx + side * (4 + 6 * fall)
        dr.rectangle([lx - 2, top, lx + 2, foot_y - 3], fill=STEEL_D)
        dr.rectangle([lx - 3, foot_y - 4, lx + 3, foot_y], fill=BOOT)
        dr.rectangle([lx - 3, foot_y - 4, lx + 3, foot_y - 3], fill=LEATHER)

    # torso
    dr.rounded_rectangle([cx - w / 2, cy - 5, cx + w / 2, cy + 11], radius=3, fill=STEEL)
    dr.rectangle([cx - w / 2 + 1, cy + 7, cx + w / 2 - 1, cy + 9], fill=LEATHER)          # cinto
    dr.rectangle([cx - 1, cy + 7, cx + 1, cy + 9], fill=GOLD)
    if not costas:
        dr.line([(cx - w / 2 + 2, cy - 3), (cx - w / 2 + 2, cy + 5)], fill=STEEL_L, width=1)
        dr.polygon([(cx - 3, cy - 5), (cx + 3, cy - 5), (cx, cy + 2)], fill=RED)           # tabardo
    else:
        dr.line([(cx, cy - 4), (cx, cy + 6)], fill=STEEL_D, width=1)

    # ombreiras
    for side in (-1, 1):
        sx = cx + side * (w / 2 + 0.5 - 2 * t * (1 if side < 0 else -0.3))
        disc(dr, sx, cy - 3, 3.6, STEEL_L if side < 0 else STEEL)
        dr.arc([sx - 3.6, cy - 6.6, sx + 3.6, cy + 0.6], 200, 340, fill=GOLD)

    # escudo na frente (S, SE) ou nas costas (N)
    if d in (0, 1, 3):
        sxp = cx + (10 - 3 * t) * (1 if not costas else -1)
        disc(dr, sxp, cy + 4, 6.5, STEEL_D)
        disc(dr, sxp, cy + 4, 4.5, STEEL)
        disc(dr, sxp, cy + 4, 1.6, GOLD)
    elif d == 4:
        disc(dr, cx, cy + 2, 6.5, STEEL_D)
        disc(dr, cx, cy + 2, 4.5, STEEL)
        disc(dr, cx, cy + 2, 1.6, GOLD)

    # cabeça
    hy = cy - 13
    disc(dr, cx + lean * 0.3, hy, 8.5, STEEL)
    hx = cx + lean * 0.3
    if not costas:
        fx = hx + 3.2 * t
        dr.ellipse([fx - 5.2 + 1.5 * t, hy - 3, fx + 5.2 + 1.5 * t, hy + 6], fill=SKIN)
        dr.rectangle([hx - 8.5, hy - 8.5, hx + 8.5, hy - 3], fill=STEEL)
        disc(dr, hx, hy - 4, 8.0, STEEL)
        dr.line([(hx - 7, hy - 3), (hx + 7, hy - 3)], fill=STEEL_D, width=1)
        ey = hy + 0.5
        if t < 0.3:
            for sx in (-2.6, 2.6):
                dr.rectangle([fx + sx - 0.5, ey, fx + sx + 0.5, ey + 1.4], fill=OUT)
        else:
            dr.rectangle([fx + 3, ey, fx + 4, ey + 1.4], fill=OUT)
            if t > 0.9:
                dr.rectangle([fx + 5, ey + 2, fx + 5.8, ey + 2.8], fill=SKIN_D)
        dr.polygon([(hx - 1, hy - 14), (hx + 1, hy - 14), (hx + 4, hy - 8), (hx - 4, hy - 8)], fill=RED)  # crista
    else:
        disc(dr, hx, hy, 8.5, STEEL)
        dr.line([(hx, hy - 8), (hx, hy + 5)], fill=STEEL_D, width=1)
        dr.polygon([(hx - 1.5, hy - 14), (hx + 1.5, hy - 14), (hx + 3, hy - 4), (hx - 3, hy - 4)], fill=RED)
    dr.arc([hx - 8, hy - 8, hx + 8, hy + 8], 200, 320, fill=STEEL_L)

    # braço da espada e espada
    if d == 0:
        hand = (cx - w / 2 - 5, cy + 5)
    elif d == 4:
        hand = (cx + w / 2 + 5, cy + 5)
    else:
        hand = (cx + 5 + 4 * t, cy + 5)
    ang = p["sw"]
    if d == 0:
        ang = -180 - ang if False else ang
    if d == 4:
        ang = ang
    sg = p["swing"]
    if sg:
        hand = (hand[0] + math.cos(math.radians(ang)) * 3, hand[1] + math.sin(math.radians(ang)) * 3)
    arm_from = (cx + (-w / 2 if d == 0 else w / 2 if d == 4 else 2 * t), cy - 3)
    dr.line([arm_from, hand], fill=STEEL, width=4)
    disc(dr, hand[0], hand[1], 2.2, SKIN if not costas else STEEL_D)
    if d == 0:
        ang = 180 - ang if ang < -90 or ang > 90 else ang  # espelha o arco para o lado do braço
    sword(dr, hand[0], hand[1], ang)

    if fall:
        # tombado: gira a figura em torno dos pés
        img = img.rotate(-82 * fall, resample=Image.NEAREST, center=(PX, PY), translate=(int(6 * fall), 0))
    return img


OUT_FIX = OUT  # alias para o contorno


def contorno(img, flash=False):
    a = img.split()[3].point(lambda v: 255 if v > 40 else 0)
    maior = a.filter(ImageFilter.MaxFilter(3))
    borda = Image.new("RGBA", img.size, (0, 0, 0, 0))
    borda.paste(OUT, mask=maior)
    img2 = img.copy()
    img2.putalpha(a)
    borda.alpha_composite(img2)
    if flash:
        branco = Image.new("RGBA", img.size, (255, 255, 255, 120))
        mask = borda.split()[3]
        tint = Image.new("RGBA", img.size, (0, 0, 0, 0))
        tint.paste(branco, mask=mask)
        borda.alpha_composite(tint)
    return borda


def folha(anim, n):
    W = 128
    sheet = Image.new("RGBA", (W * n, W * 5), (0, 0, 0, 0))
    for d in range(5):
        for q in range(n):
            p = pose_frame(anim, q, n)
            fr = contorno(desenhar(d, p), p["flash"])
            # a tela lógica 64 vira 128; o pivô (32,52) cai em (64,104)
            fr = fr.resize((W, W), Image.NEAREST)
            sheet.alpha_composite(fr, (q * W, d * W))
    return sheet


def main():
    saida = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..", "godot", "art2d", "sprites", "guerreiro")
    os.makedirs(saida, exist_ok=True)
    for anim, n in ANIMS.items():
        folha(anim, n).save(os.path.join(saida, f"guerreiro_{anim}.png"))
    print("folhas em", os.path.abspath(saida))


if __name__ == "__main__":
    main()
