#!/usr/bin/env python3
"""Gera as folhas 2D do Mago (128 px por quadro, 5 direções: S, SE, E, NE, N; o resto é espelho).
Desenho vetorial em supersampling, com contorno escuro e sombreamento em 3 tons, sem dependências além de Pillow.
Uso: python3 gerar_mago.py <pasta_saida>   (ex.: godot/art2d/sprites/mago)
Formato da folha: docs/arte/25_formato_folhas_sprites_2d.md (colunas = quadros, linhas = direções)."""
import math, sys, os
from PIL import Image, ImageDraw, ImageFilter, ImageChops

L = 128          # lado do quadro final
SS = 4           # supersampling
U = 1.62 * SS    # 1 unidade do rig = 1,62 px finais
PIVO = (64, 104) # pés (igual ao arqueiro)
DIRS = [0, 45, 90, 135, 180]   # graus de giro: S, SE, E, NE, N

ROXO = (86, 56, 150); ROXO_ESC = (52, 32, 104); ROXO_CLARO = (132, 96, 205)
CAPUZ = (70, 44, 128)
PELE = (240, 200, 165)
OURO = (214, 168, 70)
BOTA = (62, 44, 36)
CAJADO = (116, 78, 50)
CRISTAL = (120, 235, 255)
OLHO = (130, 245, 255)

def mix(c, k):  # k>0 clareia, k<0 escurece
    if k >= 0:
        return tuple(int(v + (255 - v) * k) for v in c)
    return tuple(int(v * (1 + k)) for v in c)

class Cena:
    def __init__(self, ang, tint=None):
        self.th = math.radians(ang)
        self.ops = []
        self.tint = tint
    # coordenadas do personagem: x = direita dele, z = frente, y = altura
    def proj(self, x, z, y):
        c, s = math.cos(self.th), math.sin(self.th)
        sx = -x * c + z * s
        dep = z * c + x * s
        return sx, dep, y
    def elipse(self, x, z, y, rx, ry, cor, bias=0.0, brilho=True):
        sx, dep, yy = self.proj(x, z, y)
        self.ops.append((dep + bias, "e", sx, yy, rx, ry, cor, brilho))
    def poli(self, pts, cor, bias=0.0):
        # pts: lista (x,z,y) do personagem
        pr = [self.proj(*p) for p in pts]
        dep = sum(p[1] for p in pr) / len(pr)
        self.ops.append((dep + bias, "p", [(p[0], p[2]) for p in pr], cor))
    def linha(self, a, b, esp, cor, bias=0.0, passos=5):
        # segmento grosso com pontas redondas (braços, cajado)
        pa, pb = self.proj(*a), self.proj(*b)
        self.ops.append(((pa[1] + pb[1]) / 2 + bias, "l", (pa[0], pa[2]), (pb[0], pb[2]), esp, cor))
    def diamante(self, x, z, y, w, h, cor, bias=0.0):
        sx, dep, yy = self.proj(x, z, y)
        self.ops.append((dep + bias, "d", sx, yy, w, h, cor))
    def manto(self, y0, y1, a0, a1, zc, cor_esc, cor, sway=0.0):
        """Manto como fatias: largura projetada = sqrt((a cos)^2 + (a sin)^2) = a (corpo redondo)."""
        sx0, _, _ = self.proj(0, zc, 0)
        dep = zc * math.cos(self.th)
        self.ops.append((dep - 0.5, "m", y0, y1, a0, a1, sx0, cor_esc, cor, sway))
    def desenhar(self, off=(0, 0), alfa=1.0):
        im = Image.new("RGBA", (L * SS, L * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        ox, oy = PIVO[0] * SS + off[0] * U, PIVO[1] * SS + off[1] * U
        def P(sx, yy):
            return ox + sx * U, oy - yy * U
        for op in sorted(self.ops, key=lambda o: o[0]):
            if op[1] == "e":
                _, _, sx, yy, rx, ry, cor, brilho = op
                cx, cy = P(sx, yy)
                rxp, ryp = rx * U, ry * U
                d.ellipse([cx - rxp, cy - ryp, cx + rxp, cy + ryp], fill=mix(cor, -0.35) + (255,))
                d.ellipse([cx - rxp * .9 - rxp * .06, cy - ryp * .9 - ryp * .08, cx + rxp * .9 - rxp * .06, cy + ryp * .9 - ryp * .08], fill=cor + (255,))
                if brilho:
                    d.ellipse([cx - rxp * .62 - rxp * .2, cy - ryp * .62 - ryp * .26, cx + rxp * .3 - rxp * .2, cy + ryp * .3 - ryp * .26], fill=mix(cor, 0.28) + (255,))
            elif op[1] == "l":
                _, _, a_, b_, esp, cor = op
                (x1, y1), (x2, y2) = P(*a_), P(*b_)
                w = esp * U * 2
                d.line([x1, y1, x2, y2], fill=cor + (255,), width=int(w))
                for (cx, cy) in ((x1, y1), (x2, y2)):
                    d.ellipse([cx - w / 2, cy - w / 2, cx + w / 2, cy + w / 2], fill=cor + (255,))
            elif op[1] == "d":
                _, _, sx, yy, w, h, cor = op
                cx, cy = P(sx, yy)
                pts = [(cx, cy - h * U), (cx + w * U, cy - h * 0.3 * U), (cx, cy + h * 0.25 * U), (cx - w * U, cy - h * 0.3 * U)]
                d.polygon(pts, fill=cor + (255,))
            elif op[1] == "m":
                _, _, y0, y1, a0, a1, sx0, cor_esc, cor, sway = op
                n = 10
                esq, dir_ = [], []
                for i in range(n + 1):
                    t = i / n
                    y = y0 + (y1 - y0) * t
                    a = a0 + (a1 - a0) * t
                    cx, cy = P(sx0 + sway * (1 - t), y)
                    esq.append((cx - a * U, cy))
                    dir_.append((cx + a * U, cy))
                cxb, cyb = P(sx0 + sway, y0)
                hem = [(cxb + math.cos(k / 16 * math.pi) * a0 * U, cyb + math.sin(k / 16 * math.pi) * a0 * 0.42 * U) for k in range(17)]
                d.polygon(esq + dir_[::-1] + hem, fill=cor_esc + (255,))
                # faixa mais clara à esquerda (luz) e dobras
                n2 = [(x + (cxb - x) * 0.0 + a * 0, y) for (x, y) in esq]
                luz = [(esq[i][0] + (dir_[i][0] - esq[i][0]) * 0.08, esq[i][1]) for i in range(n + 1)] + \
                      [(esq[i][0] + (dir_[i][0] - esq[i][0]) * 0.62, esq[i][1]) for i in range(n, -1, -1)]
                d.polygon(luz, fill=cor + (255,))
                for k in (0.3, 0.55, 0.8):
                    xs = [(esq[i][0] + (dir_[i][0] - esq[i][0]) * k, esq[i][1]) for i in range(1, n + 1)]
                    d.line(xs, fill=cor_esc + (255,), width=int(1.2 * SS))
                d.line(hem, fill=OURO + (255,), width=int(2.4 * SS))
            else:
                _, _, pts, cor = op
                pp = [P(*p) for p in pts]
                d.polygon(pp, fill=cor + (255,))
        # contorno escuro de ~1,5 px finais
        a = im.split()[3]
        borda = a.filter(ImageFilter.MaxFilter(2 * int(1.6 * SS) + 1))
        cont = Image.new("RGBA", im.size, (24, 14, 40, 255))
        cont.putalpha(borda)
        out = Image.alpha_composite(cont, im)
        if self.tint:
            tl = Image.new("RGBA", im.size, self.tint + (0,))
            r, g, b, al = out.split()
            ov = Image.new("RGBA", im.size, self.tint + (255,))
            out = Image.composite(Image.blend(out, ov, 0.55), out, al.point(lambda v: 255 if v > 0 else 0))
        if alfa < 1.0:
            r, g, b, al = out.split()
            out.putalpha(al.point(lambda v: int(v * alfa)))
        return out

def brilho_cristal(im_cena, pos_px, forca):
    """Aura do cristal (somada por cima, com brilho aditivo)."""
    glow = Image.new("RGBA", (L * SS, L * SS), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    forca = min(forca, 1.6)
    cx, cy = pos_px
    for k in range(5, 0, -1):
        r = (2.5 + k * 2.2 * forca) * U
        g.ellipse([cx - r, cy - r, cx + r, cy + r], fill=CRISTAL + (int(9 * forca),))
    glow = glow.filter(ImageFilter.GaussianBlur(3 * SS))
    return Image.alpha_composite(glow, im_cena)

def montar(ang, p):
    """p: dicionário de pose. Retorna imagem final 128x128 do quadro."""
    c = Cena(ang, tint=p.get("tint"))
    bob = p.get("bob", 0.0)
    lean = p.get("lean", 0.0)      # corpo inclina para a frente
    fy = p.get("fy", 0.0)          # corpo abaixado
    sway = p.get("sway", 0.0)
    pe = p.get("pe", (0, 0))       # fase dos pés: (z do pé esq, z do pé dir)
    lift = p.get("lift", (0, 0))
    zc = lean * 0.9
    # botas
    c.elipse(-3.8, 1.5 + pe[0], 2.2 + lift[0], 3.4, 2.4, BOTA)
    c.elipse(3.8, 1.5 + pe[1], 2.2 + lift[1], 3.4, 2.4, BOTA)
    # manto (barra dourada embaixo)
    c.manto(4.5 + fy, 28 + fy + bob, 10.8 + sway * 0.1, 7.6, zc * 0.5, ROXO_ESC, ROXO, sway=sway * 0.4)
    # cinto e ombros
    c.elipse(0, zc * 0.6 + 0.4, 16.5 + fy + bob * 0.6, 7.3, 1.35, OURO, bias=0.3, brilho=False)
    c.elipse(0, zc, 28.5 + fy + bob, 8.4, 4.6, ROXO_CLARO)
    # gema do peito
    c.elipse(0, zc + 5.5, 22 + fy + bob, 1.5, 1.8, CRISTAL, bias=0.6, brilho=False)
    # braço esquerdo (dele) solto
    ombro_e = (-8.4, zc, 28 + fy + bob)
    mao_e = p.get("mao_e", (-9.2, zc + 1.5, 18 + fy + bob * 0.6))
    c.linha(ombro_e, mao_e, 2.6, ROXO, bias=-0.2)
    c.elipse(*mao_e[:1], mao_e[1], mao_e[2], 2.3, 2.3, PELE, bias=-0.1, brilho=False)
    # braço direito com o cajado
    ombro_d = (8.4, zc, 28 + fy + bob)
    mao_d = p.get("mao_d", (9.2, zc + 3.0, 19 + fy + bob * 0.6))
    c.linha(ombro_d, mao_d, 2.6, ROXO, bias=0.2)
    # cajado: base e topo definidos pela mão e pela inclinação
    incl = p.get("cajado", (0.0, 0.0))   # deslocamento do topo em (x, z)
    base = (mao_d[0] + incl[0] * -0.4, mao_d[1] + incl[1] * -0.4, 0 + fy * 0.4)
    topo = (mao_d[0] + incl[0], mao_d[1] + incl[1], 50 + fy * 0.4 + p.get("cajado_y", 0.0))
    c.linha(base, topo, 1.1, CAJADO, bias=0.25, passos=12)
    c.elipse(mao_d[0], mao_d[1], mao_d[2], 2.4, 2.4, PELE, bias=0.4, brilho=False)
    # cristal do cajado: garra + losango
    tx, tz, ty = topo
    c.elipse(tx, tz, ty - 0.5, 2.2, 1.6, OURO, bias=0.3, brilho=False)
    cr = p.get("cristal", 1.0)
    c.diamante(tx, tz, ty + 3.2, 2.8, 5.2 * cr, CRISTAL, bias=0.35)
    c.diamante(tx, tz, ty + 3.2, 1.2, 4.0 * cr, (235, 255, 255), bias=0.36)
    # cabeça: capuz atrás, rosto, bordas do capuz
    hy = 38.0 + fy + bob
    hz = zc * 1.2
    c.elipse(0, hz - 2.5, hy + 0.5, 11.2, 11.0, CAPUZ)                      # casca do capuz
    c.poli([(0, hz - 5, hy + 8), (4, hz - 5, hy + 9), (0, hz - 12 - lean * 0.3, hy + 22)], CAPUZ, bias=-0.1)   # ponta
    c.poli([(0, hz - 5, hy + 8), (-4, hz - 5, hy + 9), (0, hz - 12 - lean * 0.3, hy + 22)], CAPUZ, bias=-0.1)
    c.elipse(0, hz + 3.5, hy - 1.0, 7.6, 7.6, PELE)                         # rosto
    c.elipse(-8.0, hz + 0.5, hy, 3.6, 8.6, CAPUZ, bias=0.2)                 # borda esq. do capuz
    c.elipse(8.0, hz + 0.5, hy, 3.6, 8.6, CAPUZ, bias=0.2)                  # borda dir.
    c.elipse(0, hz + 4.2, hy + 7.4, 8.4, 3.0, CAPUZ, bias=0.25)             # aba sobre a testa
    olho = p.get("olho", 1.0)
    for sx_ in (-3.1, 3.1):
        c.elipse(sx_, hz + 10.4, hy - 1.2, 1.35, 1.7 * olho, OLHO, bias=0.5, brilho=False)
    c.elipse(0, hz + 10.6, hy - 5.2, 1.5, 0.7, mix(PELE, -0.25), bias=0.5, brilho=False)  # boca
    im = c.desenhar()
    # aura do cristal
    sx, dep, yy = c.proj(tx, tz, ty + 3.5)
    ox, oy = PIVO[0] * SS, PIVO[1] * SS
    im = brilho_cristal(im, (ox + sx * U, oy - yy * U), p.get("aura", 1.0))
    return im

def sombra_final(im):
    return im.resize((L, L), Image.LANCZOS)

def frames_anim(nome):
    f = []
    if nome == "idle":
        n = 6
        for i in range(n):
            t = i / n
            f.append(dict(bob=math.sin(2 * math.pi * t) * 0.9, sway=math.sin(2 * math.pi * t) * 0.8,
                          cajado=(0.0, 0.3 * math.sin(2 * math.pi * t)), aura=0.8 + 0.4 * math.sin(2 * math.pi * t + 1)))
    elif nome == "run":
        n = 8
        for i in range(n):
            t = i / n
            s = math.sin(2 * math.pi * t)
            c = math.cos(2 * math.pi * t)
            f.append(dict(bob=abs(c) * 1.8, lean=1.4, pe=(s * 4.2, -s * 4.2), lift=(max(0, c) * 2.2, max(0, -c) * 2.2),
                          sway=-s * 1.4, mao_e=(-9.4, 2.5 - s * 3.0, 19), mao_d=(9.2, 3.0 + s * 2.0, 20 + abs(c)),
                          cajado=(0.0, 1.8 + s * 0.8), aura=1.0))
    elif nome == "attack":
        # 0-1 recolhe, 2-3 prepara, 4 solta (evento), 5 volta
        poses = [
            dict(mao_d=(9.4, 0.5, 21), cajado=(0.0, -2.0), aura=1.2, lean=-0.6),
            dict(mao_d=(9.6, -1.0, 24), cajado=(0.0, -3.5), aura=1.6, lean=-1.0, bob=0.5),
            dict(mao_d=(9.6, 1.0, 27), cajado=(0.0, -1.0), aura=2.0, lean=0.0, cristal=1.2),
            dict(mao_d=(9.4, 4.5, 26), cajado=(0.0, 2.5), aura=2.4, lean=1.0, cristal=1.3),
            dict(mao_d=(9.0, 8.5, 24), cajado=(0.0, 5.5), aura=3.2, lean=2.0, cristal=1.4, mao_e=(-7, 6, 24)),
            dict(mao_d=(9.2, 4.0, 21), cajado=(0.0, 2.0), aura=1.5, lean=0.8),
        ]
        f = poses
    elif nome == "dodge":
        for i in range(6):
            t = i / 5
            f.append(dict(lean=3.0, fy=-4.5 + 2 * t, bob=-1.0, pe=(-3, 4), lift=(2, 0), sway=-2.5,
                          mao_e=(-9.5, 5, 22), mao_d=(9.5, 6, 24), cajado=(0.0, 6.0), aura=0.7))
    elif nome == "hit":
        f = [dict(lean=-2.5, bob=-1.5, olho=0.35, tint=(255, 255, 255), cajado=(0, -3.0), mao_d=(9.2, 0.5, 20)),
             dict(lean=-3.5, bob=-1.0, olho=0.35, cajado=(0, -4.0), mao_d=(9.2, -0.5, 20)),
             dict(lean=-1.0, bob=0.0, olho=0.6)]
    elif nome == "death":
        n = 8
        for i in range(n):
            f.append(dict(lean=-1.0 - i * 0.2, bob=-i * 0.2, olho=0.2, aura=max(0.0, 1.0 - i * 0.14)))
    return f

def girar_morte(im, i, n=8):
    """Quadros de morte: cai de lado em torno dos pés e escurece."""
    k = min(1.0, i / (n - 3))
    ease = k * k * (3 - 2 * k)
    ang = -88 * ease
    pivo = (PIVO[0] * SS, PIVO[1] * SS)
    esc = 1.0 - 0.22 * ease
    im = im.resize((int(im.width * esc), int(im.height * esc)), Image.BICUBIC)
    base = Image.new("RGBA", (L * SS, L * SS), (0, 0, 0, 0))
    base.alpha_composite(im, (int(pivo[0] - pivo[0] * esc), int(pivo[1] - pivo[1] * esc)))
    r = base.rotate(ang, resample=Image.BICUBIC, center=pivo, translate=(int(-30 * ease * SS), int(8 * ease * SS)))
    if i >= n - 3:
        shade = 1.0 - 0.18 * (i - (n - 4))
        r.putalpha(r.split()[3].point(lambda v: int(v * (0.55 + 0.45 * shade))))
    return r

def gerar(pasta):
    os.makedirs(pasta, exist_ok=True)
    for nome in ["idle", "run", "attack", "dodge", "hit", "death"]:
        poses = frames_anim(nome)
        n = len(poses)
        folha = Image.new("RGBA", (L * n, L * len(DIRS)), (0, 0, 0, 0))
        for r, ang in enumerate(DIRS):
            for q, p in enumerate(poses):
                im = montar(ang, p)
                if nome == "death":
                    im = girar_morte(im, q, n)
                if nome == "dodge":
                    # rastro: cópia mais clara atrás do mago, na direção contrária ao giro
                    ghost = montar(ang, dict(p, lean=p["lean"] - 2, pe=(0, 0)))
                    ghost = ghost.filter(ImageFilter.GaussianBlur(2 * SS))
                    ghost.putalpha(ghost.split()[3].point(lambda v: int(v * 0.35)))
                    sx, _, _ = Cena(ang).proj(0, -1, 0)
                    ghost = ImageChops.offset(ghost, int(-sx * 14 * SS) if abs(sx) > 0.05 else 0, int(-14 * SS) if abs(sx) <= 0.05 else 0)
                    im = Image.alpha_composite(ghost, im)
                folha.paste(sombra_final(im), (q * L, r * L))
        folha.save(os.path.join(pasta, f"mago_{nome}.png"))
        print("ok", nome, folha.size)

if __name__ == "__main__":
    gerar(sys.argv[1] if len(sys.argv) > 1 else "mago")
